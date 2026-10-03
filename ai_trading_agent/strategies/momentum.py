"""
ai_trading_agent.strategies.momentum
====================================
Estrategia cuantitativa de Momentum.
Evalúa aceleración del precio, RSI, expansión del histograma MACD y volumen relativo (RVOL).
"""

from datetime import datetime
from typing import List, Dict, Any
from ai_trading_agent.domain.enums import SignalDirection, DataQualityStatus, MarketRegime
from ai_trading_agent.domain.models import OHLCVBar, StrategySignal
from ai_trading_agent.strategies.base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(strategy_id="momentum", version="1.0.0")

    def evaluate(
        self,
        symbol: str,
        bars: List[OHLCVBar],
        ind: Dict[str, Any],
        regime: MarketRegime
    ) -> StrategySignal:
        now = bars[-1].timestamp if bars else datetime.utcnow()

        if not ind or len(bars) < 30:
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                timestamp=now,
                data_quality=DataQualityStatus.DATA_UNAVAILABLE,
                reasons=["Datos insuficientes para evaluar momentum"]
            )

        price = ind["current_price"]
        rsi = ind["rsi"]
        macd_hist = ind["macd_hist"]
        rvol = ind["rvol"]
        atr = max(ind["atr"], 0.10)

        reasons = []
        conflicts = []

        # 1. Momentum Alcista: RSI entre 55 y 72, MACD Histograma positivo y RVOL >= 1.2
        is_bullish_mom = (55.0 <= rsi <= 72.0) and (macd_hist > 0) and (rvol >= 1.2)

        # 2. Momentum Bajista: RSI entre 28 y 45, MACD Histograma negativo y RVOL >= 1.2
        is_bearish_mom = (28.0 <= rsi <= 45.0) and (macd_hist < 0) and (rvol >= 1.2)

        if rvol < 1.0:
            conflicts.append(f"Volumen bajo (RVOL={rvol:.2f} < 1.0)")

        if is_bullish_mom:
            direction = SignalDirection.BUY
            reasons.append(f"Fuerte momentum alcista: RSI={rsi:.1f}, MACD Histograma positivo y RVOL={rvol:.1f}x")
            score = 80.0 if regime == MarketRegime.BULL_TREND else 65.0

            stop_loss = round(price - (1.2 * atr), 2)
            risk_dist = price - stop_loss
            take_profit = round(price + (2.0 * risk_dist), 2)

            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=direction,
                score=score,
                timestamp=now,
                reasons=reasons,
                conflicts=conflicts,
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit
            )

        elif is_bearish_mom:
            direction = SignalDirection.SELL
            reasons.append(f"Fuerte momentum bajista: RSI={rsi:.1f}, MACD Histograma negativo y RVOL={rvol:.1f}x")
            score = 80.0 if regime == MarketRegime.BEAR_TREND else 65.0

            stop_loss = round(price + (1.2 * atr), 2)
            risk_dist = stop_loss - price
            take_profit = round(price - (2.0 * risk_dist), 2)

            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=direction,
                score=score,
                timestamp=now,
                reasons=reasons,
                conflicts=conflicts,
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit
            )

        return StrategySignal(
            strategy_id=self.strategy_id,
            strategy_version=self.version,
            symbol=symbol,
            direction=SignalDirection.NO_TRADE,
            score=0.0,
            timestamp=now,
            reasons=["Sin impulso de momentum o volumen relativo insuficiente"]
        )


momentum_strategy = MomentumStrategy()
