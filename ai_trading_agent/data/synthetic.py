"""
ai_trading_agent.data.synthetic
===============================
Generador de datos de mercado sintéticos deterministas y reproducibles (Instrucción 7 y 21).
Permite ejecutar pruebas unitarias y simulaciones offline sin llamadas a APIs externas.
"""

from datetime import datetime, timedelta
from typing import List
import numpy as np

from ai_trading_agent.domain.enums import DataQualityStatus
from ai_trading_agent.domain.models import OHLCVBar


class SyntheticDataGenerator:
    """Generador reproducible de barras OHLCV."""

    @staticmethod
    def generate_bars(
        symbol: str = "SPY",
        count: int = 100,
        regime: str = "BULL_TREND",
        base_price: float = 500.0,
        interval_minutes: int = 5,
        start_time: datetime = None,
        seed: int = 42
    ) -> List[OHLCVBar]:
        """
        Genera barras OHLCV deterministas usando semilla aleatoria fijada.
        """
        np.random.seed(seed)
        start_time = start_time or datetime(2026, 1, 15, 9, 30)

        # Configurar drift según régimen
        if regime == "BULL_TREND":
            drift = 0.0008
            vol = 0.003
        elif regime == "BEAR_TREND":
            drift = -0.0008
            vol = 0.003
        elif regime == "HIGH_VOLATILITY":
            drift = 0.0
            vol = 0.008
        else:  # SIDEWAYS / LOW_VOLATILITY
            drift = 0.0
            vol = 0.0015

        bars = []
        current_close = base_price

        for i in range(count):
            bar_time = start_time + timedelta(minutes=i * interval_minutes)

            # Generar retorno logarítmico
            ret = drift + vol * np.random.normal()
            next_close = max(1.0, current_close * (1.0 + ret))

            open_p = current_close
            close_p = next_close

            # Rango High / Low consistente
            noise_h = abs(np.random.normal(scale=vol * current_close * 0.5))
            noise_l = abs(np.random.normal(scale=vol * current_close * 0.5))
            high_p = max(open_p, close_p) + noise_h
            low_p = max(0.5, min(open_p, close_p) - noise_l)

            # Volumen base con fluctuación
            vol_multiplier = 2.0 if (i % 25 == 0) else 1.0  # Spikes periódicos
            volume = float(int(np.random.uniform(50000, 150000) * vol_multiplier))

            bar = OHLCVBar(
                timestamp=bar_time,
                symbol=symbol,
                open=round(open_p, 2),
                high=round(high_p, 2),
                low=round(low_p, 2),
                close=round(close_p, 2),
                volume=volume,
                source="synthetic_generator",
                quality_status=DataQualityStatus.VALID
            )
            bars.append(bar)
            current_close = next_close

        return bars


synthetic_generator = SyntheticDataGenerator()
