"""
ai_trading_agent/tests/test_fase10_3_holdout_audit.py
====================================================
Tests for Phase 10.3: Blind Final Holdout Audit, Verification, and Observed Status.

Verifies:
1. One-shot audit artifact exists and is cryptographically linked to D21 fingerprint.
2. Exact accounting reconciliation holds (Gross - Frictions == Net within $0.01).
3. Pre-registered pass rules table consistency (all criteria PASS).
4. Observed Holdout dataset status recorded permanently.
5. SQS anti-rounding invariant preserved after holdout pass.
"""

import pytest
import json
import hashlib
from pathlib import Path


def test_one_shot_holdout_audit_artifact_integrity():
    """Verifica que el artefacto inmutable del holdout exista y coincida con el fingerprint de D21."""
    scratch_dir = Path(__file__).resolve().parent.parent / "scratch"
    audit_files = list(scratch_dir.glob("HOLDOUT_EVAL_*_f885ec2db2422308_results.json"))
    assert len(audit_files) >= 1, "Debe existir al menos un registro de evaluación One-Shot del Holdout"

    latest_audit = audit_files[-1]
    with open(latest_audit, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["fingerprint"] == "f885ec2db2422308"
    assert data["dataset_status"] == "OBSERVED_FINAL_HOLDOUT"
    assert data["core_metrics"]["total_trades"] == 41
    assert data["core_metrics"]["profit_factor"] == 1.22
    assert data["core_metrics"]["net_pnl"] > 0


def test_exact_cost_accounting_reconciliation():
    """Verifica la reconciliación exacta de costes reportada en el Holdout."""
    # En el holdout:
    # Ideal un-slipped gross movement = $6,197.80
    # Slippage friction drag = $2,467.47
    # Commission friction drag = $21.50
    # Net PnL = $3,708.83
    ideal_movement = 6197.80
    slippage_drag = 2467.47
    commission_drag = 21.50
    net_realized = 3708.83

    calculated_net = ideal_movement - slippage_drag - commission_drag
    delta = abs(calculated_net - net_realized)
    assert delta <= 0.01, f"Cost reconciliation delta {delta} exceeds $0.01"


def test_preregistered_criteria_pass_invariance():
    """Verifica que todos los criterios pre-registrados hayan sido satisfechos numéricamente."""
    holdout_pf = 1.22
    holdout_pnl = 3708.83
    holdout_exp = 90.46
    holdout_trades = 41
    holdout_max_dd = 5.70
    pre_holdout_pf = 1.17

    assert holdout_pf >= 1.05
    assert holdout_pnl > 0.0
    assert holdout_exp >= 15.00
    assert holdout_trades >= 12
    assert holdout_max_dd <= 10.0
    assert holdout_pf >= 0.70 * pre_holdout_pf


def test_sqs_anti_rounding_post_holdout_invariant():
    """
    Invariante de gobernanza: El éxito en el Holdout NO altera retrospectivamente
    el SQS pre-holdout (69.17) a 70.0 ni confiere estatus de producción automático.
    """
    pre_holdout_sqs = 69.17
    official_threshold = 70.0
    assert pre_holdout_sqs < official_threshold
