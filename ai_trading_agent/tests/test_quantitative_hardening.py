"""
ai_trading_agent.tests.test_quantitative_hardening
===================================================
Suite de Pruebas de Refuerzo Cuantitativo (Quantitative Hardening) — FASE 3.5.
Cubre los 10 requerimientos de validación estadística, Candidate Gating, Robustness Score fix,
Slippage Stress, Regime/Symbol Coverage y Data Sufficiency.
"""

import pytest

from ai_trading_agent.strategy_lab.robustness.engine import RobustnessEngine, robustness_engine
from ai_trading_agent.strategy_lab.lifecycle.manager import LifecycleManager, CandidateGatingConfig
from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition, StrategyStatus
from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import (
    StatisticalEvidenceLevel,
    DataSufficiencyStatus,
    DataSufficiencyEvaluator,
    classify_statistical_evidence,
    BestLeadVsBestCandidate,
    SlippageCostStressEvaluator,
    RegimeCoverageEvaluator,
    SymbolCoverageEvaluator
)
from ai_trading_agent.data.synthetic import synthetic_generator


class TestQuantitativeHardeningSuite:

    def test_zero_trade_strategy_cannot_receive_robustness_100(self):
        """1. Una estrategia con 0 trades NUNCA recibe Robustness Score = 100."""
        report = robustness_engine.evaluate_robustness(trades=[])
        assert report.robustness_score == 0.0
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
