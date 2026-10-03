"""
ai_trading_agent.data.providers
===============================
Módulo de proveedores desacoplados de datos de mercado.
"""

from ai_trading_agent.data.providers.base import BaseMarketDataProvider
from ai_trading_agent.data.providers.synthetic_provider import synthetic_provider, SyntheticMarketDataProvider
from ai_trading_agent.data.providers.yfinance_provider import yfinance_provider, YFinanceMarketDataProvider

__all__ = [
    "BaseMarketDataProvider",
    "synthetic_provider",
    "SyntheticMarketDataProvider",
    "yfinance_provider",
    "YFinanceMarketDataProvider",
]
