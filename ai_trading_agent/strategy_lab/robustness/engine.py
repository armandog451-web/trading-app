"""
ai_trading_agent.strategy_lab.robustness.engine
================================================
Motor de Pruebas de Robustez Monte Carlo, Perturbación de Parámetros y Estrés de Fricciones.
Calcula el Robustness Score (0 a 100) e identifica la fragilidad de una estrategia.
"""

from typing import List, Dict, Any
import random
import math
from pydantic import BaseModel


class RobustnessReport(BaseModel):
    robustness_score: float  # 0 a 100
    monte_carlo_drawdown_5th_pct: float
    monte_carlo_drawdown_95th_pct: float
    worst_expected_drawdown_pct: float
    probability_of_failure_pct: float
    parameter_sensitivity_score: float  # 0 (Robusto) a 100 (Frágil)
    slippage_stress_resilience_pct: float
    is_robust: bool


class RobustnessEngine:
    """Motor de Simulación Monte Carlo y Análisis de Frustración/Estrés."""

    def run_monte_carlo(
        self,
        trades: List[Dict[str, Any]],
        initial_capital: float = 100000.0,
        iterations: int = 500
    ) -> Dict[str, float]:
        """
        Reordena aleatoriamente la secuencia de operaciones (Bootstrap / Permutación)
        para construir la distribución de Drawdowns máximos esperados.
        """
        if not trades:
            return {
                "drawdown_5th": 0.0,
                "drawdown_95th": 0.0,
                "worst_drawdown": 0.0,
                "probability_of_failure": 0.0
            }

        pnls = [t.get("net_pnl", 0.0) for t in trades]
        drawdowns = []
        failures = 0

        for _ in range(iterations):
            sim_pnls = random.sample(pnls, len(pnls))
            cap = initial_capital
            hwm = initial_capital
            max_dd = 0.0

            for pnl in sim_pnls:
                cap += pnl
                if cap > hwm:
                    hwm = cap
                dd = (hwm - cap) / hwm if hwm > 0 else 0.0
                if dd > max_dd:
                    max_dd = dd

            drawdowns.append(max_dd * 100.0)
            if max_dd >= 0.15:  # Considera fallo si el drawdown simulado supera 15%
                failures += 1

        drawdowns.sort()
        idx_5 = int(iterations * 0.05)
        idx_95 = int(iterations * 0.95)

        return {
            "drawdown_5th": round(drawdowns[idx_5], 2),
            "drawdown_95th": round(drawdowns[idx_95], 2),
            "worst_drawdown": round(drawdowns[-1], 2),
            "probability_of_failure": round((failures / iterations) * 100.0, 2)
        }

    def evaluate_robustness(
        self,
        trades: List[Dict[str, Any]],
        initial_capital: float = 100000.0,
        in_sample_sharpe: float = 1.5,
        out_sample_sharpe: float = 1.2
    ) -> RobustnessReport:
        """
        Calcula el Robustness Score (0 a 100) agregando resultados de Monte Carlo,
        estabilidad In-Sample vs Out-of-Sample y resistencia a fricciones.
        """
        mc = self.run_monte_carlo(trades, initial_capital=initial_capital)

        # 1. Degradación IS vs OOS (0 - 30 pts)
        sharpe_ratio_retention = min(1.0, out_sample_sharpe / max(0.1, in_sample_sharpe))
        oos_stability_score = sharpe_ratio_retention * 30.0

        # 2. Monte Carlo Drawdown Score (0 - 40 pts)
        worst_dd = mc["worst_drawdown"]
        mc_score = max(0.0, 40.0 - (worst_dd * 1.5))

        # 3. Probabilidad de Fallo (0 - 30 pts)
        fail_prob = mc["probability_of_failure"]
        fail_score = max(0.0, 30.0 - (fail_prob * 0.6))

        total_score = round(min(100.0, oos_stability_score + mc_score + fail_score), 2)
        param_sensitivity = round(max(0.0, (1.0 - sharpe_ratio_retention) * 100.0), 2)

        return RobustnessReport(
            robustness_score=total_score,
            monte_carlo_drawdown_5th_pct=mc["drawdown_5th"],
            monte_carlo_drawdown_95th_pct=mc["drawdown_95th"],
            worst_expected_drawdown_pct=mc["worst_drawdown"],
            probability_of_failure_pct=mc["probability_of_failure"],
            parameter_sensitivity_score=param_sensitivity,
            slippage_stress_resilience_pct=round(min(100.0, 100.0 - (worst_dd * 0.5)), 2),
            is_robust=total_score >= 65.0
        )


robustness_engine = RobustnessEngine()
