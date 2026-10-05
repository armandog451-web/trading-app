"""
ai_trading_agent.strategy_lab.backtesting.execution_aware_simulator
===================================================================
Simulador de ejecución consciente de fricciones institucionales (Fase 8).
Diseñado específicamente para investigar la conversión de señales en edge económico real.

Características Institucionales:
1. Modelado riguroso de costes:
   - Comisiones por acción (default $0.005/acción)
   - Deslizamiento realista en entrada y salida (default 5 bps = 0.05%)
   - Ejecución sin sesgo de anticipación (Zero Look-Ahead Bias)
2. Geometrías de salida avanzadas:
   - Fixed RR (R:R estático)
   - ATR Target
   - Trailing ATR
   - Partial Exit (50% a 1.5R con SL a Breakeven, resto a target)
   - Time Stop (liquidación por barras máximas en mercado)
   - Volatility Exit (salida por compresión o explosión de volatilidad)
   - Regime Exit (salida si el régimen superior o local se invierte)
3. Gestión de concurrencia y solapamiento:
   - FIRST_SIGNAL (FIFO tradicional)
   - BEST_SIGNAL (selección por SQS experimental en la misma barra)
   - REPLACE_IF_STRONGER (sustitución si llega una señal con mayor convicción)
   - QUEUE_NEXT_SIGNAL (cola de espera para la siguiente señal)
   - ONE_POSITION_PER_SYMBOL (hasta 1 posición por símbolo)
   - ONE_POSITION_GLOBAL (1 posición a nivel de cartera global)
4. Score experimental de calidad de señal (SQS_exp):
   - Métrica causal independiente de SQS oficial para desempate y priorización
5. Métricas de Payoff Ratio realizado:
   - Breakeven Win Rate exacto = 1 / (1 + Payoff Ratio)
   - Payoff Ratio realizado = Avg Win / Avg Loss
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
import pandas as pd

from ai_trading_agent.domain.models import OHLCVBar, StrategySignal
from ai_trading_agent.domain.enums import SignalDirection, MarketRegime
from ai_trading_agent.market.indicators import indicators, TechnicalIndicators
from ai_trading_agent.market.regime import regime_detector
from ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer import MultiTimeframeSynchronizer


class SignalQualityScoreCalculator:
    """
    Calculador del Score Experimental de Calidad de Señal (SQS_exp, 0 a 100).
    Evalúa exclusivamente información técnica disponible al cierre de la barra de señal
    para desempate y priorización causal de señales concurrentes.
    Zero Look-Ahead Bias.
    """

    @staticmethod
    def calculate_from_features(
        bar: OHLCVBar,
        direction: SignalDirection,
        atr: float,
        rvol: float,
        rsi: float,
        d_context: Optional[Dict[str, Any]] = None
    ) -> float:
        vol_score = min(25.0, max(5.0, (rvol / 1.5) * 20.0))

        candle_range = max(0.01, bar.high - bar.low)
        body = abs(bar.close - bar.open)
        body_ratio = body / candle_range

        directional_body = (bar.close > bar.open) if direction == SignalDirection.BUY else (bar.close < bar.open)
        body_score = (body_ratio * 20.0) if directional_body else 5.0

        if direction == SignalDirection.BUY:
            rsi_score = min(25.0, max(5.0, ((rsi - 30.0) / 40.0) * 25.0)) if rsi >= 30.0 else 5.0
        else:
            rsi_score = min(25.0, max(5.0, ((70.0 - rsi) / 40.0) * 25.0)) if rsi <= 70.0 else 5.0

        ctx_score = 10.0
        if d_context:
            if direction == SignalDirection.BUY and d_context.get("daily_bullish"):
                ctx_score = 25.0
            elif direction == SignalDirection.SELL and d_context.get("daily_bearish"):
                ctx_score = 25.0

        total = vol_score + body_score + rsi_score + ctx_score
        return round(min(100.0, max(10.0, total)), 2)

    @classmethod
    def calculate(
        cls,
        bar: OHLCVBar,
        history_bars: List[OHLCVBar],
        direction: SignalDirection,
        d_context: Optional[Dict[str, Any]] = None
    ) -> float:
        if len(history_bars) < 15:
            return 50.0

        ind = indicators.calculate_all(history_bars)
        close = bar.close
        atr = ind.get("atr", close * 0.01)
        rvol = ind.get("rvol", 1.0)
        rsi = ind.get("rsi", 50.0)
        return cls.calculate_from_features(bar, direction, atr, rvol, rsi, d_context)


class FeaturePrecomputer:
    """Precalcula vectores técnicos para acelerar la simulación sin look-ahead."""

    @staticmethod
    def precompute(h_bars: List[OHLCVBar], d_bars: List[OHLCVBar]) -> Dict[str, Any]:
        daily_context_map: Dict[Any, Dict[str, Any]] = {}
        if d_bars and len(d_bars) >= 25:
            df_d = TechnicalIndicators.to_dataframe(d_bars)
            d_close = df_d["close"]
            d_sma20 = d_close.rolling(20).mean()
            d_sma50 = d_close.rolling(50).mean()
            d_ema9 = d_close.ewm(span=9, adjust=False).mean()
            d_ema21 = d_close.ewm(span=21, adjust=False).mean()

            for i in range(24, len(d_bars)):
                curr_d_bar = d_bars[i]
                c = d_close.iloc[i]
                s20 = d_sma20.iloc[i]
                s50 = d_sma50.iloc[i]
                e9 = d_ema9.iloc[i]
                e21 = d_ema21.iloc[i]
                bull = (c > s50) and (s20 >= s50) and (e9 >= e21)
                bear = (c < s50) and (s20 <= s50) and (e9 <= e21)

                # Mapear para todas las fechas posteriores a esta barra cerrada
                # hasta la siguiente barra diaria
                daily_context_map[curr_d_bar.timestamp.date()] = {
                    "daily_bullish": bool(bull),
                    "daily_bearish": bool(bear),
                    "trend": "BULLISH" if bull else ("BEARISH" if bear else "NEUTRAL")
                }

        df_h = TechnicalIndicators.to_dataframe(h_bars)
        c_h = df_h["close"]
        h_h = df_h["high"]
        l_h = df_h["low"]
        v_h = df_h["volume"]

        ema9_h = c_h.ewm(span=9, adjust=False).mean().values
        ema21_h = c_h.ewm(span=21, adjust=False).mean().values

        delta = c_h.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi_h = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0).values

        tr = np.maximum(
            h_h.iloc[1:] - l_h.iloc[1:],
            np.maximum(abs(h_h.iloc[1:] - c_h.iloc[:-1].values), abs(l_h.iloc[1:] - c_h.iloc[:-1].values))
        )
        atr_series = pd.Series(tr, index=df_h.index[1:]).rolling(14).mean()
        atr_h = atr_series.reindex(df_h.index).bfill().fillna(c_h * 0.01).values

        typ = (h_h + l_h + c_h) / 3.0
        vwap_h = ((typ * v_h).cumsum() / (v_h.cumsum() + 1e-9)).values

        vol_sma20 = v_h.rolling(20).mean().fillna(v_h).values + 1e-9
        rvol_h = (v_h.values / vol_sma20)

        high_20_h = h_h.shift(1).rolling(20).max().bfill().fillna(h_h).values
        low_20_h = l_h.shift(1).rolling(20).min().bfill().fillna(l_h).values
        avg_atr_20 = pd.Series(atr_h).shift(1).rolling(20).mean().bfill().fillna(0.0).values

        # Construir mapa rápido de contexto diario indexado por fecha intradía
        # Para cualquier fecha T, la barra cerrada disponible es la última fecha con b_date < T
        sorted_d_dates = sorted(list(daily_context_map.keys()))

        def get_d_ctx_for_date(target_date):
            valid_dates = [d for d in sorted_d_dates if d < target_date]
            if not valid_dates:
                return {"daily_bullish": False, "daily_bearish": False, "trend": "NEUTRAL"}
            return daily_context_map[valid_dates[-1]]

        return {
            "get_d_ctx": get_d_ctx_for_date,
            "ema9": ema9_h,
            "ema21": ema21_h,
            "rsi": rsi_h,
            "atr": atr_h,
            "vwap": vwap_h,
            "rvol": rvol_h,
            "high_20": high_20_h,
            "low_20": low_20_h,
            "avg_atr_20": avg_atr_20
        }


class ExecutionAwareStrategyEvaluator:
    """
    Evaluador de estrategias multi-timeframe para la Fase 8.
    Soporta 6 familias de timing intradía (1H):
    - trend_continuation
    - pullback_confirmation
    - breakout_retest
    - volatility_expansion
    - momentum_persistence
    - failed_breakout_reversal
    Con o sin contexto diario (WITH_1D_CONTEXT vs WITHOUT_1D_CONTEXT).
    """

    def __init__(
        self,
        entry_family: str = "trend_continuation",
        use_1d_context: bool = True,
        exit_geometry: str = "fixed_rr",
        rr_ratio: float = 2.5,
        atr_mult: float = 1.5,
        time_stop_bars: int = 15,
        parameters: Optional[Dict[str, Any]] = None
    ):
        self.entry_family = entry_family
        self.use_1d_context = use_1d_context
        self.exit_geometry = exit_geometry
        self.rr_ratio = rr_ratio
        self.atr_mult = atr_mult
        self.time_stop_bars = time_stop_bars
        self.parameters = parameters or {}

    def evaluate_signal_fast(
        self,
        symbol: str,
        bar: OHLCVBar,
        bar_idx: int,
        h_bars: List[OHLCVBar],
        features: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if bar_idx < 30:
            return None

        d_ctx = features["get_d_ctx"](bar.timestamp.date()) if self.use_1d_context else None
        if self.use_1d_context and d_ctx:
            if not d_ctx.get("daily_bullish") and not d_ctx.get("daily_bearish"):
                return None

        close = bar.close
        atr = float(features["atr"][bar_idx])
        rvol = float(features["rvol"][bar_idx])
        rsi = float(features["rsi"][bar_idx])
        ema9 = float(features["ema9"][bar_idx])
        ema21 = float(features["ema21"][bar_idx])
        vwap = float(features["vwap"][bar_idx])
        high_20 = float(features["high_20"][bar_idx])
        low_20 = float(features["low_20"][bar_idx])
        avg_atr_20 = float(features["avg_atr_20"][bar_idx])

        direction = SignalDirection.NO_TRADE

        # 1. Trend Continuation
        if self.entry_family == "trend_continuation":
            bull_cond = (ema9 > ema21) and (close > vwap) and (rvol >= 1.1) and (50.0 <= rsi <= 68.0)
            bear_cond = (ema9 < ema21) and (close < vwap) and (rvol >= 1.1) and (32.0 <= rsi <= 50.0)
            if bull_cond and (not self.use_1d_context or d_ctx.get("daily_bullish")):
                direction = SignalDirection.BUY
            elif bear_cond and (not self.use_1d_context or d_ctx.get("daily_bearish")):
                direction = SignalDirection.SELL

        # 2. Pullback Confirmation
        elif self.entry_family == "pullback_confirmation":
            prev_close = h_bars[bar_idx - 1].close
            prev_ema21 = float(features["ema21"][bar_idx - 1])
            bull_cond = (prev_close <= prev_ema21) and (close > ema9) and (rsi > 42.0) and (rvol >= 1.0)
            bear_cond = (prev_close >= prev_ema21) and (close < ema9) and (rsi < 58.0) and (rvol >= 1.0)
            if bull_cond and (not self.use_1d_context or d_ctx.get("daily_bullish")):
                direction = SignalDirection.BUY
            elif bear_cond and (not self.use_1d_context or d_ctx.get("daily_bearish")):
                direction = SignalDirection.SELL

        # 3. Breakout Retest
        elif self.entry_family == "breakout_retest":
            bull_cond = (close >= high_20 * 0.998) and (bar.low >= high_20 * 0.99) and (rvol >= 1.2)
            bear_cond = (close <= low_20 * 1.002) and (bar.high <= low_20 * 1.01) and (rvol >= 1.2)
            if bull_cond and (not self.use_1d_context or d_ctx.get("daily_bullish")):
                direction = SignalDirection.BUY
            elif bear_cond and (not self.use_1d_context or d_ctx.get("daily_bearish")):
                direction = SignalDirection.SELL

        # 4. Volatility Expansion
        elif self.entry_family == "volatility_expansion":
            is_expanding = (atr >= avg_atr_20 * 1.20) and (rvol >= 1.3)
            bull_cond = is_expanding and (close > vwap) and (close > bar.open)
            bear_cond = is_expanding and (close < vwap) and (close < bar.open)
            if bull_cond and (not self.use_1d_context or d_ctx.get("daily_bullish")):
                direction = SignalDirection.BUY
            elif bear_cond and (not self.use_1d_context or d_ctx.get("daily_bearish")):
                direction = SignalDirection.SELL

        # 5. Momentum Persistence
        elif self.entry_family == "momentum_persistence":
            b1_c = h_bars[bar_idx - 2].close
            b2_c = h_bars[bar_idx - 1].close
            b2_v = h_bars[bar_idx - 1].volume
            bull_cond = (close > b2_c > b1_c) and (bar.volume >= b2_v) and (52.0 <= rsi <= 72.0)
            bear_cond = (close < b2_c < b1_c) and (bar.volume >= b2_v) and (28.0 <= rsi <= 48.0)
            if bull_cond and (not self.use_1d_context or d_ctx.get("daily_bullish")):
                direction = SignalDirection.BUY
            elif bear_cond and (not self.use_1d_context or d_ctx.get("daily_bearish")):
                direction = SignalDirection.SELL

        # 6. Failed Breakout Reversal (Phase 8 Baseline)
        elif self.entry_family == "failed_breakout_reversal":
            bull_reversal = (bar.low < low_20) and (close > low_20) and (rsi < 40.0)
            bear_reversal = (bar.high > high_20) and (close < high_20) and (rsi > 60.0)
            if bull_reversal:
                direction = SignalDirection.BUY
            elif bear_reversal:
                direction = SignalDirection.SELL

        # --- FAMILIAS DE NUEVA GENERACIÓN: FASE 9 ---
        # 7. Trend Persistence (Seguimiento de tendencia estricto con confirmación de pendiente y volumen institucional)
        elif self.entry_family == "trend_persistence":
            prev_ema9 = float(features["ema9"][bar_idx - 1])
            prev_ema21 = float(features["ema21"][bar_idx - 1])
            slope_bull = (ema9 > prev_ema9) and (ema21 > prev_ema21) and (ema9 > ema21)
            slope_bear = (ema9 < prev_ema9) and (ema21 < prev_ema21) and (ema9 < ema21)
            bull_cond = slope_bull and (close > vwap) and (rvol >= 1.2) and (52.0 <= rsi <= 68.0)
            bear_cond = slope_bear and (close < vwap) and (rvol >= 1.2) and (32.0 <= rsi <= 48.0)
            if bull_cond and (not self.use_1d_context or d_ctx.get("daily_bullish")):
                direction = SignalDirection.BUY
            elif bear_cond and (not self.use_1d_context or d_ctx.get("daily_bearish")):
                direction = SignalDirection.SELL

        # 8. Compression-Release Breakout (Ruptura tras compresión extrema de volatilidad)
        elif self.entry_family == "compression_release_breakout":
            was_compressed = (atr < avg_atr_20 * 0.85) or (features.get("rvol", [1.0])[bar_idx - 1] < 0.8)
            vol_release = (rvol >= 1.5) and (bar.close > bar.open if close > high_20 * 0.995 else bar.close < bar.open)
            bull_cond = was_compressed and (close >= high_20) and vol_release
            bear_cond = was_compressed and (close <= low_20) and vol_release
            if bull_cond and (not self.use_1d_context or d_ctx.get("daily_bullish")):
                direction = SignalDirection.BUY
            elif bear_cond and (not self.use_1d_context or d_ctx.get("daily_bearish")):
                direction = SignalDirection.SELL

        # 9. Regime-Conditioned Momentum (Momentum solo cuando el régimen diario está fuertemente alineado)
        elif self.entry_family == "regime_conditioned_momentum":
            is_daily_bull = d_ctx.get("daily_bullish", False) if d_ctx else False
            is_daily_bear = d_ctx.get("daily_bearish", False) if d_ctx else False
            bull_cond = is_daily_bull and (close > ema9 > ema21) and (rsi >= 55.0) and (rvol >= 1.15)
            bear_cond = is_daily_bear and (close < ema9 < ema21) and (rsi <= 45.0) and (rvol >= 1.15)
            if bull_cond:
                direction = SignalDirection.BUY
            elif bear_cond:
                direction = SignalDirection.SELL

        # 10. Multi-Asset Relative Strength (Direccionalidad adaptativa condicionada a RVOL y distancia a VWAP)
        elif self.entry_family == "multi_asset_relative_strength":
            vwap_dist = (close - vwap) / (vwap + 1e-9)
            bull_cond = (vwap_dist > 0.003) and (rvol >= 1.3) and (ema9 > ema21) and (rsi >= 50.0)
            bear_cond = (vwap_dist < -0.003) and (rvol >= 1.3) and (ema9 < ema21) and (rsi <= 50.0)
            if bull_cond and (not self.use_1d_context or d_ctx.get("daily_bullish")):
                direction = SignalDirection.BUY
            elif bear_cond and (not self.use_1d_context or d_ctx.get("daily_bearish")):
                direction = SignalDirection.SELL

        # 11. Volatility-Adjusted Directional (Setups de rango amplio con stop amplio y target amplio)
        elif self.entry_family == "volatility_adjusted_directional":
            norm_vol = atr / (close + 1e-9)
            has_vol = (norm_vol >= 0.005) and (rvol >= 1.25)
            bull_cond = has_vol and (close > vwap) and (ema9 > ema21) and (rsi > 48.0)
            bear_cond = has_vol and (close < vwap) and (ema9 < ema21) and (rsi < 52.0)
            if bull_cond and (not self.use_1d_context or d_ctx.get("daily_bullish")):
                direction = SignalDirection.BUY
            elif bear_cond and (not self.use_1d_context or d_ctx.get("daily_bearish")):
                direction = SignalDirection.SELL

        if direction == SignalDirection.NO_TRADE:
            return None

        sl_dist = atr * self.atr_mult
        if direction == SignalDirection.BUY:
            sl = round(close - sl_dist, 2)
            tp = round(close + (sl_dist * self.rr_ratio), 2)
        else:
            sl = round(close + sl_dist, 2)
            tp = round(close - (sl_dist * self.rr_ratio), 2)

        sqs_exp = SignalQualityScoreCalculator.calculate_from_features(
            bar=bar,
            direction=direction,
            atr=atr,
            rvol=rvol,
            rsi=rsi,
            d_context=d_ctx
        )

        return {
            "symbol": symbol,
            "timestamp": bar.timestamp,
            "direction": "BUY" if direction == SignalDirection.BUY else "SELL",
            "entry_price": close,
            "stop_loss": sl,
            "take_profit": tp,
            "atr": atr,
            "sqs_exp": sqs_exp,
            "family": self.entry_family,
            "with_1d": self.use_1d_context
        }


class ExecutionAwareSimulator:
    """
    Simulador de trading multiactivo con conciencia de ejecución institucional.
    Maneja políticas de concurrencia, deslizamiento simétrico o asimétrico,
    comisiones y geometrías avanzadas de salida.
    """

    def __init__(
        self,
        evaluator: ExecutionAwareStrategyEvaluator,
        initial_capital: float = 100000.0,
        commission_per_share: float = 0.005,
        slippage_pct: float = 0.0005,
        risk_per_trade_pct: float = 0.01,
        concurrency_policy: str = "FIRST_SIGNAL",
        max_concurrent_positions: int = 1
    ):
        self.evaluator = evaluator
        self.initial_capital = initial_capital
        self.commission_per_share = commission_per_share
        self.slippage_pct = slippage_pct
        self.risk_per_trade_pct = risk_per_trade_pct
        self.concurrency_policy = concurrency_policy
        self.max_concurrent_positions = max_concurrent_positions

    def run_simulation(
        self,
        symbols_data: Dict[str, Dict[str, List[OHLCVBar]]],
        min_warmup: int = 30,
        precomputed_features: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta la simulación cronológica paso a paso sincronizada a través de múltiples símbolos.
        """
        all_timestamps = set()
        for sym, d in symbols_data.items():
            h_bars = d.get("1h", [])
            for b in h_bars[min_warmup:]:
                all_timestamps.add(b.timestamp)
        sorted_timestamps = sorted(list(all_timestamps))

        bars_by_sym_time: Dict[str, Dict[datetime, Tuple[OHLCVBar, int]]] = {}
        for sym, d in symbols_data.items():
            bars_by_sym_time[sym] = {}
            h_bars = d.get("1h", [])
            for idx, b in enumerate(h_bars):
                bars_by_sym_time[sym][b.timestamp] = (b, idx)

        # Precalcular o usar features pasados
        features_by_sym = precomputed_features or {}
        for sym, d in symbols_data.items():
            if sym not in features_by_sym:
                features_by_sym[sym] = FeaturePrecomputer.precompute(d.get("1h", []), d.get("1d", []))

        capital = self.initial_capital
        active_positions: Dict[str, Dict[str, Any]] = {}
        queued_signals: List[Dict[str, Any]] = []
        closed_trades: List[Dict[str, Any]] = []

        raw_signals_count = 0
        eligible_signals_count = 0
        suppressed_signals_count = 0
        replacement_events_count = 0

        for curr_dt in sorted_timestamps:
            # A. GESTIONAR POSICIONES ACTIVAS
            closed_pos_ids = []
            for pos_id, pos in list(active_positions.items()):
                sym = pos["symbol"]
                sym_time_entry = bars_by_sym_time.get(sym, {}).get(curr_dt)
                if not sym_time_entry:
                    continue
                curr_bar, bar_idx = sym_time_entry

                pos["bars_held"] += 1
                side = pos["side"]
                entry_p = pos["entry_price"]
                sl = pos["stop_loss"]
                tp = pos["take_profit"]
                qty = pos["quantity"]
                exit_geo = self.evaluator.exit_geometry

                exit_price = None
                exit_reason = None

                # 1. Trailing ATR update
                if exit_geo == "trailing_atr":
                    trail_dist = pos["atr_at_entry"] * 1.5
                    if side == "BUY":
                        new_high = max(pos.get("peak_price", entry_p), curr_bar.high)
                        pos["peak_price"] = new_high
                        pos["stop_loss"] = max(pos["stop_loss"], round(new_high - trail_dist, 2))
                    else:
                        new_low = min(pos.get("trough_price", entry_p), curr_bar.low)
                        pos["trough_price"] = new_low
                        pos["stop_loss"] = min(pos["stop_loss"], round(new_low + trail_dist, 2))

                # 2. Time Stop
                if exit_geo == "time_stop" and pos["bars_held"] >= self.evaluator.time_stop_bars:
                    exit_price = curr_bar.close
                    exit_reason = "TIME_STOP"

                # 3. Partial Exit Check
                if exit_geo == "partial_exit" and not pos.get("partial_taken", False):
                    partial_target_dist = abs(entry_p - sl) * 1.5
                    hit_partial = (curr_bar.high >= entry_p + partial_target_dist) if side == "BUY" else (curr_bar.low <= entry_p - partial_target_dist)
                    if hit_partial:
                        partial_qty = qty // 2
                        if partial_qty > 0:
                            p_target_price = entry_p + partial_target_dist if side == "BUY" else entry_p - partial_target_dist
                            p_exec_exit = p_target_price * (1.0 - self.slippage_pct) if side == "BUY" else p_target_price * (1.0 + self.slippage_pct)
                            p_gross = (p_exec_exit - entry_p) * partial_qty if side == "BUY" else (entry_p - p_exec_exit) * partial_qty
                            p_comm = partial_qty * self.commission_per_share
                            p_net = p_gross - p_comm

                            closed_trades.append({
                                "symbol": sym,
                                "entry_time": pos["entry_time"],
                                "exit_time": curr_bar.timestamp,
                                "side": side,
                                "entry_price": entry_p,
                                "exit_price": p_exec_exit,
                                "quantity": partial_qty,
                                "net_pnl": p_net,
                                "is_win": p_net > 0,
                                "exit_reason": "PARTIAL_TARGET",
                                "bars_held": pos["bars_held"],
                                "configured_rr": self.evaluator.rr_ratio
                            })
                            capital += p_net
                            pos["quantity"] = qty - partial_qty
                            pos["partial_taken"] = True
                            pos["stop_loss"] = entry_p

                # 4. Evaluación estándar contra SL y TP
                if exit_price is None:
                    if side == "BUY":
                        if curr_bar.low <= pos["stop_loss"]:
                            exit_price = pos["stop_loss"]
                            exit_reason = "STOP_LOSS"
                        elif curr_bar.high >= pos["take_profit"]:
                            exit_price = pos["take_profit"]
                            exit_reason = "TAKE_PROFIT"
                    else:
                        if curr_bar.high >= pos["stop_loss"]:
                            exit_price = pos["stop_loss"]
                            exit_reason = "STOP_LOSS"
                        elif curr_bar.low <= pos["take_profit"]:
                            exit_price = pos["take_profit"]
                            exit_reason = "TAKE_PROFIT"

                if exit_price is not None:
                    rem_qty = pos["quantity"]
                    exec_exit = exit_price * (1.0 - self.slippage_pct) if side == "BUY" else exit_price * (1.0 + self.slippage_pct)
                    gross = (exec_exit - entry_p) * rem_qty if side == "BUY" else (entry_p - exec_exit) * rem_qty
                    comm = rem_qty * self.commission_per_share
                    net = gross - comm

                    closed_trades.append({
                        "symbol": sym,
                        "entry_time": pos["entry_time"],
                        "exit_time": curr_bar.timestamp,
                        "side": side,
                        "entry_price": entry_p,
                        "exit_price": exec_exit,
                        "quantity": rem_qty,
                        "net_pnl": net,
                        "is_win": net > 0,
                        "exit_reason": exit_reason,
                        "bars_held": pos["bars_held"],
                        "configured_rr": self.evaluator.rr_ratio
                    })
                    capital += net
                    closed_pos_ids.append(pos_id)

            for pid in closed_pos_ids:
                del active_positions[pid]

            # B. EVALUAR SEÑALES ENTRANTE
            new_signals: List[Dict[str, Any]] = []
            for sym, d in symbols_data.items():
                sym_time_entry = bars_by_sym_time.get(sym, {}).get(curr_dt)
                if not sym_time_entry:
                    continue
                curr_bar, bar_idx = sym_time_entry
                h_bars = d.get("1h", [])

                if bar_idx < min_warmup:
                    continue

                sig = self.evaluator.evaluate_signal_fast(
                    symbol=sym,
                    bar=curr_bar,
                    bar_idx=bar_idx,
                    h_bars=h_bars,
                    features=features_by_sym[sym]
                )
                if sig is not None:
                    raw_signals_count += 1
                    new_signals.append(sig)

            if queued_signals and len(active_positions) < self.max_concurrent_positions:
                new_signals.extend(queued_signals)
                queued_signals.clear()

            if not new_signals:
                continue

            # C. APLICAR POLÍTICA DE CONCURRENCIA
            new_signals.sort(key=lambda s: s["sqs_exp"], reverse=True)

            for sig in new_signals:
                sym = sig["symbol"]
                side = sig["direction"]
                sqs = sig["sqs_exp"]

                sym_in_pos = any(p["symbol"] == sym for p in active_positions.values())
                global_pos_count = len(active_positions)

                can_enter = False

                if self.concurrency_policy in ["ONE_POSITION_GLOBAL", "FIRST_SIGNAL", "BEST_SIGNAL"]:
                    if global_pos_count < self.max_concurrent_positions and not sym_in_pos:
                        can_enter = True
                    else:
                        suppressed_signals_count += 1

                elif self.concurrency_policy == "ONE_POSITION_PER_SYMBOL":
                    if not sym_in_pos and global_pos_count < 4:
                        can_enter = True
                    else:
                        suppressed_signals_count += 1

                elif self.concurrency_policy == "REPLACE_IF_STRONGER":
                    if global_pos_count < self.max_concurrent_positions and not sym_in_pos:
                        can_enter = True
                    else:
                        weaker_pid = None
                        for pid, p in active_positions.items():
                            if sqs >= p.get("sqs_exp", 50.0) + 15.0:
                                weaker_pid = pid
                                break
                        if weaker_pid:
                            w_pos = active_positions[weaker_pid]
                            w_bar, _ = bars_by_sym_time[w_pos["symbol"]][curr_dt]
                            w_exec = w_bar.close * (1.0 - self.slippage_pct) if w_pos["side"] == "BUY" else w_bar.close * (1.0 + self.slippage_pct)
                            w_gross = (w_exec - w_pos["entry_price"]) * w_pos["quantity"] if w_pos["side"] == "BUY" else (w_pos["entry_price"] - w_exec) * w_pos["quantity"]
                            w_comm = w_pos["quantity"] * self.commission_per_share
                            w_net = w_gross - w_comm
                            closed_trades.append({
                                "symbol": w_pos["symbol"],
                                "entry_time": w_pos["entry_time"],
                                "exit_time": curr_dt,
                                "side": w_pos["side"],
                                "entry_price": w_pos["entry_price"],
                                "exit_price": w_exec,
                                "quantity": w_pos["quantity"],
                                "net_pnl": w_net,
                                "is_win": w_net > 0,
                                "exit_reason": "REPLACED_BY_STRONGER",
                                "bars_held": w_pos["bars_held"],
                                "configured_rr": self.evaluator.rr_ratio
                            })
                            capital += w_net
                            del active_positions[weaker_pid]
                            replacement_events_count += 1
                            can_enter = True
                        else:
                            suppressed_signals_count += 1

                elif self.concurrency_policy == "QUEUE_NEXT_SIGNAL":
                    if global_pos_count < self.max_concurrent_positions and not sym_in_pos:
                        can_enter = True
                    else:
                        if len(queued_signals) < 2:
                            queued_signals.append(sig)
                        suppressed_signals_count += 1

                if can_enter:
                    eligible_signals_count += 1
                    entry_p = sig["entry_price"] * (1.0 + self.slippage_pct) if side == "BUY" else sig["entry_price"] * (1.0 - self.slippage_pct)
                    risk_amount = capital * self.risk_per_trade_pct
                    risk_per_share = abs(entry_p - sig["stop_loss"])
                    if risk_per_share > 0.05:
                        qty = max(1, int(risk_amount / risk_per_share))
                        pos_id = f"{sym}_{curr_dt.strftime('%Y%m%d%H%M')}"
                        active_positions[pos_id] = {
                            "symbol": sym,
                            "entry_time": curr_dt,
                            "side": side,
                            "entry_price": entry_p,
                            "stop_loss": sig["stop_loss"],
                            "take_profit": sig["take_profit"],
                            "quantity": qty,
                            "initial_quantity": qty,
                            "bars_held": 0,
                            "sqs_exp": sqs,
                            "atr_at_entry": sig["atr"],
                            "peak_price": entry_p,
                            "trough_price": entry_p
                        }

        # Liquidar posiciones al final
        for pos_id, pos in active_positions.items():
            sym = pos["symbol"]
            last_dt = sorted_timestamps[-1]
            last_bar_tuple = bars_by_sym_time.get(sym, {}).get(last_dt)
            if last_bar_tuple:
                l_bar = last_bar_tuple[0]
                exec_exit = l_bar.close * (1.0 - self.slippage_pct) if pos["side"] == "BUY" else l_bar.close * (1.0 + self.slippage_pct)
                gross = (exec_exit - pos["entry_price"]) * pos["quantity"] if pos["side"] == "BUY" else (pos["entry_price"] - exec_exit) * pos["quantity"]
                comm = pos["quantity"] * self.commission_per_share
                net = gross - comm
                closed_trades.append({
                    "symbol": sym,
                    "entry_time": pos["entry_time"],
                    "exit_time": last_dt,
                    "side": pos["side"],
                    "entry_price": pos["entry_price"],
                    "exit_price": exec_exit,
                    "quantity": pos["quantity"],
                    "net_pnl": net,
                    "is_win": net > 0,
                    "exit_reason": "PERIOD_END",
                    "bars_held": pos["bars_held"],
                    "configured_rr": self.evaluator.rr_ratio
                })
                capital += net

        total_trades = len(closed_trades)
        wins = [t for t in closed_trades if t["net_pnl"] > 0]
        losses = [t for t in closed_trades if t["net_pnl"] <= 0]

        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / max(1, total_trades)) * 100.0

        avg_win = (sum(t["net_pnl"] for t in wins) / max(1, win_count)) if win_count > 0 else 0.0
        avg_loss = (abs(sum(t["net_pnl"] for t in losses)) / max(1, loss_count)) if loss_count > 0 else 0.0

        realized_payoff = (avg_win / avg_loss) if avg_loss > 0 else 0.0
        realized_breakeven_wr = (1.0 / (1.0 + realized_payoff) * 100.0) if realized_payoff > 0 else 100.0

        total_net_pnl = sum(t["net_pnl"] for t in closed_trades)
        gross_wins = sum(t["net_pnl"] for t in wins)
        gross_losses = abs(sum(t["net_pnl"] for t in losses))
        profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else (999.0 if gross_wins > 0 else 0.0)

        peak = self.initial_capital
        eq = self.initial_capital
        max_dd = 0.0
        for t in closed_trades:
            eq += t["net_pnl"]
            if eq > peak:
                peak = eq
            dd = (peak - eq) / max(1.0, peak)
            if dd > max_dd:
                max_dd = dd

        returns = [t["net_pnl"] / self.initial_capital for t in closed_trades]
        if len(returns) > 1:
            mean_r = sum(returns) / len(returns)
            std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1))
            rf = 0.04 / min(252, max(1, len(returns)))
            sharpe = ((mean_r - rf) / max(1e-6, std_r)) * math.sqrt(min(252, len(returns)))
        else:
            sharpe = 0.0

        expectancy = total_net_pnl / max(1, total_trades)
        overlap_rate = (suppressed_signals_count / max(1, raw_signals_count)) * 100.0

        return {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "total_net_pnl": round(total_net_pnl, 2),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd * 100.0, 2),
            "expectancy": round(expectancy, 2),
            "configured_rr": self.evaluator.rr_ratio,
            "realized_avg_win": round(avg_win, 2),
            "realized_avg_loss": round(avg_loss, 2),
            "realized_payoff_ratio": round(realized_payoff, 2),
            "realized_breakeven_win_rate": round(realized_breakeven_wr, 2),
            "actual_win_rate": round(win_rate, 2),
            "raw_signals": raw_signals_count,
            "eligible_signals": eligible_signals_count,
            "executed_trades": total_trades,
            "suppressed_signals": suppressed_signals_count,
            "replacement_events": replacement_events_count,
            "overlap_rate": round(overlap_rate, 2),
            "closed_trades": closed_trades
        }
