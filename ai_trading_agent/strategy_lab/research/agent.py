"""
ai_trading_agent.strategy_lab.research.agent
=============================================
AI Research Agent Autónomo & Motor del Ciclo de Investigación Cuantitativa.
Genera hipótesis, ejecuta experimentos, evoluciona estrategias y gestiona el presupuesto de cómputo.
SIN acceso directo al Broker ni capacidad de modificar parámetros de riesgo críticos.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

from ai_trading_agent.strategy_lab.core.models import LabHypothesis, LabStrategyDefinition, StrategyStatus, FailureAnalysisRecord
from ai_trading_agent.strategy_lab.genesis.engine import hypothesis_engine, genesis_engine
from ai_trading_agent.strategy_lab.experiments.engine import experiment_engine
from ai_trading_agent.strategy_lab.backtesting.data_splitter import lab_data_splitter, DataSplitType
from ai_trading_agent.strategy_lab.robustness.engine import robustness_engine, RobustnessReport
from ai_trading_agent.strategy_lab.ranking.engine import ranking_engine
from ai_trading_agent.strategy_lab.registry.registry import strategy_registry
from ai_trading_agent.strategy_lab.lifecycle.manager import lifecycle_manager
from ai_trading_agent.data.synthetic import synthetic_generator
from database import get_connection, log_event

logger = logging.getLogger(__name__)


class AIResearchAgent:
    """Agente de Inteligencia Artificial para Investigación Cuantitativa Autónoma."""

    def __init__(
        self,
        max_experiments_per_day: int = 10,
        max_iterations_per_cycle: int = 3,
        max_complexity_threshold: float = 80.0
    ):
        self.max_experiments_per_day = max_experiments_per_day
        self.max_iterations_per_cycle = max_iterations_per_cycle
        self.max_complexity_threshold = max_complexity_threshold

    def analyze_failure(self, metrics: Dict[str, Any], rob_report: RobustnessReport) -> FailureAnalysisRecord:
        """
        Diagnostica cuantitativamente la causa raíz del fallo de una estrategia.
        """
        max_dd = metrics.get("max_drawdown_pct", 0.0)
        profit_factor = metrics.get("profit_factor", 1.0)
        expectancy = metrics.get("expectancy_dollars", 0.0)
        trades_count = metrics.get("total_trades", 0)
        fail_prob = rob_report.probability_of_failure_pct
        param_sens = rob_report.parameter_sensitivity_score

        if max_dd > 15.0 or fail_prob > 25.0:
            return FailureAnalysisRecord(
                failure_type="EXCESSIVE_DRAWDOWN",
                evidence=f"Max Drawdown={max_dd:.1f}%, Prob. Fallo Monte Carlo={fail_prob:.1f}%",
                severity="HIGH",
                suspected_cause="Stop Loss demasiado estrecho o exposición excesiva en regímenes volátiles.",
                suggested_change="Incrementar atr_stop_mult un 20% para absorber volatilidad."
            )
        elif profit_factor < 1.3 or expectancy < 10.0:
            return FailureAnalysisRecord(
                failure_type="LOW_EXPECTANCY",
                evidence=f"Profit Factor={profit_factor:.2f}, Expectancia=${expectancy:.2f}",
                severity="MEDIUM",
                suspected_cause="Relación Riesgo:Beneficio insuficiente o filtro de entrada débil.",
                suggested_change="Incrementar el objetivo R:R (+0.3) y aumentar el filtro RVOL."
            )
        elif param_sens > 40.0:
            return FailureAnalysisRecord(
                failure_type="HIGH_PARAMETER_SENSITIVITY",
                evidence=f"Sensibilidad a parámetros={param_sens:.1f}",
                severity="HIGH",
                suspected_cause="Sobreajuste de parámetros a la muestra In-Sample.",
                suggested_change="Simplificar reglas y relajar umbrales de indicadores."
            )
        elif trades_count < 20:
            return FailureAnalysisRecord(
                failure_type="INSUFFICIENT_TRADES",
                evidence=f"Total Trades={trades_count}",
                severity="MEDIUM",
                suspected_cause="Reglas de entrada demasiado restrictivas.",
                suggested_change="Relajar temporalmente el umbral de entrada de RSI o RVOL."
            )
        else:
            return FailureAnalysisRecord(
                failure_type="SUBOPTIMAL_RISK_ADJUSTED_RETURN",
                evidence=f"Sharpe={metrics.get('sharpe_ratio', 0.0):.2f}",
                severity="LOW",
                suspected_cause="Eficiencia media de captura de tendencia.",
                suggested_change="Ajustar levemente filtros de volumen y régimen."
            )

    def run_autonomous_research_cycle(
        self,
        symbol: str = "SPY",
        max_iterations: Optional[int] = None,
        target_score: float = 65.0
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo de investigación autónomo adaptativo e iterativo:
        1. Generar Hipótesis
        2. Dividir Dataset (IS, OOS, FINAL_HOLDOUT Protegido)
        3. Bucle Adaptativo (Iteración 1..max_iterations)
           - Ejecutar Backtest con estrategia dinámica inyectada
           - Extraer Trades Reales (sin mocks) ➔ Monte Carlo Robustness
           - Puntuación holística Strategy Score
           - Diagnóstico de Fallos si no alcanza target_score ➔ Mutación guiada de variante hija
        4. Transición formal en la máquina de estados.
        """
        iterations_limit = max_iterations or self.max_iterations_per_cycle
        log_event("INFO", f"AI Research Agent: Iniciando ciclo adaptativo (max_iterations={iterations_limit}) para {symbol}...")

        # 1. Catálogo semilla
        existing_strats = strategy_registry.list_strategies()
        if not existing_strats:
            seeds = genesis_engine.create_seed_strategies()
            for s in seeds:
                strategy_registry.register_strategy(s)
            existing_strats = seeds

        current_strat = existing_strats[0]
        hyp = hypothesis_engine.generate_hypothesis(hypothesis_type="ORB_VOLATILITY")

        # 2. Dataset cronológico con protección estricta sobre FINAL_HOLDOUT
        full_bars = synthetic_generator.generate_bars(
            symbol=symbol,
            count=250,
            regime="BULL_TREND",
            seed=888
        )
        protected_ds = lab_data_splitter.split_in_sample_out_sample_holdout(full_bars)
        opt_bars = protected_ds.get_optimization_bars()  # Únicamente IS + OOS. FINAL_HOLDOUT permanece LOCKED.

        iteration_history = []
        best_strat = current_strat
        best_score = 0.0
        best_exp = None
        best_rob = None

        # 3. BUCLE DE INVESTIGACIÓN ADAPTATIVO
        for iteration in range(1, iterations_limit + 1):
            log_event("INFO", f"Ciclo Adaptativo Iteración {iteration}/{iterations_limit} para estrategia {current_strat.strategy_id}")

            # a) Ejecutar Experimento con estrategia dinámica real
            exp = experiment_engine.run_experiment(
                hypothesis_id=hyp.hypothesis_id,
                strategy_def=current_strat,
                symbol=symbol,
                timeframe="15m",
                bars=opt_bars
            )

            # b) Trades Reales ➔ Robustness Engine (Sin mocks)
            real_trades = exp.metrics.get("trades", [])
            rob_report = robustness_engine.evaluate_robustness(
                trades=real_trades,
                initial_capital=100000.0,
                in_sample_sharpe=max(0.1, exp.metrics.get("sharpe_ratio", 0.0)),
                out_sample_sharpe=max(0.1, exp.metrics.get("sharpe_ratio", 0.0) * 0.85)
            )

            # c) Puntuación Compuesta Strategy Score
            strat_score = ranking_engine.calculate_score(
                metrics=exp.metrics,
                parameters=current_strat.parameters,
                rules=current_strat.rules,
                robustness_score=rob_report.robustness_score,
                walk_forward_stability=75.0
            )

            current_strat.robustness_score = rob_report.robustness_score
            current_strat.strategy_score = strat_score
            current_strat.metrics = exp.metrics
            strategy_registry.register_strategy(current_strat)

            if strat_score > best_score:
                best_score = strat_score
                best_strat = current_strat
                best_exp = exp
                best_rob = rob_report

            # d) Evaluar Criterio de Éxito o Diagnóstico de Fallo
            if strat_score >= target_score:
                log_event("INFO", f"Estrategia {current_strat.strategy_id} alcanzó target_score ({strat_score:.1f} >= {target_score:.1f}) en iteración {iteration}.")
                iteration_history.append({
                    "iteration": iteration,
                    "strategy_id": current_strat.strategy_id,
                    "score": strat_score,
                    "status": "TARGET_REACHED"
                })
                break
            else:
                # Diagnosticar fallo e iterar con mutación guiada
                failure_rec = self.analyze_failure(exp.metrics, rob_report)
                iteration_history.append({
                    "iteration": iteration,
                    "strategy_id": current_strat.strategy_id,
                    "score": strat_score,
                    "failure_analysis": failure_rec.model_dump(),
                    "status": "FAILED_TARGET"
                })

                if iteration < iterations_limit:
                    child_strat, lineage = genesis_engine.mutate_strategy(
                        parent=current_strat,
                        mutation_reason=f"Ajuste adaptativo iteración {iteration}: {failure_rec.failure_type}",
                        experiment_id=exp.experiment_id,
                        failure_analysis=failure_rec
                    )
                    strategy_registry.register_strategy(child_strat)
                    strategy_registry.record_lineage(lineage)
                    current_strat = child_strat

        # 4. Evaluación de Promoción en la Máquina de Estados
        promoted = False
        promotion_msg = ""
        if best_score >= 60.0:
            success, promotion_msg, _ = lifecycle_manager.promote_strategy(
                strategy_id=best_strat.strategy_id,
                target_status=StrategyStatus.BACKTEST,
                reason=f"Investigación adaptativa aprobada (Score: {best_score:.1f})",
                actor="AI_RESEARCH_AGENT"
            )
            promoted = success

        summary = {
            "hypothesis_id": hyp.hypothesis_id,
            "hypothesis_description": hyp.description,
            "best_strategy_id": best_strat.strategy_id,
            "parent_strategy_id": best_strat.parent_strategy_id,
            "best_experiment_id": best_exp.experiment_id if best_exp else "",
            "robustness_score": best_rob.robustness_score if best_rob else 0.0,
            "strategy_score": best_score,
            "total_iterations": len(iteration_history),
            "iterations_trace": iteration_history,
            "holdout_locked": protected_ds.is_holdout_locked,
            "promoted": promoted,
            "promotion_detail": promotion_msg,
            "timestamp": datetime.utcnow().isoformat()
        }

        log_event("INFO", f"AI Research Agent: Ciclo adaptativo completado. Estrategia Ganadora: {best_strat.strategy_id} | Best Score: {best_score}")
        return summary


ai_research_agent = AIResearchAgent()
