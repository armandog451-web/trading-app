"""
ai_trading_agent.execution.brokers
==================================
Módulo de adaptadores de brokers de ejecución.
"""

from ai_trading_agent.execution.brokers.base import BaseBrokerAdapter
from ai_trading_agent.execution.brokers.moomoo_adapter import moomoo_adapter, MoomooBrokerAdapter
from ai_trading_agent.execution.brokers.alpaca_adapter import alpaca_adapter, AlpacaBrokerAdapter
from ai_trading_agent.execution.brokers.unified_manager import unified_broker, UnifiedBrokerManager

__all__ = [
    "BaseBrokerAdapter",
    "moomoo_adapter",
    "MoomooBrokerAdapter",
    "alpaca_adapter",
    "AlpacaBrokerAdapter",
    "unified_broker",
    "UnifiedBrokerManager",
]
