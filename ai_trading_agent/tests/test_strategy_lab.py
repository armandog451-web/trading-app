"""
ai_trading_agent.tests.test_strategy_lab
=========================================
Suite de pruebas unitarias e integración para el Autonomous Strategy Laboratory / Research Engine.
Verifica la hipótesis, génesis, mutación, Monte Carlo, ranking, lifecycle, registry y fronteras de seguridad.
"""

import pytest
from datetime import datetime
from database import init_db

from ai_trading_agent.strategy_lab.core.models import (
    StrategyStatus, HypothesisStatus, StrategyComplexityCalculator, LabStrategyDefinition
)
from ai_trading_agent.strategy_lab.genesis.engine import hypothesis_engine, genesis_engine
from ai_trading_agent.strategy_lab.backtesting.data_splitter import lab_data_splitter
from ai_trading_agent.strategy_lab.robustness.engine import robustness_engine
from ai_trading_agent.strategy_lab.ranking.engine import ranking_engine
from ai_trading_agent.strategy_lab.experiments.engine import experiment_engine
from ai_trading_agent.strategy_lab.registry.registry import strategy_registry
from ai_trading_agent.strategy_lab.lifecycle.manager import lifecycle_manager
from ai_trading_agent.strategy_lab.portfolio.engine import portfolio_strategy_engine
from ai_trading_agent.strategy_lab.research.agent import ai_research_agent
from ai_trading_agent.data.synthetic import synthetic_generator


@pytest.fixture(autouse=True)
def setup_lab_db():
    init_db()


class TestStrategyLaboratory:

    def test_hypothesis_generation(self):
        """Verifica la generación estructurada de hipótesis de investigación."""
        hyp = hypothesis_engine.generate_hypothesis(hypothesis_type="ORB_VOLATILITY")
        assert hyp.hypothesis_id.startswith("HYP-")
        assert hyp.status == HypothesisStatus.NEW
        assert len(hyp.features_used) > 0
        assert "ORB" in hyp.experiment_plan or "15m" in hyp.experiment_plan

    def test_genesis_and_mutation_lineage(self):
        """Verifica la creación de estrategias semilla y la mutación evolutiva con linaje."""
        seeds = genesis_engine.create_seed_strategies()
        assert len(seeds) >= 3
        parent = seeds[0]

        child, lineage = genesis_engine.mutate_strategy(
            parent=parent,
            mutation_reason="Prueba de optimización de RVOL"
        )

        assert child.parent_strategy_id == parent.strategy_id
        assert child.version == "1.1"
        assert lineage.parent_id == parent.strategy_id
        assert lineage.child_id == child.strategy_id

    def test_data_splitter_in_sample_out_sample_holdout(self):
        """Verifica la división temporal cronológica sin fuga de datos."""
        bars = synthetic_generator.generate_bars(symbol="SPY", count=100)
        splits = lab_data_splitter.split_in_sample_out_sample_holdout(bars)

        assert len(splits["IN_SAMPLE"]) == 60
        assert len(splits["OUT_OF_SAMPLE"]) == 20
        assert len(splits["FINAL_HOLDOUT"]) == 20
        # Verificar orden cronológico inmutable
        assert splits["IN_SAMPLE"][-1].timestamp < splits["OUT_OF_SAMPLE"][0].timestamp
        assert splits["OUT_OF_SAMPLE"][-1].timestamp < splits["FINAL_HOLDOUT"][0].timestamp

    def test_robustness_monte_carlo(self):
        """Verifica el cálculo de Monte Carlo y el Robustness Score."""
        trades = [
            {"net_pnl": 150.0}, {"net_pnl": -80.0}, {"net_pnl": 200.0},
            {"net_pnl": -50.0}, {"net_pnl": 120.0}, {"net_pnl": 90.0}
        ]
        report = robustness_engine.evaluate_robustness(trades, initial_capital=10000.0)
        assert 0.0 <= report.robustness_score <= 100.0
        assert report.worst_expected_drawdown_pct >= 0.0

    def test_strategy_complexity_and_ranking_score(self):
        """Verifica la penalización por complejidad y el cálculo del Strategy Score (0-100)."""
        metrics = {"sharpe_ratio": 1.8, "profit_factor": 2.1, "total_trades": 45}
        params = {"min_rvol": 1.5, "atr_stop_mult": 1.5, "rr_target": 2.0}
        rules = {"entry_conditions": ["c1", "c2"], "filters": ["f1"]}

        complexity = StrategyComplexityCalculator.calculate(params, rules, total_trades=45)
        assert 0.0 <= complexity <= 100.0

        score = ranking_engine.calculate_score(metrics, params, rules, robustness_score=75.0)
        assert 0.0 <= score <= 100.0
        assert score >= 50.0  # Estrategia robusta debe obtener buen puntaje

    def test_strategy_registry_sqlite_persistence(self):
        """Verifica la persistencia relacional en SQLite del registro de estrategias."""
        strat = LabStrategyDefinition(
            strategy_id="STR-TEST-001-v1.0",
            name="Test Strategy Registry",
            version="1.0",
            description="Test persistence",
            status=StrategyStatus.RESEARCH,
            robustness_score=65.5,
            strategy_score=72.0
        )
        strategy_registry.register_strategy(strat)

        retrieved = strategy_registry.get_strategy("STR-TEST-001-v1.0")
        assert retrieved is not None
        assert retrieved.name == "Test Strategy Registry"
        assert retrieved.robustness_score == 65.5

    def test_lifecycle_manager_security_gates(self):
        """Verifica que las transiciones no permitidas sean rechazadas por las puertas de seguridad."""
        strat = LabStrategyDefinition(
            strategy_id="STR-GATE-001-v1.0",
            name="Test Gate Strategy",
            version="1.0",
            description="Test security gate",
            status=StrategyStatus.RESEARCH,
            robustness_score=40.0,  # Bajo score
            strategy_score=50.0
        )
        strategy_registry.register_strategy(strat)

        # 1. Intento inválido: RESEARCH -> APPROVED directo
        success, msg, _ = lifecycle_manager.promote_strategy(
            strategy_id="STR-GATE-001-v1.0",
            target_status=StrategyStatus.APPROVED,
            reason="Salto directo prohibido"
        )
        assert success is False
        assert "TRANSICIÓN DENEGADA" in msg

        # 2. Transición válida: RESEARCH -> BACKTEST
        success2, msg2, strat2 = lifecycle_manager.promote_strategy(
            strategy_id="STR-GATE-001-v1.0",
            target_status=StrategyStatus.BACKTEST,
            reason="Promoción a Backtest"
        )
        assert success2 is True
        assert strat2.status == StrategyStatus.BACKTEST

    def test_portfolio_strategy_correlation(self):
        """Verifica la matriz de correlación entre múltiples estrategias."""
        pnls = {
            "STR-A": [100.0, -50.0, 150.0, -30.0, 80.0],
            "STR-B": [-50.0, 100.0, -80.0, 120.0, -40.0]
        }
        res = portfolio_strategy_engine.analyze_portfolio(pnls)
        assert "STR-A" in res["correlation_matrix"]
        assert res["diversification_score"] > 50.0

    def test_ai_research_agent_autonomous_cycle(self):
        """Verifica la ejecución del ciclo autónomo de investigación."""
        res = ai_research_agent.run_autonomous_research_cycle(symbol="SPY")
        assert "hypothesis_id" in res
        assert "strategy_id" in res
        assert "strategy_score" in res
        assert res["strategy_score"] > 0.0
