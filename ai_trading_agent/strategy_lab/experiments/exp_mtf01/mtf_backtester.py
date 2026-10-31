"""
ai_trading_agent.strategy_lab.experiments.exp_mtf01.mtf_backtester
==================================================================
Simulador de Ejecución Causal e Investigador de Backtesting MTF.
Simula fills en T+1 Open, comisiones ($0.005/acción), deslizamiento (2 a 6 bps),
resolución conservadora de colisiones intrabarra (SL prioritario),
y evalúa variantes de salida MTF_V1A (Structure Target) y MTF_V1B (Fixed 2.0R Target).
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


class MTFBacktester:
    """Motor de Backtesting Causal con Microestructura de Ejecución."""

    def __init__(
        self,
        initial_equity: float = 100000.0,
        risk_per_trade_pct: float = 0.0025,
        commission_per_share: float = 0.005,
        slippage_bps: float = 2.0,
        max_position_equity_pct: float = 0.20,
        max_holding_bars: int = 200
    ):
        self.initial_equity = initial_equity
        self.risk_per_trade_pct = risk_per_trade_pct
        self.commission_per_share = commission_per_share
        self.slippage_bps = slippage_bps
        self.max_position_equity_pct = max_position_equity_pct
        self.max_holding_bars = max_holding_bars

    def run_simulation(
        self,
        signals: List[Dict[str, Any]],
        df_m5: pd.DataFrame,
        tp_variant: str = "V1A"  # "V1A" (Structure Target) o "V1B" (Fixed 2.0R)
    ) -> Dict[str, Any]:
        """Ejecuta la simulación causal sobre el historial de barras M5."""
        df = df_m5.copy()
        df.sort_index(inplace=True)
        cols = {c: c.capitalize() for c in df.columns}
        df.rename(columns=cols, inplace=True)

        trades = []
        equity = self.initial_equity
        peak_equity = self.initial_equity
        max_drawdown = 0.0

        occupied_until_idx = -1

        for sig in signals:
            sig_bar_idx = sig["bar_index"]
            # Prevenir trades simultáneos sobrepuestos en el mismo activo
            if sig_bar_idx <= occupied_until_idx:
                continue

            # Fills ocurren causalmente en la apertura de la barra T+1
            fill_bar_idx = sig_bar_idx + 1
            if fill_bar_idx >= len(df):
                continue

            fill_bar = df.iloc[fill_bar_idx]
            raw_open = float(fill_bar['Open'])
            direction = sig["direction"]
            setup = sig["setup"]

            slip_factor = (self.slippage_bps / 10000.0)
            if direction == "BUY":
                fill_price = raw_open * (1.0 + slip_factor)
                sl_price = setup["fib_75"] - (0.10 * setup["atr_h1"])
                r_dist = fill_price - sl_price
                if tp_variant == "V1A":
                    tp_price = setup["p1"]
                else:
                    tp_price = fill_price + (2.0 * r_dist)
            else:
                fill_price = raw_open * (1.0 - slip_factor)
                sl_price = setup["fib_75"] + (0.10 * setup["atr_h1"])
                r_dist = sl_price - fill_price
                if tp_variant == "V1A":
                    tp_price = setup["p1"]
                else:
                    tp_price = fill_price - (2.0 * r_dist)

            # Validar distancia de riesgo
            if r_dist <= 0 or r_dist < (0.0005 * fill_price):
                continue

            # Dimensionamiento de posición
            risk_amount = equity * self.risk_per_trade_pct
            shares = int(risk_amount / r_dist)
            max_shares = int((equity * self.max_position_equity_pct) / fill_price)
            shares = max(1, min(shares, max_shares))

            # Simular evolución del trade barra a barra en M5
            exit_price = None
            exit_time = None
            exit_reason = None
            exit_bar_idx = fill_bar_idx

            end_idx = min(len(df), fill_bar_idx + self.max_holding_bars)

            for b_idx in range(fill_bar_idx, end_idx):
                bar = df.iloc[b_idx]
                h = float(bar['High'])
                l = float(bar['Low'])

                if direction == "BUY":
                    sl_hit = l <= sl_price
                    tp_hit = h >= tp_price

                    if sl_hit and tp_hit:
                        # Colisión intrabarra: Stop Loss gana (prudencia conservadora)
                        exit_price = sl_price * (1.0 - slip_factor)
                        exit_time = bar.name
                        exit_reason = "SL_COLLISION_CONSERVATIVE"
                        exit_bar_idx = b_idx
                        break
                    elif sl_hit:
                        exit_price = sl_price * (1.0 - slip_factor)
                        exit_time = bar.name
                        exit_reason = "STOP_LOSS"
                        exit_bar_idx = b_idx
                        break
                    elif tp_hit:
                        exit_price = tp_price * (1.0 - slip_factor)
                        exit_time = bar.name
                        exit_reason = "TAKE_PROFIT"
                        exit_bar_idx = b_idx
                        break
                else: # SELL
                    sl_hit = h >= sl_price
                    tp_hit = l <= tp_price

                    if sl_hit and tp_hit:
                        # Colisión intrabarra: Stop Loss gana
                        exit_price = sl_price * (1.0 + slip_factor)
                        exit_time = bar.name
                        exit_reason = "SL_COLLISION_CONSERVATIVE"
                        exit_bar_idx = b_idx
                        break
                    elif sl_hit:
                        exit_price = sl_price * (1.0 + slip_factor)
                        exit_time = bar.name
                        exit_reason = "STOP_LOSS"
                        exit_bar_idx = b_idx
                        break
                    elif tp_hit:
                        exit_price = tp_price * (1.0 + slip_factor)
                        exit_time = bar.name
                        exit_reason = "TAKE_PROFIT"
                        exit_bar_idx = b_idx
                        break

            # Si alcanzó el límite de holding sin tocar SL ni TP, cerrar a mercado
            if exit_price is None:
                last_bar = df.iloc[end_idx - 1]
                if direction == "BUY":
                    exit_price = float(last_bar['Close']) * (1.0 - slip_factor)
                else:
                    exit_price = float(last_bar['Close']) * (1.0 + slip_factor)
                exit_time = last_bar.name
                exit_reason = "MAX_HOLDING_TIMEOUT"
                exit_bar_idx = end_idx - 1

            occupied_until_idx = exit_bar_idx

            # Cálculo de PnL y Costos
            if direction == "BUY":
                gross_pnl = (exit_price - fill_price) * shares
            else:
                gross_pnl = (fill_price - exit_price) * shares

            commissions = self.commission_per_share * shares * 2.0  # Entrada + Salida
            slippage_cost = (fill_price + exit_price) * slip_factor * shares
            total_costs = commissions + slippage_cost
            net_pnl = gross_pnl - commissions  # Slippage ya está embebido en fill/exit prices

            r_return = net_pnl / risk_amount if risk_amount > 0 else 0.0
            equity += net_pnl
            peak_equity = max(peak_equity, equity)
            dd = (peak_equity - equity) / peak_equity
            max_drawdown = max(max_drawdown, dd)

            trades.append({
                "trade_id": f"TRD_{len(trades)+1:03d}",
                "direction": direction,
                "entry_time": fill_bar.name.strftime("%Y-%m-%d %H:%M:%S"),
                "entry_price": round(fill_price, 4),
                "exit_time": exit_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(exit_time, pd.Timestamp) else str(exit_time),
                "exit_price": round(exit_price, 4),
                "exit_reason": exit_reason,
                "shares": shares,
                "sl_price": round(sl_price, 4),
                "tp_price": round(tp_price, 4),
                "gross_pnl": round(gross_pnl, 2),
                "net_pnl": round(net_pnl, 2),
                "commissions": round(commissions, 2),
                "slippage_cost": round(slippage_cost, 2),
                "r_return": round(r_return, 3),
                "equity_after": round(equity, 2),
                "bars_held": exit_bar_idx - fill_bar_idx + 1
            })

        # Métricas agregadas
        total_trades = len(trades)
        if total_trades > 0:
            wins = [t for t in trades if t["net_pnl"] > 0]
            losses = [t for t in trades if t["net_pnl"] <= 0]
            win_rate = len(wins) / total_trades
            gross_win = sum(t["net_pnl"] for t in wins)
            gross_loss = abs(sum(t["net_pnl"] for t in losses))
            profit_factor = gross_win / gross_loss if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
            net_pnl_total = sum(t["net_pnl"] for t in trades)
            expectancy_r = sum(t["r_return"] for t in trades) / total_trades
        else:
            win_rate = 0.0
            profit_factor = 0.0
            net_pnl_total = 0.0
            expectancy_r = 0.0

        return {
            "total_trades": total_trades,
            "net_pnl": round(net_pnl_total, 2),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "expectancy_r": round(expectancy_r, 4),
            "max_drawdown_pct": round(max_drawdown * 100.0, 2),
            "final_equity": round(equity, 2),
            "tp_variant": tp_variant,
            "trades": trades
        }
