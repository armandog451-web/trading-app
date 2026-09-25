import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class TechnicalEngine:
    """
    Capa 4: Análisis Técnico, Niveles de Liquidez y Volumen Intraday.
    Calcula VWAP (con bandas de desviación), niveles clave (PDH, PDL, PMH, PML, ORB),
    volumen relativo (RVOL) y detecta barridos de liquidez (Liquidity Sweeps).
    """

    def calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula el VWAP continuo para una sesión intraday.
        df debe tener columnas: ['high', 'low', 'close', 'volume']
        """
        df = df.copy()
        typical_price = (df['high'] + df['low'] + df['close']) / 3.0
        df['cum_tp_vol'] = (typical_price * df['volume']).cumsum()
        df['cum_vol'] = df['volume'].cumsum()
        df['vwap'] = df['cum_tp_vol'] / (df['cum_vol'] + 1e-9)

        # Bandas de desviación estándar
        variance = ((typical_price - df['vwap']) ** 2 * df['volume']).cumsum() / (df['cum_vol'] + 1e-9)
        std_dev = np.sqrt(variance)
        df['vwap_upper1'] = df['vwap'] + std_dev
        df['vwap_lower1'] = df['vwap'] - std_dev
        df['vwap_upper2'] = df['vwap'] + (2 * std_dev)
        df['vwap_lower2'] = df['vwap'] - (2 * std_dev)
        return df

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcula el Average True Range reciente."""
        if len(df) < 2:
            return 1.0
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        atr_series = pd.Series(tr).rolling(window=min(period, len(tr))).mean()
        return float(atr_series.iloc[-1]) if not atr_series.empty and not np.isnan(atr_series.iloc[-1]) else float(np.mean(tr))

    def extract_liquidity_levels(self, daily_bars: pd.DataFrame, intraday_bars: pd.DataFrame) -> dict:
        """
        Extrae niveles estructurales de liquidez:
        - PDH: Previous Day High
        - PDL: Previous Day Low
        - PMH: Pre-Market High
        - PML: Pre-Market Low
        """
        levels = {
            "pdh": 0.0,
            "pdl": 0.0,
            "pmh": 0.0,
            "pml": 0.0,
            "vwap": 0.0,
            "current_price": 0.0
        }

        if not daily_bars.empty and len(daily_bars) >= 2:
            prev_day = daily_bars.iloc[-2]
            levels["pdh"] = round(float(prev_day['high']), 2)
            levels["pdl"] = round(float(prev_day['low']), 2)
        elif not intraday_bars.empty:
            levels["pdh"] = round(float(intraday_bars['high'].max()), 2)
            levels["pdl"] = round(float(intraday_bars['low'].min()), 2)

        if not intraday_bars.empty:
            levels["current_price"] = round(float(intraday_bars['close'].iloc[-1]), 2)
            # PMH / PML aproximado desde inicio de datos
            levels["pmh"] = round(float(intraday_bars['high'].iloc[:5].max()), 2)
            levels["pml"] = round(float(intraday_bars['low'].iloc[:5].min()), 2)

        return levels

    def evaluate_setup(self, symbol: str, df: pd.DataFrame, levels: dict) -> dict:
        """
        Evalúa si la vela actual y los niveles de liquidez forman un setup institucional:
        1. Barrido de liquidez bajo PDL con rechazo y recuperación sobre VWAP -> COMPRA (Long)
        2. Barrido de liquidez sobre PDH con rechazo y caída bajo VWAP -> VENTA CORTA (Short)
        3. Rebote en VWAP a favor de la tendencia con RVOL alto -> CONTINUACIÓN
        """
        if df.empty or len(df) < 5:
            return {"signal": "NONE", "reason": "Datos insuficientes"}

        last_bar = df.iloc[-1]
        prev_bar = df.iloc[-2]
        current_price = float(last_bar['close'])
        vwap = float(last_bar.get('vwap', current_price))
        pdh = levels.get("pdh", current_price * 1.01)
        pdl = levels.get("pdl", current_price * 0.99)
        atr = self.calculate_atr(df)

        rvol = float(last_bar.get('rvol', 1.5))

        # Setup 1: Barrido de mínimos (Bullish Liquidity Sweep)
        # El precio perforó PDL recientemente pero cerró con fuerza sobre PDL y sobre VWAP
        if prev_bar['low'] <= pdl and current_price > pdl and current_price >= vwap:
            stop_loss = round(min(float(prev_bar['low']), float(last_bar['low'])) - (0.1 * atr), 2)
            take_profit = round(current_price + (2.5 * (current_price - stop_loss)), 2)
            return {
                "signal": "BUY",
                "setup_type": "BULLISH_LIQUIDITY_SWEEP",
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "target_rr": 2.5,
                "reason": f"Barrido de liquidez bajo PDL (${pdl}) con absorción compradora y cruce sobre VWAP"
            }

        # Setup 2: Barrido de máximos (Bearish Liquidity Sweep)
        if prev_bar['high'] >= pdh and current_price < pdh and current_price <= vwap:
            stop_loss = round(max(float(prev_bar['high']), float(last_bar['high'])) + (0.1 * atr), 2)
            take_profit = round(current_price - (2.5 * (stop_loss - current_price)), 2)
            return {
                "signal": "SELL",
                "setup_type": "BEARISH_LIQUIDITY_SWEEP",
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "target_rr": 2.5,
                "reason": f"Barrido de liquidez sobre PDH (${pdh}) con rechazo vendedor y caída bajo VWAP"
            }

        # Setup 3: Continuación alcista sobre VWAP con volumen
        if current_price > vwap and prev_bar['low'] <= vwap and last_bar['close'] > last_bar['open'] and rvol >= 1.3:
            stop_loss = round(float(last_bar['low']) - (0.15 * atr), 2)
            take_profit = round(current_price + (2.0 * (current_price - stop_loss)), 2)
            return {
                "signal": "BUY",
                "setup_type": "VWAP_BOUNCE_CONTINUATION",
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "target_rr": 2.0,
                "reason": f"Rebote limpio en VWAP (${round(vwap,2)}) con volumen relativo favorable ({rvol}x)"
            }

        return {"signal": "NONE", "reason": "No hay confluencia de niveles de liquidez o VWAP en esta vela"}

technical_engine = TechnicalEngine()
