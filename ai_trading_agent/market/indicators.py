"""
ai_trading_agent.market.indicators
==================================
Suite matemática de indicadores técnicos vectorizados (Instrucción 8).
Fórmulas documentadas, sin look-ahead bias, operando estrictamente sobre barras cerradas.
"""

from typing import List, Dict, Any
import numpy as np
import pandas as pd

from ai_trading_agent.domain.models import OHLCVBar


class TechnicalIndicators:
    """Calculador de indicadores técnicos a partir de listas de OHLCVBar."""

    @staticmethod
    def to_dataframe(bars: List[OHLCVBar]) -> pd.DataFrame:
        """Convierte una lista de barras a un DataFrame de pandas limpio."""
        records = [
            {
                "timestamp": b.timestamp,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume
            }
            for b in bars
        ]
        df = pd.DataFrame.from_records(records)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    @classmethod
    def calculate_all(cls, bars: List[OHLCVBar]) -> Dict[str, Any]:
        """Calcula todos los indicadores requeridos sobre la serie temporal."""
        df = cls.to_dataframe(bars)
        if len(df) < 20:
            return {}

        close = df["close"]
        high = df["high"]
        low = df["low"]
        vol = df["volume"]

        # 1. Medias Móviles Simples (SMA)
        sma20 = float(close.rolling(20).mean().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1]) if len(df) >= 50 else sma20
        sma200 = float(close.rolling(200).mean().iloc[-1]) if len(df) >= 200 else sma50

        # 2. Medias Móviles Exponenciales (EMA 9, 21, 50)
        ema9 = float(close.ewm(span=9, adjust=False).mean().iloc[-1])
        ema21 = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
        ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1]) if len(df) >= 50 else ema21
        ema200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1]) if len(df) >= 200 else ema50

        # 3. RSI (14 periodos con fórmula de Wilder)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi = float((100.0 - (100.0 / (1.0 + rs))).iloc[-1])

        # 4. MACD (12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line
        macd_val = float(macd_line.iloc[-1])
        macd_sig = float(signal_line.iloc[-1])
        macd_h = float(macd_hist.iloc[-1])

        # 5. ATR (Average True Range - 14)
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(abs(high[1:] - close[:-1].values), abs(low[1:] - close[:-1].values))
        )
        atr_series = pd.Series(tr).rolling(14).mean()
        atr = float(atr_series.iloc[-1]) if len(atr_series) >= 14 else float(high.iloc[-1] - low.iloc[-1])
        atr_pct = (atr / float(close.iloc[-1])) * 100.0

        # 6. VWAP (Volume Weighted Average Price)
        typical_price = (high + low + close) / 3.0
        cum_vp = (typical_price * vol).cumsum()
        cum_v = vol.cumsum() + 1e-9
        vwap = float((cum_vp / cum_v).iloc[-1])

        # 7. Bandas de Bollinger (20 periodos, 2 desviaciones)
        bb_mid = float(close.rolling(20).mean().iloc[-1])
        bb_std = float(close.rolling(20).std().iloc[-1])
        bb_upper = bb_mid + (2.0 * bb_std)
        bb_lower = bb_mid - (2.0 * bb_std)

        # 8. RVOL (Relative Volume - Última barra vs promedio de 20 periodos)
        vol_sma20 = float(vol.rolling(20).mean().iloc[-1]) + 1e-9
        rvol = float(vol.iloc[-1] / vol_sma20)

        current_price = float(close.iloc[-1])

        return {
            "current_price": current_price,
            "sma20": round(sma20, 2),
            "sma50": round(sma50, 2),
            "sma200": round(sma200, 2),
            "ema9": round(ema9, 2),
            "ema21": round(ema21, 2),
            "ema50": round(ema50, 2),
            "ema200": round(ema200, 2),
            "rsi": round(rsi, 2),
            "macd": round(macd_val, 3),
            "macd_signal": round(macd_sig, 3),
            "macd_hist": round(macd_h, 3),
            "atr": round(atr, 2),
            "atr_pct": round(atr_pct, 2),
            "vwap": round(vwap, 2),
            "bb_upper": round(bb_upper, 2),
            "bb_mid": round(bb_mid, 2),
            "bb_lower": round(bb_lower, 2),
            "rvol": round(rvol, 2)
        }


indicators = TechnicalIndicators()
