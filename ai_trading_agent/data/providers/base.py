"""
ai_trading_agent.data.providers.base
====================================
Contrato abstracto para proveedores de datos de mercado (Instrucción 7).
Asegura que el núcleo cuantitativo sea 100% independiente de cualquier API externa.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from ai_trading_agent.domain.models import OHLCVBar, Quote


class BaseMarketDataProvider(ABC):
    """Interfaz estándar desacoplada para ingestión de datos de mercado."""

    @abstractmethod
    def get_historical_bars(
        self,
        symbol: str,
        count: int = 100,
        interval: str = "5m",
        end_time: Optional[datetime] = None
    ) -> List[OHLCVBar]:
        """Recupera barras históricas validadas."""
        pass

    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Recupera la cotización bid/ask actual."""
        pass

    @abstractmethod
    def get_event_calendar(self, symbol: str) -> Dict[str, Any]:
        """Recupera eventos corporativos (Earnings, dividendos) y macroeconómicos."""
        pass
