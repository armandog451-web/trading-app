"""
ai_trading_agent.execution.brokers.alpaca_adapter
=================================================
Adaptador de integración para Alpaca Markets Paper Trading REST API.
Utiliza httpx para comunicación directa, rápida y asíncrona sin librerías externas pesadas.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
import httpx

from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.models import PaperOrder
from ai_trading_agent.domain.enums import OrderStatus
from ai_trading_agent.execution.brokers.base import BaseBrokerAdapter

logger = logging.getLogger(__name__)


class AlpacaBrokerAdapter(BaseBrokerAdapter):
    """Adaptador para Alpaca Paper Trading."""

    def __init__(self):
        self.api_key = settings.ALPACA_API_KEY
        self.secret_key = settings.ALPACA_SECRET_KEY
        self.base_url = settings.ALPACA_BASE_URL
        self._sim_cash = 100000.0
        self._sim_equity = 100000.0
        self._sim_positions = []

    @property
    def name(self) -> str:
        return "Alpaca Markets (Paper API)"

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key and self.secret_key and len(self.api_key) > 5 and "<YOUR_" not in self.api_key)

    def _headers(self) -> dict:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        }

    def get_account_summary(self) -> Dict[str, Any]:
        """Consulta balance de cuenta en Alpaca Paper."""
        if self.has_credentials:
            try:
                url = f"{self.base_url}/v2/account"
                with httpx.Client(timeout=6.0) as client:
                    resp = client.get(url, headers=self._headers())
                    if resp.status_code == 200:
                        data = resp.json()
                        return {
                            "broker": self.name,
                            "account_id": data.get("id", "N/A"),
                            "status": "Conectado en Vivo (Alpaca API Paper)",
                            "connected": True,
                            "cash": float(data.get("cash", 0.0)),
                            "equity": float(data.get("equity", 0.0)),
                            "buying_power": float(data.get("buying_power", 0.0)),
                            "realized_pnl": 0.0
                        }
            except Exception as e:
                logger.warning(f"Error consultando cuenta en Alpaca: {e}")

        return {
            "broker": self.name,
            "account_id": "SIM_ALPACA_1",
            "status": "Modo Simulación (Credenciales de Alpaca pendientes de configurar en .env)",
            "connected": False,
            "cash": self._sim_cash,
            "equity": self._sim_equity,
            "buying_power": self._sim_cash * 2.0,
            "realized_pnl": 0.0
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        """Consulta posiciones abiertas en Alpaca."""
        if self.has_credentials:
            try:
                url = f"{self.base_url}/v2/positions"
                with httpx.Client(timeout=6.0) as client:
                    resp = client.get(url, headers=self._headers())
                    if resp.status_code == 200:
                        data = resp.json()
                        positions = []
                        for p in data:
                            positions.append({
                                "symbol": p.get("symbol"),
                                "quantity": int(float(p.get("qty", 0))),
                                "side": p.get("side", "long").upper(),
                                "avg_entry_price": float(p.get("avg_entry_price", 0.0)),
                                "current_price": float(p.get("current_price", 0.0)),
                                "unrealized_pnl": float(p.get("unrealized_pl", 0.0))
                            })
                        return positions
            except Exception as e:
                logger.warning(f"Error consultando posiciones en Alpaca: {e}")

        return self._sim_positions

    def submit_order(self, order: PaperOrder) -> PaperOrder:
        """Envía una orden al entorno Paper de Alpaca."""
        if self.has_credentials:
            try:
                url = f"{self.base_url}/v2/orders"
                payload = {
                    "symbol": order.symbol,
                    "qty": order.quantity,
                    "side": order.side.value.lower(),
                    "type": "market",
                    "time_in_force": "day"
                }
                with httpx.Client(timeout=6.0) as client:
                    resp = client.post(url, json=payload, headers=self._headers())
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        alp_order_id = data.get("id", order.order_id)
                        return order.model_copy(update={
                            "order_id": alp_order_id,
                            "status": OrderStatus.FILLED,
                            "filled_at": datetime.utcnow(),
                            "avg_fill_price": order.requested_price
                        })
            except Exception as e:
                logger.warning(f"Error enviando orden a Alpaca: {e}")

        # Ejecución interna simulada
        return order.model_copy(update={
            "status": OrderStatus.FILLED,
            "filled_at": datetime.utcnow(),
            "avg_fill_price": order.requested_price
        })


alpaca_adapter = AlpacaBrokerAdapter()
