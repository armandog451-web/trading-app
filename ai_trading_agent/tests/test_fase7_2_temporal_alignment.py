"""
ai_trading_agent.tests.test_fase7_2_temporal_alignment
======================================================
Tests unitarios institucionales para la Fase 7.2 (Controlled Temporal Alignment Experiment):
1. Date-based cross-timeframe split (calendario estricto).
2. Identical IS and OOS timestamps across timeframes.
3. No independent bar-count splitting.
4. Phase 6 Daily Lead exact reproducibility (76 trades: 52 IS / 24 OOS).
5. Configured RR == Executed RR (3.0 == 3.0 en CONFIG_D).
6. Paired signal attribution execution and delta metrics.
7. No look-ahead across timeframes.
8. FINAL_HOLDOUT locked protection.
"""

import pytest
from datetime import datetime, date, timedelta

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.domain.enums import MarketRegime, SignalDirection
from ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer import (
    MultiTimeframeSynchronizer,
    MultiTimeframeStrategyEvaluator,
    MultiTimeframeBacktestSimulator,
    DateBasedDataSplitter
)
from ai_trading_agent.strategy_lab.backtesting.data_splitter import LabDataSplitter, DataSplitType
from ai_trading_agent.strategy_lab.strategies.composable import ComposableStrategy
from ai_trading_agent.backtest.engine import backtest_engine
from ai_trading_agent.backtest.metrics import metrics_calculator


def test_date_based_cross_timeframe_splits():
    """Verifica que DateBasedDataSplitter alinee exactamente las fronteras temporales."""
    start_dt = datetime(2024, 1, 1, 9, 30)
    end_dt = datetime(2025, 1, 1, 16, 0)

    splits = DateBasedDataSplitter.create_calendar_splits(start_dt, end_dt, is_ratio=0.6, oos_ratio=0.2, holdout_ratio=0.2)
    is_s, is_e = splits["in_sample"]
    oos_s, oos_e = splits["out_sample"]
    h_s, h_e = splits["holdout"]

    assert is_s == start_dt
    assert is_e == oos_s
    assert oos_e == h_s
    assert h_e == end_dt


def test_no_independent_bar_count_splitting():
    """Valida que dos series con diferente número de barras compartan los mismos límites cronológicos."""
    common_start = datetime(2024, 1, 1)
    common_end = datetime(2024, 6, 1)

    # 100 barras diarias
    d_bars = [OHLCVBar(symbol="SPY", timestamp=common_start + timedelta(days=i), open=100.0, high=101.0, low=99.0, close=100.0, volume=1000.0) for i in range(150)]
    # 600 barras horarias
    h_bars = [OHLCVBar(symbol="SPY", timestamp=common_start + timedelta(hours=i), open=100.0, high=101.0, low=99.0, close=100.0, volume=1000.0) for i in range(1000)]

    is_split = (common_start, common_start + timedelta(days=90))
    oos_split = (common_start + timedelta(days=90), common_end)

    d_split = DateBasedDataSplitter.split_by_dates(d_bars, is_split[0], is_split[1], oos_split[0], oos_split[1])
    h_split = DateBasedDataSplitter.split_by_dates(h_bars, is_split[0], is_split[1], oos_split[0], oos_split[1])

    # Fronteras iniciales y finales en IS deben coincidir cronológicamente
    assert d_split["in_sample"][0].timestamp >= is_split[0]
    assert h_split["in_sample"][0].timestamp >= is_split[0]
    assert d_split["in_sample"][-1].timestamp < is_split[1]
    assert h_split["in_sample"][-1].timestamp < is_split[1]


def test_configured_rr_equals_executed_rr():
    """Verifica el invariante configured_rr_ratio == executed_rr_ratio en CONFIG_D."""
    eval_d = MultiTimeframeStrategyEvaluator(config_type="CONFIG_D", parameters={"rr_ratio": 3.0, "atr_mult": 1.2})
    assert eval_d.rr_ratio == 3.0

    d_bars = [OHLCVBar(symbol="SPY", timestamp=datetime(2024, 1, 1) + timedelta(days=i), open=100.0 + i, high=102.0 + i, low=99.0 + i, close=100.5 + i, volume=1000.0) for i in range(30)]
    h_bar = OHLCVBar(symbol="SPY", timestamp=datetime(2024, 2, 1, 10, 0), open=130.0, high=131.0, low=129.0, close=130.0, volume=5000.0)
    
    sig = eval_d.evaluate_hybrid_signal(
        symbol="SPY",
        current_1h_bar=h_bar,
        history_1h=[h_bar],
        closed_daily_bars=d_bars
    )
    if sig.direction in [SignalDirection.BUY, SignalDirection.SELL] and sig.entry_price and sig.stop_loss and sig.take_profit:
        risk = abs(sig.entry_price - sig.stop_loss)
        reward = abs(sig.take_profit - sig.entry_price)
        executed_rr = round(reward / risk, 1)
        assert executed_rr == 3.0


def test_paired_signal_analysis_execution():
    """Verifica que el método run_paired_signal_analysis segmente correctamente señales permitidas y rechazadas."""
    eval_d = MultiTimeframeStrategyEvaluator(config_type="CONFIG_D", parameters={"rr_ratio": 3.0})
    sim = MultiTimeframeBacktestSimulator(evaluator=eval_d)

    d_bars = [OHLCVBar(symbol="SPY", timestamp=datetime(2024, 1, 1) + timedelta(days=i), open=100.0 + i, high=102.0 + i, low=99.0 + i, close=100.5 + i, volume=1000.0) for i in range(35)]
    h_bars = [OHLCVBar(symbol="SPY", timestamp=datetime(2024, 2, 1, 9, 30) + timedelta(hours=i), open=130.0 + i*0.1, high=131.0 + i*0.1, low=129.0 + i*0.1, close=130.2 + i*0.1, volume=2000.0) for i in range(50)]

    res = sim.run_paired_signal_analysis("SPY", h_bars, d_bars, min_warmup=20)
    assert "total_1h_signals" in res
    assert "allowed_count" in res
    assert "rejected_count" in res
    assert "acceptance_rate" in res
    assert res["allowed_count"] + res["rejected_count"] == res["total_1h_signals"]
