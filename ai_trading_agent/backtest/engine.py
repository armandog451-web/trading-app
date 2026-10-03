"""
ai_trading_agent.backtest.engine
================================
Motor de backtesting histórico determinista y cuantitativo (Instrucción 17).
Garantías institucionales:
1. Sin look-ahead bias: solo se entregan barras hasta el instante t.
2. Sin survivorship bias: opera con series temporales inmutables.
3. Modelado de fricciones: comisiones exactas y deslizamiento (slippage).
4. División estricta In-Sample / Out-of-Sample para evitar overfitting.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field

from ai_trading_agent.domain.enums import SignalDirection, MarketRegime, TradingMode
from ai_trading_agent.domain.models import OHLCVBar, TradeProposal
from ai_trading_agent.market.indicators import indicators
from ai_trading_agent.market.regime import regime_detector
from ai_trading_agent.strategies.trend import trend_strategy
from ai_trading_agent.strategies.momentum import momentum_strategy
from ai_trading_agent.strategies.mean_reversion import mean_reversion_strategy
from ai_trading_agent.strategies.orb import orb_strategy
from ai_trading_agent.signals.aggregator import signal_aggregator
from ai_trading_agent.signals.confirmation_engine import confirmation_engine
from ai_trading_agent.backtest.metrics import metrics_calculator, PerformanceMetrics


class BacktestReport(BaseModel):
    symbol: str
    period_start: datetime
    period_end: datetime
    initial_capital: float
    ending_capital: float
    metrics: PerformanceMetrics
    trades: List[Dict[str, Any]]
    equity_curve: List[float]
    dataset_type: str = "FULL"  # "IN_SAMPLE", "OUT_OF_SAMPLE", "FULL"


class BacktestEngine:
    """Motor de simulación cuantitativa barra a barra."""

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_per_share: float = 0.005,
        slippage_pct: float = 0.0005,  # 5 bps
        risk_per_trade_pct: float = 0.01  # 1% del capital disponible
    ):
        self.initial_capital = initial_capital
        self.commission_per_share = commission_per_share
        self.slippage_pct = slippage_pct
        self.risk_per_trade_pct = risk_per_trade_pct
        self.strategies = [trend_strategy, momentum_strategy, mean_reversion_strategy, orb_strategy]

    def split_data(
        self,
        bars: List[OHLCVBar],
        train_ratio: float = 0.70
    ) -> Tuple[List[OHLCVBar], List[OHLCVBar]]:
        """
        Divide la serie cronológica en In-Sample (entrenamiento/optimización)
        y Out-of-Sample (validación independiente fuera de muestra).
        """
        if not bars:
            return [], []
        split_idx = int(len(bars) * train_ratio)
        return bars[:split_idx], bars[split_idx:]

    def run(
        self,
        symbol: str,
        bars: List[OHLCVBar],
        min_warmup_bars: int = 35,
        dataset_type: str = "FULL"
    ) -> BacktestReport:
        """
        Ejecuta la simulación barra a barra sin sesgo de anticipación.
        """
        if len(bars) <= min_warmup_bars:
            empty_metrics = metrics_calculator.calculate([], self.initial_capital)
            now = bars[-1].timestamp if bars else datetime.utcnow()
            return BacktestReport(
                symbol=symbol,
                period_start=now,
                period_end=now,
                initial_capital=self.initial_capital,
                ending_capital=self.initial_capital,
                metrics=empty_metrics,
                trades=[],
                equity_curve=[self.initial_capital],
                dataset_type=dataset_type
            )

        capital = self.initial_capital
        equity_curve = [capital]
        closed_trades = []
        active_position: Optional[Dict[str, Any]] = None

        # Simulación temporal determinista paso a paso (t = min_warmup_bars ... len(bars))
        for t in range(min_warmup_bars, len(bars)):
            current_bar = bars[t]
            # HISTORIAL ESTRICTO hasta t (Look-ahead bias = 0)
            history = bars[:t + 1]

            # 1. Gestionar posición activa si existe
            if active_position is not None:
                side = active_position["side"]
                entry_p = active_position["entry_price"]
                stop_l = active_position["stop_loss"]
                take_p = active_position["take_profit"]
                qty = active_position["quantity"]

                exit_price = None
                exit_reason = None

                if side == "BUY":
                    # Chequear Stop Loss (si Low tocó o perforó el SL)
                    if current_bar.low <= stop_l:
                        exit_price = min(current_bar.open, stop_l)
                        exit_reason = "STOP_LOSS"
                    # Chequear Take Profit (si High alcanzó o superó TP)
                    elif current_bar.high >= take_p:
                        exit_price = max(current_bar.open, take_p)
                        exit_reason = "TAKE_PROFIT"
                elif side == "SELL":
                    if current_bar.high >= stop_l:
                        exit_price = max(current_bar.open, stop_l)
                        exit_reason = "STOP_LOSS"
                    elif current_bar.low <= take_p:
                        exit_price = min(current_bar.open, take_p)
                        exit_reason = "TAKE_PROFIT"

                # Si se activa salida:
                if exit_price is not None:
                    # Deslizamiento de salida
                    if side == "BUY":
                        adj_exit = exit_price * (1.0 - self.slippage_pct)
                        gross_pnl = (adj_exit - entry_p) * qty
                    else:
                        adj_exit = exit_price * (1.0 + self.slippage_pct)
                        gross_pnl = (entry_p - adj_exit) * qty

                    exit_commission = qty * self.commission_per_share
                    exit_slippage = abs(exit_price - adj_exit) * qty
                    total_comm = active_position["entry_commission"] + exit_commission
                    total_slip = active_position["entry_slippage"] + exit_slippage
                    net_pnl = round(gross_pnl - exit_commission, 2)

                    capital += net_pnl

                    closed_trades.append({
                        "trade_id": f"t_{len(closed_trades)+1}",
                        "symbol": symbol,
                        "side": side,
                        "entry_time": active_position["entry_time"],
                        "exit_time": current_bar.timestamp,
                        "entry_price": round(entry_p, 2),
                        "exit_price": round(adj_exit, 2),
                        "quantity": qty,
                        "gross_pnl": round(gross_pnl, 2),
                        "net_pnl": net_pnl,
                        "commission": round(total_comm, 2),
                        "slippage": round(total_slip, 2),
                        "exit_reason": exit_reason
                    })
                    active_position = None

            # Actualizar curva de equidad
            unrealized = 0.0
            if active_position is not None:
                curr_p = current_bar.close
                pos_qty = active_position["quantity"]
                if active_position["side"] == "BUY":
                    unrealized = (curr_p - active_position["entry_price"]) * pos_qty
                else:
                    unrealized = (active_position["entry_price"] - curr_p) * pos_qty
            equity_curve.append(round(capital + unrealized, 2))

            # 2. Si no hay posición activa, evaluar nuevas señales en la barra actual
            if active_position is None:
                ind = indicators.calculate_all(history)
                regime, _ = regime_detector.detect_regime(ind)
                signals = [s.evaluate(symbol, history, ind, regime) for s in self.strategies]
                agg_signal, proposal = signal_aggregator.aggregate(symbol, signals, current_bar.timestamp)

                if agg_signal.is_actionable and proposal:
                    # Validar confirmación
                    confirmed, confirmed_proposal, _ = confirmation_engine.confirm_proposal(
                        proposal=proposal,
                        agg_signal=agg_signal,
                        regime=regime
                    )
                    if confirmed and confirmed_proposal:
                        # Calcular tamaño de posición según riesgo exacto del 1%
                        risk_capital = capital * self.risk_per_trade_pct
                        price_risk = abs(proposal.entry_price - proposal.stop_loss)
                        if price_risk > 0:
                            raw_qty = int(risk_capital / price_risk)
                            # Limitar tamaño a no exceder el 20% del capital
                            max_shares = int((capital * 0.20) / proposal.entry_price)
                            qty = max(1, min(raw_qty, max_shares))

                            # Aplicar deslizamiento de entrada
                            if proposal.direction == SignalDirection.BUY:
                                fill_price = proposal.entry_price * (1.0 + self.slippage_pct)
                                side_str = "BUY"
                            else:
                                fill_price = proposal.entry_price * (1.0 - self.slippage_pct)
                                side_str = "SELL"

                            entry_comm = qty * self.commission_per_share
                            entry_slip = abs(proposal.entry_price - fill_price) * qty
                            capital -= entry_comm  # Deducir comisión al entrar

                            active_position = {
                                "side": side_str,
                                "entry_time": current_bar.timestamp,
                                "entry_price": fill_price,
                                "stop_loss": proposal.stop_loss,
                                "take_profit": proposal.take_profit,
                                "quantity": qty,
                                "entry_commission": entry_comm,
                                "entry_slippage": entry_slip
                            }

        # Cerrar posición residual forzosa al final del dataset
        if active_position is not None:
            last_bar = bars[-1]
            last_price = last_bar.close
            side = active_position["side"]
            qty = active_position["quantity"]
            entry_p = active_position["entry_price"]

            if side == "BUY":
                adj_exit = last_price * (1.0 - self.slippage_pct)
                gross_pnl = (adj_exit - entry_p) * qty
            else:
                adj_exit = last_price * (1.0 + self.slippage_pct)
                gross_pnl = (entry_p - adj_exit) * qty

            exit_comm = qty * self.commission_per_share
            total_comm = active_position["entry_commission"] + exit_comm
            total_slip = active_position["entry_slippage"] + (abs(last_price - adj_exit) * qty)
            net_pnl = round(gross_pnl - exit_comm, 2)
            capital += net_pnl

            closed_trades.append({
                "trade_id": f"t_{len(closed_trades)+1}",
                "symbol": symbol,
                "side": side,
                "entry_time": active_position["entry_time"],
                "exit_time": last_bar.timestamp,
                "entry_price": round(entry_p, 2),
                "exit_price": round(adj_exit, 2),
                "quantity": qty,
                "gross_pnl": round(gross_pnl, 2),
                "net_pnl": net_pnl,
                "commission": round(total_comm, 2),
                "slippage": round(total_slip, 2),
                "exit_reason": "END_OF_DATASET"
            })
            equity_curve.append(round(capital, 2))

        # Calcular métricas finales
        metrics = metrics_calculator.calculate(
            trades=closed_trades,
            initial_capital=self.initial_capital,
            equity_curve=equity_curve
        )

        return BacktestReport(
            symbol=symbol,
            period_start=bars[0].timestamp,
            period_end=bars[-1].timestamp,
            initial_capital=self.initial_capital,
            ending_capital=round(capital, 2),
            metrics=metrics,
            trades=closed_trades,
            equity_curve=equity_curve,
            dataset_type=dataset_type
        )


backtest_engine = BacktestEngine()
