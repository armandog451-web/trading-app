"""
ai_trading_agent.execution.brokers.moomoo_adapter
=================================================
Adaptador de integración para Moomoo OpenD (Futu API).
Conecta con el Gateway local (127.0.0.1:11111) en cuenta Paper/Simulate.
Soporta fallback elegante si OpenD no está iniciado en la máquina local.
"""

import socket
import logging
from typing import Dict, Any, List
from datetime import datetime

from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.models import PaperOrder
from ai_trading_agent.domain.enums import OrderStatus
from ai_trading_agent.execution.brokers.base import BaseBrokerAdapter

logger = logging.getLogger(__name__)


def _is_port_listening(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class MoomooBrokerAdapter(BaseBrokerAdapter):
    """Adaptador institucional para Moomoo OpenD."""

    def __init__(self):
        self.host = settings.MOOMOO_HOST
        self.port = settings.MOOMOO_PORT
        self.acc_id = settings.MOOMOO_ACC_ID
        self._sim_cash = 100000.0
        self._sim_equity = 100000.0
        self._sim_positions = []

    @property
    def name(self) -> str:
        return "Moomoo OpenD (US Paper)"

    def is_connected(self) -> bool:
        return _is_port_listening(self.host, self.port)

    def get_account_summary(self) -> Dict[str, Any]:
        """Consulta balance en Moomoo OpenD en vivo o retorna estado de simulación."""
        if self.is_connected():
            try:
                import moomoo as ft
                trd_ctx = ft.OpenSecTradeContext(
                    filter_trdmarket=ft.TrdMarket.US,
                    host=self.host,
                    port=self.port
                )
                ret, funds = trd_ctx.accinfo_query(
                    trd_env=ft.TrdEnv.SIMULATE,
                    acc_id=self.acc_id
                )
                trd_ctx.close()
                if ret == 0 and not funds.empty:
                    row = funds.iloc[0]
                    return {
                        "broker": self.name,
                        "account_id": self.acc_id,
                        "status": f"Conectado en Vivo ({self.host}:{self.port})",
                        "connected": True,
                        "cash": float(row.get("cash", 0.0)),
                        "equity": float(row.get("total_assets", 0.0)),
                        "buying_power": float(row.get("power", 0.0)),
                        "realized_pnl": float(row.get("realized_pl", 0.0))
                    }
            except Exception as e:
                logger.warning(f"Error consultando cuenta en Moomoo OpenD: {e}")

        # Fallback a cuenta simulada si OpenD no está activo en segundo plano
        return {
            "broker": self.name,
            "account_id": self.acc_id,
            "status": "Modo Simulación (OpenD Gateway no detectado en puerto 11111)",
            "connected": False,
            "cash": self._sim_cash,
            "equity": self._sim_equity,
            "buying_power": self._sim_cash * 2.0,
            "realized_pnl": 0.0
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        """Consulta posiciones abiertas en Moomoo OpenD."""
        if self.is_connected():
            try:
                import moomoo as ft
                trd_ctx = ft.OpenSecTradeContext(
                    filter_trdmarket=ft.TrdMarket.US,
                    host=self.host,
                    port=self.port
                )
                ret, pos = trd_ctx.position_list_query(
                    trd_env=ft.TrdEnv.SIMULATE,
                    acc_id=self.acc_id
                )
                trd_ctx.close()
                if ret == 0 and not pos.empty:
                    positions = []
                    for _, p in pos.iterrows():
                        positions.append({
                            "symbol": str(p["code"]).replace("US.", ""),
                            "quantity": int(p["qty"]),
                            "side": "BUY" if p["qty"] > 0 else "SELL",
                            "avg_entry_price": float(p["cost_price"]),
                            "current_price": float(p["nominal_price"]),
                            "unrealized_pnl": float(p.get("pl_val", 0.0))
                        })
                    return positions
            except Exception as e:
                logger.warning(f"Error consultando posiciones en Moomoo: {e}")

        return self._sim_positions

    def submit_order(self, order: PaperOrder) -> PaperOrder:
        """Simula o ejecuta orden en Paper Trading de Moomoo."""
        if self.is_connected():
            try:
                import moomoo as ft
                trd_ctx = ft.OpenSecTradeContext(
                    filter_trdmarket=ft.TrdMarket.US,
                    host=self.host,
                    port=self.port
                )
                trd_side = ft.TrdSide.BUY if order.side.value == "BUY" else ft.TrdSide.SELL
                ret, data = trd_ctx.place_order(
                    price=order.requested_price,
                    qty=order.quantity,
                    code=f"US.{order.symbol}",
                    trd_side=trd_side,
                    order_type=ft.OrderType.MARKET,
                    trd_env=ft.TrdEnv.SIMULATE,
                    acc_id=self.acc_id
                )
                trd_ctx.close()
                if ret == 0 and not data.empty:
                    moo_order_id = str(data.iloc[0].get("order_id", order.order_id))
                    return order.model_copy(update={
                        "order_id": moo_order_id,
                        "status": OrderStatus.FILLED,
                        "filled_at": datetime.utcnow(),
                        "avg_fill_price": order.requested_price
                    })
            except Exception as e:
                logger.warning(f"Error enviando orden a Moomoo: {e}")

        # Ejecución interna simulada
        return order.model_copy(update={
            "status": OrderStatus.FILLED,
            "filled_at": datetime.utcnow(),
            "avg_fill_price": order.requested_price
        })


moomoo_adapter = MoomooBrokerAdapter()
