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


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or str(val).strip().upper() in ("N/A", "NAN", "NONE", ""):
            return default
        return float(val)
    except Exception:
        return default


class MoomooBrokerAdapter(BaseBrokerAdapter):
    """Adaptador institucional para Moomoo OpenD."""

    def __init__(self):
        self.host = settings.MOOMOO_HOST
        self.port = settings.MOOMOO_PORT
        self.acc_id = settings.MOOMOO_ACC_ID
        self._sim_cash = settings.PAPER_INITIAL_CAPITAL
        self._sim_equity = settings.PAPER_INITIAL_CAPITAL
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
                    cash_val = _safe_float(row.get("cash"), self._sim_cash)
                    equity_val = _safe_float(row.get("total_assets"), self._sim_equity)
                    power_val = _safe_float(row.get("power"), cash_val * 2.0)
                    realized_val = _safe_float(row.get("realized_pl"), 0.0)
                    return {
                        "broker": self.name,
                        "account_id": self.acc_id,
                        "status": f"Conectado en Vivo ({self.host}:{self.port})",
                        "connected": True,
                        "cash": cash_val,
                        "equity": equity_val,
                        "buying_power": power_val,
                        "realized_pnl": realized_val
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

    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Consulta órdenes en Moomoo OpenD (SIMULATE).
        REGLA OBLIGATORIA (FAIL_CLOSED): Si no puede verificarse la conexión o falla el Gateway,
        DEBE lanzar excepción y NUNCA devolver una lista vacía para evitar órdenes duplicadas.
        """
        if not self.is_connected():
            raise ConnectionError(
                f"Moomoo OpenD no está escuchando en {self.host}:{self.port}. "
                f"Bloqueando consulta de órdenes para prevenir falsos vacíos."
            )

        try:
            import moomoo as ft
            trd_ctx = ft.OpenSecTradeContext(
                filter_trdmarket=ft.TrdMarket.US,
                host=self.host,
                port=self.port
            )
            ret, orders_df = trd_ctx.order_list_query(
                trd_env=ft.TrdEnv.SIMULATE,
                acc_id=self.acc_id,
                refresh_cache=True
            )
            trd_ctx.close()
            if ret != 0:
                raise RuntimeError(f"Error consultando order_list_query en Moomoo: ret={ret}")

            results = []
            if not orders_df.empty:
                status_map = {
                    "FILLED_ALL": "FILLED",
                    "FILLED_PART": "PARTIALLY_FILLED",
                    "SUBMITTED": "SUBMITTED",
                    "WAITING_SUBMIT": "SUBMITTED",
                    "CANCELLED_ALL": "CANCELLED",
                    "CANCELLED_PART": "CANCELLED",
                    "FAILED": "REJECTED",
                    "SUBMIT_FAILED": "REJECTED"
                }
                for _, row in orders_df.iterrows():
                    results.append({
                        "order_id": str(row.get("order_id")),
                        "symbol": str(row.get("code", "")).replace("US.", ""),
                        "side": "BUY" if str(row.get("trd_side")) in ("BUY", "1") else "SELL",
                        "quantity": int(row.get("qty", 0)),
                        "dealt_quantity": int(row.get("dealt_qty", 0)),
                        "price": float(row.get("price", 0.0)),
                        "status": status_map.get(str(row.get("order_status")), "UNKNOWN"),
                        "created_at": str(row.get("create_time", "")),
                        "updated_at": str(row.get("updated_time", "")),
                        "account_id": self.acc_id
                    })
            return results
        except Exception as e:
            logger.error(f"Fallo en Moomoo get_orders: {e}")
            raise

    def submit_order(self, order: PaperOrder) -> PaperOrder:
        """Simula o ejecuta orden en Paper Trading de Moomoo."""
        # BARRERA INSTITUCIONAL INFRANQUEABLE DE EJECUCIÓN (Modo CONTROLLED_RECOVERY)
        if getattr(settings, "PAPER_EXECUTION_BARRIER_ACTIVE", True):
            logger.critical("EJECUCIÓN PAPER BLOQUEADA: Barrera institucional activa en MoomooBrokerAdapter.submit_order()")
            raise PermissionError("EJECUCIÓN PAPER BLOQUEADA POR BARRERA INSTITUCIONAL: Se prohíbe el envío de órdenes.")

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
