"""
ai_trading_agent.execution.brokers.unified_manager
=================================================
Enrutador y gestor de brokers unificado para AI Trading Agent 1.0 (SuperRobot).
Permite alternar entre Moomoo OpenD, Alpaca Markets y Paper Broker interno.
"""

import logging
from typing import Dict, Any, List
from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.models import PaperOrder
from ai_trading_agent.execution.paper_broker import paper_broker
from ai_trading_agent.execution.brokers.moomoo_adapter import moomoo_adapter
from ai_trading_agent.execution.brokers.alpaca_adapter import alpaca_adapter

logger = logging.getLogger(__name__)


class UnifiedBrokerManager:
    """Gestor unificado que conmuta dinámicamente entre Moomoo, Alpaca y Paper."""

    def __init__(self):
        self.active_broker_name = settings.ACTIVE_BROKER.lower()

    def set_active_broker(self, broker_name: str) -> str:
        """Cambia el broker activo ('moomoo', 'alpaca', 'paper')."""
        b = broker_name.lower().strip()
        if b in ("moomoo", "alpaca", "paper"):
            self.active_broker_name = b
            settings.ACTIVE_BROKER = b
            return self.active_broker_name
        return self.active_broker_name

    @property
    def current_adapter(self):
        if self.active_broker_name == "moomoo":
            return moomoo_adapter
        elif self.active_broker_name == "alpaca":
            return alpaca_adapter
        else:
            return paper_broker

    def get_account_summary(self) -> Dict[str, Any]:
        """Obtiene el resumen de cuenta del broker activo."""
        if self.active_broker_name == "moomoo":
            return moomoo_adapter.get_account_summary()
        elif self.active_broker_name == "alpaca":
            return alpaca_adapter.get_account_summary()
        else:
            acc = paper_broker.get_account_summary()
            return {
                "broker": "Paper Broker Interno",
                "status": "Simulación Determinista",
                "connected": True,
                "cash": acc["cash"],
                "equity": acc["equity"],
                "buying_power": acc["buying_power"],
                "realized_pnl": acc["realized_pnl"]
            }

    def get_positions(self) -> List[Dict[str, Any]]:
        """Obtiene las posiciones abiertas del broker activo."""
        if self.active_broker_name == "moomoo":
            return moomoo_adapter.get_positions()
        elif self.active_broker_name == "alpaca":
            return alpaca_adapter.get_positions()
        else:
            return [p.model_dump() for p in paper_broker.get_positions()]

    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Recupera las órdenes del broker activo.
        POLÍTICA FAIL_CLOSED: Si el adaptador no implementa el método o falla,
        propaga la excepción para impedir que un falso vacío permita órdenes duplicadas.
        """
        active = self.current_adapter
        if not hasattr(active, "get_orders"):
            raise NotImplementedError(f"El broker activo '{self.active_broker_name}' no implementa get_orders().")
        return active.get_orders()

    def submit_order(self, order: PaperOrder, mode=None) -> PaperOrder:
        """Envía la orden a través del broker activo respetando el modo operativo."""
        # BARRERA INSTITUCIONAL INFRANQUEABLE DE EJECUCIÓN (Modo CONTROLLED_RECOVERY)
        if getattr(settings, "PAPER_EXECUTION_BARRIER_ACTIVE", True):
            logger.critical("EJECUCIÓN PAPER BLOQUEADA: Barrera institucional activa en UnifiedBrokerManager.submit_order()")
            raise PermissionError("EJECUCIÓN PAPER BLOQUEADA POR BARRERA INSTITUCIONAL: Se prohíbe el envío de órdenes.")

        if self.active_broker_name == "moomoo":
            return moomoo_adapter.submit_order(order)
        elif self.active_broker_name == "alpaca":
            return alpaca_adapter.submit_order(order)
        else:
            return paper_broker.submit_order(order, mode=mode)


unified_broker = UnifiedBrokerManager()
