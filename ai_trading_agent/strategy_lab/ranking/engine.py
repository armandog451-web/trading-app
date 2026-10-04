"""
ai_trading_agent.strategy_lab.ranking.engine
=============================================
Motor de Clasificación Compuesta (Strategy Ranking Engine) y Cálculo del Strategy Score (0 - 100).
Recompensa la robustez, simplicidad y desempeño ajustado por riesgo, penalizando el sobreajuste.
"""

from typing import Dict, Any
from ai_trading_agent.strategy_lab.core.models import StrategyComplexityCalculator


class StrategyRankingEngine:
    """Calcula la puntuación holística compuesta (Strategy Score) para cada estrategia del laboratorio."""

    def calculate_score(
        self,
        metrics: Dict[str, Any],
        parameters: Dict[str, Any],
        rules: Dict[str, Any],
        robustness_score: float = 70.0,
        walk_forward_stability: float = 75.0
    ) -> float:
        """
        Calcula el Strategy Score (0 - 100) ponderando:
        + Sharpe / Sortino Ratio (25%)
        + Profit Factor & Expectancy (20%)
        + Robustness Monte Carlo (20%)
        + Walk Forward Stability (15%)
        + Simplicidad (10%)
        - Penalizaciones por Complejidad y Sobreajuste (-10%)
        """
        sharpe = metrics.get("sharpe_ratio", 0.0)
        profit_factor = metrics.get("profit_factor", 1.0)
        total_trades = metrics.get("total_trades", 0)

        # 1. Rendimiento Ajustado por Riesgo (0 - 25 pts)
        risk_adj_score = min(25.0, max(0.0, sharpe * 12.5))

        # 2. Factor de Beneficio y Expectancia (0 - 20 pts)
        pf_score = min(20.0, max(0.0, (profit_factor - 1.0) * 15.0))

        # 3. Robustez Monte Carlo (0 - 20 pts)
        mc_score = (robustness_score / 100.0) * 20.0

        # 4. Estabilidad Walk-Forward (0 - 15 pts)
        wf_score = (walk_forward_stability / 100.0) * 15.0

        # 5. Complejidad (Calculada) y Penalización (0 - 10 pts)
        complexity_score = StrategyComplexityCalculator.calculate(parameters, rules, total_trades)
        simplicity_score = max(0.0, (100.0 - complexity_score) * 0.10)

        # 6. Penalización por Sobreajuste si trades < 25
        overfitting_penalty = 0.0
        if total_trades < 25:
            overfitting_penalty = (25 - total_trades) * 0.4

        final_score = risk_adj_score + pf_score + mc_score + wf_score + simplicity_score - overfitting_penalty
        return round(min(100.0, max(0.0, final_score)), 2)


ranking_engine = StrategyRankingEngine()
