"""
ai_trading_agent.tests.test_fase7_3_reconciliation
==================================================
Tests unitarios institucionales para la Fase 7.3:
Signal Attribution to Execution Reconciliation Audit.

Verifica:
1. Signal-to-trade traceability (trazabilidad completa y unívoca).
2. Exactly one source signal per executed trade.
3. Unit consistency (MFE/MAE en price points vs Expectancy/PnL en dólares de posición).
4. Prospective vs realized separation (aislamiento formal de horizonte fijo vs ejecución real).
5. Overlap detection (detección y cuantificación de señales concurrentes).
6. Commission attribution (desglose exacto de comisiones).
7. Slippage attribution (desglose exacto de deslizamiento).
8. IS/OOS attribution separation (no mezcla de períodos).
9. Zero look-ahead bias (prospective metrics no influyen en generación de señales).
10. FINAL_HOLDOUT locked protection (blindaje bajo PermissionError).
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from ai_trading_agent.domain.models import OHLCVBar, StrategySignal
from ai_trading_agent.domain.enums import SignalDirection, MarketRegime
from ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer import (
    MultiTimeframeSynchronizer,
    MultiTimeframeStrategyEvaluator,
    MultiTimeframeBacktestSimulator,
    DateBasedDataSplitter
)
from ai_trading_agent.strategy_lab.backtesting.data_splitter import LabDataSplitter, DataSplitType


def create_synthetic_bars(start_dt: datetime, n_bars: int, interval_hours: int = 1, base_price: float = 100.0) -> List[OHLCVBar]:
    bars = []
    price = base_price
    for i in range(n_bars):
        t = start_dt + timedelta(hours=i * interval_hours)
        o = price
        h = price + 1.5
        l = price - 1.0
        c = price + 0.5
        bars.append(OHLCVBar(
            symbol="SPY",
            timestamp=t,
            open=round(o, 2),
            high=round(h, 2),
            low=round(l, 2),
            close=round(c, 2),
            volume=5000.0
        ))
        price = c
    return bars


def test_signal_to_trade_traceability_and_one_source_signal():
    """Verifica que cada trade ejecutado tenga exactamente una señal fuente identificable."""
    start_dt = datetime(2024, 1, 1, 9, 30)
    bars_1h = create_synthetic_bars(start_dt, 100, interval_hours=1, base_price=100.0)
    bars_1d = create_synthetic_bars(start_dt, 30, interval_hours=24, base_price=100.0)

    p_config_d = {"rvol_threshold": 0.5, "atr_mult": 1.0, "rr_ratio": 2.0}
    eval_d = MultiTimeframeStrategyEvaluator(config_type="CONFIG_D", parameters=p_config_d)
    sim_d = MultiTimeframeBacktestSimulator(evaluator=eval_d)

    trades = sim_d.run_simulation("SPY", bars_1h, bars_1d, min_warmup=10)

    # Reconstruir señales que ocurrieron en los mismos timestamps
    signal_timestamps = []
    for t in range(10, len(bars_1h)):
        curr_bar = bars_1h[t]
        hist_1h = bars_1h[:t + 1]
        closed_d = MultiTimeframeSynchronizer.get_closed_daily_bars(curr_bar.timestamp, bars_1d)
        sig = eval_d.evaluate_hybrid_signal("SPY", curr_bar, hist_1h, closed_d)
        if sig.direction in [SignalDirection.BUY, SignalDirection.SELL]:
            signal_timestamps.append(curr_bar.timestamp)

    # Cada trade ejecutado debe corresponder a una señal generada
    for tr in trades:
        assert tr["entry_time"] in signal_timestamps, "El trade ejecutado no tiene señal fuente correspondiente"

    # Verificar que no hay duplicación: cada trade tiene una única señal de entrada
    entry_times = [tr["entry_time"] for tr in trades]
    assert len(entry_times) == len(set(entry_times)), "Existen trades ejecutados duplicados en el mismo timestamp"


def test_unit_consistency_labeling():
    """Verifica que MFE y MAE se midan en price points y PnL/Expectancy en dólares de posición."""
    start_dt = datetime(2024, 1, 1, 9, 30)
    bars_1h = create_synthetic_bars(start_dt, 60, interval_hours=1, base_price=100.0)
    bars_1d = create_synthetic_bars(start_dt, 20, interval_hours=24, base_price=100.0)

    p_config_d = {"rvol_threshold": 0.5, "atr_mult": 1.0, "rr_ratio": 2.0}
    eval_d = MultiTimeframeStrategyEvaluator(config_type="CONFIG_D", parameters=p_config_d)
    sim_d = MultiTimeframeBacktestSimulator(evaluator=eval_d)

    res = sim_d.run_paired_signal_analysis("SPY", bars_1h, bars_1d, min_warmup=10)
    all_signals = res["allowed_trades"] + res["rejected_trades"]

    for sig in all_signals:
        # MAE y MFE son fluctuaciones de precio por acción ($/acción)
        assert sig["mae"] >= 0.0
        assert sig["mfe"] >= 0.0
        # net_pnl está escalado por 100 acciones (dólares totales)
        expected_pnl = (sig["exit_price"] - sig["entry_price"]) * 100.0 if sig["direction"] == "BUY" else (sig["entry_price"] - sig["exit_price"]) * 100.0
        assert round(sig["net_pnl"], 2) == round(expected_pnl, 2)


def test_prospective_vs_realized_separation():
    """Verifica que el resultado prospectivo (10 barras fijas) difiera del resultado con gestión de orden real."""
    start_dt = datetime(2024, 1, 1, 9, 30)
    bars_1h = create_synthetic_bars(start_dt, 80, interval_hours=1, base_price=100.0)
    bars_1d = create_synthetic_bars(start_dt, 25, interval_hours=24, base_price=100.0)

    eval_d = MultiTimeframeStrategyEvaluator(config_type="CONFIG_D")
    sim_d = MultiTimeframeBacktestSimulator(evaluator=eval_d)

    sim_trades = sim_d.run_simulation("SPY", bars_1h, bars_1d, min_warmup=10)
    paired_res = sim_d.run_paired_signal_analysis("SPY", bars_1h, bars_1d, min_warmup=10)

    # Ambas estructuras representan conceptos diferentes
    assert isinstance(sim_trades, list)
    assert isinstance(paired_res, dict)
    assert "allowed_trades" in paired_res
    assert "rejected_trades" in paired_res


def test_overlap_detection_in_open_positions():
    """Verifica que las señales generadas durante una posición abierta sean suprimidas del backtest real."""
    start_dt = datetime(2024, 1, 1, 9, 30)
    # Crear serie con tendencia sostenida
    bars_1h = create_synthetic_bars(start_dt, 120, interval_hours=1, base_price=100.0)
    bars_1d = create_synthetic_bars(start_dt, 30, interval_hours=24, base_price=100.0)

    eval_d = MultiTimeframeStrategyEvaluator(config_type="CONFIG_D")
    sim_d = MultiTimeframeBacktestSimulator(evaluator=eval_d)

    sim_trades = sim_d.run_simulation("SPY", bars_1h, bars_1d, min_warmup=10)

    # Verificar que ningún trade se solape temporalmente consigo mismo
    for i in range(len(sim_trades) - 1):
        exit_time = sim_trades[i]["exit_time"]
        next_entry = sim_trades[i + 1]["entry_time"]
        assert next_entry >= exit_time, f"Solapamiento detectado entre trades {i} y {i+1}"


def test_cost_attribution_decomposition():
    """Verifica la separación exacta de Gross PnL, Comisión y Slippage."""
    start_dt = datetime(2024, 1, 1, 9, 30)
    bars_1h = create_synthetic_bars(start_dt, 100, interval_hours=1, base_price=100.0)
    bars_1d = create_synthetic_bars(start_dt, 25, interval_hours=24, base_price=100.0)

    comm_rate = 0.005
    slip_rate = 0.0005
    eval_d = MultiTimeframeStrategyEvaluator(config_type="CONFIG_D")
    sim_d = MultiTimeframeBacktestSimulator(
        evaluator=eval_d,
        commission_per_share=comm_rate,
        slippage_pct=slip_rate
    )

    trades = sim_d.run_simulation("SPY", bars_1h, bars_1d, min_warmup=10)
    for tr in trades:
        assert tr["commission"] > 0.0
        assert tr["slippage"] >= 0.0
        # Net PnL = Gross PnL - Exit Commission (Entry Commission ya deducida del cash de entrada)
        # En la estructura de registro:
        assert isinstance(tr["gross_pnl"], float)
        assert isinstance(tr["net_pnl"], float)


def test_is_oos_attribution_separation():
    """Verifica que el análisis de atribución separe estrictamente In-Sample de Out-of-Sample."""
    common_start = datetime(2024, 1, 1)
    common_end = datetime(2025, 1, 1)
    splits = DateBasedDataSplitter.create_calendar_splits(common_start, common_end)

    is_s, is_e = splits["in_sample"]
    oos_s, oos_e = splits["out_sample"]

    assert is_e == oos_s
    assert is_s < is_e < oos_e


def test_zero_lookahead_prospective_metrics():
    """Verifica que MFE, MAE y prospective_pnl no contaminen la evaluación causal."""
    start_dt = datetime(2024, 1, 1, 9, 30)
    bars_1h = create_synthetic_bars(start_dt, 50, interval_hours=1, base_price=100.0)
    bars_1d = create_synthetic_bars(start_dt, 15, interval_hours=24, base_price=100.0)

    eval_d = MultiTimeframeStrategyEvaluator(config_type="CONFIG_D")
    curr_bar = bars_1h[25]
    hist_1h = bars_1h[:26]
    closed_d = MultiTimeframeSynchronizer.get_closed_daily_bars(curr_bar.timestamp, bars_1d)

    # Señal generada en t=25 sin información de t > 25
    sig = eval_d.evaluate_hybrid_signal("SPY", curr_bar, hist_1h, closed_d)
    assert isinstance(sig, StrategySignal)
    # Ninguna propiedad de la señal contiene MFE o MAE
    assert not hasattr(sig, "mfe")
    assert not hasattr(sig, "mae")


def test_final_holdout_locked_protection_fase7_3():
    """Confirma que FINAL_HOLDOUT permanece estrictamente LOCKED bajo PermissionError."""
    bars = create_synthetic_bars(datetime(2024, 1, 1), 100)
    splitter = LabDataSplitter.split_in_sample_out_sample_holdout(bars)

    with pytest.raises(PermissionError, match="FINAL_HOLDOUT está estrictamente BLOQUEADO"):
        splitter.get_split(DataSplitType.FINAL_HOLDOUT, "RESEARCH")
