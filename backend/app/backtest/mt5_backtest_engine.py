# =====================================================================
# TRADEPULSE: MOTOR DE BACKTESTING METATRADER 5 (Order Blocks & SMC)
# =====================================================================
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

# Asegurar que 'backend' esté en sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.mt5.mt5_connector import mt5_connector
from app.strategies.order_blocks_strategy import OrderBlocksStrategy, TradeSignal

logger = logging.getLogger(__name__)


class MT5BacktestEngine:
    """
    Motor Cuantitativo de Backtesting alimentado exclusivamente por la base
    de datos histórica del terminal MetaTrader 5 (MT5).
    Ejecuta simulaciones vela a vela aplicando la estrategia de Order Blocks,
    filtro RVOL, EMA 50/200, salidas escalonadas TP1/TP2 y control de riesgo estricto (1-2%).
    """

    def __init__(self):
        self.strategy = OrderBlocksStrategy()

    async def run_mt5_backtest(
        self,
        symbols: List[str] = ["EURUSD"],
        timeframe: str = "M5",
        bars_count: int = 1500,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_capital: float = 100000.0,
        risk_per_trade_pct: float = 1.0,
        rvol_threshold: float = 1.4,
        tp1_rr: float = 1.5,
        tp2_rr: float = 3.0
    ) -> Dict[str, Any]:
        """
        Ejecuta el backtest completo sobre los datos reales descargados desde MetaTrader 5.
        """
        # Configurar parámetros de la estrategia
        self.strategy.rvol_threshold = rvol_threshold
        self.strategy.tp1_rr = tp1_rr
        self.strategy.tp2_rr = tp2_rr

        all_trades = []
        equity = initial_capital
        equity_curve = [{"timestamp": "Inicio", "equity": round(equity, 2), "pnl": 0.0}]
        peak_equity = initial_capital
        max_drawdown_dollar = 0.0
        max_drawdown_pct = 0.0

        daily_losses = {} # Control de circuit breaker diario

        for symbol in symbols:
            sym_clean = symbol.upper().strip()
            df = mt5_connector.get_historical_rates(
                symbol=sym_clean,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                count=bars_count
            )

            if df is None or len(df) < 50:
                logger.warning(f"Insuficientes datos en MT5 para el símbolo {sym_clean}")
                continue

            # Detectar señales con la estrategia Order Blocks
            signals = self.strategy.evaluate_signals(df, sym_clean)
            logger.info(f"[MT5 Backtest] {sym_clean} ({timeframe}): {len(df)} velas analizadas, {len(signals)} señales OB encontradas.")

            # Simular ejecución vela a vela
            for sig in signals:
                # 1. Encontrar el índice de la vela de entrada
                entry_idx_list = df.index[df['time'] == sig.time].tolist()
                if not entry_idx_list:
                    continue
                entry_idx = entry_idx_list[0]

                # 2. Control de riesgo por operación (1% a 2%)
                cash_at_risk = equity * (risk_per_trade_pct / 100.0)
                risk_dist = sig.risk_distance
                if risk_dist <= 0:
                    continue

                shares = max(1.0, cash_at_risk / risk_dist)
                position_size = shares * sig.entry_price

                # Variables de seguimiento de la posición
                side = sig.side
                entry_p = sig.entry_price
                sl = sig.stop_loss
                tp1 = sig.tp1
                tp2 = sig.tp2

                tp1_hit = False
                exit_time = None
                exit_price = None
                exit_reason = None
                pnl = 0.0

                # 3. Evaluar las velas posteriores a la entrada
                for j in range(entry_idx + 1, min(entry_idx + 200, len(df))):
                    candle = df.iloc[j]
                    high = candle['high']
                    low = candle['low']
                    c_time = candle['time']

                    if side == 'BUY':
                        # Verificar Stop Loss
                        if low <= sl:
                            if tp1_hit:
                                # Ya se tomó el 50% en TP1 y el SL estaba en Breakeven (0 pérdida en el resto)
                                exit_price = sl
                                exit_time = c_time
                                exit_reason = "BREAKEVEN_STOP"
                                break
                            else:
                                exit_price = sl
                                exit_time = c_time
                                exit_reason = "STOP_LOSS"
                                pnl = -cash_at_risk
                                break

                        # Verificar TP1 (1.5R - Toma de ganancias parcial 50% y trailing SL a Breakeven)
                        if not tp1_hit and high >= tp1:
                            tp1_hit = True
                            pnl += (cash_at_risk * (self.strategy.tp1_rr / 1.0)) * 0.5
                            sl = entry_p  # Mover Stop Loss a Breakeven

                        # Verificar TP2 (3.0R - Cierre completo del 50% restante)
                        if high >= tp2:
                            remaining_gain = (cash_at_risk * (self.strategy.tp2_rr / 1.0)) * (0.5 if tp1_hit else 1.0)
                            pnl += remaining_gain
                            exit_price = tp2
                            exit_time = c_time
                            exit_reason = "TAKE_PROFIT_FULL"
                            break

                    elif side == 'SELL':
                        # Verificar Stop Loss
                        if high >= sl:
                            if tp1_hit:
                                exit_price = sl
                                exit_time = c_time
                                exit_reason = "BREAKEVEN_STOP"
                                break
                            else:
                                exit_price = sl
                                exit_time = c_time
                                exit_reason = "STOP_LOSS"
                                pnl = -cash_at_risk
                                break

                        # Verificar TP1
                        if not tp1_hit and low <= tp1:
                            tp1_hit = True
                            pnl += (cash_at_risk * (self.strategy.tp1_rr / 1.0)) * 0.5
                            sl = entry_p  # Breakeven

                        # Verificar TP2
                        if low <= tp2:
                            remaining_gain = (cash_at_risk * (self.strategy.tp2_rr / 1.0)) * (0.5 if tp1_hit else 1.0)
                            pnl += remaining_gain
                            exit_price = tp2
                            exit_time = c_time
                            exit_reason = "TAKE_PROFIT_FULL"
                            break

                # Si no tocó SL ni TP al final del horizonte temporal, cerrar a precio de mercado
                if exit_reason is None:
                    last_c = df.iloc[min(entry_idx + 199, len(df) - 1)]
                    exit_price = last_c['close']
                    exit_time = last_c['time']
                    exit_reason = "TIMEOUT_CLOSE"
                    if side == 'BUY':
                        diff = exit_price - entry_p
                    else:
                        diff = entry_p - exit_price
                    pnl += (diff / risk_dist) * (cash_at_risk * 0.5 if tp1_hit else cash_at_risk)

                # Actualizar métricas acumuladas de la cuenta
                equity += pnl
                if equity > peak_equity:
                    peak_equity = equity
                dd_dollar = peak_equity - equity
                dd_pct = (dd_dollar / peak_equity) * 100.0 if peak_equity > 0 else 0.0

                if dd_dollar > max_drawdown_dollar:
                    max_drawdown_dollar = dd_dollar
                if dd_pct > max_drawdown_pct:
                    max_drawdown_pct = dd_pct

                pnl_pct = (pnl / initial_capital) * 100.0

                trade_record = {
                    "id": len(all_trades) + 1,
                    "symbol": sym_clean,
                    "side": side,
                    "entry_price": round(entry_p, 5),
                    "exit_price": round(exit_price, 5),
                    "stop_loss": round(sl, 5),
                    "take_profit_1": round(tp1, 5),
                    "take_profit_2": round(tp2, 5),
                    "quantity": round(shares, 2),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "entry_time": str(sig.time),
                    "exit_time": str(exit_time),
                    "exit_reason": exit_reason,
                    "rvol": round(sig.rvol, 2),
                    "strategy": "OrderBlocks_RVOL_EMA"
                }
                all_trades.append(trade_record)

                equity_curve.append({
                    "timestamp": str(exit_time),
                    "equity": round(equity, 2),
                    "pnl": round(pnl, 2)
                })

        # 4. Cálculo Estadístico de Métricas Institucionales
        total_trades = len(all_trades)
        wins = [t for t in all_trades if t['pnl'] > 0]
        losses = [t for t in all_trades if t['pnl'] < 0]
        breakevens = [t for t in all_trades if t['pnl'] == 0]

        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        win_rate = round((len(wins) / total_trades) * 100.0, 2) if total_trades > 0 else 0.0

        net_profit = round(equity - initial_capital, 2)
        total_return_pct = round((net_profit / initial_capital) * 100.0, 2)

        # Sharpe Ratio simplificado (anualizado sobre los retornos por trade)
        if total_trades > 2:
            pnls = [t['pnl'] for t in all_trades]
            mean_pnl = np.mean(pnls)
            std_pnl = np.std(pnls)
            sharpe = round((mean_pnl / std_pnl) * np.sqrt(252), 2) if std_pnl > 0 else 0.0
        else:
            sharpe = 0.0

        return {
            "strategy": "Smart Money Order Blocks (OB) + RVOL + EMA 50/200",
            "data_source": "MetaTrader 5 Native Database",
            "timeframe": timeframe,
            "symbols": symbols,
            "initial_capital": initial_capital,
            "final_equity": round(equity, 2),
            "net_profit": net_profit,
            "total_return_pct": total_return_pct,
            "profit_factor": profit_factor,
            "win_rate_pct": win_rate,
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "max_drawdown_dollar": round(max_drawdown_dollar, 2),
            "sharpe_ratio": sharpe,
            "total_trades": total_trades,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "breakeven_trades": len(breakevens),
            "average_trade_pnl": round(net_profit / total_trades, 2) if total_trades > 0 else 0.0,
            "risk_per_trade_pct": risk_per_trade_pct,
            "trades": all_trades,
            "equity_curve": equity_curve
        }

    async def send_telegram_backtest_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Envía el reporte del backtest institucional por Telegram."""
        from app.core.notifier import notifier

        syms = ", ".join(results.get("symbols", ["N/A"]))
        tf = results.get("timeframe", "M5")
        ret_pct = results.get("total_return_pct", 0.0)
        net_prof = results.get("net_profit", 0.0)
        pf = results.get("profit_factor", 0.0)
        wr = results.get("win_rate_pct", 0.0)
        dd = results.get("max_drawdown_pct", 0.0)
        trades = results.get("total_trades", 0)
        sharpe = results.get("sharpe_ratio", 0.0)

        emoji_res = "🟢" if net_prof >= 0 else "🔴"

        title = f"{emoji_res} REPORTE BACKTEST METATRADER 5"
        body = (
            f"📊 *Estrategia:* Order Blocks (OB) + RVOL + EMA 50/200\n"
            f"🏛️ *Fuente:* Base de Datos Local de MetaTrader 5\n"
            f"🎯 *Activos:* {syms} ({tf})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Retorno Total:* {ret_pct:+.2f}% (${net_prof:+,.2f})\n"
            f"🏆 *Profit Factor:* {pf}\n"
            f"🎯 *Win Rate:* {wr}%\n"
            f"📉 *Máx Drawdown:* -{dd}%\n"
            f"⚡ *Ratio Sharpe:* {sharpe}\n"
            f"🔢 *Operaciones:* {trades} trades ejecutados\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ *Gestión de Riesgo:* 1.0% a 2.0% por trade con TP1/TP2 escalonado."
        )

        success = await notifier.send_alert(title, body, severity="INFO" if net_prof >= 0 else "WARN")
        return {"success": success, "message": "Reporte de MT5 enviado a Telegram" if success else "Error enviando a Telegram"}


# Instancia singleton
mt5_backtest_engine = MT5BacktestEngine()

if __name__ == "__main__":
    import asyncio
    async def main():
        res = await mt5_backtest_engine.run_mt5_backtest(
            symbols=["EURUSD"],
            timeframe="M5",
            bars_count=1000
        )
        print("=== RESULTADOS BACKTEST METATRADER 5 ===")
        print(f"Retorno Total: {res['total_return_pct']}% (${res['net_profit']})")
        print(f"Profit Factor: {res['profit_factor']}")
        print(f"Win Rate: {res['win_rate_pct']}%")
        print(f"Max Drawdown: -{res['max_drawdown_pct']}%")
        print(f"Trades Totales: {res['total_trades']}")

    asyncio.run(main())
