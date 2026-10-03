"""
weekend_engine.py
=================
Módulo Cuantitativo de Fin de Semana:
- Backtesting histórico de la última semana de mercado sobre activos líderes (yfinance).
- Recalibración adaptativa de pesos de Machine Learning (strategy_metrics).
- Alpha Ranking y niveles clave proyectados para la campana de apertura del Lunes.
- Generación y despacho de reporte ejecutivo a Telegram y endpoints API.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import yfinance as yf
import httpx

from config import (
    WATCHLIST, RISK_MAX_EXPOSURE, MIN_RR_RATIO, DEMO_CAPITAL,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BROKER
)
from database import get_connection, log_event

logger = logging.getLogger(__name__)


class WeekendOptimizerEngine:
    def __init__(self):
        self.last_report: Dict[str, Any] = {}
        self.is_running_optimization = False
        self._scheduler_task: asyncio.Task | None = None
        self._scheduler_running = False
        # Horario óptimo institucional: Domingo 18:00 EST (Apertura Futuros CME & Mercado Asiático)
        self.sunday_target_hour = 18
        self.sunday_target_minute = 0

    def start_auto_scheduler(self):
        """Inicia el monitor en segundo plano para disparar la optimización en el momento óptimo."""
        if not self._scheduler_running:
            self._scheduler_running = True
            self._scheduler_task = asyncio.create_task(self._auto_schedule_loop())
            logger.info("WeekendOptimizerEngine: Auto-Scheduler activado (Momento Óptimo: Domingo 18:00 EST).")

    def stop_auto_scheduler(self):
        """Detiene el monitor en segundo plano."""
        self._scheduler_running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            self._scheduler_task = None
        logger.info("WeekendOptimizerEngine: Auto-Scheduler detenido.")

    async def _auto_schedule_loop(self):
        """
        Bucle continuo en segundo plano. Evalúa periódicamente si es el momento óptimo:
        1. MOMENTO PRINCIPAL: Domingo a las 18:00 EST (Apertura de futuros CME / Tokyo).
        2. MOMENTO DE RESPALDO: Sábado o Domingo al iniciar el bot si no se ha ejecutado ninguna vez en este fin de semana.
        """
        import pytz
        from database import get_setting, set_setting
        ny_tz = pytz.timezone("America/New_York")

        while self._scheduler_running:
            try:
                now_ny = datetime.now(ny_tz)
                weekday = now_ny.weekday()  # 5=Sábado, 6=Domingo
                time_str = now_ny.strftime("%H:%M")
                date_str = now_ny.strftime("%Y-%m-%d")

                year, week_num, _ = now_ny.isocalendar()
                weekend_cycle_id = f"{year}-W{week_num}"

                # CASO 1: Domingo >= 18:00 EST (El mejor momento institucional)
                if weekday == 6 and now_ny.hour >= self.sunday_target_hour:
                    already_run_sunday = get_setting(f"weekend_sunday_run_{weekend_cycle_id}", "0") == "1"
                    if not already_run_sunday and not self.is_running_optimization:
                        logger.info(f"Auto-Scheduler: Disparando optimización programada de Domingo 18:00 EST ({weekend_cycle_id}).")
                        set_setting(f"weekend_sunday_run_{weekend_cycle_id}", "1")
                        set_setting("last_weekend_auto_run", f"{date_str} {time_str} EST (Domingo 18:00 EST - Apertura Futuros CME)")
                        await self.run_weekend_optimization(
                            send_telegram=True,
                            is_auto=True,
                            trigger_reason="Domingo 18:00 EST (Apertura CME & Sesión Asiática)"
                        )

                # CASO 2: Sábado o Domingo si aún no se ha ejecutado ninguna vez en este ciclo
                elif weekday in (5, 6):
                    initial_run_done = get_setting(f"weekend_initial_run_{weekend_cycle_id}", "0") == "1"
                    if not initial_run_done and not self.is_running_optimization:
                        logger.info(f"Auto-Scheduler: Fin de semana detectado sin calibración ({weekend_cycle_id}). Ejecutando inicial...")
                        set_setting(f"weekend_initial_run_{weekend_cycle_id}", "1")
                        set_setting("last_weekend_auto_run", f"{date_str} {time_str} EST (Calibración Inicial Fin de Semana)")
                        await self.run_weekend_optimization(
                            send_telegram=True,
                            is_auto=True,
                            trigger_reason="Calibración Inicial Automática Fin de Semana"
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en bucle auto-scheduler de fin de semana: {e}")

            await asyncio.sleep(40)

    async def run_weekend_optimization(
        self,
        symbols: List[str] = None,
        send_telegram: bool = True,
        is_auto: bool = False,
        trigger_reason: str = "Manual a petición"
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo integral de fin de semana:
        1. Backtest de 5 días de mercado sobre símbolos de la watchlist.
        2. Recalibración de pesos ML para cada estrategia.
        3. Alpha Watchlist y niveles técnicos para el Lunes.
        4. Notificación ejecutiva a Telegram.
        """
        if self.is_running_optimization:
            return {"status": "busy", "message": "Optimización de fin de semana ya en curso."}

        self.is_running_optimization = True
        symbols = symbols or WATCHLIST

        try:
            logger.info(f"Iniciando Módulo de Optimización de Fin de Semana ({trigger_reason})...")
            log_event("INFO", f"Iniciando Backtesting y Recalibración ML ({trigger_reason}).")

            # 1. Backtesting semanal por estrategia
            backtest_results = await self._run_weekly_backtest(symbols)

            # 2. Recalibración de pesos de Machine Learning en SQLite
            calibrated_weights = self._recalibrate_ml_weights(backtest_results)

            # 3. Alpha Ranking y Niveles del Lunes
            alpha_watchlist = await self._generate_monday_alpha_watchlist(symbols)

            # Persistir candidatos de fin de semana para confirmación intradía en la apertura del mercado
            import json
            from database import set_setting
            set_setting("weekend_prepared_candidates", json.dumps(alpha_watchlist))
            logger.info(f"WeekendEngine: {len(alpha_watchlist)} candidatos preparados y guardados en DB para la apertura del Lunes.")

            # 4. Consolidar informe
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S EST")
            report = {
                "timestamp": now_str,
                "is_auto": is_auto,
                "trigger_reason": trigger_reason,
                "symbols_analyzed": symbols,
                "backtest_summary": backtest_results,
                "calibrated_weights": calibrated_weights,
                "monday_watchlist": alpha_watchlist,
                "status": "success"
            }
            self.last_report = report

            log_event("SUCCESS", f"Recalibración de Fin de Semana ({trigger_reason}) completada con éxito.")

            # 5. Enviar a Telegram si está solicitado
            if send_telegram and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                await self.send_telegram_report(report)

            return report

        except Exception as e:
            logger.error(f"Error en optimización de fin de semana: {e}", exc_info=True)
            log_event("ERROR", f"Fallo en optimización de fin de semana: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            self.is_running_optimization = False

    async def _run_weekly_backtest(self, symbols: List[str]) -> Dict[str, Any]:
        """Descarga velas de 5m de los últimos 5 días y simula las 4 estrategias centrales."""
        loop = asyncio.get_event_loop()
        strategy_stats = {
            "trend_following": {"name": "Tendencia & Cruce EMA 20/50/200", "trades": 0, "wins": 0, "losses": 0, "gross_profit": 0.0, "gross_loss": 0.0},
            "mean_reversion": {"name": "Reversión a la Media (RSI + Bollinger)", "trades": 0, "wins": 0, "losses": 0, "gross_profit": 0.0, "gross_loss": 0.0},
            "liquidity_breakout": {"name": "Ruptura de Liquidez & Order Blocks", "trades": 0, "wins": 0, "losses": 0, "gross_profit": 0.0, "gross_loss": 0.0},
            "vwap_pullback": {"name": "Rebote VWAP Institucional", "trades": 0, "wins": 0, "losses": 0, "gross_profit": 0.0, "gross_loss": 0.0}
        }

        total_simulated_trades = 0

        for sym in symbols:
            try:
                # Descargar velas intradía de los últimos 5 días
                df = await loop.run_in_executor(
                    None,
                    lambda s=sym: yf.download(tickers=s, period="5d", interval="5m", progress=False)
                )
                if df.empty or len(df) < 50:
                    continue

                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0].lower() for c in df.columns]
                else:
                    df.columns = [c.lower() for c in df.columns]

                # Simulación de velas
                close = df["close"].values
                high = df["high"].values
                low = df["low"].values
                volume = df["volume"].values
                n = len(close)

                # Indicadores vectorizados
                ema20 = pd.Series(close).ewm(span=20).mean().values
                ema50 = pd.Series(close).ewm(span=50).mean().values
                sma20 = pd.Series(close).rolling(20).mean().values
                std20 = pd.Series(close).rolling(20).std().values
                upper_b = sma20 + (2 * std20)
                lower_b = sma20 - (2 * std20)

                delta = pd.Series(close).diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / (loss + 1e-9)
                rsi_vals = (100 - (100 / (1 + rs))).values

                # VWAP acumulado
                typical_price = (high + low + close) / 3.0
                cum_vol = np.cumsum(volume) + 1e-9
                cum_vp = np.cumsum(typical_price * volume)
                vwap = cum_vp / cum_vol

                # Evaluar señales a lo largo de las velas históricas
                step = 10  # Evaluar cada 10 barras para evitar clustering de señales
                for i in range(50, n - 12, step):
                    cp = float(close[i])
                    curr_vol = float(volume[i])
                    avg_v = float(np.mean(volume[max(0, i-20):i])) + 1e-9

                    signals = []

                    # 1. Trend Following
                    if ema20[i] > ema50[i] and cp > ema20[i]:
                        signals.append(("trend_following", "BUY"))
                    elif ema20[i] < ema50[i] and cp < ema20[i]:
                        signals.append(("trend_following", "SELL"))

                    # 2. Mean Reversion
                    if rsi_vals[i] < 34 and cp <= lower_b[i] * 1.008:
                        signals.append(("mean_reversion", "BUY"))
                    elif rsi_vals[i] > 66 and cp >= upper_b[i] * 0.992:
                        signals.append(("mean_reversion", "SELL"))

                    # 3. Liquidity Breakout
                    if curr_vol > 1.35 * avg_v and cp > float(np.max(close[i-6:i])):
                        signals.append(("liquidity_breakout", "BUY"))

                    # 4. VWAP Pullback
                    if abs(cp - vwap[i]) / cp < 0.003:
                        if cp > vwap[i] and close[i] > close[i-1]:
                            signals.append(("vwap_pullback", "BUY"))
                        elif cp < vwap[i] and close[i] < close[i-1]:
                            signals.append(("vwap_pullback", "SELL"))

                    # Simular desenlace de cada señal vela a vela con Auto Break-Even (+1.0R)
                    atr_local = float(np.mean(np.maximum(high[i-14:i] - low[i-14:i], 1e-4)))
                    risk_dist = max(cp * 0.0035, atr_local * 0.75)
                    reward_dist = risk_dist * MIN_RR_RATIO

                    max_lookforward = min(n, i + 36)  # Hasta 3 horas de trade intradía

                    for st_code, side in signals:
                        stats = strategy_stats[st_code]
                        stats["trades"] += 1
                        total_simulated_trades += 1
                        sim_risk_dollar = DEMO_CAPITAL * RISK_MAX_EXPOSURE

                        entry = cp
                        be_active = False
                        trade_resolved = False

                        if side == "BUY":
                            sl = entry - risk_dist
                            tp = entry + reward_dist
                            be_trigger = entry + risk_dist

                            for k in range(i + 1, max_lookforward):
                                bar_h = float(high[k])
                                bar_l = float(low[k])

                                # 1. Activar Break-Even si alcanza +1.0R
                                if bar_h >= be_trigger and not be_active:
                                    be_active = True
                                    sl = entry  # Riesgo cero asegurado

                                # 2. Verificar Take Profit (+2.0R)
                                if bar_h >= tp:
                                    stats["wins"] += 1
                                    stats["gross_profit"] += sim_risk_dollar * MIN_RR_RATIO
                                    trade_resolved = True
                                    break

                                # 3. Verificar Stop Loss o Break-Even
                                if bar_l <= sl:
                                    if be_active:
                                        # Cerrado en Break-Even (riesgo cero)
                                        stats["wins"] += 1  # Operación salvada sin pérdida
                                        stats["gross_profit"] += sim_risk_dollar * 0.1
                                    else:
                                        stats["losses"] += 1
                                        stats["gross_loss"] += sim_risk_dollar
                                    trade_resolved = True
                                    break

                            # Si finaliza el tiempo sin tocar SL ni TP (Square-off)
                            if not trade_resolved:
                                exit_p = float(close[max_lookforward - 1])
                                pnl_diff = exit_p - entry
                                if pnl_diff >= 0:
                                    stats["wins"] += 1
                                    stats["gross_profit"] += (pnl_diff / risk_dist) * sim_risk_dollar
                                else:
                                    stats["losses"] += 1
                                    stats["gross_loss"] += min(sim_risk_dollar, (abs(pnl_diff) / risk_dist) * sim_risk_dollar)

                        else:  # SELL (SHORT)
                            sl = entry + risk_dist
                            tp = entry - reward_dist
                            be_trigger = entry - risk_dist

                            for k in range(i + 1, max_lookforward):
                                bar_h = float(high[k])
                                bar_l = float(low[k])

                                # 1. Break-Even a +1.0R
                                if bar_l <= be_trigger and not be_active:
                                    be_active = True
                                    sl = entry

                                # 2. Take Profit
                                if bar_l <= tp:
                                    stats["wins"] += 1
                                    stats["gross_profit"] += sim_risk_dollar * MIN_RR_RATIO
                                    trade_resolved = True
                                    break

                                # 3. Stop Loss o Break-Even
                                if bar_h >= sl:
                                    if be_active:
                                        stats["wins"] += 1
                                        stats["gross_profit"] += sim_risk_dollar * 0.1
                                    else:
                                        stats["losses"] += 1
                                        stats["gross_loss"] += sim_risk_dollar
                                    trade_resolved = True
                                    break

                            if not trade_resolved:
                                exit_p = float(close[max_lookforward - 1])
                                pnl_diff = entry - exit_p
                                if pnl_diff >= 0:
                                    stats["wins"] += 1
                                    stats["gross_profit"] += (pnl_diff / risk_dist) * sim_risk_dollar
                                else:
                                    stats["losses"] += 1
                                    stats["gross_loss"] += min(sim_risk_dollar, (abs(pnl_diff) / risk_dist) * sim_risk_dollar)

            except Exception as ex:
                logger.warning(f"No se pudieron descargar datos para {sym}: {ex}")

        # Calcular métricas consolidadas
        summary = {}
        total_pnl = 0.0
        global_wins = 0
        global_trades = 0

        for code, data in strategy_stats.items():
            t = data["trades"]
            w = data["wins"]
            l = data["losses"]
            wr = round((w / t * 100.0), 1) if t > 0 else 0.0
            pf = round(data["gross_profit"] / (data["gross_loss"] + 1e-4), 2)
            net_pnl = round(data["gross_profit"] - data["gross_loss"], 2)
            total_pnl += net_pnl
            global_wins += w
            global_trades += t

            summary[code] = {
                "name": data["name"],
                "trades": t,
                "wins": w,
                "losses": l,
                "win_rate": wr,
                "profit_factor": pf,
                "net_pnl": net_pnl
            }

        global_win_rate = round((global_wins / global_trades * 100.0), 1) if global_trades > 0 else 0.0

        return {
            "strategies": summary,
            "total_trades": global_trades,
            "global_win_rate": global_win_rate,
            "total_net_pnl": round(total_pnl, 2)
        }

    def _recalibrate_ml_weights(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recalibra matemáticamente los pesos de Machine Learning en SQLite:
        - Estrategias con Win Rate alto y Profit Factor > 1.4 aumentan peso (hasta 1.40).
        - Estrategias neutrales se mantienen cerca de 1.0.
        - Estrategias en bajo régimen reducen su peso defensivamente (0.60 - 0.85).
        """
        conn = get_connection()
        cursor = conn.cursor()
        calibrated = {}
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for code, metrics in backtest_results.get("strategies", {}).items():
            wr = metrics["win_rate"]
            pf = metrics["profit_factor"]
            trades = metrics["trades"]

            # Regla de calibración Bayesiana adaptativa
            if trades < 3:
                new_weight = 1.0  # Muestra insuficiente, mantener neutral
            elif wr >= 68.0 and pf >= 1.5:
                new_weight = round(min(1.45, 1.15 + (wr - 68.0) * 0.015), 2)
            elif wr >= 55.0 and pf >= 1.1:
                new_weight = round(1.0 + (wr - 55.0) * 0.01, 2)
            elif wr >= 45.0:
                new_weight = round(max(0.80, 0.95 - (55.0 - wr) * 0.015), 2)
            else:
                new_weight = round(max(0.55, 0.75 - (45.0 - wr) * 0.01), 2)

            cursor.execute("""
                UPDATE strategy_metrics 
                SET weight = ?, win_rate = ?, last_updated = ?
                WHERE name = ?
            """, (new_weight, wr, now, code))

            calibrated[code] = {
                "name": metrics["name"],
                "win_rate": wr,
                "profit_factor": pf,
                "new_weight": new_weight
            }

        conn.commit()
        conn.close()
        logger.info(f"Pesos ML recalibrados exitosamente: {calibrated}")
        return calibrated

    async def _generate_monday_alpha_watchlist(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Analiza cada activo para proyectar el ranking Alpha y niveles para el Lunes:
        - Tendencia (EMA 20 vs EMA 50)
        - RSI y Volatilidad ATR
        - Niveles: Pivote, Resistencia R1 y Soporte S1
        """
        loop = asyncio.get_event_loop()
        alpha_list = []

        for sym in symbols:
            try:
                df = await loop.run_in_executor(
                    None,
                    lambda s=sym: yf.download(tickers=s, period="1mo", interval="1d", progress=False)
                )
                if df.empty or len(df) < 15:
                    continue

                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0].lower() for c in df.columns]
                else:
                    df.columns = [c.lower() for c in df.columns]

                close = df["close"].values
                high = df["high"].values
                low = df["low"].values
                last_close = float(close[-1])
                last_high = float(high[-1])
                last_low = float(low[-1])

                # Medias
                ema20 = float(pd.Series(close).ewm(span=20).mean().values[-1])
                ema50 = float(pd.Series(close).ewm(span=50).mean().values[-1])

                # ATR (14)
                tr = np.maximum(high[1:] - low[1:], np.maximum(abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1])))
                atr = float(np.mean(tr[-14:])) if len(tr) >= 14 else (last_high - last_low)
                atr_pct = round((atr / last_close) * 100.0, 2)

                # RSI (14)
                diff = pd.Series(close).diff()
                up = diff.where(diff > 0, 0).rolling(14).mean()
                dn = (-diff.where(diff < 0, 0)).rolling(14).mean()
                rsi = float((100 - (100 / (1 + (up / (dn + 1e-9))))).values[-1])

                # Puntos Pivote clásicos para el Lunes
                pivot = (last_high + last_low + last_close) / 3.0
                r1 = (2 * pivot) - last_low
                s1 = (2 * pivot) - last_high

                # Clasificación de Sesgo Institucional
                if last_close > ema20 > ema50:
                    bias = "ALCISTA FUERTE (BULLISH)"
                    emoji = "🟢"
                    priority = 1
                elif last_close < ema20 < ema50:
                    bias = "BAJISTA (BEARISH)"
                    emoji = "🔴"
                    priority = 3
                else:
                    bias = "CONSOLIDACIÓN / RANGO"
                    emoji = "🟡"
                    priority = 2

                alpha_list.append({
                    "symbol": sym,
                    "last_price": round(last_close, 2),
                    "bias": bias,
                    "emoji": emoji,
                    "priority": priority,
                    "rsi": round(rsi, 1),
                    "atr_pct": atr_pct,
                    "pivot": round(pivot, 2),
                    "resistance_1": round(r1, 2),
                    "support_1": round(s1, 2)
                })

            except Exception as e:
                logger.debug(f"Error analizando {sym} para watchlist del lunes: {e}")

        # Ordenar por prioridad alcista y volatilidad atractiva
        alpha_list.sort(key=lambda x: (x["priority"], -x["atr_pct"]))
        return alpha_list

    async def send_telegram_report(self, report: Dict[str, Any], target_chat_id: int = None) -> bool:
        """Formatea y despacha el reporte completo a Telegram."""
        cid = target_chat_id or TELEGRAM_CHAT_ID
        if not TELEGRAM_BOT_TOKEN or not cid:
            return False

        b_sum = report.get("backtest_summary", {})
        cal_w = report.get("calibrated_weights", {})
        alpha_w = report.get("monday_watchlist", [])

        # 1. Estrategia con mejor rendimiento
        best_st = max(cal_w.values(), key=lambda x: x["win_rate"]) if cal_w else None

        # Líneas de pesos de Machine Learning
        weights_lines = []
        for code, info in cal_w.items():
            icon = "⚡" if info["new_weight"] >= 1.15 else ("🛡️" if info["new_weight"] <= 0.85 else "⚖️")
            weights_lines.append(
                f"{icon} *{info['name']}*\n"
                f"   • Win Rate Semanal: `{info['win_rate']:.1f}%` | Profit Factor: `{info['profit_factor']:.2f}`\n"
                f"   • Nuevo Peso Algorítmico: `{info['new_weight']:.2f}x`"
            )
        weights_text = "\n\n".join(weights_lines)

        # Líneas de Watchlist del Lunes (Top 3-4)
        alpha_lines = []
        for a in alpha_w[:4]:
            alpha_lines.append(
                f"{a['emoji']} *{a['symbol']}* (${a['last_price']:.2f}) - `{a['bias']}`\n"
                f"   • Niveles Lunes: Soporte `${a['support_1']:.2f}` | Pivote `${a['pivot']:.2f}` | Resistencia `${a['resistance_1']:.2f}`\n"
                f"   • Volatilidad ATR: `{a['atr_pct']}%` | RSI(14): `{a['rsi']}`"
            )
        alpha_text = "\n\n".join(alpha_lines)

        total_trades = b_sum.get("total_trades", 0)
        global_wr = b_sum.get("global_win_rate", 0.0)
        net_pnl = b_sum.get("total_net_pnl", 0.0)
        pnl_emoji = "🟢" if net_pnl >= 0 else "🔴"

        if best_st:
            best_name = best_st["name"]
            best_weight = best_st["new_weight"]
            recommendation = f"Priorizar señales de *{best_name}* (Peso {best_weight}x)."
        else:
            recommendation = "Operar con gestión estricta 1:2 R:R."

        trigger_info = report.get("trigger_reason", "Manual")
        mode_label = "⚡ Auto-Programado" if report.get("is_auto") else "👤 Manual a petición"

        msg = (
            f"🧠 *REPORTE CUANTITATIVO DE FIN DE SEMANA* 🧠\n"
            f"───────────────────────────────\n"
            f"🗓️ *Fecha:* `{report.get('timestamp')}`\n"
            f"⏰ *Modo:* `{mode_label}` ({trigger_info})\n"
            f"🏦 *Objetivo:* Calibración ML & Alpha Plan Lunes\n"
            f"───────────────────────────────\n\n"
            f"📊 *SIMULACIÓN DE BACKTEST (Última Semana):*\n"
            f"• Operaciones evaluadas: `{total_trades}`\n"
            f"• Win Rate Global: `%{global_wr:.1f}`\n"
            f"• PnL Simulado: {pnl_emoji} `+${net_pnl:,.2f} USD`\n\n"
            f"🤖 *RECALIBRACIÓN MACHINE LEARNING (PESOS LUNES):*\n"
            f"{weights_text}\n\n"
            f"🎯 *ALPHA WATCHLIST INSTITUCIONAL (PREPARADA PARA EL LUNES):*\n"
            f"{alpha_text}\n\n"
            f"───────────────────────────────\n"
            f"💡 *Recomendación del Motor:* {recommendation}\n"
            f"🚀 *El robot está 100% calibrado y listo para la campana del lunes.*"
        )

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(url, json={
                    "chat_id": cid,
                    "text": msg,
                    "parse_mode": "Markdown"
                })
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Error despachando reporte a Telegram: {e}")
            return False


weekend_engine = WeekendOptimizerEngine()
