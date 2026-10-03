"""
ai_trading_agent.strategies.base
================================
Contrato base abstracto para todas las estrategias cuantitativas (Instrucción 9).
Exige retorno estructurado StrategySignal y prohíbe el envío directo de órdenes.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ai_trading_agent.domain.enums import MarketRegime
from ai_trading_agent.domain.models import OHLCVBar, StrategySignal


class BaseStrategy(ABC):
    """Interfaz común inmutable para toda estrategia en el sistema."""

    def __init__(self, strategy_id: str, version: str = "1.0.0"):
        self.strategy_id = strategy_id
        self.version = version

    @abstractmethod
    def evaluate(
        self,
        symbol: str,
        bars: List[OHLCVBar],
        indicators: Dict[str, Any],
        regime: MarketRegime
    ) -> StrategySignal:
        """
        Evalúa el contexto de mercado y devuelve una señal estructurada.
        NINGUNA estrategia tiene permiso para enviar órdenes directamente.
        """
        pass
