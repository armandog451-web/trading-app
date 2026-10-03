"""
ai_trading_agent.market.regime
==============================
Detector cuantitativo de régimen de mercado (Instrucción 8).
Clasifica el entorno en BULL_TREND, BEAR_TREND, SIDEWAYS, HIGH_VOLATILITY o UNKNOWN.
"""

from typing import Dict, Any, Tuple
from ai_trading_agent.domain.enums import MarketRegime


class MarketRegimeDetector:
    """Clasificador de regímenes de mercado basado en confluencia técnica."""

    @staticmethod
    def detect_regime(ind: Dict[str, Any]) -> Tuple[MarketRegime, str]:
        """
        Evalúa el estado del mercado a partir del diccionario de indicadores.
        """
        if not ind or "current_price" not in ind:
            return MarketRegime.UNKNOWN, "Indicadores insuficientes para determinar régimen"

        price = ind["current_price"]
        ema9 = ind["ema9"]
        ema21 = ind["ema21"]
        ema50 = ind["ema50"]
        rsi = ind["rsi"]
        atr_pct = ind["atr_pct"]
        bb_upper = ind["bb_upper"]
        bb_lower = ind["bb_lower"]
        bb_width = (bb_upper - bb_lower) / ind["bb_mid"]

        # 1. Régimen de Alta Volatilidad (Filtro prioritario)
        if atr_pct > 2.5 or bb_width > 0.06:
            return MarketRegime.HIGH_VOLATILITY, f"Volatilidad extrema detectada (ATR: {atr_pct:.2f}%, Ancho Bollinger: {bb_width*100:.2f}%)"

        # 2. Régimen Alcista (Bull Trend)
        if price > ema21 and ema9 > ema21 > ema50 and rsi > 52.0:
            return MarketRegime.BULL_TREND, f"Estructura alcista sólida: Precio > EMA21 > EMA50 y RSI={rsi:.1f}"

        # 3. Régimen Bajista (Bear Trend)
        if price < ema21 and ema9 < ema21 < ema50 and rsi < 48.0:
            return MarketRegime.BEAR_TREND, f"Estructura bajista sólida: Precio < EMA21 < EMA50 y RSI={rsi:.1f}"

        # 4. Régimen de Baja Volatilidad / Compresión
        if bb_width < 0.015:
            return MarketRegime.LOW_VOLATILITY, f"Compresión de volatilidad (Squeeze): Ancho Bollinger {bb_width*100:.2f}%"

        # 5. Régimen Lateral (Sideways / Rango)
        if 42.0 <= rsi <= 58.0 and abs(price - ind["bb_mid"]) / ind["bb_mid"] < 0.01:
            return MarketRegime.SIDEWAYS, f"Mercado en equilibrio/rango: RSI neutro ({rsi:.1f}) y precio pegado a SMA20"

        return MarketRegime.SIDEWAYS, "Mercado sin tendencia definida predominante"


regime_detector = MarketRegimeDetector()
