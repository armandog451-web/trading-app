"""
ai_trading_agent.strategy_lab.experiments.exp_mtf01.m5_entry_engine
===================================================================
Motor de Entrada de Precisión Intradía M5 Causal.
Monitorea microestructura con fractales rápidos (L=2, R=2),
detecta ruptura local de confirmación, aplica expiración por timeout (24 barras M5)
e invalidación por perforación de Fib 0.75.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


class M5EntryEngine:
    """Motor de Disparador de Entrada en M5."""

    def __init__(
        self,
        m5_swing_left: int = 2,
        m5_swing_right: int = 2,
        timeout_bars: int = 24
    ):
        self.m5_swing_left = m5_swing_left
        self.m5_swing_right = m5_swing_right
        self.timeout_bars = timeout_bars

    def compute_m5_swings(self, df_m5: pd.DataFrame) -> pd.DataFrame:
        """Calcula fractales locales en M5 causales."""
        df = df_m5.copy()
        df.sort_index(inplace=True)
        rename_map = {c: c.capitalize() for c in ['open', 'high', 'low', 'close', 'volume'] if c in df.columns}
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        n = len(df)
        df['M5_Swing_High'] = np.nan
        df['M5_Swing_Low'] = np.nan

        highs = df['High'].values
        lows = df['Low'].values

        for k in range(self.m5_swing_left, n - self.m5_swing_right):
            # Swing High
            is_sh = True
            for m in range(1, self.m5_swing_left + 1):
                if highs[k] <= highs[k - m]:
                    is_sh = False
                    break
            if is_sh:
                for m in range(1, self.m5_swing_right + 1):
                    if highs[k] <= highs[k + m]:
                        is_sh = False
                        break
            if is_sh:
                conf_idx = k + self.m5_swing_right
                df.iloc[conf_idx, df.columns.get_loc('M5_Swing_High')] = highs[k]

            # Swing Low
            is_sl = True
            for m in range(1, self.m5_swing_left + 1):
                if lows[k] >= lows[k - m]:
                    is_sl = False
                    break
            if is_sl:
                for m in range(1, self.m5_swing_right + 1):
                    if lows[k] >= lows[k + m]:
                        is_sl = False
                        break
            if is_sl:
                conf_idx = k + self.m5_swing_right
                df.iloc[conf_idx, df.columns.get_loc('M5_Swing_Low')] = lows[k]

        df['Last_M5_Swing_High'] = df['M5_Swing_High'].ffill()
        df['Last_M5_Swing_Low'] = df['M5_Swing_Low'].ffill()

        return df

    def evaluate_entry_trigger(
        self,
        current_bar: pd.Series,
        setup: Dict[str, Any],
        bars_since_setup: int
    ) -> Dict[str, Any]:
        """
        Evalúa si la barra M5 actual confirma la entrada.
        setup contiene: direction, fib_618, fib_75, zone_min, zone_max, p0, p1, etc.
        """
        if bars_since_setup > self.timeout_bars:
            return {"triggered": False, "status": "TIMEOUT_EXPIRED"}

        direction = setup["direction"]
        fib_75 = setup["fib_75"]

        # Comprobar invalidación
        if direction == "BUY":
            if current_bar['Low'] < fib_75:
                return {"triggered": False, "status": "INVALIDATED_FIB_75"}
            # Ruptura de swing high local M5
            last_sh = current_bar.get('Last_M5_Swing_High', np.nan)
            if not pd.isna(last_sh) and current_bar['Close'] > last_sh:
                return {
                    "triggered": True,
                    "status": "CONFIRMED_BREAKOUT",
                    "breakout_level": float(last_sh),
                    "signal_time": current_bar.name,
                    "signal_close": float(current_bar['Close'])
                }
        else: # SELL
            if current_bar['High'] > fib_75:
                return {"triggered": False, "status": "INVALIDATED_FIB_75"}
            # Ruptura de swing low local M5
            last_sl = current_bar.get('Last_M5_Swing_Low', np.nan)
            if not pd.isna(last_sl) and current_bar['Close'] < last_sl:
                return {
                    "triggered": True,
                    "status": "CONFIRMED_BREAKOUT",
                    "breakout_level": float(last_sl),
                    "signal_time": current_bar.name,
                    "signal_close": float(current_bar['Close'])
                }

        return {"triggered": False, "status": "WAITING_BREAKOUT"}
