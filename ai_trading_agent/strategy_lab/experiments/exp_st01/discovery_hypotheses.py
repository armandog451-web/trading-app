"""
ai_trading_agent.strategy_lab.experiments.exp_st01.discovery_hypotheses
=======================================================================
Evaluador Cuantitativo de Hipótesis de Descubrimiento (H1 a H5) para ST_EMA200_V1.

Hipótesis Formuladas:
- H1 (Filtro ADX): ADX(14) > 25 para evitar mercados laterales/ruido.
- H2 (Filtro RVOL): Volumen de la barra > 1.2 * SMA(Volumen, 20).
- H3 (Filtro Volatilidad ATR): Expansión de ATR vs SMA(ATR, 20).
- H4 (Filtro Horario de Sesión): Entrada limitada a horario núcleo 10:00 a 15:00 ET (reduce gap de apertura/cierre).
- H5 (Salida Adaptativa Trailing): Trailing stop dinámico por la línea SuperTrend en lugar de TP rígido de 1.5R.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, time
import math
import numpy as np

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.experiments.exp_st01.supertrend_indicator import (
    SuperTrendCalculator,
    SuperTrendPoint,
)
from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_strategy import (
    StEma200Strategy,
    StrategySignalST,
    TradeDirection,
)
from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_backtester import (
    StEma200Backtester,
    TradeRecordST,
    BacktestMetricsST,
    COST_TIERS,
)


@dataclass
class HypothesisTestResult:
    hypothesis_id: str
    name: str
    symbol: str
    timeframe: str
    baseline_trades: int
    baseline_net_pnl: float
    baseline_pf: float
    baseline_win_rate: float
    modified_trades: int
    modified_net_pnl: float
    modified_pf: float
    modified_win_rate: float
    delta_pnl: float
    delta_pf: float
    delta_win_rate: float
    accepted: bool
    verdict: str


class DiscoveryHypothesesEvaluator:
    """Evaluador de hipótesis H1-H5 comparando contra la línea base de ST_EMA200_V1."""

    def __init__(self, initial_equity: float = 100000.0, risk_per_trade: float = 250.0):
        self.initial_equity = initial_equity
        self.risk_per_trade = risk_per_trade
        self.cost_model = COST_TIERS["1x"]

    def calculate_adx(self, bars: List[OHLCVBar], period: int = 14) -> List[Optional[float]]:
        """Calcula ADX causalmente usando el suavizado de Wilder."""
        n = len(bars)
        if n < period * 2:
            return [None] * n

        plus_dm = [0.0] * n
        minus_dm = [0.0] * n
        tr = [0.0] * n

        for i in range(1, n):
            up = bars[i].high - bars[i - 1].high
            down = bars[i - 1].low - bars[i].low
            plus_dm[i] = up if (up > down and up > 0) else 0.0
            minus_dm[i] = down if (down > up and down > 0) else 0.0
            tr[i] = max(
                bars[i].high - bars[i].low,
                abs(bars[i].high - bars[i - 1].close),
                abs(bars[i].low - bars[i - 1].close),
            )

        # Wilder smoothing
        tr_smooth = [0.0] * n
        p_dm_smooth = [0.0] * n
        m_dm_smooth = [0.0] * n

        tr_smooth[period] = sum(tr[1 : period + 1])
        p_dm_smooth[period] = sum(plus_dm[1 : period + 1])
        m_dm_smooth[period] = sum(minus_dm[1 : period + 1])

        for i in range(period + 1, n):
            tr_smooth[i] = tr_smooth[i - 1] - (tr_smooth[i - 1] / period) + tr[i]
            p_dm_smooth[i] = p_dm_smooth[i - 1] - (p_dm_smooth[i - 1] / period) + plus_dm[i]
            m_dm_smooth[i] = m_dm_smooth[i - 1] - (m_dm_smooth[i - 1] / period) + minus_dm[i]

        dx = [0.0] * n
        for i in range(period, n):
            p_di = 100.0 * (p_dm_smooth[i] / tr_smooth[i]) if tr_smooth[i] > 0 else 0.0
            m_di = 100.0 * (m_dm_smooth[i] / tr_smooth[i]) if tr_smooth[i] > 0 else 0.0
            di_sum = p_di + m_di
            dx[i] = 100.0 * abs(p_di - m_di) / di_sum if di_sum > 0 else 0.0

        adx: List[Optional[float]] = [None] * n
        adx_idx = period * 2 - 1
        if adx_idx < n:
            adx[adx_idx] = sum(dx[period : adx_idx + 1]) / period
            for i in range(adx_idx + 1, n):
                adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

        return adx

    def evaluate_h1_adx(self, symbol: str, timeframe: str, bars: List[OHLCVBar], adx_thresh: float = 25.0) -> HypothesisTestResult:
        """H1: Requiere ADX(14) > 25 al momento de la señal."""
        strat = StEma200Strategy()
        bt = StEma200Backtester(strat, self.initial_equity, self.risk_per_trade)
        base_m, _ = bt.run(symbol, timeframe, bars)

        adx_series = self.calculate_adx(bars, period=14)
        signals = strat.generate_signals(symbol, bars)

        filtered_signals = []
        for s in signals:
            val = adx_series[s.bar_index]
            if val is not None and val >= adx_thresh:
                filtered_signals.append(s)

        mod_m, _ = self._run_custom_signals(symbol, timeframe, bars, strat, filtered_signals)

        delta_pnl = mod_m.net_pnl - base_m.net_pnl
        delta_pf = mod_m.profit_factor - base_m.profit_factor
        delta_wr = mod_m.win_rate - base_m.win_rate

        accepted = (mod_m.profit_factor > base_m.profit_factor and mod_m.net_pnl >= base_m.net_pnl * 0.90 and mod_m.total_trades >= 15)
        verdict = "CONFIRMADA (Mejora PF con retención de PnL)" if accepted else "RECHAZADA (No mejora o reduce trades excesivamente)"

        return HypothesisTestResult("H1", f"Regime ADX > {adx_thresh}", symbol, timeframe, base_m.total_trades, base_m.net_pnl, base_m.profit_factor, base_m.win_rate, mod_m.total_trades, mod_m.net_pnl, mod_m.profit_factor, mod_m.win_rate, delta_pnl, delta_pf, delta_wr, accepted, verdict)

    def evaluate_h2_rvol(self, symbol: str, timeframe: str, bars: List[OHLCVBar], rvol_mult: float = 1.2) -> HypothesisTestResult:
        """H2: Volumen de barra de señal > 1.2 * SMA(Volumen, 20)."""
        strat = StEma200Strategy()
        bt = StEma200Backtester(strat, self.initial_equity, self.risk_per_trade)
        base_m, _ = bt.run(symbol, timeframe, bars)

        vols = [b.volume for b in bars]
        sma_vol = [None] * len(bars)
        for i in range(19, len(bars)):
            sma_vol[i] = sum(vols[i - 19 : i + 1]) / 20.0

        signals = strat.generate_signals(symbol, bars)
        filtered = []
        for s in signals:
            sv = sma_vol[s.bar_index]
            if sv is not None and sv > 0 and vols[s.bar_index] >= rvol_mult * sv:
                filtered.append(s)

        mod_m, _ = self._run_custom_signals(symbol, timeframe, bars, strat, filtered)
        delta_pnl = mod_m.net_pnl - base_m.net_pnl
        delta_pf = mod_m.profit_factor - base_m.profit_factor
        delta_wr = mod_m.win_rate - base_m.win_rate

        accepted = (mod_m.profit_factor > base_m.profit_factor and mod_m.net_pnl >= base_m.net_pnl * 0.85 and mod_m.total_trades >= 15)
        verdict = "CONFIRMADA (Confirmación institucional de volumen)" if accepted else "RECHAZADA (Filtro demasiado restrictivo o sin edge)"

        return HypothesisTestResult("H2", f"RVOL > {rvol_mult}x SMA20", symbol, timeframe, base_m.total_trades, base_m.net_pnl, base_m.profit_factor, base_m.win_rate, mod_m.total_trades, mod_m.net_pnl, mod_m.profit_factor, mod_m.win_rate, delta_pnl, delta_pf, delta_wr, accepted, verdict)

    def evaluate_h3_atr_expansion(self, symbol: str, timeframe: str, bars: List[OHLCVBar]) -> HypothesisTestResult:
        """H3: ATR de la señal en expansión (ATR > SMA(ATR, 20))."""
        strat = StEma200Strategy()
        bt = StEma200Backtester(strat, self.initial_equity, self.risk_per_trade)
        base_m, _ = bt.run(symbol, timeframe, bars)

        calc = SuperTrendCalculator()
        pts = calc.calculate_series(bars)
        atrs = [p.atr for p in pts]
        sma_atr = [None] * len(bars)
        for i in range(19, len(bars)):
            sma_atr[i] = sum(atrs[i - 19 : i + 1]) / 20.0

        signals = strat.generate_signals(symbol, bars)
        filtered = []
        for s in signals:
            sa = sma_atr[s.bar_index]
            if sa is not None and atrs[s.bar_index] > sa:
                filtered.append(s)

        mod_m, _ = self._run_custom_signals(symbol, timeframe, bars, strat, filtered)
        delta_pnl = mod_m.net_pnl - base_m.net_pnl
        delta_pf = mod_m.profit_factor - base_m.profit_factor
        delta_wr = mod_m.win_rate - base_m.win_rate

        accepted = (mod_m.profit_factor > base_m.profit_factor and mod_m.net_pnl >= base_m.net_pnl * 0.85 and mod_m.total_trades >= 15)
        verdict = "CONFIRMADA (Filtro de expansión de volatilidad favorable)" if accepted else "RECHAZADA"

        return HypothesisTestResult("H3", "ATR Volatility Expansion (ATR > SMA20)", symbol, timeframe, base_m.total_trades, base_m.net_pnl, base_m.profit_factor, base_m.win_rate, mod_m.total_trades, mod_m.net_pnl, mod_m.profit_factor, mod_m.win_rate, delta_pnl, delta_pf, delta_wr, accepted, verdict)

    def evaluate_h4_session_timing(self, symbol: str, timeframe: str, bars: List[OHLCVBar]) -> HypothesisTestResult:
        """H4: Filtro de horario regular 10:00 a 15:00 ET (para intradía)."""
        strat = StEma200Strategy()
        bt = StEma200Backtester(strat, self.initial_equity, self.risk_per_trade)
        base_m, _ = bt.run(symbol, timeframe, bars)

        signals = strat.generate_signals(symbol, bars)
        filtered = []
        for s in signals:
            ts = s.timestamp
            # Si tiene hora (intradía)
            if hasattr(ts, "hour"):
                h = ts.hour
                m = ts.minute
                # Horario 10:00 a 15:00
                if 10 <= h <= 15:
                    filtered.append(s)
            else:
                filtered.append(s)

        mod_m, _ = self._run_custom_signals(symbol, timeframe, bars, strat, filtered)
        delta_pnl = mod_m.net_pnl - base_m.net_pnl
        delta_pf = mod_m.profit_factor - base_m.profit_factor
        delta_wr = mod_m.win_rate - base_m.win_rate

        accepted = (mod_m.profit_factor > base_m.profit_factor and mod_m.total_trades >= 15)
        verdict = "CONFIRMADA (Filtrado de colas de sesión mejora PF)" if accepted else "RECHAZADA (No aporta ventaja)"

        return HypothesisTestResult("H4", "Session Timing Core (10:00 - 15:00 ET)", symbol, timeframe, base_m.total_trades, base_m.net_pnl, base_m.profit_factor, base_m.win_rate, mod_m.total_trades, mod_m.net_pnl, mod_m.profit_factor, mod_m.win_rate, delta_pnl, delta_pf, delta_wr, accepted, verdict)

    def evaluate_h5_trailing_stop(self, symbol: str, timeframe: str, bars: List[OHLCVBar]) -> HypothesisTestResult:
        """H5: Salida adaptativa mediante Trailing Stop por la línea SuperTrend sin TP fijo."""
        strat = StEma200Strategy()
        bt = StEma200Backtester(strat, self.initial_equity, self.risk_per_trade)
        base_m, _ = bt.run(symbol, timeframe, bars)

        calc = SuperTrendCalculator()
        pts = calc.calculate_series(bars)
        pt_map = {i: pts[i] for i in range(len(pts))}

        signals = strat.generate_signals(symbol, bars)
        sig_map = {s.bar_index: s for s in signals}

        trades: List[TradeRecordST] = []
        equity = self.initial_equity
        i = 0
        n_bars = len(bars)
        trade_id = 1
        cost_model = self.cost_model

        while i < n_bars - 1:
            if i in sig_map:
                sig = sig_map[i]
                entry_idx = i + 1
                entry_bar = bars[entry_idx]
                raw_entry = entry_bar.open

                if sig.direction == TradeDirection.LONG:
                    fill_entry = raw_entry * (1.0 + cost_model.slippage_rate)
                    curr_sl = sig.stop_loss_level
                    sl_dist = fill_entry - curr_sl
                    if sl_dist <= 0.001:
                        i += 1
                        continue
                else:
                    fill_entry = raw_entry * (1.0 - cost_model.slippage_rate)
                    curr_sl = sig.stop_loss_level
                    sl_dist = curr_sl - fill_entry
                    if sl_dist <= 0.001:
                        i += 1
                        continue

                shares = max(1, min(math.floor(self.risk_per_trade / sl_dist), math.floor(equity * 0.95 / fill_entry)))
                risk_usd = shares * sl_dist

                curr_k = entry_idx
                closed = False
                raw_exit = 0.0
                exit_price = 0.0
                exit_time = entry_bar.timestamp
                exit_reason = ""

                while curr_k < n_bars and not closed:
                    bk = bars[curr_k]
                    pt_k = pt_map[curr_k]

                    if sig.direction == TradeDirection.LONG:
                        # Trailing: el SL sube con la línea de SuperTrend si está en tendencia alcista
                        if pt_k.trend == 1 and pt_k.supertrend > curr_sl:
                            curr_sl = pt_k.supertrend

                        if bk.low <= curr_sl or pt_k.direction_flip == -1:
                            raw_exit = min(bk.open, curr_sl)
                            exit_price = raw_exit * (1.0 - cost_model.slippage_rate)
                            exit_time = bk.timestamp
                            exit_reason = "TRAILING_SL"
                            closed = True
                    else:  # SHORT
                        if pt_k.trend == -1 and pt_k.supertrend < curr_sl:
                            curr_sl = pt_k.supertrend

                        if bk.high >= curr_sl or pt_k.direction_flip == 1:
                            raw_exit = max(bk.open, curr_sl)
                            exit_price = raw_exit * (1.0 + cost_model.slippage_rate)
                            exit_time = bk.timestamp
                            exit_reason = "TRAILING_SL"
                            closed = True

                    if not closed:
                        if curr_k == n_bars - 1:
                            raw_exit = bk.close
                            exit_price = raw_exit * (1.0 - cost_model.slippage_rate if sig.direction == TradeDirection.LONG else 1.0 + cost_model.slippage_rate)
                            exit_time = bk.timestamp
                            exit_reason = "END_OF_DATA"
                            closed = True
                        else:
                            curr_k += 1

                if sig.direction == TradeDirection.LONG:
                    gross_pnl = shares * (raw_exit - raw_entry)
                    net_pnl = shares * (exit_price - fill_entry)
                else:
                    gross_pnl = shares * (raw_entry - raw_exit)
                    net_pnl = shares * (fill_entry - exit_price)

                comm_cost = 2.0 * shares * cost_model.commission_per_share
                net_pnl -= comm_cost
                slip_cost = abs(gross_pnl - net_pnl - comm_cost)
                pnl_r = net_pnl / risk_usd if risk_usd > 0 else 0.0

                trades.append(
                    TradeRecordST(
                        trade_id=trade_id,
                        symbol=symbol,
                        direction=sig.direction,
                        entry_bar_idx=entry_idx,
                        entry_time=entry_bar.timestamp,
                        entry_price=fill_entry,
                        raw_entry_price=raw_entry,
                        exit_bar_idx=curr_k,
                        exit_time=exit_time,
                        exit_price=exit_price,
                        raw_exit_price=raw_exit,
                        shares=shares,
                        stop_loss=curr_sl,
                        take_profit=0.0,
                        risk_r_usd=risk_usd,
                        gross_pnl=gross_pnl,
                        net_pnl=net_pnl,
                        slippage_cost=slip_cost,
                        commission_cost=comm_cost,
                        pnl_r=pnl_r,
                        exit_reason=exit_reason,
                        bars_held=curr_k - entry_idx + 1,
                    )
                )
                trade_id += 1
                equity += net_pnl
                i = curr_k + 1
            else:
                i += 1

        mod_m = bt._calculate_metrics(symbol, timeframe, "1x_Base", bars, trades, [self.initial_equity] + [self.initial_equity + t.net_pnl for t in trades])
        delta_pnl = mod_m.net_pnl - base_m.net_pnl
        delta_pf = mod_m.profit_factor - base_m.profit_factor
        delta_wr = mod_m.win_rate - base_m.win_rate

        accepted = (mod_m.profit_factor > base_m.profit_factor and mod_m.net_pnl > base_m.net_pnl)
        verdict = "CONFIRMADA (Trailing Stop captura tendencias largas)" if accepted else "RECHAZADA (Cortes prematuros o whipsaws)"

        return HypothesisTestResult("H5", "Adaptive SuperTrend Trailing Stop", symbol, timeframe, base_m.total_trades, base_m.net_pnl, base_m.profit_factor, base_m.win_rate, mod_m.total_trades, mod_m.net_pnl, mod_m.profit_factor, mod_m.win_rate, delta_pnl, delta_pf, delta_wr, accepted, verdict)

    def _run_custom_signals(
        self,
        symbol: str,
        timeframe: str,
        bars: List[OHLCVBar],
        strat: StEma200Strategy,
        signals: List[StrategySignalST],
    ) -> Tuple[BacktestMetricsST, List[TradeRecordST]]:
        bt = StEma200Backtester(strat, self.initial_equity, self.risk_per_trade)
        sig_map = {s.bar_index: s for s in signals}
        trades: List[TradeRecordST] = []
        equity = self.initial_equity
        equity_curve = [equity]
        i = 0
        n_bars = len(bars)
        trade_id = 1
        cost_model = self.cost_model

        while i < n_bars - 1:
            if i in sig_map:
                sig = sig_map[i]
                entry_idx = i + 1
                entry_bar = bars[entry_idx]
                raw_entry = entry_bar.open

                if sig.direction == TradeDirection.LONG:
                    fill_entry = raw_entry * (1.0 + cost_model.slippage_rate)
                    sl = sig.stop_loss_level
                    sl_dist = fill_entry - sl
                    if sl_dist <= 0.001:
                        i += 1
                        continue
                    tp = fill_entry + strat.tp_r_multiple * sl_dist
                else:
                    fill_entry = raw_entry * (1.0 - cost_model.slippage_rate)
                    sl = sig.stop_loss_level
                    sl_dist = sl - fill_entry
                    if sl_dist <= 0.001:
                        i += 1
                        continue
                    tp = fill_entry - strat.tp_r_multiple * sl_dist

                shares = max(1, min(math.floor(self.risk_per_trade / sl_dist), math.floor(equity * 0.95 / fill_entry)))
                risk_usd = shares * sl_dist

                curr_k = entry_idx
                closed = False
                raw_exit = 0.0
                exit_price = 0.0
                exit_time = entry_bar.timestamp
                exit_reason = ""

                while curr_k < n_bars and not closed:
                    bk = bars[curr_k]
                    if sig.direction == TradeDirection.LONG:
                        hit_sl = bk.low <= sl
                        hit_tp = bk.high >= tp
                        if hit_sl and hit_tp:
                            raw_exit = min(bk.open, sl)
                            exit_price = raw_exit * (1.0 - cost_model.slippage_rate)
                            exit_time = bk.timestamp
                            exit_reason = "COLLISION_SL"
                            closed = True
                        elif hit_sl:
                            raw_exit = min(bk.open, sl)
                            exit_price = raw_exit * (1.0 - cost_model.slippage_rate)
                            exit_time = bk.timestamp
                            exit_reason = "SL"
                            closed = True
                        elif hit_tp:
                            raw_exit = max(bk.open, tp) if bk.open >= tp else tp
                            exit_price = raw_exit * (1.0 - cost_model.slippage_rate)
                            exit_time = bk.timestamp
                            exit_reason = "TP"
                            closed = True
                    else:
                        hit_sl = bk.high >= sl
                        hit_tp = bk.low <= tp
                        if hit_sl and hit_tp:
                            raw_exit = max(bk.open, sl)
                            exit_price = raw_exit * (1.0 + cost_model.slippage_rate)
                            exit_time = bk.timestamp
                            exit_reason = "COLLISION_SL"
                            closed = True
                        elif hit_sl:
                            raw_exit = max(bk.open, sl)
                            exit_price = raw_exit * (1.0 + cost_model.slippage_rate)
                            exit_time = bk.timestamp
                            exit_reason = "SL"
                            closed = True
                        elif hit_tp:
                            raw_exit = min(bk.open, tp) if bk.open <= tp else tp
                            exit_price = raw_exit * (1.0 + cost_model.slippage_rate)
                            exit_time = bk.timestamp
                            exit_reason = "TP"
                            closed = True

                    if not closed:
                        if curr_k == n_bars - 1:
                            raw_exit = bk.close
                            exit_price = raw_exit * (1.0 - cost_model.slippage_rate if sig.direction == TradeDirection.LONG else 1.0 + cost_model.slippage_rate)
                            exit_time = bk.timestamp
                            exit_reason = "END_OF_DATA"
                            closed = True
                        else:
                            curr_k += 1

                if sig.direction == TradeDirection.LONG:
                    gross_pnl = shares * (raw_exit - raw_entry)
                    net_pnl = shares * (exit_price - fill_entry)
                else:
                    gross_pnl = shares * (raw_entry - raw_exit)
                    net_pnl = shares * (fill_entry - exit_price)

                comm_cost = 2.0 * shares * cost_model.commission_per_share
                net_pnl -= comm_cost
                slip_cost = abs(gross_pnl - net_pnl - comm_cost)
                pnl_r = net_pnl / risk_usd if risk_usd > 0 else 0.0

                trades.append(
                    TradeRecordST(
                        trade_id=trade_id,
                        symbol=symbol,
                        direction=sig.direction,
                        entry_bar_idx=entry_idx,
                        entry_time=entry_bar.timestamp,
                        entry_price=fill_entry,
                        raw_entry_price=raw_entry,
                        exit_bar_idx=curr_k,
                        exit_time=exit_time,
                        exit_price=exit_price,
                        raw_exit_price=raw_exit,
                        shares=shares,
                        stop_loss=sl,
                        take_profit=tp,
                        risk_r_usd=risk_usd,
                        gross_pnl=gross_pnl,
                        net_pnl=net_pnl,
                        slippage_cost=slip_cost,
                        commission_cost=comm_cost,
                        pnl_r=pnl_r,
                        exit_reason=exit_reason,
                        bars_held=curr_k - entry_idx + 1,
                    )
                )
                trade_id += 1
                equity += net_pnl
                equity_curve.append(equity)
                i = curr_k + 1
            else:
                i += 1

        metrics = bt._calculate_metrics(symbol, timeframe, cost_model.name, bars, trades, equity_curve)
        return metrics, trades
