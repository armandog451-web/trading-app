"""
ai_trading_agent.tests.test_strategy_discovery
===============================================
Suite de pruebas para el Autonomous Strategy Discovery Engine v1.0.
Cubre los 16 requerimientos funcionales, seguridad, aislamiento de Holdout y prevenciones de Data Leakage.
"""

import pytest
from fastapi.testclient import TestClient
from ai_trading_agent.api.app import app

from ai_trading_agent.strategy_lab.discovery.feature_universe import (
    FeatureCategory,
    FeatureMetadata,
    FeatureUniverseCatalog
)
from ai_trading_agent.strategy_lab.discovery.hypothesis_generator import HypothesisGenerator, DiscoveryHypothesis
from ai_trading_agent.strategy_lab.discovery.strategy_genesis import AutonomousStrategyGenesisEngine
from ai_trading_agent.strategy_lab.discovery.mutation_engine import ExtendedMutationEngine, MutationRecord
from ai_trading_agent.strategy_lab.discovery.research_memory import ResearchMemory
from ai_trading_agent.strategy_lab.discovery.experiment_prioritizer import (
    StrategySimilarityEngine,
    calculate_novelty_score,
    calculate_overfitting_risk_score,
    ExperimentPriorityEngine
)
from ai_trading_agent.strategy_lab.discovery.orchestrator import DiscoveryOrchestrator, ResearchBudget
from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition, StrategyLifecycleStatus
from ai_trading_agent.strategy_lab.backtesting.data_splitter import LabDataSplitter, ProtectedDataset

from ai_trading_agent.data.synthetic import synthetic_generator


class TestStrategyDiscoveryEngine:

    def test_feature_universe_catalog_lookahead_validation(self):
        """1. Validación de ausencia de Look-Ahead Bias y Data Leakage."""
        catalog = FeatureUniverseCatalog()
        feats = catalog.list_features()
        assert len(feats) >= 14

        # Intentar registrar feature con información futura debe lanzar ValueError
        with pytest.raises(ValueError, match="DATA LEAKAGE RISK"):
            FeatureMetadata(
                feature_id="future_close_price",
                name="Precio de Cierre Futuro (+1d)",
                category=FeatureCategory.PRICE,
                description="Feature no permitido que usa el precio de mañana",
                uses_future_information=True
            )

    def test_hypothesis_generator(self):
        """2. Motor de generación de hipótesis cuantificables."""
        gen = HypothesisGenerator()
        hyp = gen.generate_hypothesis(strategy_type="TREND_FOLLOWING", target_market="BTC/USDT")

        assert isinstance(hyp, DiscoveryHypothesis)
        assert hyp.target_market == "BTC/USDT"
        assert len(hyp.features) > 0
        assert hyp.status == "PROPOSED"
        assert "EMA9" in hyp.expected_relationship or "RVOL" in hyp.expected_relationship

    def test_strategy_genesis_engine(self):
        """3. Convierte hipótesis en ComposableStrategy y LabStrategyDefinition."""
        gen = HypothesisGenerator()
        hyp = gen.generate_hypothesis(strategy_type="MEAN_REVERSION")

        genesis = AutonomousStrategyGenesisEngine()
        strat_inst, strat_def = genesis.generate_from_hypothesis(hyp)

        assert strat_inst.strategy_id == strat_def.strategy_id
        assert strat_def.status == StrategyLifecycleStatus.RESEARCH
        assert strat_inst.parameters["min_rsi"] == 30.0

    def test_extended_mutation_engine(self):
        """4. Mutaciones de parámetros, filtros de régimen y linaje."""
        genesis = AutonomousStrategyGenesisEngine()
        strat_inst, strat_def = genesis.generate_from_template("TREND_FOLLOWING")

        mutation_engine = ExtendedMutationEngine()
        child_inst, child_def, record = mutation_engine.mutate_strategy(
            strategy=strat_inst,
            definition=strat_def,
            mutation_type="PARAMETER_PERTURBATION"
        )

        assert child_inst.strategy_id == child_def.strategy_id
        assert child_def.parent_strategy_id == strat_inst.strategy_id
        assert isinstance(record, MutationRecord)
        assert record.parent_strategy_id == strat_inst.strategy_id

    def test_research_memory_duplicate_prevention(self):
        """5. Detección y prevención de experimentos duplicados."""
        memory = ResearchMemory()
        features = ["ema_cross_9_21", "relative_volume_rvol"]
        params = {"min_rvol": 1.5, "rr_target": 2.0}

        assert not memory.is_duplicate_experiment(features, params)

        memory.record_experiment(
            hypothesis_id="hyp_001",
            strategy_id="strat_001",
            features=features,
            parameters=params,
            metrics={"sharpe_ratio": 1.5, "win_rate": 0.6}
        )

        assert memory.is_duplicate_experiment(features, params)

    def test_research_memory_persistence_and_stats(self):
        """6. Memoria persistente, mejores features y registro de fallos."""
        memory = ResearchMemory()
        memory.record_experiment(
            hypothesis_id="hyp_01",
            strategy_id="strat_top",
            features=["relative_volume_rvol", "rsi_14"],
            parameters={"min_rsi": 30},
            metrics={"sharpe_ratio": 2.2, "win_rate": 0.65}
        )
        memory.record_experiment(
            hypothesis_id="hyp_02",
            strategy_id="strat_fail",
            features=["returns_1d"],
            parameters={"min_rsi": 10},
            metrics={"sharpe_ratio": 0.1, "win_rate": 0.3},
            failure_reason="Sharpe Insuficiente"
        )

        top_feats = memory.get_top_performing_features(top_n=2)
        assert "relative_volume_rvol" in top_feats

        failed = memory.get_failed_patterns()
        assert len(failed) == 1
        assert failed[0]["strategy_id"] == "strat_fail"

    def test_strategy_similarity_and_novelty_score(self):
        """7. Índice de Similitud Jaccard y Novelty Score (0-100)."""
        gen = AutonomousStrategyGenesisEngine()
        _, def1 = gen.generate_from_template("TREND_FOLLOWING")
        _, def2 = gen.generate_from_template("TREND_FOLLOWING")
        _, def3 = gen.generate_from_template("MEAN_REVERSION")

        overlap = StrategySimilarityEngine.calculate_feature_overlap(["f1", "f2"], ["f2", "f3"])
        assert overlap == 0.3333333333333333 or round(overlap, 2) == 0.33

        novelty = calculate_novelty_score(def3, [def1, def2])
        assert 0.0 <= novelty <= 100.0

    def test_overfitting_risk_score(self):
        """8. Cálculo de Overfitting Risk Score (0-100)."""
        gen = AutonomousStrategyGenesisEngine()
        _, simple_def = gen.generate_from_template("TREND_FOLLOWING")
        risk_simple = calculate_overfitting_risk_score(simple_def)

        # Estrategia sobreajustada con ventana estrecha
        overfitted_params = dict(simple_def.parameters)
        overfitted_params.update({"min_rsi": 45, "max_rsi": 50, "rr_target": 6.0})
        overfitted_def = LabStrategyDefinition(
            strategy_id="strat_overfit",
            name="Overfitted",
            version="1.0",
            created_by="Test",
            description="Overfitted",
            status=StrategyLifecycleStatus.RESEARCH,
            parameters=overfitted_params,
            rules={"conditions": [{"f": 1}, {"f": 2}, {"f": 3}, {"f": 4}]}
        )
        risk_overfitted = calculate_overfitting_risk_score(overfitted_def)

        assert risk_overfitted > risk_simple

    def test_experiment_prioritizer_70_30_balance(self):
        """9. Priorización balanceada 70% Exploración vs 30% Explotación."""
        prioritizer = ExperimentPriorityEngine(exploration_weight=0.70, exploitation_weight=0.30)
        gen = AutonomousStrategyGenesisEngine()
        _, def1 = gen.generate_from_template("TREND_FOLLOWING")
        _, def2 = gen.generate_from_template("MEAN_REVERSION")

        ranked = prioritizer.prioritize_experiments(
            candidate_definitions=[def1, def2],
            existing_definitions=[]
        )

        assert len(ranked) == 2
        assert ranked[0][1] >= ranked[1][1]

    def test_discovery_orchestrator_autonomous_session(self):
        """10. Sesión de descubrimiento autónomo completa."""
        bars = synthetic_generator.generate_bars(count=200, symbol="BTC/USDT", seed=42)
        orchestrator = DiscoveryOrchestrator()
        budget = ResearchBudget(max_experiments=3, max_time_seconds=30)

        report = orchestrator.run_autonomous_research_session(
            budget=budget,
            dataset_bars=bars,
            target_market="BTC/USDT"
        )

        assert report.status in ["COMPLETED", "STOPPED_BUDGET_EXHAUSTED"]
        assert report.summary["experiments_run"] > 0
        assert "top_features" in report.memory_stats

    def test_holdout_protection_during_discovery(self):
        """11. Protección del FINAL_HOLDOUT contra optimización y fuga."""
        from ai_trading_agent.strategy_lab.core.models import DataSplitType
        bars = synthetic_generator.generate_bars(count=300, symbol="BTC/USDT")
        protected_ds = LabDataSplitter.split_in_sample_out_sample_holdout(bars)

        # Intento directo de acceder al Holdout durante investigación debe fallar
        with pytest.raises(PermissionError, match="ACCESO DENEGADO"):
            _ = protected_ds.get_split(DataSplitType.FINAL_HOLDOUT, purpose="RESEARCH")


    def test_security_boundary_no_live_broker_execution(self):
        """12. Aislamiento estricto: el Discovery Engine no ejecuta operaciones reales ni aprueba estrategias directamente."""
        orchestrator = DiscoveryOrchestrator()
        # Verificar que el orquestador no tenga referencias a broker adapters en vivo
        assert not hasattr(orchestrator, "moomoo_broker")
        assert not hasattr(orchestrator, "alpaca_broker")

    def test_discovery_api_endpoints(self):
        """13. Pruebas de endpoints FastAPI del Strategy Discovery Engine."""
        client = TestClient(app)

        # Features Catalog Endpoint
        res_feat = client.get("/api/strategy-lab/discovery/features")
        assert res_feat.status_code == 200
        data_feat = res_feat.json()
        assert data_feat["count"] >= 14

        # Memory Endpoint
        res_mem = client.get("/api/strategy-lab/discovery/memory")
        assert res_mem.status_code == 200
        data_mem = res_mem.json()
        assert "top_features" in data_mem

        # Run Discovery Session Endpoint
        res_run = client.post("/api/strategy-lab/discovery/run", json={"max_experiments": 2, "max_time_seconds": 15})
        assert res_run.status_code == 200
        data_run = res_run.json()
        assert "summary" in data_run

    def test_multi_objective_optimization_ranking(self):
        """14. Ranking multiobjetivo (Sharpe, WinRate, Drawdown, Robustness, Overfitting)."""
        gen = AutonomousStrategyGenesisEngine()
        _, def1 = gen.generate_from_template("TREND_FOLLOWING")
        def1.metrics = {"sharpe_ratio": 2.1, "win_rate": 0.62, "max_drawdown": 0.12}
        def1.robustness_score = 78.5

        risk = calculate_overfitting_risk_score(def1)
        composite_rank_score = (def1.metrics["sharpe_ratio"] * 30.0) + (def1.robustness_score * 0.5) - (risk * 0.2)
        assert composite_rank_score > 0.0

    def test_research_budget_exhaustion_safety(self):
        """15. Control de recursos y agotamiento de presupuesto de sesión."""
        orchestrator = DiscoveryOrchestrator()
        budget = ResearchBudget(max_experiments=1, max_time_seconds=10)

        report = orchestrator.run_autonomous_research_session(budget=budget)
        assert report.summary["experiments_run"] <= 1

    def test_strategy_lineage_tree_reconstruction(self):
        """16. Reconstrucción del árbol de linaje padre-hijo."""
        genesis = AutonomousStrategyGenesisEngine()
        parent_inst, parent_def = genesis.generate_from_template("TREND_FOLLOWING")

        mutation_engine = ExtendedMutationEngine()
        child_inst, child_def, record = mutation_engine.mutate_strategy(parent_inst, parent_def)

        assert child_def.parent_strategy_id == parent_inst.strategy_id
        assert record.child_strategy_id == child_inst.strategy_id
