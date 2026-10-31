"""
ai_trading_agent.strategy_lab.experiments.exp_mtf01.fibonacci_confluence_engine
==============================================================================
Motor de Confluencia Fibonacci (0.618 / 0.75) y EMA 50 en H1.
Calcula retrocesos objetivos sobre impulsos estructurales confirmados y
delimita la zona de confluencia con EMA 50.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


class FibonacciConfluenceEngine:
    """Motor de Retroceso de Fibonacci y Confluencia con EMA 50."""

    def __init__(
        self,
        ema_period: int = 50,
        fib_retracement: float = 0.618,
        fib_stop_reference: float = 0.75,
        confluence_tolerance_atr_multiple: float = 0.25,
        atr_period: int = 14
    ):
        self.ema_period = ema_period
        self.fib_retracement = fib_retracement
        self.fib_stop_reference = fib_stop_reference
        self.confluence_tolerance_atr_multiple = confluence_tolerance_atr_multiple
        self.atr_period = atr_period

    def compute_h1_indicators(self, df_h1: pd.DataFrame) -> pd.DataFrame:
        """Calcula EMA 50 y ATR 14 en H1."""
        df = df_h1.copy()
        df.sort_index(inplace=True)
        cols = {c: c.capitalize() for c in df.columns}
        df.rename(columns=cols, inplace=True)

        df['EMA50'] = df['Close'].ewm(span=self.ema_period, adjust=False).mean()

        prev_close = df['Close'].shift(1)
        tr1 = df['High'] - df['Low']
        tr2 = (df['High'] - prev_close).abs()
        tr3 = (df['Low'] - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR_H1'] = tr.rolling(window=self.atr_period).mean()

        return df

    def evaluate_confluence(
        self,
        p0: float,
        p1: float,
        direction: str,
        ema50: float,
        atr_h1: float
    ) -> Dict[str, Any]:
        """
        Evalúa si el nivel 0.618 presenta confluencia causal con la EMA 50.
        direction: 'BUY' (Long) o 'SELL' (Short).
        """
        if p1 == p0 or atr_h1 <= 0:
            return {"confluent": False, "fib_618": 0.0, "fib_75": 0.0, "zone_min": 0.0, "zone_max": 0.0}

        impulse_range = abs(p1 - p0)

        if direction == "BUY":
            fib_618 = p1 - (self.fib_retracement * impulse_range)
            fib_75 = p1 - (self.fib_stop_reference * impulse_range)
        else:
            fib_618 = p1 + (self.fib_retracement * impulse_range)
            fib_75 = p1 + (self.fib_stop_reference * impulse_range)

        # Distancia entre Fib 0.618 y EMA 50
        dist_ema = abs(fib_618 - ema50)
        tol = self.confluence_tolerance_atr_multiple * atr_h1
        is_confluent = dist_ema <= tol

        zone_min = min(fib_618, ema50) - tol
        zone_max = max(fib_618, ema50) + tol

        return {
            "confluent": is_confluent,
            "fib_618": round(fib_618, 4),
            "fib_75": round(fib_75, 4),
            "distance_to_ema": round(dist_ema, 4),
            "tolerance": round(tol, 4),
            "zone_min": round(zone_min, 4),
            "zone_max": round(zone_max, 4),
            "p0": p0,
            "p1": p1
        }
