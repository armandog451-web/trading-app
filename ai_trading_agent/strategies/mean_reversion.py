"""
ai_trading_agent.strategies.mean_reversion
==========================================
Estrategia cuantitativa de reversión a la media (Mean Reversion - Instrucción 9C).
Identifica agotamiento extremo en Bandas de Bollinger y distancia a VWAP,
filtrando enérgicamente contra tendencias fuertes para evitar cuchillos cayendo.
"""

from datetime import datetime
from typing import List, Dict, Any
from ai_trading_agent.domain.enums import SignalDirection, DataQualityStatus, MarketRegime
from ai_trading_agent.domain.models import OHLCVBar, StrategySignal
from ai_trading_agent.strategies.base import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(strategy_id="mean_reversion", version="1.0.0")

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
                reasons=["Datos insuficientes para evaluar reversión a la media"]
            )

        price = ind["current_price"]
        rsi = ind["rsi"]
        bb_upper = ind["bb_upper"]
        bb_lower = ind["bb_lower"]
        bb_mid = ind["bb_mid"]
        vwap = ind["vwap"]
        atr = max(ind["atr"], 0.10)

        reasons = []
        conflicts = []

        # 1. Filtro Estricto Anti-Tendencia Fuerte (Instrucción 9C)
        # No comprar en caídas libres si el régimen es BEAR_TREND
        if regime == MarketRegime.BEAR_TREND:
            conflicts.append("Filtro de tendencia fuerte: No se permiten compras por reversión en BEAR_TREND (riesgo de caída libre)")
        if regime == MarketRegime.BULL_TREND:
            conflicts.append("Filtro de tendencia fuerte: No se permiten ventas en corto por reversión en BULL_TREND (fuerza compradora)")

        # 2. Detección de Sobreventa / Sobrecompra técnica
        raw_oversold = (price <= bb_lower * 1.005) and (rsi <= 32.0)
        raw_overbought = (price >= bb_upper * 0.995) and (rsi >= 68.0)

        # Si hay sobreventa pero el mercado está en caída libre (BEAR_TREND): Bloqueo estricto
        if raw_oversold and regime == MarketRegime.BEAR_TREND:
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                timestamp=now,
                reasons=["Filtro anti-tendencia: Compra por reversión bloqueada en régimen BEAR_TREND (cuchillo cayendo)."],
                conflicts=conflicts
            )

        # Si hay sobrecompra pero el mercado está en euforia compradora (BULL_TREND): Bloqueo estricto
        if raw_overbought and regime == MarketRegime.BULL_TREND:
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                timestamp=now,
                reasons=["Filtro anti-tendencia: Venta corta por reversión bloqueada en régimen BULL_TREND."],
                conflicts=conflicts
            )

        if raw_oversold:
            direction = SignalDirection.BUY
            reasons.append(
                f"Agotamiento bajista extremo: RSI sobrevendido ({rsi:.1f} <= 32) tocando Banda Inferior (${bb_lower:.2f})"
            )
            target = max(vwap, bb_mid)
            stop_loss = round(price - (1.2 * atr), 2)
            risk_dist = price - stop_loss
            take_profit = round(max(target, price + (2.0 * risk_dist)), 2)
            score = 82.0 if regime == MarketRegime.SIDEWAYS else 68.0

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

        elif raw_overbought:
            direction = SignalDirection.SELL
            reasons.append(
                f"Agotamiento alcista extremo: RSI sobrecomprado ({rsi:.1f} >= 68) rechazando Banda Superior (${bb_upper:.2f})"
            )
            target = min(vwap, bb_mid)
            stop_loss = round(price + (1.2 * atr), 2)
            risk_dist = stop_loss - price
            take_profit = round(min(target, price - (2.0 * risk_dist)), 2)
            score = 82.0 if regime == MarketRegime.SIDEWAYS else 68.0

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
            reasons=["El precio se encuentra dentro de zonas normales de volatilidad (sin sobrecompra/sobreventa extrema)"],
            conflicts=conflicts
        )


mean_reversion_strategy = MeanReversionStrategy()
