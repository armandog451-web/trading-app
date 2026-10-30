"""
ai_trading_agent.strategy_lab.experiments.exp_st01.supertrend_indicator
======================================================================
Indicador SuperTrend y Media Móvil Exponencial (EMA) Causal e Incremental.

Reglas matemáticas:
1. True Range (TR):
   TR_t = max(High_t - Low_t, |High_t - Close_{t-1}|, |Low_t - Close_{t-1}|)
   TR_0 = High_0 - Low_0
2. Average True Range (ATR):
   Wilder's Smoothing (RMA) con período N (por defecto 10):
   Para t < N: promedio acumulado sum(TR_0..t) / (t + 1)
   Para t == N - 1: promedio simple sum(TR_0..N-1) / N
   Para t >= N: ATR_t = (ATR_{t-1} * (N - 1) + TR_t) / N
3. Bandas SuperTrend:
   Basic Upper = (High_t + Low_t) / 2 + Multiplier * ATR_t
   Basic Lower = (High_t + Low_t) / 2 - Multiplier * ATR_t
4. Bandas Finales (Anti-repaint / Causal):
   Para t == 0:
     Final Upper_0 = Basic Upper_0
     Final Lower_0 = Basic Lower_0
   Para t > 0:
     Final Upper_t = Basic Upper_t si (Basic Upper_t < Final Upper_{t-1} o Close_{t-1} > Final Upper_{t-1})
                     sino Final Upper_{t-1}
     Final Lower_t = Basic Lower_t si (Basic Lower_t > Final Lower_{t-1} o Close_{t-1} < Final Lower_{t-1})
                     sino Final Lower_{t-1}
5. Dirección / SuperTrend Line:
   Para t < N: Trend_t = 1 (warmup, flip = 0)
   Para t >= N:
     Si Trend_{t-1} == 1:
       Si Close_t < Final Lower_t:
         Trend_t = -1, SuperTrend_t = Final Upper_t
       Sino:
         Trend_t = 1, SuperTrend_t = Final Lower_t
     Sino (Trend_{t-1} == -1):
       Si Close_t > Final Upper_t:
         Trend_t = 1, SuperTrend_t = Final Lower_t
       Sino:
         Trend_t = -1, SuperTrend_t = Final Upper_t
   Flip se produce cuando Trend_t != Trend_{t-1} a partir de t >= N.
"""

from typing import List, Optional, Any
from dataclasses import dataclass
from ai_trading_agent.domain.models import OHLCVBar


@dataclass
class SuperTrendPoint:
    timestamp: Any
    close: float
    atr: float
    basic_upper: float
    basic_lower: float
    final_upper: float
    final_lower: float
    trend: int  # +1 para Bullish, -1 para Bearish
    supertrend: float
    direction_flip: int  # +1 si flip a Bullish, -1 si flip a Bearish, 0 si sin cambio
    ema_200: Optional[float] = None


class SuperTrendCalculator:
    """Calculador causal de SuperTrend y EMA para secuencias de barras."""

    def __init__(self, atr_period: int = 10, multiplier: float = 3.0, ema_period: int = 200):
        self.atr_period = atr_period
        self.multiplier = multiplier
        self.ema_period = ema_period

    def calculate_series(self, bars: List[OHLCVBar]) -> List[SuperTrendPoint]:
        n_bars = len(bars)
        if n_bars == 0:
            return []

        # 1. Calcular True Range
        tr = [bars[0].high - bars[0].low]
        for i in range(1, n_bars):
            h = bars[i].high
            l = bars[i].low
            prev_c = bars[i - 1].close
            tr.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))

        # 2. Calcular Wilder RMA ATR
        atr = [0.0] * n_bars
        running_tr_sum = 0.0
        for i in range(n_bars):
            if i < self.atr_period:
                running_tr_sum += tr[i]
                atr[i] = running_tr_sum / (i + 1)
            else:
                atr[i] = (atr[i - 1] * (self.atr_period - 1) + tr[i]) / self.atr_period

        # 3. Calcular EMA
        ema = [None] * n_bars
        running_close_sum = 0.0
        alpha = 2.0 / (self.ema_period + 1.0)
        for i in range(n_bars):
            c = bars[i].close
            if i < self.ema_period - 1:
                running_close_sum += c
                ema[i] = None
            elif i == self.ema_period - 1:
                running_close_sum += c
                ema[i] = running_close_sum / self.ema_period
            else:
                ema[i] = c * alpha + ema[i - 1] * (1.0 - alpha)

        # 4. Calcular Bandas y Dirección
        points: List[SuperTrendPoint] = []
        prev_final_upper = 0.0
        prev_final_lower = 0.0
        prev_trend = 1

        for i in range(n_bars):
            c = bars[i].close
            h = bars[i].high
            l = bars[i].low
            hl2 = (h + l) / 2.0
            curr_atr = atr[i]

            basic_upper = hl2 + self.multiplier * curr_atr
            basic_lower = hl2 - self.multiplier * curr_atr

            if i == 0:
                final_upper = basic_upper
                final_lower = basic_lower
                curr_trend = 1
                st_val = final_lower
                flip = 0
            else:
                prev_c = bars[i - 1].close

                # Final Upper
                if basic_upper < prev_final_upper or prev_c > prev_final_upper:
                    final_upper = basic_upper
                else:
                    final_upper = prev_final_upper

                # Final Lower
                if basic_lower > prev_final_lower or prev_c < prev_final_lower:
                    final_lower = basic_lower
                else:
                    final_lower = prev_final_lower

                # Trend transition
                if i < self.atr_period:
                    curr_trend = 1
                    st_val = final_lower
                    flip = 0
                else:
                    if prev_trend == 1:
                        if c < final_lower:
                            curr_trend = -1
                            st_val = final_upper
                        else:
                            curr_trend = 1
                            st_val = final_lower
                    else:  # prev_trend == -1
                        if c > final_upper:
                            curr_trend = 1
                            st_val = final_lower
                        else:
                            curr_trend = -1
                            st_val = final_upper

                    flip = 0
                    if curr_trend == 1 and prev_trend == -1:
                        flip = 1
                    elif curr_trend == -1 and prev_trend == 1:
                        flip = -1

            points.append(
                SuperTrendPoint(
                    timestamp=bars[i].timestamp,
                    close=c,
                    atr=curr_atr,
                    basic_upper=basic_upper,
                    basic_lower=basic_lower,
                    final_upper=final_upper,
                    final_lower=final_lower,
                    trend=curr_trend,
                    supertrend=st_val,
                    direction_flip=flip,
                    ema_200=ema[i],
                )
            )

            prev_final_upper = final_upper
            prev_final_lower = final_lower
            prev_trend = curr_trend

        return points


class IncrementalSuperTrend:
    """Rastreador SuperTrend estrictamente incremental estado a estado."""

    def __init__(self, atr_period: int = 10, multiplier: float = 3.0, ema_period: int = 200):
        self.atr_period = atr_period
        self.multiplier = multiplier
        self.ema_period = ema_period

        self.bar_count = 0
        self.prev_close: Optional[float] = None
        self.running_tr_sum = 0.0
        self.current_atr: Optional[float] = None

        self.running_close_sum = 0.0
        self.current_ema: Optional[float] = None

        self.prev_final_upper: float = 0.0
        self.prev_final_lower: float = 0.0
        self.prev_trend: int = 1

    def update(self, bar: OHLCVBar) -> SuperTrendPoint:
        c = bar.close
        h = bar.high
        l = bar.low
        hl2 = (h + l) / 2.0

        # 1. TR
        if self.prev_close is None:
            tr_val = h - l
        else:
            tr_val = max(h - l, abs(h - self.prev_close), abs(l - self.prev_close))

        # 2. ATR
        if self.bar_count < self.atr_period:
            self.running_tr_sum += tr_val
            self.current_atr = self.running_tr_sum / (self.bar_count + 1)
        else:
            self.current_atr = (self.current_atr * (self.atr_period - 1) + tr_val) / self.atr_period

        # 3. EMA
        if self.bar_count < self.ema_period - 1:
            self.running_close_sum += c
            self.current_ema = None
        elif self.bar_count == self.ema_period - 1:
            self.running_close_sum += c
            self.current_ema = self.running_close_sum / self.ema_period
        else:
            alpha = 2.0 / (self.ema_period + 1.0)
            self.current_ema = c * alpha + self.current_ema * (1.0 - alpha)

        basic_upper = hl2 + self.multiplier * self.current_atr
        basic_lower = hl2 - self.multiplier * self.current_atr

        if self.bar_count == 0:
            final_upper = basic_upper
            final_lower = basic_lower
            curr_trend = 1
            st_val = final_lower
            flip = 0
        else:
            # Final Upper
            if basic_upper < self.prev_final_upper or self.prev_close > self.prev_final_upper:
                final_upper = basic_upper
            else:
                final_upper = self.prev_final_upper

            # Final Lower
            if basic_lower > self.prev_final_lower or self.prev_close < self.prev_final_lower:
                final_lower = basic_lower
            else:
                final_lower = self.prev_final_lower

            # Trend
            if self.bar_count < self.atr_period:
                curr_trend = 1
                st_val = final_lower
                flip = 0
            else:
                if self.prev_trend == 1:
                    if c < final_lower:
                        curr_trend = -1
                        st_val = final_upper
                    else:
                        curr_trend = 1
                        st_val = final_lower
                else:
                    if c > final_upper:
                        curr_trend = 1
                        st_val = final_lower
                    else:
                        curr_trend = -1
                        st_val = final_upper

                flip = 0
                if curr_trend == 1 and self.prev_trend == -1:
                    flip = 1
                elif curr_trend == -1 and self.prev_trend == 1:
                    flip = -1

        pt = SuperTrendPoint(
            timestamp=bar.timestamp,
            close=c,
            atr=self.current_atr,
            basic_upper=basic_upper,
            basic_lower=basic_lower,
            final_upper=final_upper,
            final_lower=final_lower,
            trend=curr_trend,
            supertrend=st_val,
            direction_flip=flip,
            ema_200=self.current_ema,
        )

        self.prev_final_upper = final_upper
        self.prev_final_lower = final_lower
        self.prev_trend = curr_trend
        self.prev_close = c
        self.bar_count += 1
        return pt
