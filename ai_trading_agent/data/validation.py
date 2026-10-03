"""
ai_trading_agent.data.validation
================================
Validación rigurosa de calidad de datos de mercado (Instrucción 7).
Detecta precios inválidos, barras duplicadas, secuencias incorrectas y obsolescencia.
"""

from datetime import datetime, timedelta
from typing import List, Tuple
from ai_trading_agent.domain.enums import DataQualityStatus
from ai_trading_agent.domain.models import OHLCVBar, Quote


class DataValidator:
    """Validador determinista de integridad de datos de mercado."""

    def __init__(self, max_staleness_hours: float = 24.0):
        self.max_staleness_hours = max_staleness_hours

    def validate_bar(self, bar: OHLCVBar, reference_time: datetime = None) -> Tuple[bool, DataQualityStatus, str]:
        """Valida una barra individual contra reglas de física de precios."""
        if bar.open <= 0 or bar.high <= 0 or bar.low <= 0 or bar.close <= 0:
            return False, DataQualityStatus.INVALID_DATA, "Precios menores o iguales a cero detectados"

        if bar.high < bar.low:
            return False, DataQualityStatus.INVALID_DATA, "High es menor que Low"

        if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close):
            return False, DataQualityStatus.INVALID_DATA, "Geometría OHLC inconsistente"

        if reference_time:
            delta = reference_time - bar.timestamp
            if delta > timedelta(hours=self.max_staleness_hours):
                return False, DataQualityStatus.STALE_DATA, f"Dato obsoleto: retraso de {delta.total_seconds() / 3600:.1f} horas"

        return True, DataQualityStatus.VALID, "Barra válida"

    def validate_bar_series(self, bars: List[OHLCVBar], min_bars: int = 30) -> Tuple[bool, DataQualityStatus, str]:
        """Valida una secuencia temporal completa de barras."""
        if not bars or len(bars) < min_bars:
            return False, DataQualityStatus.DATA_UNAVAILABLE, f"Muestra insuficiente: {len(bars) if bars else 0} barras (mínimo requerido: {min_bars})"

        seen_timestamps = set()
        prev_time = None

        for bar in bars:
            valid, status, msg = self.validate_bar(bar)
            if not valid:
                return False, status, msg

            if bar.timestamp in seen_timestamps:
                return False, DataQualityStatus.INVALID_DATA, f"Timestamp duplicado detectado: {bar.timestamp}"
            seen_timestamps.add(bar.timestamp)

            if prev_time and bar.timestamp < prev_time:
                return False, DataQualityStatus.INVALID_DATA, f"Secuencia temporal invertida: {bar.timestamp} después de {prev_time}"
            prev_time = bar.timestamp

        return True, DataQualityStatus.VALID, f"Serie válida de {len(bars)} barras"

    def validate_quote(self, quote: Quote, max_spread_pct: float = 0.005) -> Tuple[bool, DataQualityStatus, str]:
        """Valida un precio bid/ask contra spreads excesivos o anomalías."""
        if quote.bid <= 0 or quote.ask <= 0:
            return False, DataQualityStatus.INVALID_DATA, "Cotización bid/ask menor o igual a cero"

        if quote.bid > quote.ask:
            return False, DataQualityStatus.INVALID_DATA, "Bid es mayor que Ask (mercado invertido)"

        spread_pct = quote.spread / quote.mid_price
        if spread_pct > max_spread_pct:
            return False, DataQualityStatus.INVALID_DATA, f"Spread excesivo: {spread_pct * 100:.2f}% (límite: {max_spread_pct * 100:.2f}%)"

        return True, DataQualityStatus.VALID, "Cotización válida"


data_validator = DataValidator()
