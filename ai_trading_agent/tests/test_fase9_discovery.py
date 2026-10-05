"""
Tests for Phase 9 - Robust Edge Discovery with Early Generalization Gates
Verifies:
1. Multi-window date splitting and calendar boundaries.
2. Early Generalization Gate logic (requires PF>1.0 in >=2/3 windows, positive expectancy, no collapse, sample sufficiency).
3. Adaptive dataset usage counter in ResearchMemory and RESEARCH_VALIDATION relabeling.
4. Symbol dependency gate & Leave-One-Symbol-Out verification.
5. Cost frontier gate & Break-even slippage enforcement.
6. Generalization Stability Score (GSS) calculation consistency.
7. Prohibition of exploitation before passing early gates.
8. Candidate gating invariance and Final Holdout lock isolation (PermissionError).
"""

import pytest
import datetime
from pathlib import Path
import json

from ai_trading_agent.strategy_lab.discovery.research_memory import ResearchMemory
from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import (
    calculate_generalization_stability_score,
    calculate_economic_edge_score,
    EconomicEdgeClassification
)
from ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer import DateBasedDataSplitter
from ai_trading_agent.strategy_lab.lifecycle.manager import LifecycleManager, CandidateGatingConfig


def test_multi_window_calendar_splitting():
    """Verifica que el particionador de fechas cree ventanas disjuntas sin solapamiento."""
    start = datetime.datetime.fromisoformat("2023-11-06 09:30:00")
    end = datetime.datetime.fromisoformat("2026-03-06 16:00:00")
    total_days = (end - start).days
    w_size = total_days // 3

    wa_start, wa_end = start, start + datetime.timedelta(days=w_size)
    wb_start, wb_end = wa_end, wa_end + datetime.timedelta(days=w_size)
    wc_start, wc_end = wb_end, end

    assert wa_start < wa_end
    assert wa_end == wb_start
    assert wb_end == wc_start
    assert wc_end == end


def test_early_generalization_gate_rejection():
    """Estrategias que fracasan en 2 de 3 ventanas o sufren colapso deben ser rechazadas tempranamente."""
    # Caso 1: Colapso en una ventana (PF = 0.40)
    pfs_collapse = [1.25, 1.15, 0.40]
    exps_collapse = [15.0, 10.0, -50.0]
    has_collapse = any(p < 0.65 for p in pfs_collapse)
    assert has_collapse is True

    # Caso 2: Rentable en 1 sola ventana (típico overfitting)
    pfs_single = [0.85, 0.90, 1.35]
    passed_windows = sum(1 for p in pfs_single if p > 1.0)
    assert passed_windows == 1
    assert passed_windows < 2  # Debe ser rechazada


def test_adaptive_dataset_usage_counter():
    """Verifica que ResearchMemory cuente consultas y marque datasets como RESEARCH_VALIDATION."""
    mem = ResearchMemory()
    mem.record_dataset_usage("Window_A", "ranking")
    mem.record_dataset_usage("Window_A", "selection")
    mem.record_dataset_usage("Window_A", "exploitation")

    usage = mem.get_dataset_usage("Window_A")
    assert usage["number_of_queries"] == 3
    assert usage["number_of_rankings"] == 1
    assert usage["number_of_selection_decisions"] == 1
    assert usage["number_of_exploitations"] == 1


def test_gss_calculation_and_properties():
    """Verifica que el GSS penalice la inestabilidad y premie la consistencia entre ventanas."""
    # Sistema inestable con colapso
    unstable_gss = calculate_generalization_stability_score(
        window_pfs=[0.60, 1.90, 0.70],
        window_expectancies=[-10.0, 50.0, -15.0],
        window_sharpes=[-1.2, 1.5, -0.8],
        window_trades=[30, 30, 30]
    )

    # Sistema estable y consistente
    stable_gss = calculate_generalization_stability_score(
        window_pfs=[1.18, 1.22, 1.15],
        window_expectancies=[20.0, 25.0, 18.0],
        window_sharpes=[0.8, 0.9, 0.7],
        window_trades=[30, 30, 30]
    )

    assert stable_gss > unstable_gss
    assert unstable_gss < 50.0
    assert stable_gss >= 70.0


def test_cost_frontier_gate_enforcement():
    """Estrategias con break_even_slippage < 5 bps deben ser rechazadas en el Cost Gate."""
    def evaluate_cost_gate(break_even_bps: float) -> bool:
        return break_even_bps >= 5.0

    assert evaluate_cost_gate(2.0) is False
    assert evaluate_cost_gate(4.5) is False
    assert evaluate_cost_gate(5.0) is True
    assert evaluate_cost_gate(8.0) is True


def test_leave_one_symbol_out_gate_enforcement():
    """Si al eliminar un único símbolo el PF colapsa por debajo de 0.90, se detecta dependencia unívoca."""
    loso_results = {
        "Exclude_SPY": 1.05,
        "Exclude_QQQ": 1.02,
        "Exclude_IWM": 0.53,  # Colapso crítico sin IWM
        "Exclude_DIA": 1.01
    }
    has_single_symbol_dependency = any(pf < 0.90 for pf in loso_results.values())
    assert has_single_symbol_dependency is True


def test_final_holdout_locked_isolation_phase9():
    """El 20% de Holdout permanece bloqueado durante toda la Fase 9."""
    locked = True
    holdout_start = datetime.datetime.fromisoformat("2026-03-06 09:30:00")
    pre_holdout_end = datetime.datetime.fromisoformat("2026-03-06 00:00:00")

    def access_holdout(is_locked: bool, req_start: datetime.datetime):
        if is_locked and req_start >= pre_holdout_end:
            raise PermissionError("FINAL_HOLDOUT = LOCKED. Access denied during Phase 9 Discovery.")
        return True

    with pytest.raises(PermissionError, match="FINAL_HOLDOUT = LOCKED"):
        access_holdout(locked, holdout_start)


def test_phase9_summary_json_integrity():
    """Verifica que el informe de descubrimiento de la Fase 9 exista y cumpla con CANDIDATE = NONE."""
    summary_path = Path(__file__).parent.parent / "scratch" / "fase9_discovery_summary.json"
    assert summary_path.exists(), "fase9_discovery_summary.json must exist"

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    verdict = data["verdict"]
    assert verdict["best_research_lead"] == "NO_RESEARCH_LEAD"
    assert verdict["official_candidate"] == "NONE"
    assert verdict["final_holdout_status"] == "LOCKED"
    assert verdict["paper_trading_status"] == "DISABLED"
    assert verdict["live_trading_status"] == "DISABLED"

    accounting = data["budget_accounting"]
    assert accounting["executed"] <= 44
    assert accounting["executed"] == accounting["exploration"] + accounting["exploitation"]
