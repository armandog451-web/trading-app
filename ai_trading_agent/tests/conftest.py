"""
ai_trading_agent.tests.conftest
===============================
Fixtures comunes y deterministas para la suite de pruebas.
"""

import pytest
from datetime import datetime
from ai_trading_agent.data.synthetic import synthetic_generator
from ai_trading_agent.execution.paper_broker import PaperBroker


@pytest.fixture
def bull_bars():
    return synthetic_generator.generate_bars(
        symbol="SPY",
        count=60,
        regime="BULL_TREND",
        base_price=500.0,
        seed=123
    )


@pytest.fixture
def bear_bars():
    return synthetic_generator.generate_bars(
        symbol="SPY",
        count=60,
        regime="BEAR_TREND",
        base_price=500.0,
        seed=456
    )


@pytest.fixture
def sideways_bars():
    return synthetic_generator.generate_bars(
        symbol="SPY",
        count=60,
        regime="SIDEWAYS",
        base_price=500.0,
        seed=789
    )


@pytest.fixture
def paper_broker_instance():
    return PaperBroker(initial_capital=100000.0)
