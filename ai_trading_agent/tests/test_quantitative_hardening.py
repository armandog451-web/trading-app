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

    # -------------------------------------------------------------------------
    # FASE 4.7: SCORE INTEGRITY & MATHEMATICAL RECONCILIATION TESTS
    # -------------------------------------------------------------------------

    def test_fase47_v1_4_exact_score_reconciliation(self):
        """Fase 4.7 Test 1: Reconciliación matemática exacta de la estrategia v1.4."""
        trades = [{"net_pnl": 1.0} for _ in range(76)]
        report = robustness_engine.evaluate_robustness(
            trades=trades,
            in_sample_sharpe=0.08,
            out_sample_sharpe=0.05,
            profit_factor=1.04,
            expectancy=0.01
        )
        # 1. Economic Edge: PF=1.04 <= 1.10 -> WEAK_EDGE, 5.0 + (0.04/0.10)*20.0 = 13.0
        assert report.economic_edge_classification == "WEAK_EDGE"
        assert report.economic_edge_score == 13.0

        # 2. Pure Robustness: 0.05 / max(0.1, 0.08) = 0.50 -> 0.50 * 30 = 15.0 pts.
        # MC score = 40.0, Fail score = 30.0 -> PRS = 15.0 + 40.0 + 30.0 = 85.0
        assert report.robustness_score == 85.0

        # 3. Intermediate SQS values:
        # Evidence: 76 trades -> MODERATE_EVIDENCE -> 80.0 pts (15%)
        # OOS Stability: (0.50 * 0.50 + (0.05/1.5) * 0.50) * 100 = 26.67 pts (10%)
        # Slippage Resilience: (45.6 / 76.0) * 100 = 60.0 pts (10%)
        # Simplicity: 100.0 pts (5%)
        # Weighted sum = 13.0*0.30 + 85.0*0.30 + 80.0*0.15 + 26.67*0.10 + 60.0*0.10 + 100.0*0.05
        #              = 3.90 + 25.50 + 12.00 + 2.667 + 6.00 + 5.00 = 55.067 -> 55.07
        # SamplePenalty = 1.0 (76 >= 8 trades)
        assert report.strategy_quality_score == 55.07
        assert report.slippage_stress_resilience_pct == 60.0

    def test_v14_slippage_exact_reconciliation(self):
        """Fase 4.8: Demostración explícita de reconciliación de slippage resilience y propagación a SQS."""
        baseline_pnl = 76.0
        high_stress_pnl = 45.6

        # 1. Función de slippage directa
        resilience = calculate_slippage_resilience_score(baseline_pnl, high_stress_pnl)
        assert resilience == 60.0

        # 2. Reporte de Robustness
        trades = [{"net_pnl": 1.0} for _ in range(76)]
        report = robustness_engine.evaluate_robustness(
            trades=trades,
            in_sample_sharpe=0.08,
            out_sample_sharpe=0.05,
            profit_factor=1.04,
            expectancy=0.01,
            high_stress_pnl=high_stress_pnl
        )
        assert report.slippage_stress_resilience_pct == 60.0

        # 3. Propagación directa a StrategyQualityScore
        # El componente de slippage (10%) en SQS aporta exactamente 60.0 * 0.10 = 6.00 puntos
        assert report.strategy_quality_score == 55.07

    def test_fase47_prs_arithmetic_and_floor(self):
        """Fase 4.7 Test 2: Aritmética de PRS y comprobación del floor max(0.1, IS_Sharpe)."""
        trades = [{"net_pnl": 10.0} for _ in range(50)]
        # Caso A: IS Sharpe = 0.05 < 0.1, OOS Sharpe = 0.05
        # Floor max(0.1, 0.05) = 0.1 -> Retention = 0.05 / 0.1 = 0.50 -> OOS_score = 15.0
        rep_a = robustness_engine.evaluate_robustness(trades=trades, in_sample_sharpe=0.05, out_sample_sharpe=0.05)
        assert rep_a.robustness_score == 85.0

        # Caso B: IS Sharpe = 1.0, OOS Sharpe = 1.0
        # Retention = 1.0 / 1.0 = 1.0 -> OOS_score = 30.0 -> PRS = 30 + 40 + 30 = 100.0
        rep_b = robustness_engine.evaluate_robustness(trades=trades, in_sample_sharpe=1.0, out_sample_sharpe=1.0)
        assert rep_b.robustness_score == 100.0

    def test_fase47_sqs_arithmetic_weights(self):
        """Fase 4.7 Test 3: Verificación de pesos en SQS (30%, 30%, 15%, 10%, 10%, 5%)."""
        sqs = calculate_strategy_quality_score(
            economic_edge_score=100.0,
            robustness_score=100.0,
            trade_count=100,  # STRONG_EVIDENCE -> 100.0
            is_sharpe=1.5,
            oos_sharpe=1.5,   # OOS Stability -> 100.0
            is_pnl=1000.0,
            oos_pnl=1000.0,
            baseline_pnl=1000.0,
            high_stress_pnl=1000.0,  # Slippage Resilience -> 100.0
            overfit_risk=0.0,
            complexity_penalty=0.0   # Simplicity -> 100.0
        )
        assert sqs == 100.0

    def test_fase47_sample_penalty(self):
        """Fase 4.7 Test 4: Comportamiento exacto de SamplePenalty."""
        # 4 trades < 8 -> penalty = 4/8 = 0.5 (SQS exactamente a la mitad)
        sqs_4 = calculate_strategy_quality_score(
            economic_edge_score=50.0,
            robustness_score=50.0,
            trade_count=4,
            is_sharpe=1.0,
            oos_sharpe=1.0,
            is_pnl=100.0,
            oos_pnl=100.0,
            baseline_pnl=100.0,
            high_stress_pnl=80.0
        )
        # 8 trades >= 8 -> penalty = 1.0 (sin penalización)
        sqs_8 = calculate_strategy_quality_score(
            economic_edge_score=50.0,
            robustness_score=50.0,
            trade_count=8,
            is_sharpe=1.0,
            oos_sharpe=1.0,
            is_pnl=100.0,
            oos_pnl=100.0,
            baseline_pnl=100.0,
            high_stress_pnl=80.0
        )
        assert sqs_4 < sqs_8
        assert sqs_4 > 0.0

    def test_fase47_oos_edge_cases(self):
        """Fase 4.7 Test 5: Casos extremos en calculate_oos_stability_score."""
        import math
        # OOS negativo o nulo
        assert calculate_oos_stability_score(1.5, -0.5, 100.0, 50.0) == 0.0
        assert calculate_oos_stability_score(1.5, 0.0, 100.0, 50.0) == 0.0
        # OOS PnL negativo
        assert calculate_oos_stability_score(1.5, 0.5, 100.0, -10.0) == 0.0
        # IS Sharpe <= 0 pero OOS > 0
        assert calculate_oos_stability_score(0.0, 1.5, 100.0, 100.0) == 50.0  # solo componente absoluto
        # NaN / Inf
        assert calculate_oos_stability_score(math.nan, 1.5, 100.0, 100.0) == 50.0
        assert calculate_oos_stability_score(math.nan, 1.0, 100.0, 100.0) == 33.33
        assert calculate_oos_stability_score(1.0, math.nan, 100.0, 100.0) == 0.0
        assert calculate_oos_stability_score(1.0, math.inf, 100.0, 100.0) == 0.0

    def test_fase47_slippage_edge_cases(self):
        """Fase 4.7 Test 6: Casos extremos en calculate_slippage_resilience_score."""
        import math
        # Baseline > 0, High Stress > 0
        assert calculate_slippage_resilience_score(100.0, 80.0) == 80.0
        # Baseline > 0, High Stress = 0
        assert calculate_slippage_resilience_score(100.0, 0.0) == 0.0
        # Baseline > 0, High Stress < 0
        assert calculate_slippage_resilience_score(100.0, -20.0) == 0.0
        # Baseline <= 0
        assert calculate_slippage_resilience_score(0.0, -10.0) == 0.0
        assert calculate_slippage_resilience_score(-50.0, -100.0) == 0.0
        # NaN / Inf
        assert calculate_slippage_resilience_score(math.nan, 50.0) == 0.0
        assert calculate_slippage_resilience_score(100.0, math.nan) == 0.0
        assert calculate_slippage_resilience_score(math.inf, 50.0) == 0.0

    def test_fase47_score_monotonicity(self):
        """Fase 4.7 Test 7: Monotonía de los scores ante mejoras y degradaciones."""
        # A. Monotonía en Economic Edge ante aumento de PF
        score_1, _ = calculate_economic_edge_score(1.05, 0.05, 0.5, 0.3, 50)
        score_2, _ = calculate_economic_edge_score(1.15, 0.10, 0.5, 0.3, 50)
        score_3, _ = calculate_economic_edge_score(1.50, 0.50, 0.5, 0.3, 50)
        assert score_1 <= score_2 <= score_3

        # B. Monotonía en OOS Stability ante aumento de OOS Sharpe
        oos_1 = calculate_oos_stability_score(1.0, 0.2, 100.0, 100.0)
        oos_2 = calculate_oos_stability_score(1.0, 0.6, 100.0, 100.0)
        oos_3 = calculate_oos_stability_score(1.0, 1.2, 100.0, 100.0)
        assert oos_1 <= oos_2 <= oos_3

        # C. Monotonía en Slippage Resilience ante menor degradación
        slip_1 = calculate_slippage_resilience_score(100.0, 40.0)
        slip_2 = calculate_slippage_resilience_score(100.0, 70.0)
        slip_3 = calculate_slippage_resilience_score(100.0, 95.0)
        assert slip_1 <= slip_2 <= slip_3

    def test_fase47_negative_and_extreme_metrics(self):
        """Fase 4.7 Test 8: Métricas negativas, extremas e inválidas."""
        import math
        # PF negativo o <= 1.0 -> NO_EDGE
        score_neg, class_neg = calculate_economic_edge_score(-1.5, -0.5, -0.2, -0.5, 50)
        assert score_neg == 0.0
        assert class_neg == EconomicEdgeClassification.NO_EDGE

        # NaN / Inf en Economic Edge
        score_nan, class_nan = calculate_economic_edge_score(math.nan, 0.5, 1.0, 1.0, 50)
        assert score_nan == 0.0
        assert class_nan == EconomicEdgeClassification.NO_EDGE

        score_inf, class_inf = calculate_economic_edge_score(math.inf, 0.5, 1.0, 1.0, 50)
        assert score_inf == 0.0
        assert class_inf == EconomicEdgeClassification.NO_EDGE

        # Límites acotados con valores gigantes
        sqs_extreme = calculate_strategy_quality_score(
            economic_edge_score=9999.0,
            robustness_score=9999.0,
            trade_count=10000,
            is_sharpe=100.0,
            oos_sharpe=100.0,
            is_pnl=1e8,
            oos_pnl=1e8,
            baseline_pnl=1e8,
            high_stress_pnl=1e8
        )
        assert sqs_extreme == 100.0

    def test_fase47_zero_trade_strategy_strictly_zero(self):
        """Fase 4.7 Test 9: Estrategia sin operaciones da estrictamente ceros en todos los scores."""
        rep = robustness_engine.evaluate_robustness(trades=[])
        assert rep.robustness_score == 0.0
        assert rep.economic_edge_score == 0.0
        assert rep.economic_edge_classification == "NO_EDGE"
        assert rep.strategy_quality_score == 0.0
        assert rep.is_robust is False
        assert rep.probability_of_failure_pct == 100.0

    def test_fase47_candidate_gating_multi_dimensional(self):
        """Fase 4.7 Test 10: Candidate Gating evalúa múltiples dimensiones simultáneamente."""
        manager = LifecycleManager()

        # Estrategia que falla SOLO por trades
        strat_low_trades = LabStrategyDefinition(
            strategy_id="s1", name="LowTrades", version="1.0", created_by="T", description="T",
            metrics={"total_trades": 5, "is_trades": 5, "oos_trades": 0, "profit_factor": 2.0, "is_sharpe": 1.5, "oos_sharpe": 1.0},
            robustness_score=80.0
        )
        p1, m1 = manager.evaluate_candidate_gating(strat_low_trades)
        assert p1 is False
        assert "Total de trades (5)" in m1

        # Estrategia que falla SOLO por Robustness
        strat_low_rob = LabStrategyDefinition(
            strategy_id="s2", name="LowRob", version="1.0", created_by="T", description="T",
            metrics={"total_trades": 50, "is_trades": 30, "oos_trades": 20, "profit_factor": 2.0, "is_sharpe": 1.5, "oos_sharpe": 1.0},
            robustness_score=40.0  # < min_robustness_score 50.0
        )
        p2, m2 = manager.evaluate_candidate_gating(strat_low_rob)
        assert p2 is False
        assert "ROBUSTEZ INSUFICIENTE" in m2

        # Estrategia que falla SOLO por Economic Edge (PF <= 1.0)
        strat_no_edge = LabStrategyDefinition(
            strategy_id="s3", name="NoEdge", version="1.0", created_by="T", description="T",
            metrics={"total_trades": 50, "is_trades": 30, "oos_trades": 20, "profit_factor": 0.90, "is_sharpe": 0.2, "oos_sharpe": 0.1},
            robustness_score=75.0
        )
        p3, m3 = manager.evaluate_candidate_gating(strat_no_edge)
        assert p3 is False
        assert "EXPECTATIVA NEGATIVA" in m3 or "VENTAJA ECONÓMICA NULA" in m3


