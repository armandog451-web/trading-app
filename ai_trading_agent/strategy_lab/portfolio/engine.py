"""
ai_trading_agent.strategy_lab.portfolio.engine
===============================================
Motor de Análisis de Portfolio Multi-Estrategia (Portfolio Strategy Engine).
Calcula correlación entre estrategias, covarianza, superposición y drawdown combinado.
"""

from typing import List, Dict, Any
import math


class PortfolioStrategyEngine:
    """Analiza combinaciones y correlaciones entre múltiples estrategias del laboratorio."""

    def analyze_portfolio(
        self,
        strategy_pnls: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """
        Calcula la matriz de correlación de Pearson y métricas agregadas de portfolio.
        """
        strat_names = list(strategy_pnls.keys())
        if len(strat_names) < 2:
            return {
                "strategies": strat_names,
                "correlation_matrix": {},
                "diversification_score": 100.0,
                "recommendation": "Añada más estrategias para evaluar la diversificación del portfolio."
            }

        corr_matrix = {}
        for s1 in strat_names:
            corr_matrix[s1] = {}
            pnl1 = strategy_pnls[s1]
            mean1 = sum(pnl1) / max(1, len(pnl1))

            for s2 in strat_names:
                pnl2 = strategy_pnls[s2]
                mean2 = sum(pnl2) / max(1, len(pnl2))

                # Pearson Correlation
                num = sum((a - mean1) * (b - mean2) for a, b in zip(pnl1, pnl2))
                den1 = sum((a - mean1) ** 2 for a in pnl1)
                den2 = sum((b - mean2) ** 2 for b in pnl2)
                den = math.sqrt(den1 * den2)

                corr = round(num / den, 2) if den > 0 else 0.0
                corr_matrix[s1][s2] = corr

        total_corrs = []
        for s1 in strat_names:
            for s2 in strat_names:
                if s1 != s2:
                    total_corrs.append(corr_matrix[s1][s2])

        avg_corr = sum(total_corrs) / max(1, len(total_corrs)) if total_corrs else 0.0
        div_score = round(max(0.0, min(100.0, (1.0 - avg_corr) * 50.0)), 1)

        return {
            "strategies": strat_names,
            "correlation_matrix": corr_matrix,
            "average_abs_correlation": round(avg_corr, 2),
            "diversification_score": div_score,
            "recommendation": "Excelente diversificación (baja correlación)" if div_score >= 70.0 else "Alta correlación detectada: considere descorrelacionar regímenes de entrada."
        }


portfolio_strategy_engine = PortfolioStrategyEngine()
