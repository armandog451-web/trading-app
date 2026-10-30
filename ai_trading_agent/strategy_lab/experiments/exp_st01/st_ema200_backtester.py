"""
ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_backtester
======================================================================
Motor de Backtesting Causal con Resolución Conservadora y Estrés de Costes para ST_EMA200_V1.

Características:
1. Entrada Causal T -> T+1 al precio Open con deslizamiento.
2. Resolución Conservadora de Colisiones Intra-barra (Peor caso: SL se ejecuta antes que TP).
3. Modelo de Costes Multitier (1x Base, 2x Moderado, 3x Severo).
4. Sizing basado en riesgo fijo ($250 por operación sobre $100,000 de capital base).
5. Métricas cuantitativas completas: Net PnL, Profit Factor, Expectancy R, Sharpe, Drawdown, Recovery Factor.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import math
import numpy as np

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_strategy import (
    StEma200Strategy,
    StrategySignalST,
    TradeDirection,
)


@dataclass
class CostModelST:
    name: str = "1x_Base"
    slippage_bps: float = 2.0  # 2 bps = 0.0002
    commission_per_share: float = 0.005  # $0.005 / acción

    @property
    def slippage_rate(self) -> float:
        return self.slippage_bps / 10000.0


COST_TIERS = {
    "1x": CostModelST(name="1x_Base", slippage_bps=2.0, commission_per_share=0.005),
    "2x": CostModelST(name="2x_Moderate", slippage_bps=5.0, commission_per_share=0.010),
    "3x": CostModelST(name="3x_Severe", slippage_bps=10.0, commission_per_share=0.015),
}


@dataclass
class TradeRecordST:
    trade_id: int
    symbol: str
    direction: TradeDirection
    entry_bar_idx: int
    entry_time: datetime
    entry_price: float  # precio fill real con slippage
    raw_entry_price: float  # open original
    exit_bar_idx: int
    exit_time: datetime
    exit_price: float  # precio fill real con slippage
    raw_exit_price: float
    shares: int
    stop_loss: float
    take_profit: float
    risk_r_usd: float  # riesgo inicial en $ (SL dist * shares)
    gross_pnl: float
    net_pnl: float
    slippage_cost: float
    commission_cost: float
    pnl_r: float  # Net PnL / risk_r_usd
    exit_reason: str  # "TP", "SL", "COLLISION_SL", "END_OF_DATA"
    bars_held: int


@dataclass
class BacktestMetricsST:
    symbol: str
    timeframe: str
    cost_tier: str
    total_trades: int
    win_trades: int
    loss_trades: int
    win_rate: float
    gross_pnl: float
    net_pnl: float
    total_commissions: float
    total_slippage: float
    total_costs: float
    profit_factor: float
    payoff_ratio: float
    expectancy_usd: float
    expectancy_r: float
    max_drawdown_usd: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    recovery_factor: float
    avg_bars_held: float
    start_date: str
    end_date: str
    data_points: int
    status: str = "VALID"  # "VALID" o "INSUFFICIENT_DATA"


class StEma200Backtester:
    """Simulador de ejecución y backtesting para ST_EMA200_V1."""

    def __init__(
        self,
        strategy: StEma200Strategy,
        initial_equity: float = 100000.0,
        risk_per_trade: float = 250.0,
        cost_model: Optional[CostModelST] = None,
    ):
        self.strategy = strategy
        self.initial_equity = initial_equity
        self.risk_per_trade = risk_per_trade
        self.cost_model = cost_model or COST_TIERS["1x"]

    def run(
        self,
        symbol: str,
        timeframe: str,
        bars: List[OHLCVBar],
        cost_tier_override: Optional[CostModelST] = None,
    ) -> Tuple[BacktestMetricsST, List[TradeRecordST]]:
        cost_model = cost_tier_override or self.cost_model

        if len(bars) < self.strategy.ema_period + 20:
            empty_metrics = BacktestMetricsST(
                symbol=symbol,
                timeframe=timeframe,
                cost_tier=cost_model.name,
                total_trades=0,
                win_trades=0,
                loss_trades=0,
                win_rate=0.0,
                gross_pnl=0.0,
                net_pnl=0.0,
                total_commissions=0.0,
                total_slippage=0.0,
                total_costs=0.0,
                profit_factor=0.0,
                payoff_ratio=0.0,
                expectancy_usd=0.0,
                expectancy_r=0.0,
                max_drawdown_usd=0.0,
                max_drawdown_pct=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                recovery_factor=0.0,
                avg_bars_held=0.0,
                start_date=bars[0].timestamp.strftime("%Y-%m-%d") if bars else "N/A",
                end_date=bars[-1].timestamp.strftime("%Y-%m-%d") if bars else "N/A",
                data_points=len(bars),
                status="INSUFFICIENT_DATA",
            )
            return empty_metrics, []

        signals = self.strategy.generate_signals(symbol, bars)
        signal_map: Dict[int, StrategySignalST] = {sig.bar_index: sig for sig in signals}

        trades: List[TradeRecordST] = []
        equity = self.initial_equity
        equity_curve: List[float] = [equity]

        i = 0
        n_bars = len(bars)
        trade_id = 1

        while i < n_bars - 1:
            if i in signal_map:
                sig = signal_map[i]
                entry_bar_idx = i + 1  # Causal T+1
                entry_bar = bars[entry_bar_idx]
                raw_entry = entry_bar.open

                # Aplicar slippage de entrada
                if sig.direction == TradeDirection.LONG:
                    fill_entry = raw_entry * (1.0 + cost_model.slippage_rate)
                    sl = sig.stop_loss_level
                    sl_dist = fill_entry - sl
                    if sl_dist <= 0.001:
                        i += 1
                        continue
                    # Take profit adaptado al precio de entrada real
                    tp = fill_entry + self.strategy.tp_r_multiple * sl_dist
                else:
                    fill_entry = raw_entry * (1.0 - cost_model.slippage_rate)
                    sl = sig.stop_loss_level
                    sl_dist = sl - fill_entry
                    if sl_dist <= 0.001:
                        i += 1
                        continue
                    tp = fill_entry - self.strategy.tp_r_multiple * sl_dist

                # Position Sizing
                raw_shares = math.floor(self.risk_per_trade / sl_dist)
                max_shares = math.floor((equity * 0.95) / fill_entry)
                shares = max(1, min(raw_shares, max_shares))
                risk_usd = shares * sl_dist

                # Simular ciclo de vida de la posición barra a barra
                curr_bar_idx = entry_bar_idx
                closed = False
                exit_price = 0.0
                raw_exit = 0.0
                exit_time = entry_bar.timestamp
                exit_reason = ""

                while curr_bar_idx < n_bars and not closed:
                    bar_k = bars[curr_bar_idx]

                    if sig.direction == TradeDirection.LONG:
                        hit_sl = bar_k.low <= sl
                        hit_tp = bar_k.high >= tp

                        if hit_sl and hit_tp:
                            # Resolución Conservadora Anti-Lookahead: SL gana colisión
                            raw_exit = min(bar_k.open, sl)
                            exit_price = raw_exit * (1.0 - cost_model.slippage_rate)
                            exit_time = bar_k.timestamp
                            exit_reason = "COLLISION_SL"
                            closed = True
                        elif hit_sl:
                            raw_exit = min(bar_k.open, sl)
                            exit_price = raw_exit * (1.0 - cost_model.slippage_rate)
                            exit_time = bar_k.timestamp
                            exit_reason = "SL"
                            closed = True
                        elif hit_tp:
                            raw_exit = max(bar_k.open, tp) if bar_k.open >= tp else tp
                            exit_price = raw_exit * (1.0 - cost_model.slippage_rate)
                            exit_time = bar_k.timestamp
                            exit_reason = "TP"
                            closed = True

                    else:  # SHORT
                        hit_sl = bar_k.high >= sl
                        hit_tp = bar_k.low <= tp

                        if hit_sl and hit_tp:
                            # Resolución Conservadora: SL gana colisión
                            raw_exit = max(bar_k.open, sl)
                            exit_price = raw_exit * (1.0 + cost_model.slippage_rate)
                            exit_time = bar_k.timestamp
                            exit_reason = "COLLISION_SL"
                            closed = True
                        elif hit_sl:
                            raw_exit = max(bar_k.open, sl)
                            exit_price = raw_exit * (1.0 + cost_model.slippage_rate)
                            exit_time = bar_k.timestamp
                            exit_reason = "SL"
                            closed = True
                        elif hit_tp:
                            raw_exit = min(bar_k.open, tp) if bar_k.open <= tp else tp
                            exit_price = raw_exit * (1.0 + cost_model.slippage_rate)
                            exit_time = bar_k.timestamp
                            exit_reason = "TP"
                            closed = True

                    if not closed:
                        if curr_bar_idx == n_bars - 1:
                            # Cierre forzado por fin de datos al cierre
                            raw_exit = bar_k.close
                            if sig.direction == TradeDirection.LONG:
                                exit_price = raw_exit * (1.0 - cost_model.slippage_rate)
                            else:
                                exit_price = raw_exit * (1.0 + cost_model.slippage_rate)
                            exit_time = bar_k.timestamp
                            exit_reason = "END_OF_DATA"
                            closed = True
                        else:
                            curr_bar_idx += 1

                # Contabilidad y costes
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
                bars_held = curr_bar_idx - entry_bar_idx + 1

                tr_rec = TradeRecordST(
                    trade_id=trade_id,
                    symbol=symbol,
                    direction=sig.direction,
                    entry_bar_idx=entry_bar_idx,
                    entry_time=entry_bar.timestamp,
                    entry_price=fill_entry,
                    raw_entry_price=raw_entry,
                    exit_bar_idx=curr_bar_idx,
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
                    bars_held=bars_held,
                )
                trades.append(tr_rec)
                trade_id += 1

                equity += net_pnl
                equity_curve.append(equity)

                # Avanzar el puntero hasta después de la barra de salida
                i = curr_bar_idx + 1
            else:
                i += 1

        metrics = self._calculate_metrics(symbol, timeframe, cost_model.name, bars, trades, equity_curve)
        return metrics, trades

    def _calculate_metrics(
        self,
        symbol: str,
        timeframe: str,
        cost_tier_name: str,
        bars: List[OHLCVBar],
        trades: List[TradeRecordST],
        equity_curve: List[float],
    ) -> BacktestMetricsST:
        total = len(trades)
        start_date = bars[0].timestamp.strftime("%Y-%m-%d") if bars else "N/A"
        end_date = bars[-1].timestamp.strftime("%Y-%m-%d") if bars else "N/A"

        if total == 0:
            return BacktestMetricsST(
                symbol=symbol,
                timeframe=timeframe,
                cost_tier=cost_tier_name,
                total_trades=0,
                win_trades=0,
                loss_trades=0,
                win_rate=0.0,
                gross_pnl=0.0,
                net_pnl=0.0,
                total_commissions=0.0,
                total_slippage=0.0,
                total_costs=0.0,
                profit_factor=0.0,
                payoff_ratio=0.0,
                expectancy_usd=0.0,
                expectancy_r=0.0,
                max_drawdown_usd=0.0,
                max_drawdown_pct=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                recovery_factor=0.0,
                avg_bars_held=0.0,
                start_date=start_date,
                end_date=end_date,
                data_points=len(bars),
                status="INSUFFICIENT_DATA" if total < 5 else "VALID",
            )

        wins = [t for t in trades if t.net_pnl > 0]
        losses = [t for t in trades if t.net_pnl <= 0]
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total) * 100.0

        gross_pnl = sum(t.gross_pnl for t in trades)
        net_pnl = sum(t.net_pnl for t in trades)
        total_comm = sum(t.commission_cost for t in trades)
        total_slip = sum(t.slippage_cost for t in trades)
        total_costs = total_comm + total_slip

        gross_win = sum(t.net_pnl for t in wins)
        gross_loss = abs(sum(t.net_pnl for t in losses))

        if gross_loss > 0:
            profit_factor = gross_win / gross_loss
        else:
            profit_factor = 999.0 if gross_win > 0 else 0.0

        avg_win = (gross_win / win_count) if win_count > 0 else 0.0
        avg_loss = (gross_loss / loss_count) if loss_count > 0 else 0.0
        payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0

        expectancy_usd = net_pnl / total
        expectancy_r = sum(t.pnl_r for t in trades) / total
        avg_bars = sum(t.bars_held for t in trades) / total

        # Drawdown
        peak = equity_curve[0]
        max_dd_usd = 0.0
        max_dd_pct = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd_usd = peak - eq
            dd_pct = (dd_usd / peak) * 100.0 if peak > 0 else 0.0
            if dd_usd > max_dd_usd:
                max_dd_usd = dd_usd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        # Sharpe & Sortino (normalizados a trades / períodos)
        returns = [t.net_pnl / self.initial_equity for t in trades]
        mean_ret = np.mean(returns) if returns else 0.0
        std_ret = np.std(returns) if len(returns) > 1 else 0.0
        downside_returns = [r for r in returns if r < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 1 else (std_ret if std_ret > 0 else 1.0)

        # Anualización estimada basada en trades por año
        # 252 días bursátiles / año
        sharpe = (mean_ret / std_ret * math.sqrt(min(total, 50))) if std_ret > 1e-6 else 0.0
        sortino = (mean_ret / downside_std * math.sqrt(min(total, 50))) if downside_std > 1e-6 else 0.0
        recovery = (net_pnl / max_dd_usd) if max_dd_usd > 1.0 else 0.0

        status = "VALID" if total >= 15 else "INSUFFICIENT_DATA"

        return BacktestMetricsST(
            symbol=symbol,
            timeframe=timeframe,
            cost_tier=cost_tier_name,
            total_trades=total,
            win_trades=win_count,
            loss_trades=loss_count,
            win_rate=win_rate,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            total_commissions=total_comm,
            total_slippage=total_slip,
            total_costs=total_costs,
            profit_factor=profit_factor,
            payoff_ratio=payoff_ratio,
            expectancy_usd=expectancy_usd,
            expectancy_r=expectancy_r,
            max_drawdown_usd=max_dd_usd,
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            recovery_factor=recovery,
            avg_bars_held=avg_bars,
            start_date=start_date,
            end_date=end_date,
            data_points=len(bars),
            status=status,
        )
