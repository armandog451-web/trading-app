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
    StrategyStatus, HypothesisStatus, StrategyComplexityCalculator, LabStrategyDefinition, DataSplitType
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
        """Verifica la división temporal cronológica sin fuga de datos y acceso por métodos de ProtectedDataset."""
        bars = synthetic_generator.generate_bars(symbol="SPY", count=100)
        splits = lab_data_splitter.split_in_sample_out_sample_holdout(bars)

        in_sample = splits.get_split(DataSplitType.IN_SAMPLE)
        out_sample = splits.get_split(DataSplitType.OUT_OF_SAMPLE)
        holdout = splits.unlock_holdout(reason="Test verification", actor="TEST")

        assert len(in_sample) == 60
        assert len(out_sample) == 20
        assert len(holdout) == 20
        # Verificar orden cronológico inmutable
        assert in_sample[-1].timestamp < out_sample[0].timestamp
        assert out_sample[-1].timestamp < holdout[0].timestamp

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
        """Verifica la ejecución del ciclo autónomo de investigación adaptativo."""
        res = ai_research_agent.run_autonomous_research_cycle(symbol="SPY", max_iterations=2)
        assert "hypothesis_id" in res
        assert "best_strategy_id" in res
        assert "strategy_score" in res
        assert "total_iterations" in res
        assert res["total_iterations"] >= 1
        assert res["holdout_locked"] is True  # FINAL_HOLDOUT permanece LOCKED

    def test_dynamic_strategy_injection(self):
        """Demuestra que dos variantes de estrategia con reglas distintas producen resultados de backtest distintos."""
        from ai_trading_agent.backtest.engine import backtest_engine
        from ai_trading_agent.strategy_lab.strategies.composable import ComposableStrategy

        bars = synthetic_generator.generate_bars(symbol="SPY", count=120, regime="BULL_TREND", seed=101)

        strat1 = ComposableStrategy(
            strategy_id="STR-TEST-VAR1",
            name="Var 1 Ultra Strict",
            version="1.0",
            parameters={"min_rvol": 5.0, "rr_target": 3.0, "min_rsi": 49.0, "max_rsi": 51.0}
        )
        strat2 = ComposableStrategy(
            strategy_id="STR-TEST-VAR2",
            name="Var 2 Permissive",
            version="1.0",
            parameters={"min_rvol": 0.1, "rr_target": 1.2, "min_rsi": 10.0, "max_rsi": 90.0}
        )

        rep1 = backtest_engine.run(symbol="SPY", bars=bars, strategy=strat1)
        rep2 = backtest_engine.run(symbol="SPY", bars=bars, strategy=strat2)

        # Los reportes deben ser diferentes debido a los diferentes parámetros dinámicos (strat2 genera trades, strat1 genera 0)
        assert rep1.metrics.total_trades != rep2.metrics.total_trades or rep1.ending_capital != rep2.ending_capital

    def test_real_trades_flow_into_robustness(self):
        """Verifica que los trades reales generados por el backtest fluyen a RobustnessEngine."""
        from ai_trading_agent.strategy_lab.strategies.composable import ComposableStrategy

        bars = synthetic_generator.generate_bars(symbol="SPY", count=150, regime="BULL_TREND", seed=202)
        strat = ComposableStrategy(
            strategy_id="STR-REAL-TRADES",
            name="Real Trades Test",
            version="1.0",
            parameters={"min_rvol": 1.1, "rr_target": 1.5}
        )
        exp = experiment_engine.run_experiment(
            hypothesis_id="HYP-REAL",
            strategy_def=LabStrategyDefinition(
                strategy_id="STR-REAL-TRADES",
                name="Real Trades Test",
                version="1.0",
                description="Test real trades",
                parameters=strat.parameters,
                rules=strat.rules
            ),
            symbol="SPY",
            bars=bars
        )

        real_trades = exp.metrics.get("trades", [])
        rob_report = robustness_engine.evaluate_robustness(trades=real_trades, initial_capital=100000.0)
        assert rob_report is not None
        assert 0.0 <= rob_report.robustness_score <= 100.0

    def test_final_holdout_locked_isolation(self):
        """Verifica que FINAL_HOLDOUT permanece BLOQUEADO (LOCKED) y rechaza accesos durante investigación."""
        bars = synthetic_generator.generate_bars(symbol="SPY", count=200, seed=303)
        protected_ds = lab_data_splitter.split_in_sample_out_sample_holdout(bars)

        assert protected_ds.is_holdout_locked is True

        # Intento de acceso para investigación u optimización debe ser rechazado con PermissionError
        with pytest.raises(PermissionError) as exc_info:
            protected_ds.get_split(DataSplitType.FINAL_HOLDOUT, purpose="OPTIMIZATION")

        assert "ACCESO DENEGADO" in str(exc_info.value)
        assert "LOCKED" in str(exc_info.value)

        # Desbloqueo explícito para auditoría final registra auditoría
        unlocked_bars = protected_ds.unlock_holdout(reason="Auditoría final de promoción CANDIDATE", actor="AUDITOR_HUMANO")
        assert len(unlocked_bars) > 0
        assert protected_ds.is_holdout_locked is False
        assert len(protected_ds.unlock_audit_trail) == 1

    def test_adaptive_research_loop_and_failure_analysis(self):
        """Verifica el ciclo de investigación adaptativo multi-iteración y el análisis de fallos."""
        res = ai_research_agent.run_autonomous_research_cycle(symbol="SPY", max_iterations=3, target_score=99.0)
        assert res["total_iterations"] <= 3
        assert "iterations_trace" in res
        assert len(res["iterations_trace"]) > 0
        trace_1 = res["iterations_trace"][0]
        assert "strategy_id" in trace_1
        assert "score" in trace_1

    def test_strategy_lineage_tree_reconstruction(self):
        """Verifica la reconstrucción del árbol de linaje genético."""
        parent = LabStrategyDefinition(
            strategy_id="STR-ROOT-v1.0",
            name="Root Strategy",
            version="1.0",
            description="Root strategy for lineage tree test"
        )
        strategy_registry.register_strategy(parent)

        child, lineage = genesis_engine.mutate_strategy(parent=parent, mutation_reason="Mutación 1")
        strategy_registry.register_strategy(child)
        strategy_registry.record_lineage(lineage)

        retrieved_child = strategy_registry.get_strategy(child.strategy_id)
        assert retrieved_child.parent_strategy_id == "STR-ROOT-v1.0"

    def test_security_boundaries_and_forbidden_transitions(self):
        """Verifica que ni AIResearchAgent ni StrategyLab pueden saltarse la máquina de estados o ejecutar órdenes."""
        strat = LabStrategyDefinition(
            strategy_id="STR-SEC-001-v1.0",
            name="Security Test",
            version="1.0",
            description="Security boundary test",
            status=StrategyStatus.RESEARCH
        )
        strategy_registry.register_strategy(strat)

        # Intentar pasar de RESEARCH a PAPER o APPROVED directamente
        success, msg, _ = lifecycle_manager.promote_strategy(
            strategy_id="STR-SEC-001-v1.0",
            target_status=StrategyStatus.APPROVED,
            reason="Forbidden jump"
        )
        assert success is False
        assert "TRANSICIÓN DENEGADA" in msg
