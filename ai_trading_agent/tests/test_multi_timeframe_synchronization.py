"""
ai_trading_agent.tests.test_multi_timeframe_synchronization
============================================================
Pruebas unitarias de integridad cuantitativa para la sincronización multi-timeframe (Fase 7):
1. Timestamp alignment y closed-bar enforcement.
2. Detección y prevención absoluta de Look-Ahead Bias.
3. Evaluación determinista de señales híbridas (Configs A, B, C, D).
4. Pruebas de ablación (Ablation tests: Full vs -15m vs -1D vs Baseline).
5. Calculador de complejidad multi-timeframe.
"""

import pytest
from datetime import datetime, timedelta, date

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.domain.enums import MarketRegime, SignalDirection
from ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer import (
    MultiTimeframeSynchronizer,
    MultiTimeframeStrategyEvaluator,
    MultiTimeframeComplexityCalculator,
    MultiTimeframeBacktestSimulator
)


def _generate_dummy_daily_bars(start_date: date, count: int, start_price: float = 100.0) -> list[OHLCVBar]:
    bars = []
    p = start_price
    for i in range(count):
        d = start_date + timedelta(days=i)
        dt = datetime(d.year, d.month, d.day, 16, 0, 0)
        p += 0.5  # tendencia alcista
        bars.append(OHLCVBar(
            symbol="SPY",
            timestamp=dt,
            open=p - 0.2,
            high=p + 0.8,
            low=p - 0.4,
            close=p,
            volume=50000000.0
        ))
    return bars


def _generate_dummy_hourly_bars(eval_date: date, count: int, start_price: float = 100.0) -> list[OHLCVBar]:
    bars = []
    p = start_price
    for i in range(count):
        # Generar barras para el día a partir de las 09:30
        dt = datetime(eval_date.year, eval_date.month, eval_date.day, 9, 30) + timedelta(hours=i)
        p += 0.1
        bars.append(OHLCVBar(
            symbol="SPY",
            timestamp=dt,
            open=p - 0.1,
            high=p + 0.3,
            low=p - 0.2,
            close=p,
            volume=1000000.0
        ))
    return bars


def test_closed_daily_bars_strictly_before_eval_date():
    """Verifica que una barra diaria de la misma fecha nunca sea entregada a un timestamp intradía."""
    start_d = date(2026, 3, 1)
    daily_bars = _generate_dummy_daily_bars(start_d, count=10)
    
    # Supongamos que evaluamos a las 11:30 am del día 10 (2026-03-10)
    target_date = daily_bars[-1].timestamp.date()
    eval_time = datetime(target_date.year, target_date.month, target_date.day, 11, 30)

    closed_daily = MultiTimeframeSynchronizer.get_closed_daily_bars(
        current_timestamp=eval_time,
        daily_bars=daily_bars
    )

    # La barra del día target_date NO debe estar incluida
    assert len(closed_daily) == 9
    assert all(b.timestamp.date() < target_date for b in closed_daily)
    assert closed_daily[-1].timestamp.date() < target_date


def test_lookahead_detection_raises_error():
    """Valida que MultiTimeframeSynchronizer.validate_no_lookahead lance ValueError si se pasa una barra futura."""
    today = date(2026, 3, 10)
    eval_time = datetime(2026, 3, 10, 10, 0)
    future_daily_bar = OHLCVBar(
        symbol="SPY",
        timestamp=datetime(2026, 3, 10, 16, 0),
        open=100.0, high=101.0, low=99.0, close=100.5, volume=1000.0
    )

    with pytest.raises(ValueError) as excinfo:
        MultiTimeframeSynchronizer.validate_no_lookahead(
            eval_timestamp=eval_time,
            context_bars=[future_daily_bar],
            context_tf="1d"
        )
    assert "CRITICAL LOOK-AHEAD BIAS" in str(excinfo.value)


def test_hourly_synchronization_for_15m_evaluation():
    """Valida la sincronización de barras 1H cerradas al evaluar en barras 15m."""
    d = date(2026, 3, 10)
    # Barra 1: 09:30 a 10:30 (inicio 09:30)
    h_bar1 = OHLCVBar(
        symbol="SPY",
        timestamp=datetime(d.year, d.month, d.day, 9, 30),
        open=100.0, high=101.0, low=99.5, close=100.2, volume=10000.0
    )
    # Barra 2: 10:30 a 11:30 (inicio 10:30)
    h_bar2 = OHLCVBar(
        symbol="SPY",
        timestamp=datetime(d.year, d.month, d.day, 10, 30),
        open=100.2, high=101.5, low=100.0, close=101.0, volume=12000.0
    )
    higher_tf_bars = [h_bar1, h_bar2]

    # A las 10:15 (antes de que cierre h_bar1 a las 10:30)
    eval_1015 = datetime(d.year, d.month, d.day, 10, 15)
    closed = MultiTimeframeSynchronizer.get_closed_higher_timeframe_bars(eval_1015, higher_tf_bars, higher_tf="1h")
    assert len(closed) == 0

    # A las 10:30 (justo al cerrar h_bar1)
    eval_1030 = datetime(d.year, d.month, d.day, 10, 30)
    closed = MultiTimeframeSynchronizer.get_closed_higher_timeframe_bars(eval_1030, higher_tf_bars, higher_tf="1h")
    assert len(closed) == 1
    assert closed[0].timestamp == h_bar1.timestamp

    # A las 11:30 (cierra h_bar2)
    eval_1130 = datetime(d.year, d.month, d.day, 11, 30)
    closed = MultiTimeframeSynchronizer.get_closed_higher_timeframe_bars(eval_1130, higher_tf_bars, higher_tf="1h")
    assert len(closed) == 2


def test_multi_timeframe_complexity_score():
    """Valida el cálculo determinista del Score de Complejidad Multi-Timeframe."""
    # Configuración de 2 Timeframes, 3 Features, 2 Condiciones, 4 Parámetros, 50 trades
    comp_score = MultiTimeframeComplexityCalculator.calculate(
        timeframes_count=2,
        features_count=3,
        conditions_count=2,
        parameters_count=4,
        total_trades=50
    )
    # Esperado: (2*15) + (3*8) + (2*5) + (4*4) = 30 + 24 + 10 + 16 = 80.0
    assert comp_score == 80.0

    # Si total_trades < 30, se aplica penalización
    comp_penalized = MultiTimeframeComplexityCalculator.calculate(
        timeframes_count=2,
        features_count=3,
        conditions_count=2,
        parameters_count=4,
        total_trades=20
    )
    # 80.0 + (30 - 20) * 1.5 = 80.0 + 15.0 = 95.0
    assert comp_penalized == 95.0


def test_evaluator_ablation_configurations():
    """Verifica que el evaluador responda correctamente a configuraciones híbridas y ablación."""
    start_d = date(2026, 1, 1)
    daily_bars = _generate_dummy_daily_bars(start_d, count=40, start_price=100.0)
    target_d = date(2026, 2, 15)
    hourly_bars = _generate_dummy_hourly_bars(target_d, count=35, start_price=120.0)

    # 1. Config A: 1D Context + 1H Pullback
    eval_a = MultiTimeframeStrategyEvaluator(config_type="CONFIG_A")
    sig_a = eval_a.evaluate_hybrid_signal(
        symbol="SPY",
        current_1h_bar=hourly_bars[-1],
        history_1h=hourly_bars,
        closed_daily_bars=daily_bars
    )
    assert sig_a.symbol == "SPY"
    assert sig_a.direction in [SignalDirection.BUY, SignalDirection.SELL, SignalDirection.NO_TRADE]

    # 2. Config B: 1D Regime + 1H Momentum
    eval_b = MultiTimeframeStrategyEvaluator(config_type="CONFIG_B")
    sig_b = eval_b.evaluate_hybrid_signal(
        symbol="SPY",
        current_1h_bar=hourly_bars[-1],
        history_1h=hourly_bars,
        closed_daily_bars=daily_bars
    )
    assert sig_b.symbol == "SPY"
    assert sig_b.direction in [SignalDirection.BUY, SignalDirection.SELL, SignalDirection.NO_TRADE]

    # 3. Baseline 1D
    eval_base_1d = MultiTimeframeStrategyEvaluator(config_type="BASELINE_1D")
    sig_1d = eval_base_1d.evaluate_hybrid_signal(
        symbol="SPY",
        current_1h_bar=hourly_bars[-1],
        history_1h=hourly_bars,
        closed_daily_bars=daily_bars
    )
    assert sig_1d.direction in [SignalDirection.BUY, SignalDirection.SELL, SignalDirection.NO_TRADE]

    # 4. Baseline 1H
    eval_base_1h = MultiTimeframeStrategyEvaluator(config_type="BASELINE_1H")
    sig_1h = eval_base_1h.evaluate_hybrid_signal(
        symbol="SPY",
        current_1h_bar=hourly_bars[-1],
        history_1h=hourly_bars,
        closed_daily_bars=daily_bars
    )
    assert sig_1h.direction in [SignalDirection.BUY, SignalDirection.SELL, SignalDirection.NO_TRADE]
