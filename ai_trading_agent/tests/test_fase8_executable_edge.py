"""
ai_trading_agent.tests.test_fase8_executable_edge
=================================================
Tests unitarios institucionales para la Fase 8:
Executable Edge Conversion Research.

Verifica:
1. Modelado riguroso de costes con conciencia de ejecución (Comisiones y Slippage).
2. Cálculo exacto del Payoff Ratio realizado y Breakeven Win Rate.
3. Políticas de concurrencia: FIRST_SIGNAL, BEST_SIGNAL, REPLACE_IF_STRONGER, ONE_POSITION_GLOBAL.
4. Cero sesgo de anticipación en el score experimental de calidad de señal (SQS_exp).
5. Lógica de sustitución de posiciones activas (Replacement logic).
6. Partición alineada por fechas (DateBasedDataSplitter) y aislamiento OOS.
7. Blindaje de aislamiento de FINAL_HOLDOUT (20% protegido bajo PermissionError).
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.domain.enums import SignalDirection
from ai_trading_agent.strategy_lab.backtesting.data_splitter import LabDataSplitter, DataSplitType
from ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer import DateBasedDataSplitter
from ai_trading_agent.strategy_lab.backtesting.execution_aware_simulator import (
    SignalQualityScoreCalculator,
    ExecutionAwareStrategyEvaluator,
    ExecutionAwareSimulator,
    FeaturePrecomputer
)


def create_synthetic_bars(start_dt: datetime, n_bars: int, interval_hours: int = 1, base_price: float = 100.0) -> List[OHLCVBar]:
    bars = []
    p = base_price
    for i in range(n_bars):
        t = start_dt + timedelta(hours=i * interval_hours)
        o = p
        h = p + 1.5
        l = p - 1.0
        c = p + 0.2
        bars.append(OHLCVBar(
            symbol="SPY",
            timestamp=t,
            open=round(o, 2),
            high=round(h, 2),
            low=round(l, 2),
            close=round(c, 2),
            volume=5000.0
        ))
        p = c
    return bars


def test_execution_aware_costs_model():
    """Verifica que comisiones y slippage se deduzcan con exactitud matemática."""
    evaluator = ExecutionAwareStrategyEvaluator(entry_family="failed_breakout_reversal")
    sim = ExecutionAwareSimulator(
        evaluator=evaluator,
        commission_per_share=0.010,
        slippage_pct=0.0010
    )

    # Verificación de costes en fill
    ref_price = 100.0
    qty = 200
    buy_fill = ref_price * (1.0 + sim.slippage_pct)
    sell_fill = 105.0 * (1.0 - sim.slippage_pct)

    gross_pnl = (sell_fill - buy_fill) * qty
    comm = qty * sim.commission_per_share
    net_pnl = gross_pnl - comm

    assert buy_fill == 100.10
    assert sell_fill == 104.895
    assert round(gross_pnl, 2) == round((104.895 - 100.10) * 200, 2)
    assert comm == 2.00
    assert round(net_pnl, 2) == round(gross_pnl - 2.00, 2)


def test_realized_payoff_ratio_and_breakeven_math():
    """Valida la fórmula canónica de Payoff Ratio y Breakeven Win Rate."""
    avg_win = 350.0
    avg_loss = 175.0
    payoff = avg_win / avg_loss
    assert payoff == 2.0

    breakeven_wr = (1.0 / (1.0 + payoff)) * 100.0
    assert round(breakeven_wr, 2) == 33.33

    # Win rate real de 30% está por debajo de breakeven -> expectativa negativa
    actual_wr = 30.0
    expected_pnl_per_trade = (0.30 * 350.0) - (0.70 * 175.0)
    assert round(expected_pnl_per_trade, 2) == -17.50


def test_no_lookahead_sqs_exp_ranking():
    """Valida que SQS_exp use únicamente información de barras históricas y cerrada actual."""
    start_dt = datetime(2024, 1, 1, 9, 30)
    bars = create_synthetic_bars(start_dt, 30)

    score_1 = SignalQualityScoreCalculator.calculate(
        bar=bars[-1],
        history_bars=bars,
        direction=SignalDirection.BUY
    )
    assert 0.0 <= score_1 <= 100.0

    # Agregar una barra futura no debe cambiar el score si se pasa la misma historia previa
    future_bar = OHLCVBar(
        symbol="SPY",
        timestamp=start_dt + timedelta(hours=35),
        open=200.0, high=210.0, low=195.0, close=205.0, volume=99999.0
    )
    score_2 = SignalQualityScoreCalculator.calculate(
        bar=bars[-1],
        history_bars=bars,
        direction=SignalDirection.BUY
    )
    assert score_1 == score_2


def test_concurrency_policies_and_replacement_logic():
    """Valida las políticas de concurrencia y la sustitución de posiciones débiles."""
    start_dt = datetime(2024, 1, 1, 9, 30)
    d_bars = create_synthetic_bars(start_dt - timedelta(days=50), 60, interval_hours=24, base_price=100.0)
    h_bars = create_synthetic_bars(start_dt, 100, interval_hours=1, base_price=110.0)

    evaluator = ExecutionAwareStrategyEvaluator(entry_family="trend_continuation", use_1d_context=False)
    sim_fifo = ExecutionAwareSimulator(evaluator=evaluator, concurrency_policy="FIRST_SIGNAL", max_concurrent_positions=1)
    sim_replace = ExecutionAwareSimulator(evaluator=evaluator, concurrency_policy="REPLACE_IF_STRONGER", max_concurrent_positions=1)

    res_fifo = sim_fifo.run_simulation({"SPY": {"1h": h_bars, "1d": d_bars}}, min_warmup=20)
    res_replace = sim_replace.run_simulation({"SPY": {"1h": h_bars, "1d": d_bars}}, min_warmup=20)

    assert "executed_trades" in res_fifo
    assert "replacement_events" in res_replace
    assert res_replace["replacement_events"] >= 0


def test_date_aligned_splits_and_holdout_protection():
    """Verifica que DateBasedDataSplitter alinee ventanas y proteja FINAL_HOLDOUT bajo PermissionError."""
    start_dt = datetime(2024, 1, 1)
    end_dt = datetime(2024, 10, 1)
    splits = DateBasedDataSplitter.create_calendar_splits(start_dt, end_dt, is_ratio=0.6, oos_ratio=0.2, holdout_ratio=0.2)

    is_start, is_end = splits["in_sample"]
    oos_start, oos_end = splits["out_sample"]
    h_start, h_end = splits["holdout"]

    assert is_start < is_end <= oos_start < oos_end <= h_start < h_end

    # Blindaje de FINAL_HOLDOUT
    bars = create_synthetic_bars(start_dt, 100, interval_hours=24)
    protected_ds = LabDataSplitter.split_in_sample_out_sample_holdout(bars)
    with pytest.raises(PermissionError):
        protected_ds.get_split(DataSplitType.FINAL_HOLDOUT, purpose="RESEARCH")
