import asyncio
import logging
import random
from datetime import datetime, time
import pytz
import numpy as np
import pandas as pd
import yfinance as yf

from config import WATCHLIST, RISK_MAX_EXPOSURE, MIN_RR_RATIO, DEMO_CAPITAL, BROKER, ENFORCE_ENTRY_WINDOW, MARKET_TIMEZONE
from database import get_connection, log_event
from broker import broker_manager
from telegram_service import telegram_service

logger = logging.getLogger(__name__)

def is_market_in_entry_window(check_weekend: bool = True) -> bool:
    tz = pytz.timezone('US/Eastern')
    now_dt = datetime.now(tz)
    now = now_dt.time()
    
    # Proteger fines de semana si está habilitado
    if check_weekend and now_dt.weekday() >= 5:
        return False
    
    # Ventana matutina principal (9:45 AM a 11:15 AM)
    morning_open = time(9, 45)
    morning_close = time(11, 15)
    
    # Ventana vespertina opcional (2:00 PM a 3:30 PM)
    afternoon_open = time(14, 0)
    afternoon_close = time(15, 30)
    
    return (morning_open <= now <= morning_close) or (afternoon_open <= now <= afternoon_close)

class StrategyEngine:
    def __init__(self):
        self.is_running = False
        self._task = None
        self.scan_interval = 25  # segundos entre escaneos en modo activo
        self.last_scan_time = None
        self.active_signals_count = 0
        self.current_session = "Standby"
        self.in_entry_window = False

    def is_in_entry_window(self) -> bool:
        return is_market_in_entry_window()

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._scan_loop())
            logger.info("StrategyEngine: Bucle de escaneo cuantitativo iniciado...")
            log_event("INFO", "Motor de Estrategias Híbridas iniciado.")

    def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
        log_event("WARNING", "Motor de Estrategias pausado.")

    async def _scan_loop(self):
        # Generar un primer barrido
        await self.scan_market()
        while self.is_running:
            try:
                await asyncio.sleep(self.scan_interval)
                await self.scan_market()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en bucle de escaneo: {e}")
                await asyncio.sleep(10)

    async def scan_market(self, force: bool = False):
        """Descarga datos recientes y evalúa las 4 estrategias híbridas en los símbolos con filtro de sesión."""
        ny_tz = pytz.timezone(MARKET_TIMEZONE)
        now_ny = datetime.now(ny_tz)
        now_time = now_ny.time()
        self.last_scan_time = now_ny.strftime("%H:%M:%S EST")

        in_window = is_market_in_entry_window()
        self.in_entry_window = in_window

        # Identificación de la fase de la sesión
        morning_open = time(9, 45)
        morning_close = time(11, 15)
        afternoon_open = time(14, 0)
        afternoon_close = time(15, 30)

        if morning_open <= now_time <= morning_close:
            self.current_session = "Ventana Matutina (9:45 - 11:15 EST - Tendencia Óptima)"
            min_score = 68.0
        elif afternoon_open <= now_time <= afternoon_close:
            self.current_session = "Ventana Vespertina (14:00 - 15:30 EST - Power Window)"
            min_score = 70.0
        elif time(9, 30) <= now_time < morning_open:
            self.current_session = "Apertura Wall St (9:30 - 9:45 EST - Esperando Ventana)"
            min_score = 85.0
        elif morning_close < now_time < afternoon_open:
            self.current_session = "Almuerzo Wall St (11:15 - 14:00 EST - Filtro Chop)"
            min_score = 80.0
        elif afternoon_close < now_time < time(15, 55):
            self.current_session = "Pre-Cierre (15:30 - 15:55 EST - Fuera de Ventana)"
            min_score = 85.0
        elif time(15, 55) <= now_time < time(16, 0):
            self.current_session = "Cierre de Mercado (Auto-Square Off Activo)"
            return  # Liquidación obligatoria, no abrir nuevas posiciones
        else:
            self.current_session = "Fuera de Horario Regular (Standby / 24/7)"
            min_score = 68.0

        logger.info(f"Escaneando [{self.current_session}] | Ventana Entrada: {'ABIERTA' if in_window else 'CERRADA'} a las {self.last_scan_time}...")

        # Filtro estricto de entrada institucional: Solo abrir trades en la ventana
        if ENFORCE_ENTRY_WINDOW and not in_window and not force:
            logger.info(f"Filtro de Horario: Fuera de ventana de entrada (9:45-11:15 o 14:00-15:30 EST). Monitoreo en espera.")
            return

        # Obtener pesos actuales de las estrategias de la base de datos
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, weight, win_rate FROM strategy_metrics")
        weights = {row["name"]: float(row["weight"]) for row in cursor.fetchall()}
        conn.close()

        # Seleccionar aleatoriamente o ciclar por los símbolos de la watchlist
        symbol = random.choice(WATCHLIST)
        await self.evaluate_symbol(symbol, weights, min_score)

    async def evaluate_symbol(self, symbol: str, weights: dict, min_score: float = 68.0):
        """Descarga velas intradía de yfinance y calcula indicadores técnicos."""
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: yf.download(
                tickers=symbol,
                period="2d",
                interval="5m",
                progress=False
            ))
            if df.empty or len(df) < 30:
                return

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0].lower() for c in df.columns]
            else:
                df.columns = [c.lower() for c in df.columns]

            close = df["close"].values
            volume = df["volume"].values
            current_price = float(close[-1])

            # 1. Medias Móviles Exponenciales (EMA 20, 50)
            ema20 = pd.Series(close).ewm(span=20).mean().values[-1]
            ema50 = pd.Series(close).ewm(span=50).mean().values[-1]

            # 2. RSI (14)
            delta = pd.Series(close).diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / (loss + 1e-9)
            rsi = float((100 - (100 / (1 + rs))).values[-1])

            # 3. Bandas de Bollinger (20, 2)
            sma20 = pd.Series(close).rolling(20).mean().values[-1]
            std20 = pd.Series(close).rolling(20).std().values[-1]
            upper_band = sma20 + (2 * std20)
            lower_band = sma20 - (2 * std20)

            # 4. Volumen relativo
            avg_vol = float(np.mean(volume[-20:]))
            curr_vol = float(volume[-1])
            vol_surge = curr_vol > (1.3 * avg_vol)

            # Evaluación Cuantitativa de Estrategias
            signals_found = []

            # Estrategia 1: Trend Following (Cruce EMA y tendencia)
            if ema20 > ema50 and current_price > ema20:
                signals_found.append({
                    "strategy": "Tendencia & Cruce EMA 20/50/200",
                    "code": "trend_following",
                    "side": "BUY",
                    "score": 75 * weights.get("trend_following", 1.0),
                    "rationale": f"Precio (${current_price:.2f}) sobre EMA20 y EMA20 > EMA50 en expansión alcista."
                })
            elif ema20 < ema50 and current_price < ema20:
                signals_found.append({
                    "strategy": "Tendencia & Cruce EMA 20/50/200",
                    "code": "trend_following",
                    "side": "SELL",
                    "score": 75 * weights.get("trend_following", 1.0),
                    "rationale": f"Precio (${current_price:.2f}) bajo EMA20 y EMA20 < EMA50 en estructura bajista."
                })

            # Estrategia 2: Mean Reversion (RSI + Bollinger)
            if rsi < 36 and current_price <= lower_band * 1.01:
                signals_found.append({
                    "strategy": "Reversión a la Media (RSI + Bollinger)",
                    "code": "mean_reversion",
                    "side": "BUY",
                    "score": 85 * weights.get("mean_reversion", 1.0),
                    "rationale": f"RSI sobrevendido ({rsi:.1f}) tocando Banda Inferior de Bollinger (${lower_band:.2f})."
                })
            elif rsi > 68 and current_price >= upper_band * 0.99:
                signals_found.append({
                    "strategy": "Reversión a la Media (RSI + Bollinger)",
                    "code": "mean_reversion",
                    "side": "SELL",
                    "score": 85 * weights.get("mean_reversion", 1.0),
                    "rationale": f"RSI sobrecomprado ({rsi:.1f}) rechazando Banda Superior de Bollinger (${upper_band:.2f})."
                })

            # Estrategia 3: Ruptura de Liquidez & Order Block con Volumen
            if vol_surge and current_price > float(np.max(close[-6:-1])):
                signals_found.append({
                    "strategy": "Ruptura de Liquidez & Order Blocks",
                    "code": "liquidity_breakout",
                    "side": "BUY",
                    "score": 80 * weights.get("liquidity_breakout", 1.0),
                    "rationale": f"Ruptura de máximo reciente con volumen institucional +{(curr_vol/avg_vol - 1)*100:.0f}%."
                })

            if not signals_found:
                return

            # Seleccionar la señal con mayor puntuación ponderada
            best_sig = max(signals_found, key=lambda x: x["score"])
            if best_sig["score"] < min_score:
                return  # No alcanza el umbral de confianza de la sesión

            confidence = min(96.0, best_sig["score"])

            # FIX #1: Verificar si ya hay posición abierta en broker (evitar colisiones)
            if broker_manager.has_open_position(symbol):
                return  # Ya hay posición abierta, no abrir otra

            # Comprobar si ya existe una señal idéntica PENDIENTE en los últimos 15 min
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM signals 
                WHERE symbol = ? AND status = 'PENDIENTE'
            """, (symbol,))
            if cursor.fetchone()[0] > 0:
                conn.close()
                return

            # Calcular Gestión de Riesgo (Risk:Reward mínimo 1:2)
            risk_dist = max(current_price * 0.008, 0.10)  # Mínimo $0.10 de riesgo  # 0.8% de riesgo
            reward_dist = risk_dist * MIN_RR_RATIO

            if best_sig["side"] == "BUY":
                stop_loss = round(current_price - risk_dist, 2)
                take_profit = round(current_price + reward_dist, 2)
            else:
                stop_loss = round(current_price + risk_dist, 2)
                take_profit = round(current_price - reward_dist, 2)

            # Evaluación de Salud Backtest (Walk-Forward Integrity Check)
            from backtest_validator import backtest_validator
            val_health = backtest_validator.evaluate_health()
            if val_health.get("action") == "PAUSE_TRADING":
                logger.critical(f"BacktestValidator: Nueva orden rechazada. {val_health.get('reason')}")
                log_event("ERROR", f"BacktestValidator Circuit Breaker: {val_health.get('reason')}")
                return

            # Cálculo de tamaño de posición (Position Sizing) con multiplicador dinámico
            account = broker_manager.get_account_summary()
            capital = account["cash"]
            risk_amount = capital * RISK_MAX_EXPOSURE
            base_qty = max(1, int(risk_amount / (abs(current_price - stop_loss) + 1e-4)))
            
            # Limitar tamaño máximo para diversificación
            max_capital_allocation = capital * 0.15
            if (base_qty * current_price) > max_capital_allocation:
                base_qty = max(1, int(max_capital_allocation / current_price))

            # Aplicar multiplicador del BacktestValidator (1.0x saludable, 0.5x degradado)
            size_mult = val_health.get("size_multiplier", 1.0)
            shares_qty = max(1, int(base_qty * size_mult))

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # FIX #4: Validar que SL y TP son coherentes antes de insertar
            assert stop_loss > 0 and take_profit > 0, f"SL/TP inválidos: SL={stop_loss}, TP={take_profit}"
            if best_sig["side"] == "BUY":
                assert stop_loss < current_price < take_profit, f"Geometría BUY inválida: SL={stop_loss} < Price={current_price} < TP={take_profit}"
            else:
                assert take_profit < current_price < stop_loss, f"Geometría SELL inválida: TP={take_profit} < Price={current_price} < SL={stop_loss}"
            rr_actual = round(abs(take_profit - current_price) / abs(current_price - stop_loss), 1)
            logger.info(f"Señal {symbol} {best_sig['side']}: SL=${stop_loss:.2f} TP=${take_profit:.2f} R:R=1:{rr_actual}")

            cursor.execute("""
                INSERT INTO signals 
                (symbol, side, qty, price, stop_loss, take_profit, rr_ratio, strategy, rationale, confidence, status, broker, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, best_sig["side"], shares_qty, current_price,
                stop_loss, take_profit, MIN_RR_RATIO, best_sig["strategy"],
                best_sig["rationale"], confidence, "PENDIENTE", BROKER.upper(), now_str
            ))
            sig_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # Enviar notificación a Telegram de inmediato
            sig_payload = {
                "id": sig_id,
                "symbol": symbol,
                "side": best_sig["side"],
                "qty": shares_qty,
                "price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "rr_ratio": MIN_RR_RATIO,
                "strategy": best_sig["strategy"],
                "rationale": best_sig["rationale"],
                "confidence": confidence
            }
            msg_id = await telegram_service.send_signal_alert(sig_payload)

            if msg_id:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE signals SET telegram_message_id = ? WHERE id = ?", (msg_id, sig_id))
                conn.commit()
                conn.close()

            log_event("SUCCESS", f"Nueva oportunidad detectada: {best_sig['side']} {shares_qty} {symbol} @ ${current_price:.2f} [{best_sig['strategy']}]")

        except Exception as e:
            logger.error(f"Error evaluando símbolo {symbol}: {e}")

strategy_engine = StrategyEngine()
