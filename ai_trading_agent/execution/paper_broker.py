"""
ai_trading_agent.execution.paper_broker
=======================================
Simulador determinista de ejecución Paper Trading (Instrucción 13 y 14).
Aplica deslizamiento (slippage), comisiones y control inviolable de ANALYSIS_ONLY.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.enums import TradingMode, OrderStatus, OrderSide
from ai_trading_agent.domain.models import PaperOrder, Position
from ai_trading_agent.execution.interfaces import BrokerInterface


class PaperBroker(BrokerInterface):
    def __init__(self, initial_capital: float = None):
        self.initial_capital = initial_capital or settings.PAPER_INITIAL_CAPITAL
        self.cash = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, PaperOrder] = {}
        self.slippage_bps = settings.ESTIMATED_SLIPPAGE_BPS
        self.commission_per_share = settings.ESTIMATED_COMMISSION_PER_SHARE

    def get_account_summary(self) -> Dict[str, Any]:
        unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        realized = sum(p.realized_pnl for p in self.positions.values())
        market_val = sum(p.quantity * p.current_price for p in self.positions.values())
        equity = self.cash + market_val

        return {
            "initial_capital": self.initial_capital,
            "cash": round(self.cash, 2),
            "market_value": round(market_val, 2),
            "equity": round(equity, 2),
            "unrealized_pnl": round(unrealized, 2),
            "realized_pnl": round(realized, 2),
            "open_positions_count": len(self.positions)
        }

    def get_positions(self) -> List[Position]:
        return list(self.positions.values())

    def submit_order(self, order: PaperOrder, mode: TradingMode = None) -> PaperOrder:
        """
        Envía una orden al simulador.
        REGLA DE SEGURIDAD CRÍTICA (Instrucción 14):
        En ANALYSIS_ONLY es técnicamente imposible ejecutar órdenes.
        """
        active_mode = mode or settings.TRADING_MODE

        if active_mode == TradingMode.ANALYSIS_ONLY:
            rejected_order = order.model_copy(update={
                "status": OrderStatus.REJECTED
            })
            self.orders[order.order_id] = rejected_order
            raise PermissionError(
                "EJECUCIÓN BLOQUEADA POR DISEÑO: El modo configurado es ANALYSIS_ONLY. "
                "Cualquier intento de enviar órdenes es físicamente rechazado por el core."
            )

        if settings.KILL_SWITCH_ACTIVE:
            rejected_order = order.model_copy(update={
                "status": OrderStatus.REJECTED
            })
            self.orders[order.order_id] = rejected_order
            raise PermissionError("KILL SWITCH ACTIVO: Nuevas órdenes bloqueadas.")

        # Simulación de Deslizamiento (Slippage) y Comisiones
        slippage_mult = self.slippage_bps / 10000.0  # 5 bps = 0.0005
        if order.side == OrderSide.BUY:
            fill_price = round(order.requested_price * (1.0 + slippage_mult), 2)
            slippage_cost = round(fill_price - order.requested_price, 2)
        else:
            fill_price = round(order.requested_price * (1.0 - slippage_mult), 2)
            slippage_cost = round(order.requested_price - fill_price, 2)

        commission = round(order.quantity * self.commission_per_share, 2)
        total_cost = (order.quantity * fill_price) + commission

        if order.side == OrderSide.BUY and total_cost > self.cash:
            rejected_order = order.model_copy(update={
                "status": OrderStatus.REJECTED
            })
            self.orders[order.order_id] = rejected_order
            raise ValueError(f"FONDOS INSUFICIENTES: Costo ${total_cost:,.2f} supera efectivo disponible ${self.cash:,.2f}")

        # Ejecución y Actualización de Cartera
        now = datetime.utcnow()
        filled_order = order.model_copy(update={
            "status": OrderStatus.FILLED,
            "filled_at": now,
            "avg_fill_price": fill_price,
            "commission": commission,
            "slippage": slippage_cost
        })
        self.orders[order.order_id] = filled_order

        if order.side == OrderSide.BUY:
            self.cash -= total_cost
            self.positions[order.symbol] = Position(
                symbol=order.symbol,
                side=OrderSide.BUY,
                quantity=order.quantity,
                avg_entry_price=fill_price,
                current_price=fill_price,
                stop_loss=order.stop_loss or (fill_price * 0.98),
                take_profit=order.take_profit or (fill_price * 1.04),
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                opened_at=now,
                updated_at=now
            )
        else:  # OrderSide.SELL (Cierre o Short)
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                pnl = (fill_price - pos.avg_entry_price) * order.quantity - commission
                self.cash += (order.quantity * fill_price) - commission
                del self.positions[order.symbol]

        return filled_order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders and self.orders[order_id].status == OrderStatus.PENDING:
            self.orders[order_id] = self.orders[order_id].model_copy(update={"status": OrderStatus.CANCELLED})
            return True
        return False


paper_broker = PaperBroker()
