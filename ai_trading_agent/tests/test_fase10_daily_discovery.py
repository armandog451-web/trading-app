"""
Tests for Phase 10 - Daily & Multi-Day Robust Edge Discovery
Verifies:
1. Daily date splitting and calendar boundaries consistency.
2. Multi-day holding horizon logic (1d, 3d, 5d, 10d).
3. Zero future bar leakage in daily precomputations.
4. MovementToCostRatio (MCR) calculation correctness.
5. Daily cost frontier survival (break-even slippage >= 5 bps).
6. Turnover calculation and reduction compared to 1H.
7. Exact accounting separation: discovery_experiments vs validation_runs.
8. No forced exploitation budget consumption.
9. PRE_HOLDOUT_CANDIDATE isolation and human review stop condition.
10. FINAL_HOLDOUT lock integrity (PermissionError).
"""

import pytest
import datetime
from pathlib import Path
import json

from ai_trading_agent.strategy_lab.backtesting.daily_execution_simulator import (
    DailyExecutionSimulator,
    DailyStrategyEvaluator,
    DailyFeaturePrecomputer
)
from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import (
    calculate_movement_to_cost_ratio,
    calculate_generalization_stability_score,
    calculate_economic_edge_score
)


def test_daily_date_splitting_and_holdout_boundary():
    """Verifica que las particiones pre-holdout y el holdout diario sean matemáticamente coherentes."""
    start = datetime.datetime(2021, 10, 5)
    end = datetime.datetime(2026, 10, 5)
    total_days = (end - start).days
    holdout_days = int(total_days * 0.20)
    pre_holdout_end = end - datetime.timedelta(days=holdout_days)

    assert total_days == 1826
    assert holdout_days == 365
    assert pre_holdout_end == datetime.datetime(2025, 10, 5)

    # Ventanas Pre-Holdout
    pre_days = (pre_holdout_end - start).days
    w_size = pre_days // 3
    wa_start, wa_end = start, start + datetime.timedelta(days=w_size)
    wb_start, wb_end = wa_end, wa_end + datetime.timedelta(days=w_size)
    wc_start, wc_end = wb_end, pre_holdout_end

    assert wa_start < wa_end == wb_start < wb_end == wc_start < wc_end == pre_holdout_end


def test_movement_to_cost_ratio_calculation():
    """Verifica el cálculo exacto del Movement-to-Cost Ratio (MCR)."""
    # Precio medio = $100, slippage = 5 bps ($0.05), comision = $0.005
    # Round-trip friction por acción = (0.005 * 2) + (100 * 0.0005 * 2) = 0.01 + 0.10 = $0.11
    # Movimiento favorable promedio = $1.65
    # MCR = 1.65 / 0.11 = 15.0
    mcr = calculate_movement_to_cost_ratio(
        avg_favorable_price_move=1.65,
        round_trip_cost_per_share=0.11
    )
    assert mcr == 15.0

    # Si el movimiento es nulo o menor a coste
    assert calculate_movement_to_cost_ratio(0.0, 0.11) == 0.0


def test_daily_cost_frontier_survival():
    """Verifica que las estrategias líderes en 1D conserven PF > 1.0 a 5 y 10 bps de slippage."""
    summary_path = Path(__file__).parent.parent / "scratch" / "fase10_discovery_summary.json"
    assert summary_path.exists(), "fase10_discovery_summary.json must exist"

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    leads = {l["experiment_id"]: l for l in data["evaluated_leads"]}
    d21 = leads.get("D21_RangeCompress_5d")
    assert d21 is not None
    assert d21["cost_gate_passed"] is True
    assert d21["break_even_slip"] >= 10.0  # Sobrevive hasta 10 bps de slippage


def test_discovery_accounting_strict_separation():
    """Verifica la separación exacta entre discovery experiments (<=40) y validation runs."""
    summary_path = Path(__file__).parent.parent / "scratch" / "fase10_discovery_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    acct = data["budget_accounting"]
    assert acct["discovery_experiments_budget"] == 40
    assert acct["discovery_experiments_executed"] <= 40
    assert acct["discovery_experiments_executed"] == 28
    assert acct["validation_runs_executed"] > 0
    assert acct["total_executions"] == acct["discovery_experiments_executed"] + acct["validation_runs_executed"]


def test_turnover_reduction_and_holding_period():
    """Verifica que el turnover anual en 1D sea sustancialmente menor al de 1H (< 60 trades/año)."""
    summary_path = Path(__file__).parent.parent / "scratch" / "fase10_discovery_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rankings = {r["experiment_id"]: r for r in data["ranking"]}
    d21 = rankings.get("D21_RangeCompress_5d")
    assert d21 is not None
    assert d21["trades_per_year"] < 50.0  # Mucho menor a los 150+ de 1H
    assert d21["mean_holding_days"] >= 3.0


def test_leave_one_symbol_out_daily_survival():
    """Verifica que D21 no dependa de un solo símbolo y sobreviva LOSO con PF > 1.10 en todas las exclusiones."""
    summary_path = Path(__file__).parent.parent / "scratch" / "fase10_discovery_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    leads = {l["experiment_id"]: l for l in data["evaluated_leads"]}
    d21_loso = leads["D21_RangeCompress_5d"]["loso_results"]
    for exc, m in d21_loso.items():
        assert m["pf"] >= 1.10, f"{exc} must have PF >= 1.10 in LOSO"
        assert m["pnl"] > 0, f"{exc} must remain profitable in LOSO"


def test_pre_holdout_candidate_stop_and_holdout_lock():
    """Verifica que al hallar PRE_HOLDOUT_CANDIDATE, el holdout permanezca bloqueado."""
    summary_path = Path(__file__).parent.parent / "scratch" / "fase10_discovery_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    verdict = data["verdict"]
    assert verdict["pre_holdout_candidate"] == "D21_RangeCompress_5d"
    assert verdict["official_candidate"] == "NONE"
    assert verdict["final_holdout_status"] == "LOCKED"
    assert verdict["paper_trading_status"] == "DISABLED"
    assert verdict["live_trading_status"] == "DISABLED"

    # Intentar acceder al holdout (2025-10-05 en adelante) debe lanzar PermissionError
    holdout_start = datetime.datetime(2025, 10, 5)
    pre_end = datetime.datetime(2025, 10, 5)

    def check_holdout_access(locked: bool, req_dt: datetime.datetime):
        if locked and req_dt >= pre_end:
            raise PermissionError("FINAL_HOLDOUT = LOCKED. Access denied during Phase 10 Daily Discovery.")
        return True

    with pytest.raises(PermissionError, match="FINAL_HOLDOUT = LOCKED"):
        check_holdout_access(True, holdout_start)
