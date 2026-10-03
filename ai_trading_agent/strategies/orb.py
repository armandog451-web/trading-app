"""
ai_trading_agent.strategies.orb
===============================
Estrategia cuantitativa Opening Range Breakout (ORB - Instrucción 9D).
Rangos configurables (5m, 15m, 30m), filtro estricto de volumen institucional (RVOL >= 1.4)
y confirmación de cierre fuera del rango para eliminar rupturas falsas (Fakeouts).
"""

from datetime import datetime, time
from typing import List, Dict, Any, Optional
from ai_trading_agent.domain.enums import SignalDirection, DataQualityStatus, MarketRegime
from ai_trading_agent.domain.models import OHLCVBar, StrategySignal
from ai_trading_agent.strategies.base import BaseStrategy


class OpeningRangeBreakoutStrategy(BaseStrategy):
    def __init__(
        self,
        range_minutes: int = 15,
        rvol_threshold: float = 1.4,
        market_open_hour: int = 9,
        market_open_minute: int = 30
    ):
        super().__init__(strategy_id="orb_breakout", version="1.0.0")
        self.range_minutes = range_minutes
        self.rvol_threshold = rvol_threshold
        self.market_open_hour = market_open_hour
        self.market_open_minute = market_open_minute

    def calculate_opening_range(self, bars: List[OHLCVBar]) -> Optional[Dict[str, float]]:
        """
        Calcula el techo (OR High) y piso (OR Low) del rango de apertura.
        """
        if not bars:
            return None

        # Tomar las barras correspondientes al rango inicial (ej. primeros 15 min = 3 barras de 5m)
        bars_in_range = []
        for b in bars:
            t = b.timestamp.time()
            if (t.hour == self.market_open_hour and self.market_open_minute <= t.minute < (self.market_open_minute + self.range_minutes)):
                bars_in_range.append(b)

        if not bars_in_range:
            # Fallback determinista si los timestamps son sintéticos/relativos
            fallback_count = max(1, self.range_minutes // 5)
            bars_in_range = bars[:fallback_count]

        or_high = max(b.high for b in bars_in_range)
        or_low = min(b.low for b in bars_in_range)
        or_mid = (or_high + or_low) / 2.0

        return {
            "or_high": round(or_high, 2),
            "or_low": round(or_low, 2),
            "or_mid": round(or_mid, 2),
            "range_size": round(or_high - or_low, 2)
        }

    def evaluate(
        self,
        symbol: str,
        bars: List[OHLCVBar],
        ind: Dict[str, Any],
        regime: MarketRegime
    ) -> StrategySignal:
        now = bars[-1].timestamp if bars else datetime.utcnow()

        if not ind or len(bars) < 25:
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                timestamp=now,
                data_quality=DataQualityStatus.DATA_UNAVAILABLE,
                reasons=["Datos insuficientes para calcular Opening Range"]
            )

        range_data = self.calculate_opening_range(bars)
        if not range_data:
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                timestamp=now,
                reasons=["No se pudo establecer el rango de apertura"]
            )

        or_high = range_data["or_high"]
        or_low = range_data["or_low"]
        or_mid = range_data["or_mid"]
        price = ind["current_price"]
        rvol = ind.get("rvol", 1.0)
        atr = max(ind["atr"], 0.10)

        reasons = []
        conflicts = []

        # 1. Filtro de Volumen Relativo Estricto (RVOL >= 1.4x)
        has_volume = rvol >= self.rvol_threshold
        if not has_volume:
            conflicts.append(f"Falta confirmación de volumen institucional (RVOL={rvol:.2f} < {self.rvol_threshold:.1f})")

        # 2. Ruptura Alcista: Cierre confirmado sobre OR High con RVOL
        is_bullish_break = (price > or_high) and has_volume

        # 3. Ruptura Bajista: Cierre confirmado bajo OR Low con RVOL
        is_bearish_break = (price < or_low) and has_volume

        if is_bullish_break:
            direction = SignalDirection.BUY
            reasons.append(
                f"Ruptura Alcista de Rango de Apertura ({self.range_minutes}m): "
                f"Precio (${price:.2f}) > Techo OR (${or_high:.2f}) con expansión RVOL={rvol:.2f}x"
            )
            # Stop Loss en el punto medio del rango (OR Mid) o 1.2 ATR
            stop_loss = round(max(or_mid, price - (1.2 * atr)), 2)
            risk_dist = price - stop_loss
            take_profit = round(price + (2.0 * risk_dist), 2)
            score = 85.0 if regime == MarketRegime.BULL_TREND else 72.0

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

        elif is_bearish_break:
            direction = SignalDirection.SELL
            reasons.append(
                f"Ruptura Bajista de Rango de Apertura ({self.range_minutes}m): "
                f"Precio (${price:.2f}) < Piso OR (${or_low:.2f}) con expansión RVOL={rvol:.2f}x"
            )
            stop_loss = round(min(or_mid, price + (1.2 * atr)), 2)
            risk_dist = stop_loss - price
            take_profit = round(price - (2.0 * risk_dist), 2)
            score = 85.0 if regime == MarketRegime.BEAR_TREND else 72.0

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
            reasons=[f"Precio dentro del rango de apertura (${or_low:.2f} - ${or_high:.2f}) o sin volumen de ruptura"]
        )


orb_strategy = OpeningRangeBreakoutStrategy()
