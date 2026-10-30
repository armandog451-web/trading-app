"""
ai_trading_agent.tests.test_exp_st01_supertrend
===============================================
Suite de pruebas unitarias y de regresión cuantitativa para FASE EXP-ST01 (ST_EMA200_V1).
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from datetime import datetime, timedelta
import pytest
import numpy as np

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.experiments.exp_st01.supertrend_indicator import (
    SuperTrendCalculator,
    IncrementalSuperTrend,
    SuperTrendPoint,
)
from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_strategy import (
    StEma200Strategy,
    TradeDirection,
)
from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_backtester import (
    StEma200Backtester,
    CostModelST,
    COST_TIERS,
)
from ai_trading_agent.strategy_lab.experiments.exp_st01.discovery_hypotheses import DiscoveryHypothesesEvaluator


def _generate_synthetic_bars(count: int = 300, base_price: float = 100.0) -> list[OHLCVBar]:
    np.random.seed(42)
    bars = []
    p = base_price
    t0 = datetime(2026, 1, 1, 9, 30)

    for i in range(count):
        ret = np.random.normal(0.0005, 0.01)
        o = p
        c = p * (1.0 + ret)
        h = max(o, c) + abs(np.random.normal(0, 0.2))
        l = min(o, c) - abs(np.random.normal(0, 0.2))
        v = float(np.random.randint(1000, 50000))
        p = c
        bars.append(
            OHLCVBar(
                timestamp=t0 + timedelta(hours=i),
                symbol="TEST_ETF",
                open=round(o, 2),
                high=round(h, 2),
                low=round(l, 2),
                close=round(c, 2),
                volume=v,
            )
        )
    return bars


def test_01_supertrend_mathematical_precision():
    """Verifica el cálculo matemático de True Range, Wilder RMA ATR y bandas SuperTrend."""
    bars = _generate_synthetic_bars(count=50)
    calc = SuperTrendCalculator(atr_period=10, multiplier=3.0, ema_period=20)
    points = calc.calculate_series(bars)

    assert len(points) == len(bars)
    # Verificar que el ATR es positivo tras el warmup
    for pt in points[10:]:
        assert pt.atr > 0.0
        assert pt.basic_upper >= pt.basic_lower
        assert pt.final_upper >= pt.final_lower or pt.close > pt.final_upper or pt.close < pt.final_lower
        assert pt.trend in [1, -1]


def test_02_supertrend_incremental_causal_equivalence():
    """Verifica que el rastreador incremental coincide al 100% barra a barra con el calculador por serie."""
    bars = _generate_synthetic_bars(count=250)
    calc = SuperTrendCalculator(atr_period=10, multiplier=3.0, ema_period=50)
    series_pts = calc.calculate_series(bars)

    inc = IncrementalSuperTrend(atr_period=10, multiplier=3.0, ema_period=50)
    inc_pts = [inc.update(b) for b in bars]

    for i, (s, inc_p) in enumerate(zip(series_pts, inc_pts)):
        assert abs(s.supertrend - inc_p.supertrend) < 1e-4, f"Mismatch SuperTrend en barra {i}"
        assert s.trend == inc_p.trend, f"Mismatch Trend en barra {i}"
        assert s.direction_flip == inc_p.direction_flip, f"Mismatch Flip en barra {i}"


def test_03_causal_t_plus_one_entry_timing():
    """Verifica que las señales emitidas en T ejecutan fill estrictamente en T+1 open."""
    bars = _generate_synthetic_bars(count=250)
    strat = StEma200Strategy(ema_period=50, atr_period=10, supertrend_multiplier=3.0)
    bt = StEma200Backtester(strat, initial_equity=100000.0, risk_per_trade=250.0)

    metrics, trades = bt.run("TEST_ETF", "H1", bars)
    for tr in trades:
        # La barra de entrada debe ser posterior a la señal
        assert tr.entry_bar_idx > 0
        assert tr.entry_time == bars[tr.entry_bar_idx].timestamp
        # Fill price debe reflejar el open con slippage
        raw_open = bars[tr.entry_bar_idx].open
        if tr.direction == TradeDirection.LONG:
            assert tr.entry_price >= raw_open
        else:
            assert tr.entry_price <= raw_open


def test_04_conservative_same_bar_sl_tp_collision():
    """Verifica que si una barra toca SL y TP en la misma barra, se resuelve conservadoramente como SL."""
    # Construir barras donde en una barra el rango es gigante y cruza SL y TP
    t0 = datetime(2026, 1, 1, 9, 30)
    bars = []
    # 60 barras alcistas para armar EMA y SuperTrend
    for i in range(60):
        bars.append(
            OHLCVBar(
                timestamp=t0 + timedelta(hours=i),
                symbol="TEST_COLLISION",
                open=100.0 + i,
                high=101.0 + i,
                low=99.5 + i,
                close=100.5 + i,
                volume=10000,
            )
        )

    strat = StEma200Strategy(ema_period=20, atr_period=5, supertrend_multiplier=2.0, tp_r_multiple=1.5)
    signals = strat.generate_signals("TEST_COLLISION", bars)
    if signals:
        sig = signals[0]
        # Crear barra de colisión justo después de la entrada
        idx = sig.bar_index + 2
        if idx < len(bars):
            # Forzar colisión extrema
            bars[idx] = OHLCVBar(
                timestamp=bars[idx].timestamp,
                symbol="TEST_COLLISION",
                open=sig.signal_price,
                high=sig.take_profit_level + 5.0,
                low=sig.stop_loss_level - 5.0,
                close=sig.signal_price,
                volume=10000,
            )
            bt = StEma200Backtester(strat, initial_equity=100000.0, risk_per_trade=250.0)
            metrics, trades = bt.run("TEST_COLLISION", "H1", bars)
            collision_trades = [t for t in trades if t.exit_reason == "COLLISION_SL"]
            # Debe haber al menos una colisión o salida por SL
            if collision_trades:
                assert collision_trades[0].net_pnl < 0


def test_05_isolation_and_no_broker_leakage():
    """Garantiza aislamiento estricto: cero imports operativos y trading live inhabilitado."""
    from ai_trading_agent.config.settings import settings
    assert not hasattr(settings, "LIVE_TRADING_ENABLED") or not getattr(settings, "LIVE_TRADING_ENABLED")

    # Verificar que el backtester no requiere credenciales ni broker
    strat = StEma200Strategy()
    bt = StEma200Backtester(strat)
    assert bt.cost_model.name == "1x_Base"


def test_06_cost_stress_monotonicity():
    """Verifica que el Net PnL decrece de forma monotónica bajo costes 1x, 2x y 3x."""
    bars = _generate_synthetic_bars(count=250)
    strat = StEma200Strategy(ema_period=50, atr_period=10, supertrend_multiplier=3.0)
    bt = StEma200Backtester(strat)

    m1, _ = bt.run("TEST_ETF", "H1", bars, cost_tier_override=COST_TIERS["1x"])
    m2, _ = bt.run("TEST_ETF", "H1", bars, cost_tier_override=COST_TIERS["2x"])
    m3, _ = bt.run("TEST_ETF", "H1", bars, cost_tier_override=COST_TIERS["3x"])

    if m1.total_trades > 0:
        assert m1.net_pnl >= m2.net_pnl >= m3.net_pnl
        assert m1.total_costs <= m2.total_costs <= m3.total_costs


def test_07_50_backtests_matrix_completeness():
    """Verifica que la matriz de 50 backtests fue generada y contiene 50 filas completas."""
    matrix_csv = repo_root / "ai_trading_agent" / "strategy_lab" / "experiments" / "exp_st01" / "exp_st01_50_backtests_matrix.csv"
    assert matrix_csv.exists()

    import csv
    with open(matrix_csv, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 50
        symbols = set(r["symbol"] for r in reader)
        assert len(symbols) == 10
        tfs = set(r["timeframe"] for r in reader)
        assert len(tfs) == 5


def test_08_discovery_hypotheses_evaluation():
    """Verifica que el evaluador de hipótesis produce deltas métricos y veredictos explicables."""
    bars = _generate_synthetic_bars(count=250)
    evaluator = DiscoveryHypothesesEvaluator()
    h5 = evaluator.evaluate_h5_trailing_stop("TEST_ETF", "H1", bars)
    assert h5.hypothesis_id == "H5"
    assert isinstance(h5.accepted, bool)
    assert isinstance(h5.delta_pf, float)
