"""
ai_trading_agent.backtest
=========================
Módulo de simulación histórica y análisis cuantitativo riguroso.
"""

from ai_trading_agent.backtest.metrics import metrics_calculator, PerformanceMetrics
from ai_trading_agent.backtest.engine import backtest_engine, BacktestReport

__all__ = [
    "metrics_calculator",
    "PerformanceMetrics",
    "backtest_engine",
    "BacktestReport",
]
