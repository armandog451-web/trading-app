"""
ai_trading_agent.strategy_lab.discovery.orchestrator
====================================================
Orquestador Principal del Autonomous Strategy Discovery Engine v1.0.
Ejecuta el ciclo continuo de descubrimiento quantitative:
DISCOVER -> HYPOTHESIZE -> GENERATE -> EXPERIMENT -> BACKTEST -> VALIDATE -> LEARN -> EVOLVE -> RANK -> PROMOTE/REJECT.
"""

import uuid
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.core.models import (
    LabStrategyDefinition,
    StrategyStatus,
    StrategyLifecycleStatus,
    StrategyLineage
)
from ai_trading_agent.strategy_lab.discovery.feature_universe import feature_universe, FeatureUniverseCatalog
from ai_trading_agent.strategy_lab.discovery.hypothesis_generator import HypothesisGenerator, DiscoveryHypothesis
from ai_trading_agent.strategy_lab.discovery.strategy_genesis import AutonomousStrategyGenesisEngine
from ai_trading_agent.strategy_lab.discovery.mutation_engine import ExtendedMutationEngine
from ai_trading_agent.strategy_lab.discovery.research_memory import ResearchMemory
from ai_trading_agent.strategy_lab.discovery.experiment_prioritizer import (
    ExperimentPriorityEngine,
    calculate_novelty_score,
    calculate_overfitting_risk_score
)
from ai_trading_agent.strategy_lab.experiments.engine import ExperimentEngine
from ai_trading_agent.strategy_lab.robustness.engine import RobustnessEngine
from ai_trading_agent.strategy_lab.registry.registry import strategy_registry, StrategyRegistry
from ai_trading_agent.strategy_lab.lifecycle.manager import LifecycleManager


class ResearchBudget(BaseModel):
    """Presupuesto de Recursos para la Sesión de Investigación."""
    max_experiments: int = 10
    max_time_seconds: int = 300
    max_overfitting_risk: float = 70.0
    min_required_sharpe: float = 1.0
    target_win_rate: float = 0.50


class ResearchSession(BaseModel):
    """Estado y resumen de una Sesión de Descubrimiento Autónomo."""
    session_id: str = Field(default_factory=lambda: f"session_{uuid.uuid4().hex[:8]}")
    budget: ResearchBudget = Field(default_factory=ResearchBudget)
    status: str = "INITIALIZED"  # INITIALIZED, RUNNING, COMPLETED, STOPPED_BUDGET_EXHAUSTED, FAILED
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    hypotheses_generated: int = 0
    experiments_run: int = 0
    strategies_promoted: int = 0


class DiscoveryReport(BaseModel):
    """Informe final estructurado de la sesión de descubrimiento."""
    session_id: str
    status: str
    summary: Dict[str, Any]
    hypotheses: List[Dict[str, Any]]
    experiments: List[Dict[str, Any]]
    promoted_strategies: List[str]
    memory_stats: Dict[str, Any]


class DiscoveryOrchestrator:
    """Orquestador Autónomo de Investigación Cuantitativa y Descubrimiento de Estrategias."""

    def __init__(
        self,
        catalog: Optional[FeatureUniverseCatalog] = None,
        registry: Optional[StrategyRegistry] = None,
        db_path: Optional[str] = "ai_trading_app.db"
    ):
        self.catalog = catalog or feature_universe
        self.registry = registry or strategy_registry
        self.hypothesis_gen = HypothesisGenerator(catalog=self.catalog)
        self.genesis_engine = AutonomousStrategyGenesisEngine()
        self.mutation_engine = ExtendedMutationEngine()
        self.memory = ResearchMemory(db_path=db_path)
        self.prioritizer = ExperimentPriorityEngine()
        self.experiment_engine = ExperimentEngine()
        self.robustness_engine = RobustnessEngine()
        self.lifecycle_manager = LifecycleManager()

    def run_autonomous_research_session(
        self,
        budget: Optional[ResearchBudget] = None,
        dataset_bars: Optional[List[OHLCVBar]] = None,
        target_market: str = "BTC/USDT",
        target_timeframe: str = "1h"
    ) -> DiscoveryReport:
        """
        Ejecuta una sesión completa de investigación y descubrimiento autónomo.
        Garantiza aislamiento estricto (NO accesos al broker, NO promociones prohibidas, NO Holdout data leakage).
        """
        active_budget = budget or ResearchBudget()
        session = ResearchSession(budget=active_budget)
        session.status = "RUNNING"
        start_ts = time.time()

        hypotheses_records = []
        experiments_records = []
        promoted_ids = []

        families = ["TREND_FOLLOWING", "MEAN_REVERSION", "VOLATILITY_BREAKOUT", "REGIME_FILTERED"]

        try:
            for family in families:
                if session.experiments_run >= active_budget.max_experiments:
                    session.status = "STOPPED_BUDGET_EXHAUSTED"
                    break

                if (time.time() - start_ts) > active_budget.max_time_seconds:
                    session.status = "STOPPED_TIME_LIMIT"
                    break

                # 1. Generar Hipótesis
                failed_feats = [f["features"][0] for f in self.memory.get_failed_patterns() if f.get("features")]
                hyp = self.hypothesis_gen.generate_hypothesis(
                    strategy_type=family,
                    target_market=target_market,
                    target_timeframe=target_timeframe,
                    past_failed_features=failed_feats
                )
                session.hypotheses_generated += 1
                hypotheses_records.append(hyp.model_dump())

                # 2. Strategy Genesis
                strat_inst, strat_def = self.genesis_engine.generate_from_hypothesis(hyp)

                # 3. Priorización & Evaluación de Sobreajuste
                existing = self.registry.list_strategies()
                prioritized = self.prioritizer.prioritize_experiments([strat_def], existing, self.memory)
                strat_def, priority_score = prioritized[0]

                overfit_risk = calculate_overfitting_risk_score(strat_def)
                if overfit_risk > active_budget.max_overfitting_risk:
                    # Descartar por alto riesgo de sobreajuste
                    self.memory.record_experiment(
                        hypothesis_id=hyp.hypothesis_id,
                        strategy_id=strat_def.strategy_id,
                        features=hyp.features,
                        parameters=strat_def.parameters,
                        metrics={"sharpe_ratio": 0.0},
                        failure_reason=f"Exceso de riesgo de sobreajuste ({overfit_risk:.1f} > {active_budget.max_overfitting_risk:.1f})"
                    )
                    continue

                # 4. Registrar en Registry
                self.registry.register_strategy(strat_def)

                # 5. Ejecutar Experimento
                exp_result = self.experiment_engine.run_experiment(
                    strategy=strat_inst,
                    bars=dataset_bars,
                    parameters=strat_def.parameters,
                    name=f"Exp_{strat_def.name}"
                )
                session.experiments_run += 1

                metrics = exp_result.metrics
                sharpe = float(metrics.get("sharpe_ratio", 0.0))
                win_rate = float(metrics.get("win_rate", 0.0))

                experiments_records.append({
                    "experiment_id": exp_result.experiment_id,
                    "strategy_id": strat_def.strategy_id,
                    "sharpe_ratio": sharpe,
                    "win_rate": win_rate,
                    "metrics": metrics
                })

                # 6. Memoria
                fail_reason = None
                if sharpe < active_budget.min_required_sharpe:
                    fail_reason = f"Sharpe Insuficiente ({sharpe:.2f} < {active_budget.min_required_sharpe:.2f})"

                self.memory.record_experiment(
                    hypothesis_id=hyp.hypothesis_id,
                    strategy_id=strat_def.strategy_id,
                    features=hyp.features,
                    parameters=strat_def.parameters,
                    metrics=metrics,
                    failure_reason=fail_reason
                )

                # 7. Si cumple criterios, evaluar mutación y ciclo de promoción
                if sharpe >= active_budget.min_required_sharpe and win_rate >= active_budget.target_win_rate:
                    # Robustness testing con trades reales
                    trades_list = exp_result.metrics.get("trades", [])
                    robustness = self.robustness_engine.run_full_robustness_battery(trades_list)
                    strat_def.robustness_score = robustness.get("robustness_score", 60.0)
                    strat_def.metrics = metrics
                    self.registry.register_strategy(strat_def)

                    # Intentar promoción mediante LifecycleManager (RESEARCH -> VALIDATING -> CANDIDATE / PAPER)
                    try:
                        self.lifecycle_manager.transition(strat_def.strategy_id, StrategyLifecycleStatus.VALIDATING)
                        self.lifecycle_manager.transition(strat_def.strategy_id, StrategyLifecycleStatus.CANDIDATE)
                        promoted_ids.append(strat_def.strategy_id)
                        session.strategies_promoted += 1
                    except Exception as le:
                        print(f"[DiscoveryOrchestrator] Restricción de ciclo de vida: {le}")

                    # Intentar Mutación Evolutiva para crear variante de alta calidad
                    child_inst, child_def, mut_rec = self.mutation_engine.mutate_strategy(
                        strategy=strat_inst,
                        definition=strat_def,
                        mutation_type="PARAMETER_PERTURBATION"
                    )
                    self.registry.register_strategy(child_def)
                    self.registry.record_lineage(StrategyLineage(
                        parent_id=strat_def.strategy_id,
                        child_id=child_def.strategy_id,
                        mutation_description=mut_rec.expected_effect,
                        reason="Mutación evolutiva de estrategia exitosa",
                        experiment_id=exp_result.experiment_id
                    ))

            if session.status == "RUNNING":
                session.status = "COMPLETED"

        except Exception as e:
            session.status = "FAILED"
            print(f"[DiscoveryOrchestrator] Error durante la sesión de investigación: {e}")

        session.end_time = datetime.now(timezone.utc).isoformat()

        report = DiscoveryReport(
            session_id=session.session_id,
            status=session.status,
            summary={
                "duration_seconds": round(time.time() - start_ts, 2),
                "hypotheses_generated": session.hypotheses_generated,
                "experiments_run": session.experiments_run,
                "strategies_promoted": session.strategies_promoted,
            },
            hypotheses=hypotheses_records,
            experiments=experiments_records,
            promoted_strategies=promoted_ids,
            memory_stats={
                "top_features": self.memory.get_top_performing_features(top_n=5),
                "failed_patterns_count": len(self.memory.get_failed_patterns()),
                "total_observations": len(self.memory.get_all_observations())
            }
        )

        return report
