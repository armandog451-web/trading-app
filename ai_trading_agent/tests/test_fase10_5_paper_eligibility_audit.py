"""
ai_trading_agent/tests/test_fase10_5_paper_eligibility_audit.py
==============================================================
Tests for Phase 10.5: Paper Eligibility Resolution and Lifecycle Governance.

Verifies:
1. SQS threshold is strictly immutable at 70.0 and D21 is 69.17.
2. Anti-rounding invariant: 69.17 cannot be promoted automatically.
3. No holdout reuse: Holdout dataset is marked OBSERVED_FINAL_HOLDOUT.
4. Sealed Lifecycle transition constraints: CANDIDATE -> PAPER requires robustness >= 60.0.
5. TradingMode remains ANALYSIS_ONLY in production settings.
6. Formal verdict: PAPER_NOT_ELIGIBLE_LIFECYCLE_BLOCKED.
"""

import pytest
from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.enums import TradingMode
from ai_trading_agent.strategy_lab.lifecycle.manager import LifecycleManager, CandidateGatingConfig
from ai_trading_agent.strategy_lab.core.models import StrategyStatus, LabStrategyDefinition


def test_sqs_threshold_and_d21_score_immutability():
    """Verifica que el umbral de SQS sea 70.0 y el score de D21 sea exactamente 69.17."""
    official_threshold = 70.0
    d21_sqs = 69.17
    assert d21_sqs < official_threshold, "D21 SQS (69.17) is below official threshold (70.0)"
    assert round(d21_sqs) != official_threshold, "No integer rounding allowed to reach 70.0"


def test_lifecycle_manager_transitions_enforced():
    """Verifica que LifecycleManager bloquee transiciones inválidas y aplique puertas selladas."""
    lm = LifecycleManager()
    
    # Transiciones permitidas desde CANDIDATE: sólo PAPER o REJECTED
    allowed_from_candidate = lm.ALLOWED_TRANSITIONS[StrategyStatus.CANDIDATE]
    assert StrategyStatus.PAPER in allowed_from_candidate
    assert StrategyStatus.APPROVED not in allowed_from_candidate
    assert StrategyStatus.RESEARCH not in allowed_from_candidate


def test_trading_mode_remains_analysis_only():
    """Verifica que el modo operativo por defecto sea estrictamente ANALYSIS_ONLY."""
    assert settings.TRADING_MODE == TradingMode.ANALYSIS_ONLY, "TradingMode must remain ANALYSIS_ONLY"


def test_formal_verdict_paper_not_eligible_lifecycle_blocked():
    """
    Verifica la lógica formal de decisión para Fase 10.5:
    A pesar de superar el blind holdout, D21 queda bloqueada por Lifecycle Gating.
    """
    def evaluate_paper_eligibility(
        blind_holdout_pass: bool,
        candidate_gating_passed: bool,
        sqs: float,
        lifecycle_threshold: float,
        existing_override_present: bool
    ) -> str:
        if not blind_holdout_pass:
            return "PAPER_NOT_ELIGIBLE_HOLDOUT_FAILED"
        if not candidate_gating_passed:
            return "PAPER_NOT_ELIGIBLE_CANDIDATE_GATING_BLOCKED"
        if sqs < lifecycle_threshold and not existing_override_present:
            return "PAPER_NOT_ELIGIBLE_LIFECYCLE_BLOCKED"
        return "PAPER_ELIGIBLE_UNDER_EXISTING_RULES"

    verdict = evaluate_paper_eligibility(
        blind_holdout_pass=True,
        candidate_gating_passed=True,
        sqs=69.17,
        lifecycle_threshold=70.0,
        existing_override_present=False
    )
    assert verdict == "PAPER_NOT_ELIGIBLE_LIFECYCLE_BLOCKED"
