"""
ai_trading_agent.strategy_lab.backtesting.daily_execution_simulator
===================================================================
Simulador institucional de trading diario y swing multidiario (Fase 10).
Diseñado específicamente para investigar la conversión de señales en horizonte 1D
con holding periods de 1 a 10 días, cálculo de Movement-to-Cost Ratio (MCR),
deslizamiento realista y sin sesgo de anticipación.

Horizontes de holding:
- 1 día (overnight)
- 2 a 3 días (short swing)
- 4 a 5 días (weekly swing)
- 6 a 10 días (extended swing)
- > 10 días

Familias de investigación soportadas:
1. daily_trend_persistence
2. multi_day_momentum
3. daily_volatility_contraction_expansion
4. daily_pullback_trend
5. regime_conditioned_swing_momentum
6. daily_mean_reversion
7. daily_gap_continuation
8. daily_range_compression_breakout
9. multi_day_reversal
10. etf_relative_strength_rotation
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
import numpy as np
import pandas as pd

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.domain.enums import SignalDirection, MarketRegime
from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import calculate_movement_to_cost_ratio


class DailyFeaturePrecomputer:
    """Precalcula vectores técnicos sobre barras diarias con cero look-ahead bias."""

    @staticmethod
    def precompute(d_bars: List[OHLCVBar]) -> Dict[str, Any]:
        if not d_bars or len(d_bars) < 30:
            return {}

        df = pd.DataFrame([{
            "timestamp": b.timestamp,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume
        } for b in d_bars])

        close = df["close"]
        high = df["high"]
        low = df["low"]
        vol = df["volume"]

        sma20 = close.rolling(20).mean().values
        sma50 = close.rolling(50).mean().values
        sma200 = close.rolling(200).mean().bfill().fillna(close).values
        ema9 = close.ewm(span=9, adjust=False).mean().values
        ema21 = close.ewm(span=21, adjust=False).mean().values

        # RSI 14
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0).values

        # ATR 14
        tr = np.maximum(
            high.iloc[1:] - low.iloc[1:],
            np.maximum(abs(high.iloc[1:] - close.iloc[:-1].values), abs(low.iloc[1:] - close.iloc[:-1].values))
        )
        atr_series = pd.Series(tr, index=df.index[1:]).rolling(14).mean()
        atr = atr_series.reindex(df.index).bfill().fillna(close * 0.015).values

        # RVOL 20
        vol_sma20 = vol.rolling(20).mean().fillna(vol).values + 1e-9
        rvol = vol.values / vol_sma20

        # Donchian 20
        high_20 = high.shift(1).rolling(20).max().bfill().fillna(high).values
        low_20 = low.shift(1).rolling(20).min().bfill().fillna(low).values
        high_50 = high.shift(1).rolling(50).max().bfill().fillna(high).values
        low_50 = low.shift(1).rolling(50).min().bfill().fillna(low).values

        atr_s = pd.Series(atr)
        avg_atr_20 = atr_s.shift(1).rolling(20).mean().bfill().fillna(atr_s).values

        # Momentum de 20 días
        mom_20 = close.pct_change(20).fillna(0.0).values

        # Régimen diario: BULL_TREND, BEAR_TREND, SIDEWAYS, HIGH_VOL, LOW_VOL
        bull_trend = (close.values > sma50) & (sma20 >= sma50) & (close.values > sma200)
        bear_trend = (close.values < sma50) & (sma20 <= sma50) & (close.values < sma200)
        high_vol = atr > (avg_atr_20 * 1.25)
        low_vol = atr < (avg_atr_20 * 0.80)

        regimes = []
        for i in range(len(df)):
            if high_vol[i]:
                reg = "HIGH_VOL"
            elif low_vol[i]:
                reg = "LOW_VOL"
            elif bull_trend[i]:
                reg = "BULL_TREND"
            elif bear_trend[i]:
                reg = "BEAR_TREND"
            else:
                reg = "SIDEWAYS"
            regimes.append(reg)

        return {
            "sma20": sma20,
            "sma50": sma50,
            "sma200": sma200,
            "ema9": ema9,
            "ema21": ema21,
            "rsi": rsi,
            "atr": atr,
            "rvol": rvol,
            "high_20": high_20,
            "low_20": low_20,
            "high_50": high_50,
            "low_50": low_50,
            "avg_atr_20": avg_atr_20,
            "mom_20": mom_20,
            "bull_trend": bull_trend,
            "bear_trend": bear_trend,
            "regimes": regimes
        }


class DailyStrategyEvaluator:
    """Evaluador de estrategias en velas diarias (1D)."""

    def __init__(
        self,
        family: str,
        holding_horizon_days: int = 5,
        exit_geometry: str = "time_stop",
        rr_ratio: float = 2.0,
        atr_mult: float = 1.5,
        trailing_mult: float = 2.0,
        parameters: Optional[Dict[str, Any]] = None
    ):
        self.family = family
        self.holding_horizon_days = holding_horizon_days
        self.exit_geometry = exit_geometry
        self.rr_ratio = rr_ratio
        self.atr_mult = atr_mult
        self.trailing_mult = trailing_mult
        self.parameters = parameters or {}

    def evaluate_signal_fast(
        self,
        symbol: str,
        bar: OHLCVBar,
        idx: int,
        bars: List[OHLCVBar],
        feat: Dict[str, Any],
        cross_etf_context: Optional[Dict[str, float]] = None
    ) -> Optional[Dict[str, Any]]:
        if idx < 50:
            return None

        close = bar.close
        open_p = bar.open
        high = bar.high
        low = bar.low
        prev_close = bars[idx - 1].close
        prev_open = bars[idx - 1].open

        atr = float(feat["atr"][idx])
        rvol = float(feat["rvol"][idx])
        rsi = float(feat["rsi"][idx])
        ema9 = float(feat["ema9"][idx])
        ema21 = float(feat["ema21"][idx])
        sma20 = float(feat["sma20"][idx])
        sma50 = float(feat["sma50"][idx])
        sma200 = float(feat["sma200"][idx])
        high_20 = float(feat["high_20"][idx])
        low_20 = float(feat["low_20"][idx])
        avg_atr_20 = float(feat["avg_atr_20"][idx])
        regime = feat["regimes"][idx]

        direction = SignalDirection.NO_TRADE

        # 1. Daily Trend Persistence
        if self.family == "daily_trend_persistence":
            bull_cond = (close > sma50 > sma200) and (ema9 > ema21) and (52.0 <= rsi <= 68.0) and (rvol >= 1.05)
            bear_cond = (close < sma50 < sma200) and (ema9 < ema21) and (32.0 <= rsi <= 48.0) and (rvol >= 1.05)
            if bull_cond:
                direction = SignalDirection.BUY
            elif bear_cond:
                direction = SignalDirection.SELL

        # 2. Multi-Day Momentum
        elif self.family == "multi_day_momentum":
            # 3 barras consecutivas de cierres crecientes/decrecientes con expansión
            c_3 = bars[idx - 3].close
            c_2 = bars[idx - 2].close
            c_1 = bars[idx - 1].close
            bull_cond = (close > c_1 > c_2 > c_3) and (close > sma20) and (rsi >= 55.0) and (rvol >= 1.1)
            bear_cond = (close < c_1 < c_2 < c_3) and (close < sma20) and (rsi <= 45.0) and (rvol >= 1.1)
            if bull_cond:
                direction = SignalDirection.BUY
            elif bear_cond:
                direction = SignalDirection.SELL

        # 3. Volatility Contraction -> Expansion
        elif self.family == "daily_volatility_contraction_expansion":
            prev_atr = float(feat["atr"][idx - 1])
            was_contracted = prev_atr < (avg_atr_20 * 0.85)
            is_expanding = (atr >= avg_atr_20 * 1.15) and (rvol >= 1.25)
            if was_contracted and is_expanding:
                if close > open_p and close > sma20:
                    direction = SignalDirection.BUY
                elif close < open_p and close < sma20:
                    direction = SignalDirection.SELL

        # 4. Pullback within Established Daily Trend
        elif self.family == "daily_pullback_trend":
            in_uptrend = (close > sma50 > sma200) and (sma20 >= sma50)
            in_downtrend = (close < sma50 < sma200) and (sma20 <= sma50)
            # Pullback a la EMA21 con giro positivo
            bull_pullback = in_uptrend and (low <= ema21) and (close > ema9) and (45.0 <= rsi <= 60.0)
            bear_pullback = in_downtrend and (high >= ema21) and (close < ema9) and (40.0 <= rsi <= 55.0)
            if bull_pullback:
                direction = SignalDirection.BUY
            elif bear_pullback:
                direction = SignalDirection.SELL

        # 5. Regime-Conditioned Swing Momentum
        elif self.family == "regime_conditioned_swing_momentum":
            if regime == "BULL_TREND":
                if (close > ema9) and (rsi >= 52.0) and (close > open_p):
                    direction = SignalDirection.BUY
            elif regime == "BEAR_TREND":
                if (close < ema9) and (rsi <= 48.0) and (close < open_p):
                    direction = SignalDirection.SELL

        # 6. Daily Mean Reversion
        elif self.family == "daily_mean_reversion":
            # Reversión a la media solo en tendencia alcista de largo plazo (> SMA200) o lateral
            if close > sma200 or regime == "SIDEWAYS":
                if rsi <= 32.0 and close < (sma20 - atr * 1.5):
                    direction = SignalDirection.BUY
            if close < sma200 or regime == "SIDEWAYS":
                if rsi >= 68.0 and close > (sma20 + atr * 1.5):
                    direction = SignalDirection.SELL

        # 7. Gap Continuation / Gap Failure
        elif self.family == "daily_gap_continuation":
            gap_pct = (open_p - prev_close) / (prev_close + 1e-9)
            if gap_pct > 0.005 and close > open_p and rvol >= 1.2:
                direction = SignalDirection.BUY
            elif gap_pct < -0.005 and close < open_p and rvol >= 1.2:
                direction = SignalDirection.SELL

        # 8. Daily Range Compression Breakout
        elif self.family == "daily_range_compression_breakout":
            bull_bo = (close >= high_20) and (rvol >= 1.25) and (close > sma50)
            bear_bo = (close <= low_20) and (rvol >= 1.25) and (close < sma50)
            if bull_bo:
                direction = SignalDirection.BUY
            elif bear_bo:
                direction = SignalDirection.SELL

        # 9. Multi-Day Reversal
        elif self.family == "multi_day_reversal":
            # Falso rompimiento de 20 días en escala diaria
            bull_rev = (low < low_20) and (close > low_20) and (rsi < 38.0)
            bear_rev = (high > high_20) and (close < high_20) and (rsi > 62.0)
            if bull_rev:
                direction = SignalDirection.BUY
            elif bear_rev:
                direction = SignalDirection.SELL

        # 10. Cross-ETF Relative Strength Rotation
        elif self.family == "etf_relative_strength_rotation":
            if cross_etf_context:
                my_rank = cross_etf_context.get(symbol, 0.0)
                # Si este símbolo es el top performer en momentum a 20 días
                if my_rank >= 0.75 and close > sma50:
                    direction = SignalDirection.BUY
                elif my_rank <= 0.25 and close < sma50:
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

        return {
            "symbol": symbol,
            "timestamp": bar.timestamp,
            "direction": "BUY" if direction == SignalDirection.BUY else "SELL",
            "entry_price": close,
            "stop_loss": sl,
            "take_profit": tp,
            "atr": atr,
            "regime": regime,
            "family": self.family
        }


class DailyExecutionSimulator:
    """Simulador de carteras y ejecución para estrategias en timeframe 1D."""

    def __init__(
        self,
        evaluator: DailyStrategyEvaluator,
        initial_capital: float = 100000.0,
        commission_per_share: float = 0.005,
        slippage_pct: float = 0.0005,
        risk_per_trade_pct: float = 0.01,
        concurrency_policy: str = "ONE_POSITION_PER_SYMBOL",
        max_concurrent_positions: int = 2
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
        symbols_data: Dict[str, List[OHLCVBar]],
        precomputed_features: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        capital = self.initial_capital
        peak_capital = capital
        max_drawdown = 0.0

        # Mapear barras por timestamp ordenadas
        all_dates = set()
        bars_by_sym_date: Dict[str, Dict[date, Tuple[OHLCVBar, int]]] = {}
        for sym, bars in symbols_data.items():
            bars_by_sym_date[sym] = {}
            for idx, b in enumerate(bars):
                d = b.timestamp.date()
                bars_by_sym_date[sym][d] = (b, idx)
                all_dates.add(d)

        sorted_dates = sorted(list(all_dates))
        active_positions: Dict[str, Dict[str, Any]] = {}
        closed_trades: List[Dict[str, Any]] = []

        total_commission_paid = 0.0
        total_slippage_drag = 0.0
        total_favorable_moves = []

        for curr_d in sorted_dates:
            # 1. ACTUALIZAR Y EVALUAR SALIDAS DE POSICIONES ACTIVAS
            closed_pos_ids = []
            for pos_id, pos in active_positions.items():
                sym = pos["symbol"]
                sym_entry = bars_by_sym_date.get(sym, {}).get(curr_d)
                if not sym_entry:
                    continue
                curr_bar, _ = sym_entry
                pos["days_held"] += 1

                side = pos["side"]
                entry_p = pos["entry_price"]
                qty = pos["quantity"]
                sl = pos["stop_loss"]
                tp = pos["take_profit"]

                exit_price = None
                exit_reason = None

                # Trailing ATR
                if self.evaluator.exit_geometry == "atr_trailing":
                    trail_dist = pos["atr"] * self.evaluator.trailing_mult
                    if side == "BUY":
                        new_high = max(pos.get("peak_price", entry_p), curr_bar.high)
                        pos["peak_price"] = new_high
                        pos["stop_loss"] = max(pos["stop_loss"], round(new_high - trail_dist, 2))
                    else:
                        new_low = min(pos.get("trough_price", entry_p), curr_bar.low)
                        pos["trough_price"] = new_low
                        pos["stop_loss"] = min(pos["stop_loss"], round(new_low + trail_dist, 2))

                # Time Stop (días de permanencia)
                if pos["days_held"] >= self.evaluator.holding_horizon_days:
                    exit_price = curr_bar.close
                    exit_reason = "TIME_EXIT"

                # SL / TP
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
                    exec_exit = exit_price * (1.0 - self.slippage_pct) if side == "BUY" else exit_price * (1.0 + self.slippage_pct)
                    gross = (exec_exit - entry_p) * qty if side == "BUY" else (entry_p - exec_exit) * qty
                    comm = qty * self.commission_per_share
                    net = gross - comm

                    # Slippage drag
                    slip_exit_drag = abs(exec_exit - exit_price) * qty
                    slip_entry_drag = pos.get("entry_slippage_drag", 0.0)
                    total_slippage_drag += (slip_exit_drag + slip_entry_drag)
                    total_commission_paid += (comm + pos.get("entry_commission", 0.0))

                    # Movimiento favorable
                    fav_move = max(0.0, (curr_bar.high - entry_p) if side == "BUY" else (entry_p - curr_bar.low))
                    total_favorable_moves.append(fav_move)

                    closed_trades.append({
                        "symbol": sym,
                        "entry_date": pos["entry_date"],
                        "exit_date": curr_d,
                        "side": side,
                        "entry_price": entry_p,
                        "exit_price": exec_exit,
                        "quantity": qty,
                        "gross_pnl": gross,
                        "net_pnl": net,
                        "is_win": net > 0,
                        "exit_reason": exit_reason,
                        "days_held": pos["days_held"],
                        "regime": pos["regime"]
                    })
                    capital += net
                    closed_pos_ids.append(pos_id)

            for pid in closed_pos_ids:
                del active_positions[pid]

            # 2. EVALUAR SEÑALES DIARIAS ENTRANTE
            # Calcular ranking cross-etf si aplica
            cross_context = {}
            if self.evaluator.family == "etf_relative_strength_rotation":
                moms = {}
                for sym, b_map in bars_by_sym_date.items():
                    if curr_d in b_map:
                        _, b_idx = b_map[curr_d]
                        moms[sym] = float(precomputed_features[sym]["mom_20"][b_idx])
                sorted_syms = sorted(moms.keys(), key=lambda s: moms[s])
                n_syms = max(1, len(sorted_syms))
                for rank_idx, s in enumerate(sorted_syms):
                    cross_context[s] = rank_idx / n_syms

            new_signals = []
            for sym, d_bars in symbols_data.items():
                sym_entry = bars_by_sym_date.get(sym, {}).get(curr_d)
                if not sym_entry:
                    continue
                curr_bar, b_idx = sym_entry
                sig = self.evaluator.evaluate_signal_fast(
                    symbol=sym,
                    bar=curr_bar,
                    idx=b_idx,
                    bars=d_bars,
                    feat=precomputed_features[sym],
                    cross_etf_context=cross_context
                )
                if sig is not None:
                    new_signals.append(sig)

            # 3. POLÍTICA DE CONCURRENCIA
            for sig in new_signals:
                sym = sig["symbol"]
                side = sig["direction"]
                sym_in_pos = any(p["symbol"] == sym for p in active_positions.values())
                global_pos_count = len(active_positions)

                can_enter = False
                if self.concurrency_policy == "ONE_POSITION_GLOBAL":
                    if global_pos_count < self.max_concurrent_positions and not sym_in_pos:
                        can_enter = True
                elif self.concurrency_policy in ["ONE_POSITION_PER_SYMBOL", "FIRST_SIGNAL"]:
                    if not sym_in_pos and global_pos_count < self.max_concurrent_positions:
                        can_enter = True

                if can_enter:
                    entry_p = sig["entry_price"] * (1.0 + self.slippage_pct) if side == "BUY" else sig["entry_price"] * (1.0 - self.slippage_pct)
                    risk_amount = capital * self.risk_per_trade_pct
                    risk_per_share = abs(entry_p - sig["stop_loss"])
                    if risk_per_share > 0.10:
                        qty = max(1, int(risk_amount / risk_per_share))
                        pos_id = f"{sym}_{curr_d.strftime('%Y%m%d')}"
                        entry_slip_drag = abs(entry_p - sig["entry_price"]) * qty
                        entry_comm = qty * self.commission_per_share

                        active_positions[pos_id] = {
                            "symbol": sym,
                            "entry_date": curr_d,
                            "side": side,
                            "entry_price": entry_p,
                            "stop_loss": sig["stop_loss"],
                            "take_profit": sig["take_profit"],
                            "quantity": qty,
                            "days_held": 0,
                            "atr": sig["atr"],
                            "regime": sig["regime"],
                            "entry_slippage_drag": entry_slip_drag,
                            "entry_commission": entry_comm
                        }

            # Actualizar Drawdown
            if capital > peak_capital:
                peak_capital = capital
            dd = (peak_capital - capital) / peak_capital * 100.0 if peak_capital > 0 else 0.0
            if dd > max_drawdown:
                max_drawdown = dd

        # MÉTRICAS GLOBALES
        n_trades = len(closed_trades)
        wins = [t for t in closed_trades if t["is_win"]]
        losses = [t for t in closed_trades if not t["is_win"]]
        win_rate = (len(wins) / n_trades * 100.0) if n_trades > 0 else 0.0

        gross_profit = sum(t["gross_pnl"] for t in wins)
        gross_loss = abs(sum(t["gross_pnl"] for t in losses))
        net_profit = sum(t["net_pnl"] for t in wins)
        net_loss = abs(sum(t["net_pnl"] for t in losses))

        profit_factor = round(net_profit / net_loss, 2) if net_loss > 0 else (2.0 if net_profit > 0 else 0.0)
        total_net_pnl = round(sum(t["net_pnl"] for t in closed_trades), 2)
        total_gross_pnl = round(sum(t["gross_pnl"] for t in closed_trades), 2)
        expectancy = round(total_net_pnl / n_trades, 2) if n_trades > 0 else 0.0

        pnl_series = [t["net_pnl"] for t in closed_trades]
        if len(pnl_series) > 1 and np.std(pnl_series) > 0:
            sharpe = round(float((np.mean(pnl_series) / np.std(pnl_series)) * math.sqrt(252.0 / max(1, self.evaluator.holding_horizon_days))), 2)
        else:
            sharpe = 0.0

        # Holding period distribution
        holding_days = [t["days_held"] for t in closed_trades]
        mean_holding = round(float(np.mean(holding_days)), 2) if holding_days else 0.0
        median_holding = round(float(np.median(holding_days)), 2) if holding_days else 0.0
        min_holding = min(holding_days) if holding_days else 0
        max_holding = max(holding_days) if holding_days else 0

        h_dist = {
            "1_day": sum(1 for d in holding_days if d == 1),
            "2_3_days": sum(1 for d in holding_days if 2 <= d <= 3),
            "4_5_days": sum(1 for d in holding_days if 4 <= d <= 5),
            "6_10_days": sum(1 for d in holding_days if 6 <= d <= 10),
            "gt_10_days": sum(1 for d in holding_days if d > 10)
        }

        # Turnover
        total_years = max(1.0, len(sorted_dates) / 252.0)
        trades_per_year = round(n_trades / total_years, 2)

        # Movement-to-cost ratio (MCR)
        avg_fav = float(np.mean(total_favorable_moves)) if total_favorable_moves else 0.0
        avg_price = float(np.mean([t["entry_price"] for t in closed_trades])) if closed_trades else 100.0
        rt_friction_per_share = (self.commission_per_share * 2.0) + (avg_price * self.slippage_pct * 2.0)
        mcr = calculate_movement_to_cost_ratio(avg_fav, rt_friction_per_share)

        avg_w = float(np.mean([t["net_pnl"] for t in wins])) if wins else 0.0
        avg_l = abs(float(np.mean([t["net_pnl"] for t in losses]))) if losses else 0.0
        payoff = round(avg_w / avg_l, 2) if avg_l > 0 else 0.0
        breakeven_wr = round((1.0 / (1.0 + payoff)) * 100.0, 2) if payoff > 0 else 50.0

        cost_to_gross = round((total_commission_paid + total_slippage_drag) / max(1.0, abs(total_gross_pnl)) * 100.0, 2)

        return {
            "total_trades": n_trades,
            "win_rate": round(win_rate, 2),
            "profit_factor": profit_factor,
            "total_net_pnl": total_net_pnl,
            "total_gross_pnl": total_gross_pnl,
            "commission_drag": round(total_commission_paid, 2),
            "slippage_drag": round(total_slippage_drag, 2),
            "cost_to_gross_edge_pct": cost_to_gross,
            "expectancy": expectancy,
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": round(max_drawdown, 2),
            "realized_payoff_ratio": payoff,
            "realized_breakeven_win_rate": breakeven_wr,
            "actual_win_rate": round(win_rate, 2),
            "holding_period_stats": {
                "mean_days": mean_holding,
                "median_days": median_holding,
                "min_days": min_holding,
                "max_days": max_holding,
                "distribution": h_dist
            },
            "turnover_stats": {
                "trades_per_year": trades_per_year,
                "total_years": round(total_years, 2)
            },
            "movement_to_cost_ratio": mcr,
            "closed_trades": closed_trades
        }
