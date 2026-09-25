import logging
from typing import Dict, Any, List
from app.config import settings
from app.core.alpaca_client import alpaca_broker
from app.core.moomoo_client import moomoo_broker

logger = logging.getLogger(__name__)

class BrokerManager:
    """
    Administrador unificado de Brokers.
    Enruta las peticiones de cuenta, posiciones y órdenes al broker activo seleccionado
    (ALPACA, MOOMOO o SIMULATOR).
    """

    def get_active_broker_name(self) -> str:
        return settings.ACTIVE_BROKER.upper()

    def get_active_broker(self):
        active = self.get_active_broker_name()
        if active == "MOOMOO":
            return moomoo_broker
        elif active == "ALPACA":
            return alpaca_broker
        else: # SIMULATOR
            return alpaca_broker  # AlpacaBroker incluye emulador interno completo si no hay credenciales

    async def get_account(self) -> Dict[str, Any]:
        broker = self.get_active_broker()
        acc = await broker.get_account()
        acc["active_broker"] = self.get_active_broker_name()
        return acc

    async def get_positions(self) -> List[Dict[str, Any]]:
        broker = self.get_active_broker()
        return await broker.get_positions()

    async def submit_bracket_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        broker = self.get_active_broker()
        logger.info(f"Enviando orden a través del broker activo [{self.get_active_broker_name()}]: {symbol} {qty} {side}")
        return await broker.submit_bracket_order(
            symbol=symbol,
            qty=qty,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            order_type=order_type
        )

    async def close_all_positions(self) -> Dict[str, Any]:
        broker = self.get_active_broker()
        return await broker.close_all_positions()

    async def get_intraday_bars(self, symbol: str, num_bars: int = 60):
        """Obtiene velas de 1m desde el broker activo (Moomoo o Alpaca)."""
        broker = self.get_active_broker()
        if hasattr(broker, "get_intraday_bars"):
            return await broker.get_intraday_bars(symbol, num_bars)
        return None

broker_manager = BrokerManager()
