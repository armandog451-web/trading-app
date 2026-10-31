"""
ai_trading_agent.strategy_lab.experiments.exp_mtf01.daily_context_engine
========================================================================
Motor de Contexto Diario (D1) Causal para MTF_ExtremeReversal_V1.
Calcula extremos históricos (60d), aceleración (5d) y desaceleración en velas D1 cerradas.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


class DailyContextEngine:
    """Motor Causal de Contexto Diario D1."""

    def __init__(
        self,
        extreme_lookback: int = 60,
        extreme_atr_tolerance: float = 0.50,
        atr_period: int = 14,
        accel_lookback: int = 5,
        accel_atr_multiple: float = 2.50,
        decel_body_ratio_threshold: float = 0.45,
        decel_rejection_wick_threshold: float = 0.35,
    ):
        self.extreme_lookback = extreme_lookback
        self.extreme_atr_tolerance = extreme_atr_tolerance
        self.atr_period = atr_period
        self.accel_lookback = accel_lookback
        self.accel_atr_multiple = accel_atr_multiple
        self.decel_body_ratio_threshold = decel_body_ratio_threshold
        self.decel_rejection_wick_threshold = decel_rejection_wick_threshold

    def compute_daily_features(self, df_d1: pd.DataFrame) -> pd.DataFrame:
        """Calcula todas las métricas de D1 de forma estrictamente causal."""
        df = df_d1.copy()
        df.sort_index(inplace=True)

        # Standardize column names
        cols = {c: c.capitalize() for c in df.columns}
        df.rename(columns=cols, inplace=True)

        # True Range and ATR
        prev_close = df['Close'].shift(1)
        tr1 = df['High'] - df['Low']
        tr2 = (df['High'] - prev_close).abs()
        tr3 = (df['Low'] - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(window=self.atr_period).mean()

        # Rolling 60-day Min Low and Max High (excluyendo la barra actual para causalidad estricta)
        df['Min_Low_60'] = df['Low'].shift(1).rolling(window=self.extreme_lookback).min()
        df['Max_High_60'] = df['High'].shift(1).rolling(window=self.extreme_lookback).max()

        # Distancia al extremo
        df['Dist_To_Min_Low'] = (df['Close'] - df['Min_Low_60']).abs()
        df['Dist_To_Max_High'] = (df['Close'] - df['Max_High_60']).abs()

        df['Is_Lower_Extreme'] = df['Close'] <= (df['Min_Low_60'] + self.extreme_atr_tolerance * df['ATR'])
        df['Is_Upper_Extreme'] = df['Close'] >= (df['Max_High_60'] - self.extreme_atr_tolerance * df['ATR'])

        # Aceleración hacia el extremo
        # Para extremo inferior: caída fuerte en los últimos 5 días
        df['Displacement_5d'] = df['Close'] - df['Close'].shift(self.accel_lookback)
        df['Accel_Down'] = (df['Close'].shift(self.accel_lookback) - df['Close']) >= (self.accel_atr_multiple * df['ATR'])
        df['Accel_Up'] = (df['Close'] - df['Close'].shift(self.accel_lookback)) >= (self.accel_atr_multiple * df['ATR'])

        # Desaceleración
        bar_range = df['High'] - df['Low']
        body = (df['Close'] - df['Open']).abs()
        body_ratio = body / bar_range.replace(0, np.nan)
        lower_wick = df[['Open', 'Close']].min(axis=1) - df['Low']
        upper_wick = df['High'] - df[['Open', 'Close']].max(axis=1)
        lower_wick_ratio = lower_wick / bar_range.replace(0, np.nan)
        upper_wick_ratio = upper_wick / bar_range.replace(0, np.nan)

        inside_bar = (df['High'] <= df['High'].shift(1)) & (df['Low'] >= df['Low'].shift(1))

        # Desaceleración en extremo inferior: cuerpo pequeño + mecha inferior de rechazo O inside bar
        df['Decel_Bullish'] = (
            ((body_ratio <= self.decel_body_ratio_threshold) & (lower_wick_ratio >= self.decel_rejection_wick_threshold)) | inside_bar
        )

        # Desaceleración en extremo superior: cuerpo pequeño + mecha superior de rechazo O inside bar
        df['Decel_Bearish'] = (
            ((body_ratio <= self.decel_body_ratio_threshold) & (upper_wick_ratio >= self.decel_rejection_wick_threshold)) | inside_bar
        )

        # Contexto Diario Activo
        # Para Long: extremo inferior + aceleración bajista previa + desaceleración actual
        df['D1_Bullish_Context'] = df['Is_Lower_Extreme'] & df['Accel_Down'] & df['Decel_Bullish']
        # Para Short: extremo superior + aceleración alcista previa + desaceleración actual
        df['D1_Bearish_Context'] = df['Is_Upper_Extreme'] & df['Accel_Up'] & df['Decel_Bearish']

        return df

    def get_context_for_date(self, df_d1_features: pd.DataFrame, current_timestamp: pd.Timestamp) -> Dict[str, Any]:
        """Obtiene el contexto D1 estrictamente cerrado disponible para current_timestamp."""
        target_date = current_timestamp.date()
        # Solo barras con fecha estrictamente anterior al día de trading actual
        closed_bars = df_d1_features[df_d1_features.index.date < target_date]
        if closed_bars.empty:
            return {
                "bullish_context": False,
                "bearish_context": False,
                "last_closed_date": None,
                "atr": 0.0
            }

        last_row = closed_bars.iloc[-1]
        # El contexto es válido si ocurrió en las últimas 3 sesiones cerradas
        recent_bars = closed_bars.iloc[-3:]
        bullish = bool(recent_bars['D1_Bullish_Context'].any())
        bearish = bool(recent_bars['D1_Bearish_Context'].any())

        return {
            "bullish_context": bullish,
            "bearish_context": bearish,
            "last_closed_date": last_row.name.strftime("%Y-%m-%d"),
            "atr": float(last_row['ATR']) if not pd.isna(last_row['ATR']) else 0.0,
            "min_low_60": float(last_row['Min_Low_60']) if not pd.isna(last_row['Min_Low_60']) else 0.0,
            "max_high_60": float(last_row['Max_High_60']) if not pd.isna(last_row['Max_High_60']) else 0.0
        }
