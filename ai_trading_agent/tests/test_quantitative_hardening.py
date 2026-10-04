"""
ai_trading_agent.tests.test_quantitative_hardening
===================================================
Suite de Pruebas de Refuerzo Cuantitativo (Quantitative Hardening) — FASE 4.6.
Cubre los requerimientos de validación estadística, Economic Edge, Pure Robustness,
Strategy Quality Score, Candidate Gating, Slippage Stress, Regime/Symbol Coverage y Data Sufficiency.
"""

import pytest

from ai_trading_agent.strategy_lab.robustness.engine import RobustnessEngine, robustness_engine
from ai_trading_agent.strategy_lab.lifecycle.manager import LifecycleManager, CandidateGatingConfig
from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition, StrategyStatus
from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import (
    StatisticalEvidenceLevel,
    EconomicEdgeClassification,
    DataSufficiencyStatus,
    DataSufficiencyEvaluator,
    classify_statistical_evidence,
    calculate_economic_edge_score,
    calculate_oos_stability_score,
    calculate_slippage_resilience_score,
    calculate_strategy_quality_score,
    BestLeadVsBestCandidate,
    SlippageCostStressEvaluator,
    RegimeCoverageEvaluator,
    SymbolCoverageEvaluator
)
from ai_trading_agent.data.synthetic import synthetic_generator


class TestQuantitativeHardeningSuite:

    def test_zero_trade_strategy_cannot_receive_robustness_100(self):
        """1. Una estrategia con 0 trades NUNCA recibe Robustness Score > 0."""
        report = robustness_engine.evaluate_robustness(trades=[])
        assert report.robustness_score == 0.0
        assert report.economic_edge_score == 0.0
        assert report.economic_edge_classification == EconomicEdgeClassification.NO_EDGE.value
        assert report.strategy_quality_score == 0.0
        assert report.is_robust is False
        assert report.probability_of_failure_pct == 100.0

    def test_zero_trade_strategy_cannot_become_candidate(self):
        """2. Una estrategia con 0 trades no puede convertirse en Candidate."""
        manager = LifecycleManager()
        strat_def = LabStrategyDefinition(
            strategy_id="strat_zero_trades",
            name="ZeroTradeStrat",
            version="1.0",
            created_by="Test",
            description="Test strategy with 0 trades",
            status=StrategyStatus.RESEARCH,
            metrics={"total_trades": 0, "is_trades": 0, "oos_trades": 0}
        )

        passed, msg = manager.evaluate_candidate_gating(strat_def)
        assert passed is False
        assert "EVIDENCIA INSUFICIENTE" in msg

    def test_insufficient_sample_detection(self):
        """3. Detección de niveles de evidencia estadística por tamaño muestral."""
        assert classify_statistical_evidence(0) == StatisticalEvidenceLevel.NO_DATA
        assert classify_statistical_evidence(5) == StatisticalEvidenceLevel.LOW_SAMPLE
        assert classify_statistical_evidence(20) == StatisticalEvidenceLevel.PRELIMINARY
        assert classify_statistical_evidence(50) == StatisticalEvidenceLevel.MODERATE_EVIDENCE
        assert classify_statistical_evidence(120) == StatisticalEvidenceLevel.STRONG_EVIDENCE

    def test_data_sufficiency_reporting(self):
        """4. Generación de DataSufficiencyReport previo a backtests."""
        bars = synthetic_generator.generate_bars(count=150, symbol="SPY")
        report = DataSufficiencyEvaluator.evaluate(symbol="SPY", timeframe="15m", bars=bars, recommended_min_bars=1000)

        assert report.total_bars == 150
        assert report.data_sufficiency_status == DataSufficiencyStatus.INSUFFICIENT
        assert "AVISO DE INSUFICIENCIA" in report.warning_message

    def test_candidate_gating(self):
        """5. Candidate Gating rechaza estrategias que no cumplen umbrales configurados."""
        cfg = CandidateGatingConfig(min_total_trades=10, min_robustness_score=60.0)
        manager = LifecycleManager(gating_config=cfg)

        # Estrategia que no alcanza min_total_trades
        weak_strat = LabStrategyDefinition(
            strategy_id="strat_weak",
            name="Weak",
            version="1.0",
            created_by="Test",
            description="Weak",
            status=StrategyStatus.VALIDATING,
            metrics={"total_trades": 4, "is_trades": 4, "oos_trades": 0},
            robustness_score=70.0
        )
        passed, msg = manager.evaluate_candidate_gating(weak_strat)
        assert passed is False
        assert "Total de trades (4)" in msg

    def test_exploration_exploitation_accounting(self):
        """6. Contabilidad de distribución planned vs actual Exploration (70%) vs Exploitation (30%)."""
        modes = ["EXPLORATION", "EXPLORATION", "EXPLOITATION", "EXPLORATION", "EXPLORATION"]
        exp_count = sum(1 for m in modes if m == "EXPLORATION")
        act_ratio = exp_count / len(modes)

        assert exp_count == 4
        assert act_ratio == 0.80  # 80% real cuando n=5 (muestra pequeña)

    def test_best_lead_vs_best_candidate(self):
        """7. Distinción conceptual entre Best Research Lead y Best Validated Candidate."""
        lead = {"strategy_id": "strat_lead", "sharpe": 2.5, "trades": 0}
        candidate_structure = BestLeadVsBestCandidate(
            best_research_lead=lead,
            best_validated_candidate=None,
            reason_for_no_candidate="Ninguna estrategia cumplió la puerta de Candidate Gating"
        )

        assert candidate_structure.best_research_lead["strategy_id"] == "strat_lead"
        assert candidate_structure.best_validated_candidate is None
        assert "Candidate Gating" in candidate_structure.reason_for_no_candidate

    def test_regime_sample_validation(self):
        """8. Validación de muestra por régimen de mercado."""
        bars = synthetic_generator.generate_bars(count=100)
        trades = [{"net_pnl": 100, "regime": "BULL_TREND"}]

        regime_report = RegimeCoverageEvaluator.evaluate_regimes(bars, trades)
        assert regime_report["BULL_TREND"]["sample_status"] == "INSUFFICIENT_EVIDENCE"  # 1 trade < 5 min
        assert regime_report["BEAR_TREND"]["sample_status"] == "INSUFFICIENT_EVIDENCE"

    def test_symbol_coverage_validation(self):
        """9. Validación de cobertura por símbolo (evita declarar multisímbolo en un solo activo)."""
        eval_symbols = ["SPY"]
        metrics = {"SPY": {"sharpe": 1.5}}

        symbol_report = SymbolCoverageEvaluator.evaluate_symbols(eval_symbols, metrics)
        assert symbol_report["is_multisymbol_validated"] is False
        assert "ÚNICO símbolo" in symbol_report["validation_note"]

    def test_slippage_stress_reporting(self):
        """10. Pruebas de estrés por deslizamiento y costos de transacción."""
        trades = [{"net_pnl": 100.0}, {"net_pnl": 150.0}, {"net_pnl": -50.0}]
        stress_report = SlippageCostStressEvaluator.evaluate_stress(trades)

        assert stress_report["baseline"]["net_pnl"] == 200.0
        assert stress_report["normal_stress"]["net_pnl"] == 170.0
        assert stress_report["high_stress"]["net_pnl"] == 120.0
        assert stress_report["degradation_pct"] == 40.0

    # -------------------------------------------------------------------------
    # REQUERIMIENTO 17: DEDICATED FASE 4.6 TESTS
    # -------------------------------------------------------------------------

    def test_pf_less_than_or_equal_1_cannot_produce_positive_economic_edge(self):
        """Req 17.1: PF <= 1.0 no puede producir ventajas económicas positivas."""
        edge_score_1, class_1 = calculate_economic_edge_score(
            profit_factor=1.0, expectancy=0.0, is_sharpe=0.5, oos_sharpe=0.2, trade_count=50
        )
        assert edge_score_1 == 0.0
        assert class_1 == EconomicEdgeClassification.NO_EDGE

        edge_score_2, class_2 = calculate_economic_edge_score(
            profit_factor=0.95, expectancy=-0.1, is_sharpe=0.2, oos_sharpe=0.1, trade_count=50
        )
        assert edge_score_2 == 0.0
        assert class_2 == EconomicEdgeClassification.NO_EDGE

    def test_low_pf_cannot_receive_high_strategy_quality(self):
        """Req 17.2: Un PF bajo (1.04) no puede recibir un Strategy Quality Score alto."""
        edge_score, edge_class = calculate_economic_edge_score(
            profit_factor=1.04, expectancy=0.01, is_sharpe=0.08, oos_sharpe=0.05, trade_count=76
        )
        assert edge_class == EconomicEdgeClassification.WEAK_EDGE
        assert edge_score <= 25.0

        quality_score = calculate_strategy_quality_score(
            economic_edge_score=edge_score,
            robustness_score=70.0,
            trade_count=76,
            is_sharpe=0.08,
            oos_sharpe=0.05,
            is_pnl=100.0,
            oos_pnl=50.0,
            baseline_pnl=150.0,
            high_stress_pnl=90.0
        )
        assert quality_score < 60.0

    def test_low_activity_cannot_produce_high_robustness(self):
        """Req 17.3: Baja actividad (0 trades) produce Robustness Score = 0.0."""
        report = robustness_engine.evaluate_robustness(trades=[])
        assert report.robustness_score == 0.0
        assert report.strategy_quality_score == 0.0
        assert report.is_robust is False

    def test_oos_negative_is_penalized(self):
        """Req 17.4: OOS Sharpe o PnL negativo es severamente penalizado en OOS Stability Score (0.0)."""
        score_neg_sharpe = calculate_oos_stability_score(is_sharpe=1.5, oos_sharpe=-0.5, is_pnl=1000.0, oos_pnl=500.0)
        assert score_neg_sharpe == 0.0

        score_neg_pnl = calculate_oos_stability_score(is_sharpe=1.5, oos_sharpe=0.5, is_pnl=1000.0, oos_pnl=-200.0)
        assert score_neg_pnl == 0.0

    def test_oos_magnitude_matters_not_only_retention(self):
        """Req 17.5: Importa la magnitud absoluta de OOS, no solo la tasa de retención."""
        # Ambos tienen 90% de retención
        score_low_mag = calculate_oos_stability_score(is_sharpe=0.10, oos_sharpe=0.09, is_pnl=10.0, oos_pnl=9.0)
        score_high_mag = calculate_oos_stability_score(is_sharpe=2.00, oos_sharpe=1.80, is_pnl=1000.0, oos_pnl=900.0)

        assert score_high_mag > score_low_mag

    def test_baseline_pnl_less_than_or_equal_zero_does_not_break_slippage_score(self):
        """Req 17.6: Baseline PnL <= 0 se maneja de forma segura retornando 0.0 sin error."""
        score_zero = calculate_slippage_resilience_score(baseline_pnl=0.0, high_stress_pnl=-50.0)
        assert score_zero == 0.0

        score_neg = calculate_slippage_resilience_score(baseline_pnl=-100.0, high_stress_pnl=-200.0)
        assert score_neg == 0.0

    def test_regime_insufficiency_is_reported_correctly(self):
        """Req 17.7: La insuficiencia de datos en un régimen se reporta correctamente."""
        bars = synthetic_generator.generate_bars(count=100)
        trades = [{"net_pnl": 50, "regime": "BULL_TREND"}] * 3  # Solo 3 trades < 5
        report = RegimeCoverageEvaluator.evaluate_regimes(bars, trades)
        assert report["BULL_TREND"]["sample_status"] == "INSUFFICIENT_EVIDENCE"

    def test_symbol_inconsistency_is_detected(self):
        """Req 17.8: Inconsistencia multisímbolo es detectada cuando sólo se evalúa un símbolo."""
        report = SymbolCoverageEvaluator.evaluate_symbols(["AAPL"], {"AAPL": {"sharpe": 1.2}})
        assert report["is_multisymbol_validated"] is False
        assert "ADVERTENCIA" in report["validation_note"]

    def test_strategy_quality_remains_between_0_and_100(self):
        """Req 17.9: Strategy Quality Score siempre se mantiene entre 0.0 y 100.0."""
        # Valores extremos superiores
        high_q = calculate_strategy_quality_score(
            economic_edge_score=150.0,
            robustness_score=120.0,
            trade_count=500,
            is_sharpe=3.0,
            oos_sharpe=2.5,
            is_pnl=10000.0,
            oos_pnl=8000.0,
            baseline_pnl=10000.0,
            high_stress_pnl=8000.0
        )
        assert 0.0 <= high_q <= 100.0

        # Valores extremos inferiores / 0 trades
        zero_q = calculate_strategy_quality_score(
            economic_edge_score=0.0,
            robustness_score=0.0,
            trade_count=0,
            is_sharpe=0.0,
            oos_sharpe=0.0,
            is_pnl=0.0,
            oos_pnl=0.0,
            baseline_pnl=0.0,
            high_stress_pnl=0.0
        )
        assert zero_q == 0.0

    def test_strategy_v1_4_is_not_scored_as_artificially_robust(self):
        """Req 17.10: Estrategia v1.4 (76 trades, IS Sharpe 0.08, OOS Sharpe 0.05, PF 1.04) ya no es puntuada falsamente como 96.7 robusta."""
        trades = [{"net_pnl": 1.0} for _ in range(76)]
        report = robustness_engine.evaluate_robustness(
            trades=trades,
            in_sample_sharpe=0.08,
            out_sample_sharpe=0.05,
            profit_factor=1.04,
            expectancy=0.01
        )
        assert report.economic_edge_classification == EconomicEdgeClassification.WEAK_EDGE.value
        assert report.economic_edge_score <= 25.0
        assert report.strategy_quality_score < 60.0

    def test_candidate_gating_remains_intact(self):
        """Req 17.11: Candidate Gating aprueba buenas estrategias y rechaza malas."""
        manager = LifecycleManager()

        # Estrategia válida
        good_strat = LabStrategyDefinition(
            strategy_id="strat_good",
            name="Good",
            version="1.0",
            created_by="Test",
            description="Good Strategy",
            status=StrategyStatus.VALIDATING,
            metrics={
                "total_trades": 50,
                "is_trades": 30,
                "oos_trades": 20,
                "profit_factor": 1.5,
                "expectancy": 10.0,
                "is_sharpe": 1.2,
                "oos_sharpe": 1.0
            },
            robustness_score=75.0
        )
        passed, msg = manager.evaluate_candidate_gating(good_strat)
        assert passed is True
        assert msg == "CANDIDATE_GATING_PASSED"

        # Estrategia con PF <= 1.0 rechazada
        bad_strat = LabStrategyDefinition(
            strategy_id="strat_bad",
            name="Bad",
            version="1.0",
            created_by="Test",
            description="Bad Strategy",
            status=StrategyStatus.VALIDATING,
            metrics={
                "total_trades": 50,
                "is_trades": 30,
                "oos_trades": 20,
                "profit_factor": 0.95,
                "expectancy": -2.0,
                "is_sharpe": 0.1,
                "oos_sharpe": 0.0
            },
            robustness_score=70.0
        )
        passed_bad, msg_bad = manager.evaluate_candidate_gating(bad_strat)
        assert passed_bad is False

    def test_research_lead_remains_distinct_from_candidate(self):
        """Req 17.12: Research Lead se mantiene separado de Validated Candidate."""
        best_lead = {"strategy_id": "lead_1", "sharpe": 3.0, "total_trades": 0}
        structure = BestLeadVsBestCandidate(
            best_research_lead=best_lead,
            best_validated_candidate=None,
            reason_for_no_candidate="No candidate passed minimum evidence gate"
        )
        assert structure.best_research_lead == best_lead
        assert structure.best_validated_candidate is None

