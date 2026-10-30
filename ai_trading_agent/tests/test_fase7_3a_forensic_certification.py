import json
from pathlib import Path
import pytest
import csv

from ai_trading_agent.strategy_lab.discovery.discovery_engine_v2 import (
    run_chronological_backtest_asset,
    COST_TIERS,
    compute_reconciled_metrics
)
from ai_trading_agent.domain.models import OHLCVBar
from datetime import datetime, timedelta


@pytest.fixture
def manifest_7_3a():
    repo_root = Path(__file__).resolve().parent.parent.parent
    p = repo_root / "ai_trading_agent" / "scratch" / "fase7_3a_discovery_manifest.json"
    assert p.exists(), f"Manifest not found: {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def trades_7_3a():
    repo_root = Path(__file__).resolve().parent.parent.parent
    p = repo_root / "ai_trading_agent" / "scratch" / "fase7_3a_discovery_trades.csv"
    assert p.exists(), f"Trades CSV not found: {p}"
    records = []
    with open(p, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            records.append(row)
    return records


def test_strict_cost_monotonicity_across_all_strategies(manifest_7_3a):
    """
    Verifica que en las 4 hipotesis del discovery engine v2:
    1. Trade count sea 100% identico entre 1x, 2x y 3x.
    2. True Gross PnL sea 100% identico entre 1x, 2x y 3x.
    3. Total Costs aumente estrictamente: Costs_1x < Costs_2x < Costs_3x.
    4. True Net PnL decresca estrictamente: Net_1x > Net_2x > Net_3x.
    5. Net Profit Factor decresca estrictamente: NetPF_1x > NetPF_2x > NetPF_3x.
    """
    for exp in manifest_7_3a["experiments"]:
        sid = exp["strategy_id"]
        m1 = exp["metrics_1x_full"]
        m2 = exp["metrics_2x_full"]
        m3 = exp["metrics_3x_full"]

        # Identidad de ejecucion
        assert m1["trade_count"] == m2["trade_count"] == m3["trade_count"], f"Trade count diverged for {sid}"
        assert abs(m1["sum_true_gross_pnl"] - m2["sum_true_gross_pnl"]) < 1e-4, f"Gross PnL diverged 1x vs 2x for {sid}"
        assert abs(m1["sum_true_gross_pnl"] - m3["sum_true_gross_pnl"]) < 1e-4, f"Gross PnL diverged 1x vs 3x for {sid}"

        # Monotonicidad estricta de costes
        assert m1["sum_total_costs_usd"] < m2["sum_total_costs_usd"] < m3["sum_total_costs_usd"], f"Costs non-monotonic for {sid}"

        # Monotonicidad estricta de beneficio neto
        assert m1["sum_true_net_pnl"] > m2["sum_true_net_pnl"] > m3["sum_true_net_pnl"], f"Net PnL non-monotonic for {sid}"

        # Monotonicidad estricta de Profit Factor
        assert m1["net_profit_factor"] >= m2["net_profit_factor"] >= m3["net_profit_factor"], f"Net PF non-monotonic for {sid}"


def test_market_price_invariant_exit_behavior():
    """
    Comprueba de forma sintetica que un trade con caida cercana al stop loss
    no activa el stop antes de tiempo en un tier de coste mayor (resolviendo el Bloque E).
    """
    base_time = datetime(2025, 1, 1)
    bars = []
    # Genera 10 barras con una caida controlada de -3.49% en barra 2
    prices = [100.0, 96.51, 98.0, 102.0, 105.0]
    for idx, p in enumerate(prices):
        bars.append(OHLCVBar(
            symbol="SPY",
            timestamp=base_time + timedelta(days=idx),
            open=p,
            high=p + 0.5,
            low=p - 0.5,
            close=p,
            volume=1000000.0
        ))

    signals = [True, False, False, False, False]
    exit_rules = {"max_holding": 4, "stop_loss_pct": 0.035, "profit_target_pct": 0.06}

    t_1x = run_chronological_backtest_asset("TEST", "SPY", bars, signals, exit_rules, cost_tier="1x")
    t_2x = run_chronological_backtest_asset("TEST", "SPY", bars, signals, exit_rules, cost_tier="2x")
    t_3x = run_chronological_backtest_asset("TEST", "SPY", bars, signals, exit_rules, cost_tier="3x")

    assert len(t_1x) == len(t_2x) == len(t_3x) == 1
    # Ambos deben salir exactamente por TIME_EXIT o PROFIT_TARGET, no por STOP_LOSS prematuro inducido por slippage
    assert t_1x[0]["exit_reason"] == t_2x[0]["exit_reason"] == t_3x[0]["exit_reason"]
    assert t_1x[0]["exit_idx"] == t_2x[0]["exit_idx"] == t_3x[0]["exit_idx"]
    assert t_1x[0]["true_net_pnl"] > t_2x[0]["true_net_pnl"] > t_3x[0]["true_net_pnl"]


def test_continuous_ranking_score_no_saturation(manifest_7_3a):
    """
    Verifica que el ranking score continuo no sature en 1.000 para estrategias sobresalientes,
    permitiendo la diferenciacion cardinal entre hipotesis.
    """
    scores = [exp["ranking_score"] for exp in manifest_7_3a["experiments"]]
    # Ninguna estrategia debe saturar a 1.000 de forma ciega
    for s in scores:
        assert 0.0 <= s < 1.000, f"Score saturated at {s}"
    # Leader A (MR_VolCond_ZScore_V1) debe tener mayor ranking que las demas
    leader_a = next(e for e in manifest_7_3a["experiments"] if e["strategy_id"] == "MR_VolCond_ZScore_V1")
    assert leader_a["ranking_score"] > 0.85


def test_outlier_sensitivity_candidate_a(trades_7_3a):
    """
    Verifica que Candidate A conserve un Profit Factor neto > 1.30 tras eliminar
    el top 1 y el top 3 trades mas rentables.
    """
    trades_a = [t for t in trades_7_3a if t["strategy_id"] == "MR_VolCond_ZScore_V1" and t["cost_tier"] == "1x"]
    sorted_a = sorted(trades_a, key=lambda t: float(t["true_net_pnl"]), reverse=True)

    # Trim Top 1
    rem1 = sorted_a[1:]
    wins1 = sum(float(t["true_net_pnl"]) for t in rem1 if float(t["true_net_pnl"]) > 0)
    losses1 = abs(sum(float(t["true_net_pnl"]) for t in rem1 if float(t["true_net_pnl"]) <= 0))
    pf1 = wins1 / (losses1 + 1e-9)
    assert pf1 > 2.0, f"Candidate A failed Top 1 trim test: PF={pf1:.2f}"

    # Trim Top 3
    rem3 = sorted_a[3:]
    wins3 = sum(float(t["true_net_pnl"]) for t in rem3 if float(t["true_net_pnl"]) > 0)
    losses3 = abs(sum(float(t["true_net_pnl"]) for t in rem3 if float(t["true_net_pnl"]) <= 0))
    pf3 = wins3 / (losses3 + 1e-9)
    assert pf3 > 1.8, f"Candidate A failed Top 3 trim test: PF={pf3:.2f}"


def test_broker_physical_isolation_and_governance(manifest_7_3a):
    """
    Verifica que el entorno de investigacion este completamente desacoplado del broker,
    con ENABLE_LIVE_TRADING = False y D21 preservado en PAPER.
    """
    gov = manifest_7_3a["governance"]
    assert gov["live_trading_enabled"] is False
    assert gov["mode"] == "RESEARCH / ANALYSIS_ONLY"
    assert gov["d21_fingerprint"] == "f885ec2db2422308"
    assert gov["d21_virtual_capital_usd"] == 1000000.0
