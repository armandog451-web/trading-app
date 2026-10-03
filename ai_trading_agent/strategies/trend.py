"""
ai_trading_agent.strategies.trend
=================================
Estrategia cuantitativa de seguimiento de tendencia (Trend Following).
Filtra por cruce dinámico de EMAs, VWAP y estructura de precio con ratio R:R >= 1:2.
"""

from datetime import datetime
from typing import List, Dict, Any
from ai_trading_agent.domain.enums import SignalDirection, DataQualityStatus, MarketRegime
from ai_trading_agent.domain.models import OHLCVBar, StrategySignal
from ai_trading_agent.strategies.base import BaseStrategy


class TrendFollowingStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(strategy_id="trend_following", version="1.0.0")

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
                reasons=["Datos insuficientes para evaluar tendencia"]
            )

        price = ind["current_price"]
        ema9 = ind["ema9"]
        ema21 = ind["ema21"]
        ema50 = ind["ema50"]
        vwap = ind["vwap"]
        atr = max(ind["atr"], 0.10)

        reasons = []
        conflicts = []

        # 1. Condición Tendencia Alcista (BUY)
        is_bullish = (price > ema21) and (ema9 > ema21 > ema50) and (price >= vwap)
        # 2. Condición Tendencia Bajista (SELL)
        is_bearish = (price < ema21) and (ema9 < ema21 < ema50) and (price <= vwap)

        # Filtro de régimen
        if regime == MarketRegime.HIGH_VOLATILITY:
            conflicts.append("Régimen de alta volatilidad activo (mayor riesgo de falso rompimiento)")

        if is_bullish:
            direction = SignalDirection.BUY
            reasons.append(f"Precio (${price:.2f}) sobre EMA21 (${ema21:.2f}) y VWAP (${vwap:.2f}) en expansión alcista")
            score = 78.0 if regime == MarketRegime.BULL_TREND else 62.0

            stop_loss = round(price - (1.5 * atr), 2)
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

        elif is_bearish:
            direction = SignalDirection.SELL
            reasons.append(f"Precio (${price:.2f}) bajo EMA21 (${ema21:.2f}) y VWAP (${vwap:.2f}) en estructura bajista")
            score = 78.0 if regime == MarketRegime.BEAR_TREND else 62.0

            stop_loss = round(price + (1.5 * atr), 2)
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
            reasons=["Sin estructura tendencial clara (mercado en consolidación o EMA enredadas)"]
        )


trend_strategy = TrendFollowingStrategy()
