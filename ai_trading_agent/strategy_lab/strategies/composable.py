"""
ai_trading_agent.strategy_lab.strategies.composable
======================================================
Estrategia compuesta modular y parametrizable para el Strategy Laboratory.
Permite combinar dinámicamente condiciones de entrada, salidas, filtros de régimen y volumen.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from ai_trading_agent.domain.enums import SignalDirection, MarketRegime
from ai_trading_agent.domain.models import OHLCVBar, StrategySignal
from ai_trading_agent.strategies.base import BaseStrategy


class ComposableStrategy(BaseStrategy):
    """
    Estrategia compuesta parametrizable capaz de ser instanciada por el Strategy Genesis Engine.
    """

    def __init__(
        self,
        strategy_id: str,
        name: str,
        version: str = "1.0",
        parameters: Optional[Dict[str, Any]] = None,
        rules: Optional[Dict[str, Any]] = None
    ):
        super().__init__(strategy_id=strategy_id, version=version)
        self.name = name
        self.parameters = parameters or {}
        self.rules = rules or {}

        # Extraer parámetros con valores por defecto conservadores
        self.min_rsi = self.parameters.get("min_rsi", 30.0)
        self.max_rsi = self.parameters.get("max_rsi", 70.0)
        self.min_rvol = self.parameters.get("min_rvol", 1.2)
        self.atr_stop_mult = self.parameters.get("atr_stop_mult", 1.5)
        self.rr_target = self.parameters.get("rr_target", 2.0)
        self.allowed_regimes = self.parameters.get(
            "allowed_regimes",
            [MarketRegime.BULL_TREND.value, MarketRegime.SIDEWAYS.value, MarketRegime.HIGH_VOLATILITY.value]
        )

    def evaluate(
        self,
        symbol: str,
        bars: List[OHLCVBar],
        indicators: Dict[str, Any],
        regime: MarketRegime
    ) -> StrategySignal:
        if not bars or len(bars) < 20:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                direction=SignalDirection.NONE,
                score=0.0,
                reasons=["Histórico insuficiente"],
                timestamp=bars[-1].timestamp if bars else datetime.utcnow()
            )

        # 1. Filtro de Régimen de Mercado
        if regime.value not in self.allowed_regimes:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                direction=SignalDirection.NONE,
                score=0.0,
                reasons=[f"Régimen no permitido: {regime.value}"],
                timestamp=bars[-1].timestamp
            )

        current_bar = bars[-1]
        close = current_bar.close
        rsi = indicators.get("rsi", 50.0)
        rvol = indicators.get("rvol", 1.0)
        vwap = indicators.get("vwap", close)
        atr = indicators.get("atr", close * 0.01)
        ema9 = indicators.get("ema_9", close)
        ema21 = indicators.get("ema_21", close)

        reasons = []
        score = 50.0
        direction = SignalDirection.NONE

        # 2. Evaluación de Condiciones de Entrada (Modular)
        is_long_setup = (ema9 > ema21) and (close > vwap) and (rvol >= self.min_rvol) and (rsi >= self.min_rsi and rsi <= self.max_rsi)
        is_short_setup = (ema9 < ema21) and (close < vwap) and (rvol >= self.min_rvol) and (rsi >= self.min_rsi and rsi <= self.max_rsi)

        if is_long_setup:
            direction = SignalDirection.BUY
            score = min(95.0, 60.0 + (rvol * 10.0) + ((close - vwap) / close * 100.0))
            reasons.append(f"Setup Alcista Compuesto: EMA9 ({ema9:.2f}) > EMA21 ({ema21:.2f}) | RVOL: {rvol:.2f} | RSI: {rsi:.1f}")
        elif is_short_setup:
            direction = SignalDirection.SELL
            score = min(95.0, 60.0 + (rvol * 10.0) + ((vwap - close) / vwap * 100.0))
            reasons.append(f"Setup Bajista Compuesto: EMA9 ({ema9:.2f}) < EMA21 ({ema21:.2f}) | RVOL: {rvol:.2f} | RSI: {rsi:.1f}")
        else:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                direction=SignalDirection.NONE,
                score=0.0,
                reasons=["Sin setup compuesto actionable"],
                timestamp=current_bar.timestamp
            )

        # 3. Geometría de Precios
        if direction == SignalDirection.BUY:
            stop_loss = round(close - (atr * self.atr_stop_mult), 2)
            take_profit = round(close + ((close - stop_loss) * self.rr_target), 2)
        else:
            stop_loss = round(close + (atr * self.atr_stop_mult), 2)
            take_profit = round(close - ((stop_loss - close) * self.rr_target), 2)

        return StrategySignal(
            strategy_name=self.name,
            symbol=symbol,
            direction=direction,
            score=round(score, 1),
            suggested_entry=close,
            suggested_stop_loss=stop_loss,
            suggested_take_profit=take_profit,
            reasons=reasons,
            timestamp=current_bar.timestamp
        )
