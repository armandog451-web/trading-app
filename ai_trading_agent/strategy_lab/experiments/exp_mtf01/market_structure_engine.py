"""
ai_trading_agent.strategy_lab.experiments.exp_mtf01.market_structure_engine
============================================================================
Motor de Estructura de Mercado H1 (Market Structure & BOS) Causal.
Identifica Swing Highs y Swing Lows causales (SWING_LEFT=3, SWING_RIGHT=3),
confirmados estrictamente al cierre de la barra T+3.
Detecta Break of Structure (BOS) y delimita impulsos estructurales (P0, P1).
"""

from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np


class MarketStructureEngine:
    """Motor de Detección Causal de Swings y Cambios de Estructura."""

    def __init__(self, swing_left: int = 3, swing_right: int = 3):
        self.swing_left = swing_left
        self.swing_right = swing_right

    def identify_swings_causally(self, df_h1: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula swings y registra su tiempo de confirmación estricto.
        Para un swing en índice k, se confirma al cierre de k + swing_right.
        """
        df = df_h1.copy()
        df.sort_index(inplace=True)
        rename_map = {c: c.capitalize() for c in ['open', 'high', 'low', 'close', 'volume'] if c in df.columns}
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        n = len(df)
        df['Is_Swing_High'] = False
        df['Is_Swing_Low'] = False
        df['Swing_High_Price'] = np.nan
        df['Swing_Low_Price'] = np.nan
        df['Confirmed_Swing_High_Price'] = np.nan
        df['Confirmed_Swing_Low_Price'] = np.nan

        highs = df['High'].values
        lows = df['Low'].values

        # Identificar pivotes retrospectivos
        for k in range(self.swing_left, n - self.swing_right):
            # Check swing high
            is_sh = True
            for m in range(1, self.swing_left + 1):
                if highs[k] <= highs[k - m]:
                    is_sh = False
                    break
            if is_sh:
                for m in range(1, self.swing_right + 1):
                    if highs[k] <= highs[k + m]:
                        is_sh = False
                        break
            if is_sh:
                df.iloc[k, df.columns.get_loc('Is_Swing_High')] = True
                df.iloc[k, df.columns.get_loc('Swing_High_Price')] = highs[k]
                # Confirmado en k + swing_right
                conf_idx = k + self.swing_right
                df.iloc[conf_idx, df.columns.get_loc('Confirmed_Swing_High_Price')] = highs[k]

            # Check swing low
            is_sl = True
            for m in range(1, self.swing_left + 1):
                if lows[k] >= lows[k - m]:
                    is_sl = False
                    break
            if is_sl:
                for m in range(1, self.swing_right + 1):
                    if lows[k] >= lows[k + m]:
                        is_sl = False
                        break
            if is_sl:
                df.iloc[k, df.columns.get_loc('Is_Swing_Low')] = True
                df.iloc[k, df.columns.get_loc('Swing_Low_Price')] = lows[k]
                # Confirmado en k + swing_right
                conf_idx = k + self.swing_right
                df.iloc[conf_idx, df.columns.get_loc('Confirmed_Swing_Low_Price')] = lows[k]

        # Propagar hacia adelante los últimos swings confirmados causalmente
        df['Last_Confirmed_Swing_High'] = df['Confirmed_Swing_High_Price'].ffill()
        df['Last_Confirmed_Swing_Low'] = df['Confirmed_Swing_Low_Price'].ffill()

        # Detección de Break of Structure (BOS)
        # BOS alcista: Close supera Last_Confirmed_Swing_High
        df['BOS_Bullish'] = (
            (df['Close'] > df['Last_Confirmed_Swing_High'].shift(1)) &
            (df['Close'].shift(1) <= df['Last_Confirmed_Swing_High'].shift(1))
        )
        # BOS bajista: Close perfora Last_Confirmed_Swing_Low
        df['BOS_Bearish'] = (
            (df['Close'] < df['Last_Confirmed_Swing_Low'].shift(1)) &
            (df['Close'].shift(1) >= df['Last_Confirmed_Swing_Low'].shift(1))
        )

        return df
