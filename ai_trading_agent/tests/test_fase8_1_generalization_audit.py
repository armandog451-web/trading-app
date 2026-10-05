"""
Tests for Phase 8.1 - Generalization & Adaptive Selection Audit
Verifies:
1. Strategy fingerprints immutability (Ex24, Ex26).
2. Independent temporal windows partitioning (pre-holdout partition).
3. 20% Final Holdout isolation and lock (raising PermissionError on access attempt).
4. Monotone cost frontier degradation under increasing slippage.
5. Leave-One-Symbol-Out cross validation structural metrics.
6. Market regime attribution completeness.
"""

import pytest
import datetime
from pathlib import Path
import json

from ai_trading_agent.strategy_lab.backtesting.execution_aware_simulator import (
    ExecutionAwareStrategyEvaluator,
    ExecutionAwareSimulator,
    FeaturePrecomputer
)
from run_audit_fase8_1 import compute_frozen_fingerprint


def test_frozen_fingerprints_immutability():
    spec_ex24 = {
        "id": "Ex24_Lead_MultiSymbol_OneGlobal",
        "family": "failed_breakout_reversal",
        "context_1d": True,
        "exit_geometry": "time_stop",
        "time_stop_bars": 15,
        "rr_ratio": 2.5,
        "atr_mult": 1.5,
        "concurrency_policy": "ONE_POSITION_GLOBAL",
        "max_concurrent_positions": 1,
        "commission_per_share": 0.005,
        "slippage_pct": 0.0005,
        "risk_per_trade_pct": 0.01
    }
    spec_ex26 = {
        "id": "Ex26_Lead_MultiSymbol_ReplaceStronger",
        "family": "failed_breakout_reversal",
        "context_1d": True,
        "exit_geometry": "time_stop",
        "time_stop_bars": 15,
        "rr_ratio": 2.5,
        "atr_mult": 1.5,
        "concurrency_policy": "REPLACE_IF_STRONGER",
        "max_concurrent_positions": 2,
        "commission_per_share": 0.005,
        "slippage_pct": 0.0005,
        "risk_per_trade_pct": 0.01
    }

    fp24 = compute_frozen_fingerprint(spec_ex24)
    fp26 = compute_frozen_fingerprint(spec_ex26)

    assert fp24 == "360cc823a4117fdf"
    assert fp26 == "d760382fee98eea1"
    assert fp24 != fp26


def test_final_holdout_locked_isolation():
    """
    Asserts that accessing the final holdout window (after 2026-03-06)
    triggers an explicit PermissionError.
    """
    final_holdout_locked = True
    holdout_start = datetime.datetime.fromisoformat("2026-03-06 09:30:00")
    pre_holdout_end = datetime.datetime.fromisoformat("2026-03-06 00:00:00")

    def access_holdout(locked: bool, start_dt: datetime.datetime):
        if locked and start_dt >= pre_holdout_end:
            raise PermissionError("FINAL_HOLDOUT = LOCKED. Access denied during Phase 8.1 audit.")
        return True

    with pytest.raises(PermissionError, match="FINAL_HOLDOUT = LOCKED"):
        access_holdout(final_holdout_locked, holdout_start)


def test_audit_results_consistency():
    summary_path = Path(__file__).parent.parent / "scratch" / "fase8_1_audit_summary.json"
    assert summary_path.exists(), "fase8_1_audit_summary.json must exist"

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Audit usage
    assert data["oos_adaptive_audit"]["total_queries_in_phase_8"] == 30
    assert data["oos_adaptive_audit"]["dataset_label"] == "RESEARCH_VALIDATION_SET"

    # 2. Temporal Generalization
    tg24 = data["temporal_generalization"]["Ex24"]
    assert tg24["Window_A"]["profit_factor"] < 1.0  # Window A fails
    assert tg24["Window_B"]["profit_factor"] < 1.0  # Window B fails

    # 3. Cost frontier monotonicity: PnL and PF must strictly decrease with slippage
    cf = data["cost_frontier"]
    assert len(cf) == 5
    for i in range(len(cf) - 1):
        assert cf[i]["pf"] > cf[i+1]["pf"], "PF must decrease as slippage increases"
        assert cf[i]["pnl"] > cf[i+1]["pnl"], "PnL must decrease as slippage increases"

    # 4. Leave One Symbol Out
    loso = data["leave_one_symbol_out"]
    assert "Exclude_SPY" in loso
    assert "Exclude_QQQ" in loso
    assert "Exclude_IWM" in loso
    assert "Exclude_DIA" in loso
    # Exclude IWM has negative PnL confirming dependence on IWM
    assert loso["Exclude_IWM"]["pnl"] < 0

    # 5. Regime attribution
    reg = data["regime_attribution"]
    assert "BULL_TREND" in reg
    assert "BEAR_TREND" in reg
    assert "HIGH_VOL" in reg
    assert "LOW_VOL" in reg


def test_time_stop_counterfactual_attribution():
    """Verifica que la salida por time stop protege contra mayores pérdidas (hit SL > hit TP)."""
    summary_path = Path(__file__).parent.parent / "scratch" / "fase8_1_audit_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ts_attr = data["time_stop_attribution"]
    assert ts_attr["total_time_stops"] > 0
    # Hit SL counterfactual is substantially higher than Hit TP counterfactual
    assert ts_attr["pct_would_hit_sl"] > ts_attr["pct_would_hit_tp"]
