import numpy as np

class BacktestMetricsCalculator:
    """
    Calculador de métricas cuantitativas para evaluar estrategias de trading:
    Win Rate, Profit Factor, Max Drawdown %, Sharpe Ratio y Curva de Equidad.
    """

    @staticmethod
    def calculate(initial_capital: float, trades: list[dict]) -> dict:
        if not trades:
            return {
                "initial_capital": initial_capital,
                "final_capital": initial_capital,
                "total_net_profit": 0.0,
                "total_return_pct": 0.0,
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0,
                "trades": [],
                "equity_curve": [{"timestamp": "Inicio", "equity": initial_capital}]
            }

        equity = initial_capital
        equity_curve = [{"timestamp": "Inicio", "equity": initial_capital}]
        profits = []
        losses = []
        equity_series = [initial_capital]

        for i, t in enumerate(trades):
            pnl = t["pnl"]
            equity += pnl
            equity_series.append(equity)
            equity_curve.append({
                "timestamp": t.get("exit_time", f"Trade #{i+1}"),
                "equity": round(equity, 2),
                "pnl": round(pnl, 2)
            })

            if pnl > 0:
                profits.append(pnl)
            else:
                losses.append(abs(pnl))

        total_trades = len(trades)
        wins = len(profits)
        win_rate = round((wins / total_trades) * 100.0, 2) if total_trades > 0 else 0.0

        gross_profit = sum(profits)
        gross_loss = sum(losses)
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        # Max Drawdown
        peak = equity_series[0]
        max_dd = 0.0
        for val in equity_series:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100.0 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        # Sharpe Ratio (estimación anualizada)
        returns = np.diff(equity_series) / equity_series[:-1]
        if len(returns) > 1 and np.std(returns) > 1e-9:
            sharpe = round((np.mean(returns) / np.std(returns)) * np.sqrt(252), 2)
        else:
            sharpe = 1.0

        total_net_profit = round(equity - initial_capital, 2)
        total_return_pct = round((total_net_profit / initial_capital) * 100.0, 2)

        return {
            "initial_capital": initial_capital,
            "final_capital": round(equity, 2),
            "total_net_profit": total_net_profit,
            "total_return_pct": total_return_pct,
            "total_trades": total_trades,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": round(max_dd, 2),
            "sharpe_ratio": sharpe,
            "trades": trades,
            "equity_curve": equity_curve
        }
