"""
ai_trading_agent.tests.test_validation_and_synthetic
====================================================
Pruebas de validación de calidad de datos y generador sintético determinista.
"""

import pytest
from datetime import datetime
from ai_trading_agent.domain.enums import DataQualityStatus
from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.data.validation import data_validator
from ai_trading_agent.data.synthetic import synthetic_generator


def test_synthetic_reproducibility():
    bars_1 = synthetic_generator.generate_bars(symbol="SPY", count=20, seed=999)
    bars_2 = synthetic_generator.generate_bars(symbol="SPY", count=20, seed=999)

    assert len(bars_1) == len(bars_2) == 20
    for b1, b2 in zip(bars_1, bars_2):
        assert b1.close == b2.close
        assert b1.timestamp == b2.timestamp


def test_validate_bar_geometry_valid(bull_bars):
    valid, status, msg = data_validator.validate_bar(bull_bars[0])
    assert valid is True
    assert status == DataQualityStatus.VALID


def test_validate_bar_invalid_geometry():
    # Pydantic valida en construcción que high no sea menor que low
    with pytest.raises(ValueError):
        OHLCVBar(
            timestamp=datetime.utcnow(),
            symbol="SPY",
            open=100.0,
            high=90.0,
            low=95.0,
            close=98.0,
            volume=1000.0
        )
