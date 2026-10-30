"""
ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_strategy
=====================================================================
Implementación de la Estrategia ST_EMA200_V1 (SuperTrend + EMA 200).

Reglas Cuantitativas:
- Filtro Direccional: EMA(200)
- Disparador: Giro (Flip) de dirección de SuperTrend(10, 3.0)
- Long: Flip a +1 con Close > EMA(200). SL en SuperTrend Line (banda inferior). TP a 1.5R.
- Short: Flip a -1 con Close < EMA(200). SL en SuperTrend Line (banda superior). TP a 1.5R.
- Causalidad Estricta: Señal generada al cierre de T, ejecución al Open de T+1.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.experiments.exp_st01.supertrend_indicator import (
    SuperTrendCalculator,
    SuperTrendPoint,
)


class TradeDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class StrategySignalST:
    bar_index: int
    timestamp: datetime
    symbol: str
    direction: TradeDirection
    signal_price: float
    ema_200: float
    supertrend_val: float
    stop_loss_level: float
    risk_distance: float
    tp_r_multiple: float
    take_profit_level: float
    atr: float


class StEma200Strategy:
    """Estrategia de investigación cuantitativa ST_EMA200_V1."""

    def __init__(
        self,
        ema_period: int = 200,
        atr_period: int = 10,
        supertrend_multiplier: float = 3.0,
        tp_r_multiple: float = 1.5,
        sl_buffer: float = 0.0,
    ):
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.supertrend_multiplier = supertrend_multiplier
        self.tp_r_multiple = tp_r_multiple
        self.sl_buffer = sl_buffer
        self.calculator = SuperTrendCalculator(
            atr_period=atr_period,
            multiplier=supertrend_multiplier,
            ema_period=ema_period,
        )

    def generate_signals(self, symbol: str, bars: List[OHLCVBar]) -> List[StrategySignalST]:
        """Evalúa toda la serie de barras y retorna señales emitidas al cierre de cada barra causalmente."""
        if len(bars) < self.ema_period + 1:
            return []

        st_points = self.calculator.calculate_series(bars)
        signals: List[StrategySignalST] = []

        for i in range(len(bars)):
            pt = st_points[i]
            if pt.ema_200 is None:
                continue

            c = pt.close

            # Condición LONG
            if pt.direction_flip == 1 and c > pt.ema_200:
                sl = pt.supertrend - self.sl_buffer
                risk = c - sl
                if risk > 0.0001:
                    tp = c + self.tp_r_multiple * risk
                    sig = StrategySignalST(
                        bar_index=i,
                        timestamp=bars[i].timestamp,
                        symbol=symbol,
                        direction=TradeDirection.LONG,
                        signal_price=c,
                        ema_200=pt.ema_200,
                        supertrend_val=pt.supertrend,
                        stop_loss_level=sl,
                        risk_distance=risk,
                        tp_r_multiple=self.tp_r_multiple,
                        take_profit_level=tp,
                        atr=pt.atr,
                    )
                    signals.append(sig)

            # Condición SHORT
            elif pt.direction_flip == -1 and c < pt.ema_200:
                sl = pt.supertrend + self.sl_buffer
                risk = sl - c
                if risk > 0.0001:
                    tp = c - self.tp_r_multiple * risk
                    sig = StrategySignalST(
                        bar_index=i,
                        timestamp=bars[i].timestamp,
                        symbol=symbol,
                        direction=TradeDirection.SHORT,
                        signal_price=c,
                        ema_200=pt.ema_200,
                        supertrend_val=pt.supertrend,
                        stop_loss_level=sl,
                        risk_distance=risk,
                        tp_r_multiple=self.tp_r_multiple,
                        take_profit_level=tp,
                        atr=pt.atr,
                    )
                    signals.append(sig)

        return signals
