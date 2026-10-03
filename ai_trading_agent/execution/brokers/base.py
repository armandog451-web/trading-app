"""
ai_trading_agent.execution.brokers.base
=======================================
Contrato base para adaptadores de brokers (Moomoo, Alpaca, Paper Interno).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ai_trading_agent.domain.models import PaperOrder


class BaseBrokerAdapter(ABC):
    """Interfaz estándar para interacción con brokers de mercado."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_account_summary(self) -> Dict[str, Any]:
        """Devuelve equity, cash, buying_power y estado de conexión."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Devuelve lista de posiciones abiertas."""
        pass

    @abstractmethod
    def submit_order(self, order: PaperOrder) -> PaperOrder:
        """Envía una orden al entorno Paper del broker."""
        pass
