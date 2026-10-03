"""
ai_trading_agent.tests.test_strategies_and_aggregator
=====================================================
Pruebas de retorno tipado de estrategias y resolución de contradicciones en el Aggregator.
"""

from datetime import datetime
from ai_trading_agent.domain.enums import SignalDirection
from ai_trading_agent.domain.models import StrategySignal
from ai_trading_agent.market.indicators import indicators
from ai_trading_agent.market.regime import regime_detector
from ai_trading_agent.strategies.trend import trend_strategy
from ai_trading_agent.strategies.momentum import momentum_strategy
from ai_trading_agent.signals.aggregator import signal_aggregator


def test_strategies_return_typed_signals(bull_bars):
    ind = indicators.calculate_all(bull_bars)
    regime, _ = regime_detector.detect_regime(ind)

    sig_trend = trend_strategy.evaluate("SPY", bull_bars, ind, regime)
    sig_mom = momentum_strategy.evaluate("SPY", bull_bars, ind, regime)

    assert isinstance(sig_trend, StrategySignal)
    assert isinstance(sig_mom, StrategySignal)
    assert sig_trend.direction in (SignalDirection.BUY, SignalDirection.SELL, SignalDirection.NO_TRADE)
    assert sig_mom.direction in (SignalDirection.BUY, SignalDirection.SELL, SignalDirection.NO_TRADE)


def test_aggregator_contradiction_triggers_no_trade():
    now = datetime.utcnow()
    # Simular una estrategia alcista y otra bajista contradictoria
    sig1 = StrategySignal(
        strategy_id="strat_a",
        symbol="SPY",
        direction=SignalDirection.BUY,
        score=75.0,
        timestamp=now,
        entry_price=500.0,
        stop_loss=495.0,
        take_profit=510.0
    )
    sig2 = StrategySignal(
        strategy_id="strat_b",
        symbol="SPY",
        direction=SignalDirection.SELL,
        score=75.0,
        timestamp=now,
        entry_price=500.0,
        stop_loss=505.0,
        take_profit=490.0
    )

    agg, proposal = signal_aggregator.aggregate("SPY", [sig1, sig2])

    assert agg.direction == SignalDirection.NO_TRADE
    assert agg.is_actionable is False
    assert proposal is None
    assert "No-Trade Engine activado" in agg.rejection_reason
