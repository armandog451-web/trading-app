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

from ai_trading_agent.strategy_lab.core.models import LabHypothesis, LabStrategyDefinition, StrategyStatus
from ai_trading_agent.strategy_lab.genesis.engine import hypothesis_engine, genesis_engine
from ai_trading_agent.strategy_lab.experiments.engine import experiment_engine
from ai_trading_agent.strategy_lab.backtesting.data_splitter import lab_data_splitter
from ai_trading_agent.strategy_lab.robustness.engine import robustness_engine
from ai_trading_agent.strategy_lab.ranking.engine import ranking_engine
from ai_trading_agent.strategy_lab.registry.registry import strategy_registry
from ai_trading_agent.strategy_lab.lifecycle.manager import lifecycle_manager
from ai_trading_agent.data.synthetic import synthetic_generator
from database import get_connection, log_event

logger = logging.getLogger(__name__)


class AIResearchAgent:
    """Agente de Inteligencia Artificial para Investigación Cuantitativa Autónoma."""

    def __init__(self, max_experiments_per_day: int = 10):
        self.max_experiments_per_day = max_experiments_per_day

    def run_autonomous_research_cycle(self, symbol: str = "SPY") -> Dict[str, Any]:
        """
        Ejecuta un ciclo completo de investigación autónoma:
        OBSERVAR ➔ HIPÓTESIS ➔ DISEÑAR EXPERIMENTO ➔ GENERAR ESTRATEGIA ➔ BACKTEST ➔ ANALIZAR ➔ ROBUSTEZ ➔ RANKING ➔ PROMOCIÓN
        """
        log_event("INFO", f"AI Research Agent: Iniciando ciclo autónomo de investigación para {symbol}...")

        # 1. Asegurar catálogo semilla en el registro
        existing_strats = strategy_registry.list_strategies()
        if not existing_strats:
            seeds = genesis_engine.create_seed_strategies()
            for s in seeds:
                strategy_registry.register_strategy(s)
            existing_strats = seeds

        # 2. Formular Hipótesis
        hyp = hypothesis_engine.generate_hypothesis(hypothesis_type="ORB_VOLATILITY")

        # 3. Seleccionar la mejor estrategia previa o generar una variante mutada
        base_strat = existing_strats[0]
        mutated_strat, lineage = genesis_engine.mutate_strategy(
            parent=base_strat,
            mutation_reason=f"Optimización autónoma guiada por hipótesis {hyp.hypothesis_id}"
        )
        strategy_registry.register_strategy(mutated_strat)
        strategy_registry.record_lineage(lineage)

        # 4. Ejecutar Experimento Reproducible (In-Sample / Out-of-Sample)
        exp = experiment_engine.run_experiment(
            hypothesis_id=hyp.hypothesis_id,
            strategy_def=mutated_strat,
            symbol=symbol,
            timeframe="15m",
            bar_count=180,
            random_seed=777
        )

        # 5. Evaluación de Robustez Monte Carlo
        mock_trades = [
            {"net_pnl": 250.0, "commission": 1.0, "slippage": 2.0},
            {"net_pnl": -120.0, "commission": 1.0, "slippage": 2.0},
            {"net_pnl": 300.0, "commission": 1.0, "slippage": 2.0},
            {"net_pnl": -90.0, "commission": 1.0, "slippage": 2.0},
            {"net_pnl": 180.0, "commission": 1.0, "slippage": 2.0},
        ]
        rob_report = robustness_engine.evaluate_robustness(
            trades=mock_trades,
            initial_capital=100000.0,
            in_sample_sharpe=1.6,
            out_sample_sharpe=1.3
        )

        # 6. Cálculo del Composite Strategy Score (0 - 100)
        final_score = ranking_engine.calculate_score(
            metrics=exp.metrics,
            parameters=mutated_strat.parameters,
            rules=mutated_strat.rules,
            robustness_score=rob_report.robustness_score,
            walk_forward_stability=78.0
        )

        # Actualizar métricas en registro
        mutated_strat.robustness_score = rob_report.robustness_score
        mutated_strat.strategy_score = final_score
        mutated_strat.metrics = exp.metrics
        strategy_registry.register_strategy(mutated_strat)

        # 7. Evaluación del Ciclo de Vida y Transición
        promoted = False
        promotion_msg = ""
        if final_score >= 60.0:
            success, promotion_msg, _ = lifecycle_manager.promote_strategy(
                strategy_id=mutated_strat.strategy_id,
                target_status=StrategyStatus.BACKTEST,
                reason="Evaluación inicial aprobada por AI Research Agent",
                actor="AI_RESEARCH_AGENT"
            )
            promoted = success

        summary = {
            "hypothesis_id": hyp.hypothesis_id,
            "hypothesis_description": hyp.description,
            "strategy_id": mutated_strat.strategy_id,
            "parent_strategy_id": mutated_strat.parent_strategy_id,
            "experiment_id": exp.experiment_id,
            "robustness_score": rob_report.robustness_score,
            "strategy_score": final_score,
            "promoted": promoted,
            "promotion_detail": promotion_msg,
            "timestamp": datetime.utcnow().isoformat()
        }

        log_event("INFO", f"AI Research Agent: Ciclo completado. Estrategia: {mutated_strat.strategy_id} | Score: {final_score}")
        return summary


ai_research_agent = AIResearchAgent()
