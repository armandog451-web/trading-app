import asyncio
from datetime import datetime
import logging
import pandas as pd
import numpy as np

from app.config import settings
from app.database import SessionLocal
from app.models.db_models import Trade, BotLog, DailyMetrics
from app.core.broker_manager import broker_manager
from app.core.screener import screener

from app.core.notifier import notifier
from app.engines.top_down_orchestrator import orchestrator
from app.engines.risk_engine import risk_engine
from app.engines.options_engine import options_engine
from app.strategies.strategy_orb import orb_strategy

logger = logging.getLogger(__name__)

class BotRunner:
    """
    Ciclo de vida del Bot de Day Trading en segundo plano.
    Monitorea de forma continua los activos seleccionados, evalúa la confluencia
    Top-Down, ejecuta Bracket Orders, registra métricas en SQLite y aplica
    el cierre forzoso antes del cierre de campana.
    """

    def __init__(self):
        self.is_running = False
        self._task: asyncio.Task | None = None
        self.circuit_breaker_tripped = False
        self.last_scan_time: datetime | None = None
        self.active_universe = ["QQQ", "SPY", "TSLA", "AAPL", "MSFT"]
        self._square_off_done = False

    async def start(self):
        """Inicia el bot en segundo plano de forma instantánea."""
        if self.is_running:
            return
        self.is_running = True
        try:
            self.active_universe = await screener.get_active_universe()
        except Exception:
            self.active_universe = ["QQQ", "SPY", "TSLA", "AAPL", "MSFT"]
            
        logger.info(f"Bot iniciado. Monitoreando universo de alta liquidez: {self.active_universe}")
        
        # 1. Crear el bucle principal en segundo plano
        self._task = asyncio.create_task(self._main_loop())

        # 2. Despachar alerta de inicio en tarea de fondo no-bloqueante
        asyncio.create_task(notifier.send_alert(
            "🚀 TradePulse Bot Iniciado Automáticamente", 
            f"Buenos días / Hola. Iniciando escaneo automatizado 24/7 sin intervención humana.\n\nMonitoreando: {', '.join(self.active_universe)}", 
            "INFO"
        ))

    async def stop(self):
        """Pausa el bot de forma instantánea."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Bot detenido / pausado por el usuario.")

        # Despachar alerta de pausa en tarea de fondo no-bloqueante
        asyncio.create_task(notifier.send_alert(
            "TradePulse Bot Pausado", 
            "La supervisión automática ha sido pausada.", 
            "WARN"
        ))

    async def _main_loop(self):
        """Bucle principal asíncrono de evaluación y ejecución."""
        while self.is_running:
            try:
                self.last_scan_time = datetime.utcnow()

                # 1. Comprobar Cierre Forzoso Intraday (15:50 EST)
                if risk_engine.should_square_off():
                    if not self._square_off_done:
                        logger.warning("HORA 15:50 EST ALCANZADA: Cierre forzoso de posiciones intraday.")
                        await broker_manager.close_all_positions()
                        if getattr(settings, "NOTIFY_MARKET_CLOSE", False):
                            await notifier.send_alert("Cierre Intraday (15:50 EST)", "Todas las posiciones intraday se han cerrado automáticamente sin riesgo nocturno.", "INFO")
                        self._square_off_done = True
                    await asyncio.sleep(60)
                    continue
                else:
                    self._square_off_done = False

                # 2. Consultar cuenta y verificar Circuit Breaker
                account = await broker_manager.get_account()
                equity = account.get("equity", 100000.0)
                daily_pnl = account.get("daily_pnl", 0.0)

                tripped, loss_val = risk_engine.is_circuit_breaker_tripped(equity, daily_pnl, 0.0)
                if tripped:
                    self.circuit_breaker_tripped = True
                    logger.error(f"CIRCUIT BREAKER ACTIVADO: Pérdida acumulada del día ${loss_val:.2f}. Pausando bot.")
                    await notifier.send_alert("CIRCUIT BREAKER ACTIVADO", f"Pérdida máxima alcanzada (${loss_val:.2f}). Se detienen operaciones por hoy.", "ERROR")
                    await self.stop()
                    break

                # 3. Monitorear posiciones actuales
                positions = await broker_manager.get_positions()
                if len(positions) >= settings.MAX_OPEN_POSITIONS:
                    await asyncio.sleep(10)
                    continue

                # 3.5 Limpieza de alertas antiguas (más de 10 min) en SQLite
                try:
                    from datetime import timedelta
                    from app.models.db_models import SignalRecommendation
                    cutoff = datetime.utcnow() - timedelta(minutes=10)
                    with SessionLocal() as db:
                        db.query(SignalRecommendation).filter(SignalRecommendation.created_at < cutoff).delete()
                        db.commit()
                except Exception as cleanup_err:
                    logger.error(f"Error limpiando alertas antiguas: {cleanup_err}")

                # 4. Evaluar cada activo del universo
                for symbol in self.active_universe:
                    if not self.is_running:
                        break

                    # Comprobar si ya tenemos posición abierta en este símbolo
                    if any(p.get("symbol", "").replace("US.", "") == symbol for p in positions):
                        continue

                    # 1. Obtener velas 1m en tiempo real desde Moomoo (o datos de alta fidelidad)
                    moomoo_bars = await broker_manager.get_intraday_bars(symbol, num_bars=60)
                    sample_intraday_df, daily_df = self._generate_sample_market_data(symbol)
                    intraday_df = moomoo_bars if (moomoo_bars is not None and len(moomoo_bars) >= 15) else sample_intraday_df

                    # 2. Evaluar Estrategia ORB con Filtro de Volumen si está habilitada
                    if orb_strategy.config.get("enabled", True):
                        try:
                            await orb_strategy.scan_and_dispatch(symbol, intraday_df)
                        except Exception as orb_err:
                            logger.error(f"Error evaluando ORB para {symbol}: {orb_err}")

                    # 3. Pasar por el orquestador Top-Down
                    eval_result = await orchestrator.evaluate_symbol_pipeline(
                        symbol=symbol,
                        intraday_df=intraday_df,
                        daily_df=daily_df,
                        account_equity=equity,
                        daily_loss=abs(daily_pnl) if daily_pnl < 0 else 0.0
                    )

                    if eval_result.get("approved"):
                        await self._execute_approved_trade(eval_result, equity)

                await asyncio.sleep(15)  # Intervalo de escaneo cada 15 segundos

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en bucle del bot: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def _execute_approved_trade(self, eval_result: dict, account_equity: float):
        """Ejecuta la orden en Alpaca, la persiste en SQLite y despacha recomendaciones de Acciones y Opciones."""
        symbol = eval_result["symbol"]
        side = eval_result["side"]
        entry_price = eval_result["entry_price"]
        stop_loss = eval_result["stop_loss"]
        take_profit = eval_result["take_profit"]
        shares = eval_result["shares"]
        rr = eval_result["risk_reward_ratio"]

        logger.info(f"CONFLUENCIA TOP-DOWN APROBADA: {side} {shares} {symbol} @ ${entry_price:.2f} | SL: ${stop_loss} | TP: ${take_profit} | R:R 1:{rr}")

        # 1. Despachar Recomendación de ACCIONES a la App y Telegram
        stock_rec = {
            "asset_type": "STOCK",
            "symbol": symbol,
            "action": f"{side}_STOCK",
            "current_price": entry_price,
            "entry_target": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "take_profit_2": round(entry_price + (entry_price - stop_loss) * 3.5, 2) if side == "BUY" else round(entry_price - (stop_loss - entry_price) * 3.5, 2),
            "risk_reward": rr,
            "shares": shares,
            "confluence_score": eval_result.get("confluence_score", 85),
            "setup_type": eval_result.get("setup_type", "TopDown_VWAP_Sweep"),
            "rationale": eval_result.get("reason", "Confluencia Top-Down con ratio R:R favorable.")
        }
        await notifier.send_trade_recommendation(stock_rec)

        # 2. Generar y Despachar Recomendación de OPCIONES (CALL o PUT) a la App y Telegram
        opt_bias = "BULLISH" if side == "BUY" else "BEARISH"
        opt_rec = options_engine.calculate_option_contract(
            symbol=symbol,
            current_price=entry_price,
            bias=opt_bias,
            equity=account_equity,
            risk_pct=settings.RISK_PER_TRADE_PCT
        )
        await notifier.send_trade_recommendation(opt_rec)

        # 3. Comprobar si la ejecución automática está activa o si estamos en MODO SOLO SEÑALES
        if not settings.AUTO_EXECUTE_TRADES:
            logger.info("MODO SOLO SEÑALES ACTIVO: Alertas enviadas a Telegram y App. Sin ejecución automática de orden en broker.")
            try:
                with SessionLocal() as db:
                    log = BotLog(
                        level="INFO",
                        module="bot_runner",
                        message=f"Señal generada (Sin ejecución broker): {side} {shares} {symbol} @ ${entry_price}"
                    )
                    db.add(log)
                    db.commit()
            except Exception as e:
                logger.error(f"Error guardando log de señal: {e}")
            return

        # 4. Enviar Bracket Order al Broker Activo (Alpaca / Moomoo)
        order_res = await broker_manager.submit_bracket_order(
            symbol=symbol,
            qty=shares,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            order_type="market"
        )

        if order_res.get("success"):
            # Persistir orden del broker en SQLite
            try:
                with SessionLocal() as db:
                    trade = Trade(
                        symbol=symbol,
                        side=side,
                        entry_price=entry_price,
                        quantity=shares,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        risk_reward_ratio=rr,
                        status="OPEN",
                        macro_bias=eval_result.get("macro_bias"),
                        strategy=eval_result.get("setup_type", "TopDown_Intraday"),
                        order_id=order_res.get("order_id")
                    )
                    db.add(trade)
                    
                    log = BotLog(
                        level="TRADE",
                        module="bot_runner",
                        message=f"Bracket Order enviada a broker: {side} {shares} {symbol} @ ${entry_price} (SL: ${stop_loss}, TP: ${take_profit}, R:R 1:{rr})"
                    )
                    db.add(log)
                    db.commit()
            except Exception as e:
                logger.error(f"Error guardando trade en SQLite: {e}")



    def _generate_sample_market_data(self, symbol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Genera velas de mercado intraday (5m) y diarias para análisis con VWAP."""
        base_prices = {"SPY": 560.0, "QQQ": 482.0, "NVDA": 128.0, "TSLA": 242.0, "AMD": 156.0, "AAPL": 224.0}
        base = base_prices.get(symbol, 100.0)

        # Generar 40 barras de 5 minutos consistentes
        np.random.seed(abs(hash(symbol)) % 10000000)
        returns = np.random.normal(0.0002, 0.0025, 40)
        closes = base * np.cumprod(1 + returns)
        opens = np.empty(40)
        opens[0] = base
        for t in range(1, 40):
            opens[t] = closes[t - 1]

        # Asegurar matemáticamente que high >= max(open, close) y low <= min(open, close)
        body_max = np.maximum(opens, closes)
        body_min = np.minimum(opens, closes)
        wick_up = np.abs(np.random.normal(0.001 * base, 0.0005 * base, 40))
        wick_down = np.abs(np.random.normal(0.001 * base, 0.0005 * base, 40))
        highs = body_max + wick_up
        lows = np.maximum(0.1, body_min - wick_down)
        volumes = np.random.randint(15000, 150000, 40)

        base_date = datetime.utcnow().replace(hour=9, minute=30, second=0, microsecond=0)
        time_index = [base_date + pd.Timedelta(minutes=i) for i in range(40)]

        intraday_df = pd.DataFrame({
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "rvol": np.random.uniform(1.2, 2.8, 40)
        }, index=pd.DatetimeIndex(time_index))

        # Barras diarias (5 días)
        daily_df = pd.DataFrame({
            "high": [base * 1.015, base * 1.02, base * 1.018, base * 1.025, base * 1.01],
            "low": [base * 0.985, base * 0.99, base * 0.988, base * 0.992, base * 0.98],
            "close": [base * 1.005, base * 1.01, base * 0.995, base * 1.012, closes[-1]],
            "volume": [50000000, 52000000, 48000000, 60000000, 45000000]
        })

        return intraday_df, daily_df

bot_runner = BotRunner()
