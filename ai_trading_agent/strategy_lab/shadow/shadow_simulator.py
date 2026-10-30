"""
ai_trading_agent.strategy_lab.shadow.shadow_simulator
=====================================================
Simulador de ejecución prospectiva realista (Bloque D).
Principios innegociables:
1. Política temporal causal: Señal en cierre T -> Orden pendiente -> Ejecución en apertura T+1.
2. Cero conexiones o dependencias de brokers.
3. Modelado de costes en 3 escenarios paralelos (1x, 2x, 3x).
4. Modelado de gaps de apertura y deslizamiento adverso real.
5. Control estricto de concurrencia y límites de efectivo disponible.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from .campaign_models import (
    CostScenario,
    ShadowPosition
)


class ShadowExecutionSimulator:
    """
    Simulador de órdenes y ejecución para el entorno Shadow.
    Opera con capital independiente de $100,000 USD y reglas realistas de mercado.
    """

    COST_SPECS = {
        CostScenario.TIER_1X: {"comm_per_share": 0.005, "slip_bps": 5.0, "min_comm": 1.0},
        CostScenario.TIER_2X: {"comm_per_share": 0.010, "slip_bps": 10.0, "min_comm": 2.0},
        CostScenario.TIER_3X: {"comm_per_share": 0.015, "slip_bps": 15.0, "min_comm": 3.0}
    }

    def __init__(
        self,
        strategy_id: str,
        initial_capital_usd: float = 100_000.0,
        risk_budget_per_trade_usd: float = 250.0,
        max_concurrent_positions: int = 2,
        cost_scenario: CostScenario = CostScenario.TIER_1X
    ):
        self.strategy_id = strategy_id
        self.initial_capital_usd = initial_capital_usd
        self.current_cash = initial_capital_usd
        self.portfolio_equity = initial_capital_usd
        self.peak_equity = initial_capital_usd
        self.max_drawdown_usd = 0.0
        self.max_drawdown_pct = 0.0

        self.risk_budget_per_trade_usd = risk_budget_per_trade_usd
        self.max_concurrent_positions = max_concurrent_positions
        self.cost_scenario = cost_scenario
        self.cost_spec = self.COST_SPECS[cost_scenario]

        # Estructuras de posición y órdenes pendientes
        self.open_positions: Dict[str, ShadowPosition] = {}  # symbol -> position
        self.pending_entry_orders: List[Dict[str, Any]] = []  # órdenes para ejecutar en apertura T+1
        self.closed_trades: List[Dict[str, Any]] = []

    def queue_entry_signal(
        self,
        signal_date: str,
        symbol: str,
        signal_close_price: float,
        stop_loss_pct: float,
        profit_target_pct: float,
        max_holding_bars: int,
        reason: str
    ) -> Optional[Dict[str, Any]]:
        """
        Encola una orden condicional tras la señal emitida al cierre de la sesión T.
        La orden se ejecutará al precio de apertura de la siguiente sesión negociable T+1.
        """
        # 1. Comprobar si ya existe posición o orden pendiente en este símbolo
        if symbol in self.open_positions:
            return None
        for po in self.pending_entry_orders:
            if po["symbol"] == symbol:
                return None

        # 2. Comprobar límite de concurrencia
        current_committed_count = len(self.open_positions) + len(self.pending_entry_orders)
        if current_committed_count >= self.max_concurrent_positions:
            return None

        # 3. Estimación inicial de tamaño de posición
        stop_dist_estimate = max(signal_close_price * stop_loss_pct, 1.0)
        shares_estimate = max(10, int(self.risk_budget_per_trade_usd / stop_dist_estimate))

        order = {
            "order_id": f"ORD-{self.strategy_id}-{symbol}-{signal_date}",
            "strategy_id": self.strategy_id,
            "symbol": symbol,
            "signal_date": signal_date,
            "signal_close_price": signal_close_price,
            "stop_loss_pct": stop_loss_pct,
            "profit_target_pct": profit_target_pct,
            "max_holding_bars": max_holding_bars,
            "shares_requested": shares_estimate,
            "reason": reason,
            "status": "PENDING_OPEN_T1"
        }
        self.pending_entry_orders.append(order)
        return order

    def process_session_open_fills(
        self,
        session_date: str,
        open_prices: Dict[str, float]
    ) -> List[Tuple[Dict[str, Any], ShadowPosition]]:
        """
        Ejecuta las órdenes pendientes en la apertura de la sesión T+1.
        Calcula el llenado con slippage y comisiones del tier activo.
        """
        fills = []
        remaining_pending = []

        slip_rate = self.cost_spec["slip_bps"] / 10000.0
        comm_per_share = self.cost_spec["comm_per_share"]
        min_comm = self.cost_spec["min_comm"]

        for order in self.pending_entry_orders:
            sym = order["symbol"]
            if sym not in open_prices:
                remaining_pending.append(order)
                continue

            open_price = open_prices[sym]

            # Recalcular tamaño exacto con el precio de apertura real
            stop_dist = max(open_price * order["stop_loss_pct"], 1.0)
            shares = max(10, int(self.risk_budget_per_trade_usd / stop_dist))

            # Comprobar límite de efectivo disponible
            cost_estimate = shares * open_price
            if cost_estimate > self.current_cash:
                shares = max(10, int(self.current_cash / open_price))
                cost_estimate = shares * open_price
                if shares < 10 or cost_estimate > self.current_cash:
                    # Sin efectivo suficiente para cumplir el lote mínimo
                    continue

            # Calcular llenado de entrada
            entry_fill = open_price * (1.0 + slip_rate)
            slip_usd = (entry_fill - open_price) * shares
            comm_usd = max(shares * comm_per_share, min_comm)
            total_cash_outflow = (entry_fill * shares) + comm_usd

            if total_cash_outflow > self.current_cash:
                continue

            self.current_cash -= total_cash_outflow

            stop_price = round(open_price * (1.0 - order["stop_loss_pct"]), 4)
            target_price = round(open_price * (1.0 + order["profit_target_pct"]), 4)

            pos = ShadowPosition(
                position_id=f"POS-{self.strategy_id}-{sym}-{session_date}",
                campaign_id="FASE_7_4_SHADOW",
                strategy_id=self.strategy_id,
                symbol=sym,
                shares=shares,
                entry_signal_date=order["signal_date"],
                entry_execution_date=session_date,
                entry_open_price=round(open_price, 4),
                entry_fill_price=round(entry_fill, 4),
                stop_loss_price=stop_price,
                profit_target_price=target_price,
                max_holding_bars=order["max_holding_bars"],
                bars_held=0,
                accumulated_slippage_usd=round(slip_usd, 2),
                accumulated_commissions_usd=round(comm_usd, 2),
                current_mark_price=round(open_price, 4),
                unrealized_gross_pnl=0.0,
                unrealized_net_pnl=round(-slip_usd - comm_usd, 2),
                status="OPEN"
            )

            self.open_positions[sym] = pos

            fill_record = {
                "order_id": order["order_id"],
                "position_id": pos.position_id,
                "symbol": sym,
                "execution_date": session_date,
                "market_open_price": round(open_price, 4),
                "fill_price": round(entry_fill, 4),
                "shares": shares,
                "slippage_usd": round(slip_usd, 2),
                "commission_usd": round(comm_usd, 2),
                "action": "BUY_OPEN"
            }
            fills.append((fill_record, pos))

        self.pending_entry_orders = remaining_pending
        self.update_portfolio_mark_to_market(open_prices)
        return fills

    def process_session_close_and_exits(
        self,
        session_date: str,
        bars_by_symbol: Dict[str, Any]
    ) -> List[Tuple[Dict[str, Any], ShadowPosition]]:
        """
        Evalúa las posiciones abiertas al cierre de la sesión T.
        Verifica:
        1. Si se alcanzó el Take Profit intradía (high >= target).
        2. Si se activó el Stop Loss intradía (low <= stop). Si la apertura tuvo gap abajo, llena al peor precio.
        3. Si se agotó el tiempo máximo de mantenimiento (holding >= max_holding).
        Actualiza mark-to-market y genera salidas realizadas.
        """
        closed_events = []
        active_symbols = list(self.open_positions.keys())

        slip_rate = self.cost_spec["slip_bps"] / 10000.0
        comm_per_share = self.cost_spec["comm_per_share"]
        min_comm = self.cost_spec["min_comm"]

        for sym in active_symbols:
            pos = self.open_positions[sym]
            if sym not in bars_by_symbol:
                continue

            bar = bars_by_symbol[sym]
            pos.bars_held += 1
            pos.current_mark_price = bar.close

            # Evaluar condición de salida
            exit_needed = False
            exit_price_mid = bar.close
            exit_reason = ""

            # Modelado de gap adverso en apertura
            if bar.open <= pos.stop_loss_price:
                # Apertura con gap bajo el stop loss -> salida a precio de apertura (gap real)
                exit_needed = True
                exit_price_mid = bar.open
                exit_reason = "STOP_LOSS_GAP_OPEN"
            elif bar.low <= pos.stop_loss_price:
                exit_needed = True
                exit_price_mid = pos.stop_loss_price
                exit_reason = "STOP_LOSS"
            elif bar.high >= pos.profit_target_price:
                exit_needed = True
                exit_price_mid = pos.profit_target_price
                exit_reason = "PROFIT_TARGET"
            elif pos.bars_held >= pos.max_holding_bars:
                exit_needed = True
                exit_price_mid = bar.close
                exit_reason = "TIME_EXIT"

            if exit_needed:
                # Ejecutar salida con fricciones
                exit_fill = exit_price_mid * (1.0 - slip_rate)
                exit_slip_usd = (exit_price_mid - exit_fill) * pos.shares
                exit_comm_usd = max(pos.shares * comm_per_share, min_comm)

                gross_pnl = (exit_price_mid - pos.entry_open_price) * pos.shares
                total_slip = pos.accumulated_slippage_usd + exit_slip_usd
                total_comm = pos.accumulated_commissions_usd + exit_comm_usd
                total_costs = total_slip + total_comm
                net_pnl = gross_pnl - total_costs

                # Restituir efectivo
                proceeds = (exit_fill * pos.shares) - exit_comm_usd
                self.current_cash += proceeds

                pos.status = "CLOSED"
                pos.accumulated_slippage_usd += round(exit_slip_usd, 2)
                pos.accumulated_commissions_usd += round(exit_comm_usd, 2)

                fill_record = {
                    "position_id": pos.position_id,
                    "symbol": sym,
                    "exit_date": session_date,
                    "exit_mid_price": round(exit_price_mid, 4),
                    "exit_fill_price": round(exit_fill, 4),
                    "shares": pos.shares,
                    "true_gross_pnl": round(gross_pnl, 2),
                    "slippage_usd": round(total_slip, 2),
                    "commission_usd": round(total_comm, 2),
                    "total_costs_usd": round(total_costs, 2),
                    "true_net_pnl": round(net_pnl, 2),
                    "exit_reason": exit_reason,
                    "action": "SELL_CLOSE"
                }

                self.closed_trades.append(fill_record)
                closed_events.append((fill_record, pos))
                del self.open_positions[sym]
            else:
                # Actualizar PnL no realizado
                cur_gross = (bar.close - pos.entry_open_price) * pos.shares
                pos.unrealized_gross_pnl = round(cur_gross, 2)
                pos.unrealized_net_pnl = round(cur_gross - pos.accumulated_slippage_usd - pos.accumulated_commissions_usd, 2)

        # Actualizar mark-to-market
        closes = {s: bars_by_symbol[s].close for s in bars_by_symbol}
        self.update_portfolio_mark_to_market(closes)
        return closed_events

    def update_portfolio_mark_to_market(self, prices_by_symbol: Dict[str, float]):
        """Calcula el valor mark-to-market de la cartera, pico de capital y drawdown."""
        positions_market_val = 0.0
        for sym, pos in self.open_positions.items():
            px = prices_by_symbol.get(sym, pos.current_mark_price)
            positions_market_val += pos.shares * px

        self.portfolio_equity = round(self.current_cash + positions_market_val, 2)
        if self.portfolio_equity > self.peak_equity:
            self.peak_equity = self.portfolio_equity

        dd_usd = self.peak_equity - self.portfolio_equity
        dd_pct = (dd_usd / self.peak_equity * 100.0) if self.peak_equity > 0 else 0.0
        if dd_usd > self.max_drawdown_usd:
            self.max_drawdown_usd = round(dd_usd, 2)
        if dd_pct > self.max_drawdown_pct:
            self.max_drawdown_pct = round(dd_pct, 2)

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Calcula métricas agregadas del portafolio en tiempo real."""
        n = len(self.closed_trades)
        net_pnls = [t["true_net_pnl"] for t in self.closed_trades]
        gross_pnls = [t["true_gross_pnl"] for t in self.closed_trades]
        costs = [t["total_costs_usd"] for t in self.closed_trades]

        wins = [p for p in net_pnls if p > 0]
        losses = [abs(p) for p in net_pnls if p <= 0]
        win_rate = (len(wins) / n * 100.0) if n > 0 else 0.0
        pf = (sum(wins) / (sum(losses) + 1e-9)) if sum(losses) > 0 else (999.0 if sum(wins) > 0 else 0.0)
        exp = (sum(net_pnls) / n) if n > 0 else 0.0

        return {
            "strategy_id": self.strategy_id,
            "cost_scenario": self.cost_scenario.value,
            "initial_capital_usd": self.initial_capital_usd,
            "current_cash_usd": round(self.current_cash, 2),
            "portfolio_equity_usd": round(self.portfolio_equity, 2),
            "max_drawdown_usd": self.max_drawdown_usd,
            "max_drawdown_pct": self.max_drawdown_pct,
            "open_positions_count": len(self.open_positions),
            "pending_orders_count": len(self.pending_entry_orders),
            "closed_trades_count": n,
            "win_rate_pct": round(win_rate, 2),
            "sum_true_gross_pnl": round(sum(gross_pnls), 2),
            "sum_costs_usd": round(sum(costs), 2),
            "sum_true_net_pnl": round(sum(net_pnls), 2),
            "net_profit_factor": round(pf, 2),
            "expectancy_usd": round(exp, 2)
        }
