"""
ai_trading_agent.backtest.metrics
=================================
Módulo cuantitativo de cálculo de métricas financieras y de rendimiento (Instrucción 17 y 22).
Fórmulas matemáticas documentadas y reproducibles:
- Retorno Total y CAGR
- Sharpe Ratio anualizado (riesgo libre rf = 0 o tasa de interés)
- Sortino Ratio (penaliza únicamente volatilidad a la baja / downside risk)
- Max Drawdown (en porcentaje y dólares)
- Profit Factor (Ganancia bruta / Pérdida bruta)
- Win Rate, Expectativa matemática ($ y R)
- Calmar Ratio (CAGR / Max Drawdown)
"""

import math
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    total_net_pnl: float
    total_return_pct: float
    max_drawdown_pct: float
    max_drawdown_dollars: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    expectancy_dollars: float
    average_trade_pnl: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    total_commission_paid: float
    total_slippage_cost: float


class QuantitativeMetricsCalculator:
    """Calculador determinista de métricas estadísticas de rendimiento."""

    @staticmethod
    def calculate(
        trades: List[Dict[str, Any]],
        initial_capital: float = 100000.0,
        equity_curve: Optional[List[float]] = None,
        risk_free_rate: float = 0.04,  # 4% anual
        trading_days_per_year: int = 252
    ) -> PerformanceMetrics:
        """
        Calcula las métricas cuantitativas a partir del historial de operaciones cerradas
        y la curva de equidad.
        """
        if not trades:
            return PerformanceMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate_pct=0.0,
                profit_factor=0.0,
                total_net_pnl=0.0,
                total_return_pct=0.0,
                max_drawdown_pct=0.0,
                max_drawdown_dollars=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                calmar_ratio=0.0,
                expectancy_dollars=0.0,
                average_trade_pnl=0.0,
                average_win=0.0,
                average_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                total_commission_paid=0.0,
                total_slippage_cost=0.0
            )

        pnls = [t.get("net_pnl", 0.0) for t in trades]
        commissions = [t.get("commission", 0.0) for t in trades]
        slippages = [t.get("slippage", 0.0) for t in trades]

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_trades = len(pnls)
        winning_trades = len(wins)
        losing_trades = len(losses)

        win_rate = round((winning_trades / total_trades) * 100.0, 2) if total_trades > 0 else 0.0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))

        if gross_loss > 0:
            profit_factor = round(gross_profit / gross_loss, 2)
        else:
            profit_factor = round(gross_profit, 2) if gross_profit > 0 else 1.0

        total_net_pnl = round(sum(pnls), 2)
        total_return_pct = round((total_net_pnl / initial_capital) * 100.0, 2)

        avg_win = round(gross_profit / winning_trades, 2) if winning_trades > 0 else 0.0
        avg_loss = round(gross_loss / losing_trades, 2) if losing_trades > 0 else 0.0
        avg_trade = round(total_net_pnl / total_trades, 2) if total_trades > 0 else 0.0

        # Expectancia = (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
        win_prob = winning_trades / total_trades if total_trades > 0 else 0.0
        loss_prob = losing_trades / total_trades if total_trades > 0 else 0.0
        expectancy = round((win_prob * avg_win) - (loss_prob * avg_loss), 2)

        largest_win = round(max(wins), 2) if wins else 0.0
        largest_loss = round(min(losses), 2) if losses else 0.0

        # Cálculo de Curva de Equidad y Max Drawdown
        if not equity_curve or len(equity_curve) < 2:
            curve = [initial_capital]
            curr = initial_capital
            for p in pnls:
                curr += p
                curve.append(curr)
        else:
            curve = equity_curve

        peak = curve[0]
        max_dd_dollars = 0.0
        max_dd_pct = 0.0

        for val in curve:
            if val > peak:
                peak = val
            dd_dollars = peak - val
            dd_pct = (dd_dollars / peak) * 100.0 if peak > 0 else 0.0
            if dd_dollars > max_dd_dollars:
                max_dd_dollars = dd_dollars
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        max_dd_dollars = round(max_dd_dollars, 2)
        max_dd_pct = round(max_dd_pct, 2)

        # Cálculo de Retornos Periódicos para Sharpe y Sortino
        returns = []
        for i in range(1, len(curve)):
            prev = curve[i - 1]
            if prev > 0:
                returns.append((curve[i] - prev) / prev)

        if len(returns) >= 2:
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = math.sqrt(variance)

            # Downside deviation para Sortino
            downside_returns = [min(0.0, r) for r in returns]
            downside_var = sum(r ** 2 for r in downside_returns) / len(downside_returns)
            downside_std = math.sqrt(downside_var)

            # Anualización asumiendo número de trades/periodos
            ann_factor = math.sqrt(min(252, len(returns)))
            rf_per_period = (risk_free_rate / 252)

            excess_return = mean_ret - rf_per_period

            sharpe = round((excess_return / (std_dev + 1e-9)) * ann_factor, 2)
            sortino = round((excess_return / (downside_std + 1e-9)) * ann_factor, 2)
        else:
            sharpe = 0.0
            sortino = 0.0

        # Calmar Ratio = Retorno % / Max Drawdown %
        if max_dd_pct > 0:
            calmar = round(total_return_pct / max_dd_pct, 2)
        else:
            calmar = round(total_return_pct, 2) if total_return_pct > 0 else 0.0

        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate_pct=win_rate,
            profit_factor=profit_factor,
            total_net_pnl=total_net_pnl,
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_dd_pct,
            max_drawdown_dollars=max_dd_dollars,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            expectancy_dollars=expectancy,
            average_trade_pnl=avg_trade,
            average_win=avg_win,
            average_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            total_commission_paid=round(sum(commissions), 2),
            total_slippage_cost=round(sum(slippages), 2)
        )


metrics_calculator = QuantitativeMetricsCalculator()
