"""
ai_trading_agent.data.providers.synthetic_provider
==================================================
Proveedor de datos de mercado sintéticos deterministas para pruebas y entornos offline.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from ai_trading_agent.domain.models import OHLCVBar, Quote
from ai_trading_agent.domain.enums import DataQualityStatus
from ai_trading_agent.data.synthetic import synthetic_generator
from ai_trading_agent.data.providers.base import BaseMarketDataProvider


class SyntheticMarketDataProvider(BaseMarketDataProvider):
    """Implementación reproducible 100% offline."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def get_historical_bars(
        self,
        symbol: str,
        count: int = 100,
        interval: str = "5m",
        end_time: Optional[datetime] = None
    ) -> List[OHLCVBar]:
        return synthetic_generator.generate_bars(
            symbol=symbol,
            count=count,
            regime="BULL_TREND",
            seed=self.seed
        )

    def get_quote(self, symbol: str) -> Optional[Quote]:
        bars = self.get_historical_bars(symbol, count=1)
        if not bars:
            return None
        last_close = bars[-1].close
        spread = round(last_close * 0.0005, 2)
        return Quote(
            timestamp=bars[-1].timestamp,
            symbol=symbol,
            bid=round(last_close - (spread / 2), 2),
            ask=round(last_close + (spread / 2), 2),
            bid_size=100.0,
            ask_size=100.0,
            quality_status=DataQualityStatus.VALID
        )

    def get_event_calendar(self, symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "has_earnings_today": False,
            "days_to_earnings": 45,
            "has_macro_event_today": False
        }


synthetic_provider = SyntheticMarketDataProvider()
