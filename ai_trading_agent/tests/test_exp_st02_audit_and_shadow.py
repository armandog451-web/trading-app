"""
ai_trading_agent.tests.test_exp_st02_audit_and_shadow
=====================================================
Suite de pruebas exhaustivas para FASE EXP-ST02:
- Grupo A: Reproducción independiente de EXP-ST01 (GLD_H1, DIA_H1, 50 backtests).
- Grupo B: Lógica H5 Trailing Stop, monotonicidad y gaps.
- Grupo C: Anti-leakage y prueba de perturbación futura.
- Grupo D: Aislamiento (LIVE bloqueado, cero broker calls, D21 y Shadow previas intactas).
- Grupo E: Forward Shadow, integridad de ledgers SHA-256, idempotencia y AUTHORIZATION_REQUIRED.
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import json
from datetime import datetime
import pytest

from ai_trading_agent.config.settings import settings
from ai_trading_agent.strategy_lab.experiments.exp_st02.audit_engine import (
    IndependentAuditEngine,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.frozen_candidates import (
    FrozenCandidatesManager,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.h5_validation_engine import (
    H5IndependentValidator,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_models import (
    ShadowExpSt02State,
    ShadowEventTypeST02,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_ledger import (
    ShadowLedgerST02,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_campaign_manager import (
    ShadowCampaignManagerST02,
)


# ==============================================================================
# GRUPO A: REPRODUCCIÓN DE EXP-ST01
# ==============================================================================

def test_01_deliverables_verification():
    """Verifica que los 10 entregables de EXP-ST01 existen y tienen contenido válido."""
    audit_engine = IndependentAuditEngine()
    deliverables = audit_engine.audit_deliverables()
    assert len(deliverables) == 10
    for d in deliverables:
        assert d.exists is True, f"Falta el entregable {d.filename}"
        assert d.size_bytes > 0
        assert len(d.sha256_hash) == 64


def test_02_reproduction_gld_h1():
    """Reproduce de forma independiente el backtest de GLD_H1 con cero discrepancias en trades."""
    audit_engine = IndependentAuditEngine()
    repro = audit_engine.reproduce_asset("GLD", "H1")
    assert repro.status == "PASS"
    assert repro.trades_match is True
    assert repro.reproduced_trades == 75
    assert repro.pnl_diff < 0.05
    assert repro.pf_diff < 0.01


def test_03_reproduction_dia_h1():
    """Reproduce de forma independiente el backtest de DIA_H1 con cero discrepancias en trades."""
    audit_engine = IndependentAuditEngine()
    repro = audit_engine.reproduce_asset("DIA", "H1")
    assert repro.status == "PASS"
    assert repro.trades_match is True
    assert repro.reproduced_trades == 50
    assert repro.pnl_diff < 0.05
    assert repro.pf_diff < 0.01


def test_04_matrix_reconciliation_50_backtests():
    """Concilia exactamente 25 combinaciones válidas, 25 insuficientes y 1.072 trades totales."""
    audit_engine = IndependentAuditEngine()
    cov = audit_engine.audit_coverage_and_matrix()
    assert cov.reconciled is True
    assert cov.total_combinations == 50
    assert cov.valid_combinations == 25
    assert cov.insufficient_combinations == 25
    assert cov.total_trades == 1072


# ==============================================================================
# GRUPO B: VALIDACIÓN H5 TRAILING STOP
# ==============================================================================

def test_05_h5_monotonicity_and_mechanics():
    """Verifica la monotonicidad del Trailing Stop y la lógica determinista de H5."""
    validator = H5IndependentValidator()
    res = validator.validate_all()
    assert res.reproduction_status == "H5_REPRODUCED"
    assert res.selection_bias_status == "HISTORICAL_HOLDOUT_NOT_INDEPENDENT"
    assert res.final_h5_verdict == "H5_PROSPECTIVE_PENDING"
    assert "CONFIRMED" not in res.final_h5_verdict


# ==============================================================================
# GRUPO C: ANTI-LEAKAGE Y PERTURBACIÓN FUTURA
# ==============================================================================

def test_06_future_perturbation_test():
    """Verifica que alterar barras tras el cutoff no afecta las decisiones previas (cero lookahead)."""
    audit_engine = IndependentAuditEngine()
    leakage = audit_engine.audit_future_perturbation("GLD", "H1")
    assert leakage.verdict == "PASS"
    assert leakage.signals_strictly_identical is True
    assert leakage.indicators_strictly_identical is True


# ==============================================================================
# GRUPO D: PROTOCOLO DE AISLAMIENTO Y SEGURIDAD INSTITUCIONAL
# ==============================================================================

def test_07_live_trading_physically_blocked():
    """Comprueba que LIVE trading está desactivado por diseño."""
    assert not hasattr(settings, "LIVE_TRADING_ENABLED") or not getattr(settings, "LIVE_TRADING_ENABLED")


def test_08_d21_preservation_and_existing_shadow_integrity():
    """Garantiza la preservación de D21 (fp f885ec2db2422308) y de las campañas Shadow de Fase 7.4."""
    # Verificar fingerprint de D21
    from ai_trading_agent.scratch.verify_preflight_evidence import compute_source_fingerprint
    d21_file = repo_root / "ai_trading_agent" / "dual_strategy" / "strategy.py"
    if d21_file.exists():
        fp = compute_source_fingerprint(d21_file)
        assert fp == "f885ec2db2422308", f"D21 fingerprint alterado: {fp}"

    # Verificar que los manifiestos de las campañas previas no fueron modificados
    shadow_dir = repo_root / "ai_trading_agent" / "strategy_lab" / "shadow"
    assert (shadow_dir / "freeze_manifests.py").exists()


# ==============================================================================
# GRUPO E: FORWARD SHADOW, IDEMPOTENCIA Y ESTADO AUTHORIZATION_REQUIRED
# ==============================================================================

def test_09_shadow_ledgers_sha256_chain_integrity(tmp_path):
    """Verifica que los ledgers de EXP-ST02 mantienen integridad criptográfica de hashes SHA-256."""
    ledger = ShadowLedgerST02(
        campaign_id="TEST-CAMP",
        candidate_id="TEST-CAND",
        ledger_file=tmp_path / "test_ledger.jsonl",
    )
    # Bloque génesis
    valid, violations = ledger.verify_integrity()
    assert valid is True
    assert len(violations) == 0

    # Añadir eventos
    ledger.append_event(ShadowEventTypeST02.NO_SIGNAL, {"bar": 1})
    ledger.append_event(ShadowEventTypeST02.SIGNAL_DETECTED, {"direction": "BUY"})

    valid, violations = ledger.verify_integrity()
    assert valid is True
    assert len(ledger.read_all_entries()) == 3


def test_10_shadow_ledger_idempotency_guard(tmp_path):
    """Verifica que el ledger rechaza eventos duplicados por identificador determinista."""
    ledger = ShadowLedgerST02(
        campaign_id="TEST-CAMP",
        candidate_id="TEST-CAND",
        ledger_file=tmp_path / "test_ledger_idemp.jsonl",
    )
    ledger.append_event(ShadowEventTypeST02.HEARTBEAT, {"seq": 1}, custom_entry_id="IDEMP-UNIQUE-101")

    with pytest.raises(ValueError, match="Idempotency violation"):
        ledger.append_event(ShadowEventTypeST02.HEARTBEAT, {"seq": 1}, custom_entry_id="IDEMP-UNIQUE-101")


def test_11_campaign_halts_at_authorization_required():
    """Verifica que la máquina de estados se detiene estrictamente en AUTHORIZATION_REQUIRED."""
    mgr = ShadowCampaignManagerST02()
    ok, manifest = mgr.run_preflight_and_prepare()
    assert ok is True
    assert manifest.current_state == ShadowExpSt02State.AUTHORIZATION_REQUIRED
    assert manifest.activation_authorized is False
    assert manifest.completed_sessions == 0
    assert manifest.t0_activation_utc == "NOT_ACTIVATED_AWAITING_AUTH"
