"""
ai_trading_agent.execution.interfaces
====================================
Contrato formal para brokers e interfaces de ejecución (Instrucción 13).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ai_trading_agent.domain.enums import TradingMode
from ai_trading_agent.domain.models import PaperOrder, Position


class BrokerInterface(ABC):
    """Interfaz abstracta que define las capacidades del broker."""

    @abstractmethod
    def get_account_summary(self) -> Dict[str, Any]:
        """Devuelve el balance de efectivo, equity y poder de compra."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Devuelve la lista actual de posiciones abiertas."""
        pass

    @abstractmethod
    def submit_order(self, order: PaperOrder, mode: TradingMode) -> PaperOrder:
        """
        Envía una orden al broker.
        Debe fallar técnicamente si el modo es ANALYSIS_ONLY.
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancela una orden pendiente."""
        pass
