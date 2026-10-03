"""
ai_trading_agent.tests.test_indicators_and_regime
=================================================
Pruebas unitarias de indicadores matemáticos y detección de régimen.
"""

from ai_trading_agent.market.indicators import indicators
from ai_trading_agent.market.regime import regime_detector
from ai_trading_agent.domain.enums import MarketRegime


def test_indicators_calculation_valid(bull_bars):
    ind = indicators.calculate_all(bull_bars)

    assert "current_price" in ind
    assert ind["current_price"] > 0
    assert ind["sma20"] > 0
    assert ind["ema9"] > 0
    assert ind["ema21"] > 0
    assert 0.0 <= ind["rsi"] <= 100.0
    assert ind["atr"] > 0.0
    assert ind["vwap"] > 0.0
    assert ind["bb_upper"] >= ind["bb_mid"] >= ind["bb_lower"]
    assert ind["rvol"] > 0.0


def test_regime_detection_bullish(bull_bars):
    ind = indicators.calculate_all(bull_bars)
    regime, reason = regime_detector.detect_regime(ind)

    assert regime in (MarketRegime.BULL_TREND, MarketRegime.HIGH_VOLATILITY, MarketRegime.SIDEWAYS)
    assert len(reason) > 0


def test_regime_detection_empty():
    regime, reason = regime_detector.detect_regime({})
    assert regime == MarketRegime.UNKNOWN
