# =====================================================================
# TRADEPULSE: ESTRATEGIA INSTITUCIONAL DE ORDER BLOCKS (OB) + RVOL + EMA
# =====================================================================
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class OrderBlock:
    ob_type: str            # 'BULLISH' o 'BEARISH'
    top: float              # Límite superior de la zona OB
    bottom: float           # Límite inferior de la zona OB
    time: datetime          # Momento de formación del OB
    index: int              # Índice de la barra
    atr: float              # Volatilidad en el momento del OB
    volume: float           # Volumen de la barra
    mitigated: bool = False # Se activa a True cuando el precio retestea la zona


@dataclass
class TradeSignal:
    symbol: str
    side: str               # 'BUY' o 'SELL'
    entry_price: float
    stop_loss: float
    tp1: float              # Take Profit 1 (1.5R - 50% parcial)
    tp2: float              # Take Profit 2 (3.0R - 100% final)
    risk_distance: float
    time: datetime
    order_block: OrderBlock
    rvol: float
    atr: float


class OrderBlocksStrategy:
    """
    Estrategia de Day Trading y Swing Institucional basada en Conceptos Smart Money (SMC):
    1. Detección de Order Blocks (OB) válidos formados tras desplazamientos con alto RVOL.
    2. Filtro direccional con EMA 50 y EMA 200 (Tendencia Macro).
    3. Validación de volumen relativo (RVOL >= 1.5) para descartar movimientos falsos.
    4. Entrada en retesteo / mitigación de la zona OB.
    5. Gestión de riesgo con ATR y salidas escalonadas TP1 / TP2.
    """

    def __init__(
        self,
        ema_fast: int = 50,
        ema_slow: int = 200,
        rvol_period: int = 20,
        rvol_threshold: float = 1.4,
        atr_period: int = 14,
        atr_sl_mult: float = 0.5,
        tp1_rr: float = 1.5,
        tp2_rr: float = 3.0
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rvol_period = rvol_period
        self.rvol_threshold = rvol_threshold
        self.atr_period = atr_period
        self.atr_sl_mult = atr_sl_mult
        self.tp1_rr = tp1_rr
        self.tp2_rr = tp2_rr

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula EMAs, RVOL y ATR sobre el dataset histórico de velas de MT5."""
        df = df.copy()

        # 1. Medias Móviles Exponenciales (EMA 50 / 200)
        df['ema_fast'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()

        # 2. Volumen Relativo (RVOL)
        vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
        df['vol_ma'] = df[vol_col].rolling(window=self.rvol_period, min_periods=5).mean()
        df['rvol'] = np.where(df['vol_ma'] > 0, df[vol_col] / df['vol_ma'], 1.0)

        # 3. Average True Range (ATR 14)
        high = df['high']
        low = df['low']
        close_prev = df['close'].shift(1)
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = df['tr'].rolling(window=self.atr_period, min_periods=5).mean()
        df['atr'] = df['atr'].bfill().ffill()

        return df

    def scan_order_blocks(self, df: pd.DataFrame) -> List[OrderBlock]:
        """
        Identifica zonas institucionales de Order Blocks:
        - Bullish OB: Última vela bajista antes de un impulso alcista fuerte con RVOL alto.
        - Bearish OB: Última vela alcista antes de un impulso bajista fuerte con RVOL alto.
        """
        order_blocks = []
        n = len(df)

        for i in range(2, n - 2):
            curr = df.iloc[i]
            next_1 = df.iloc[i + 1]
            next_2 = df.iloc[i + 2]
            rvol_impulse = max(next_1['rvol'], next_2['rvol'])
            atr = curr['atr'] if pd.notnull(curr['atr']) and curr['atr'] > 0 else (curr['high'] - curr['low'])

            # --- Detección de Bullish Order Block ---
            # Vela i es roja (bajista), y las siguientes velas explotan al alza superando su máximo
            is_bearish_candle = curr['close'] < curr['open']
            is_bullish_displacement = (next_1['close'] > curr['high']) or (next_2['close'] > curr['high'])
            strong_displacement_bull = (next_1['close'] - curr['close']) > (0.6 * atr)

            if is_bearish_candle and is_bullish_displacement and strong_displacement_bull and (rvol_impulse >= self.rvol_threshold):
                ob = OrderBlock(
                    ob_type='BULLISH',
                    top=curr['high'],
                    bottom=curr['low'],
                    time=curr['time'],
                    index=i,
                    atr=atr,
                    volume=curr['tick_volume'] if 'tick_volume' in curr else 0,
                    mitigated=False
                )
                order_blocks.append(ob)

            # --- Detección de Bearish Order Block ---
            # Vela i es verde (alcista), y las siguientes velas caen con fuerza por debajo de su mínimo
            is_bullish_candle = curr['close'] > curr['open']
            is_bearish_displacement = (next_1['close'] < curr['low']) or (next_2['close'] < curr['low'])
            strong_displacement_bear = (curr['close'] - next_1['close']) > (0.6 * atr)

            if is_bullish_candle and is_bearish_displacement and strong_displacement_bear and (rvol_impulse >= self.rvol_threshold):
                ob = OrderBlock(
                    ob_type='BEARISH',
                    top=curr['high'],
                    bottom=curr['low'],
                    time=curr['time'],
                    index=i,
                    atr=atr,
                    volume=curr['tick_volume'] if 'tick_volume' in curr else 0,
                    mitigated=False
                )
                order_blocks.append(ob)

        return order_blocks

    def evaluate_signals(self, df: pd.DataFrame, symbol: str = "MT5_ASSET") -> List[TradeSignal]:
        """
        Evalúa el flujo histórico completo buscando retest/mitigación de Order Blocks
        confluentes con la tendencia de las EMAs 50/200.
        """
        df = self.calculate_indicators(df)
        order_blocks = self.scan_order_blocks(df)
        signals = []

        active_bullish_obs: List[OrderBlock] = []
        active_bearish_obs: List[OrderBlock] = []

        # Recorrer velas cronológicamente
        for i in range(len(df)):
            candle = df.iloc[i]
            c_time = candle['time']
            c_open = candle['open']
            c_high = candle['high']
            c_low = candle['low']
            c_close = candle['close']
            ema50 = candle['ema_fast']
            ema200 = candle['ema_slow']
            atr = candle['atr']

            # Añadir OBs formados en este índice a la lista activa
            for ob in order_blocks:
                if ob.index == i:
                    if ob.ob_type == 'BULLISH':
                        active_bullish_obs.append(ob)
                    else:
                        active_bearish_obs.append(ob)

            # 1. EVALUAR SEÑAL DE COMPRA (Retest de Bullish OB + Tendencia Alcista EMA50 > EMA200)
            if ema50 > ema200 and c_close > ema50:
                for ob in active_bullish_obs:
                    if not ob.mitigated and (i > ob.index + 2):
                        # Retesteo: El mínimo de la vela entra en la zona del OB
                        if c_low <= ob.top and c_close >= ob.bottom:
                            ob.mitigated = True
                            entry = round(ob.top, 5)
                            # Stop loss protegido por debajo de la zona OB + buffer de ATR
                            sl = round(ob.bottom - (self.atr_sl_mult * atr), 5)
                            risk = entry - sl
                            if risk > 0:
                                tp1 = round(entry + (self.tp1_rr * risk), 5)
                                tp2 = round(entry + (self.tp2_rr * risk), 5)
                                signals.append(TradeSignal(
                                    symbol=symbol,
                                    side='BUY',
                                    entry_price=entry,
                                    stop_loss=sl,
                                    tp1=tp1,
                                    tp2=tp2,
                                    risk_distance=risk,
                                    time=c_time,
                                    order_block=ob,
                                    rvol=candle['rvol'],
                                    atr=atr
                                ))
                                break

            # 2. EVALUAR SEÑAL DE VENTA (Retest de Bearish OB + Tendencia Bajista EMA50 < EMA200)
            if ema50 < ema200 and c_close < ema50:
                for ob in active_bearish_obs:
                    if not ob.mitigated and (i > ob.index + 2):
                        # Retesteo: El máximo de la vela entra en la zona del OB
                        if c_high >= ob.bottom and c_close <= ob.top:
                            ob.mitigated = True
                            entry = round(ob.bottom, 5)
                            # Stop loss protegido por encima de la zona OB + buffer de ATR
                            sl = round(ob.top + (self.atr_sl_mult * atr), 5)
                            risk = sl - entry
                            if risk > 0:
                                tp1 = round(entry - (self.tp1_rr * risk), 5)
                                tp2 = round(entry - (self.tp2_rr * risk), 5)
                                signals.append(TradeSignal(
                                    symbol=symbol,
                                    side='SELL',
                                    entry_price=entry,
                                    stop_loss=sl,
                                    tp1=tp1,
                                    tp2=tp2,
                                    risk_distance=risk,
                                    time=c_time,
                                    order_block=ob,
                                    rvol=candle['rvol'],
                                    atr=atr
                                ))
                                break

        return signals


# Instancia por defecto
order_blocks_strategy = OrderBlocksStrategy()
