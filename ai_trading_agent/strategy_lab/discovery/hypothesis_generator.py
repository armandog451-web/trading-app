"""
ai_trading_agent.strategy_lab.discovery.hypothesis_generator
============================================================
Generador Autónomo de Hipótesis de Investigación Cuantitativa.
Genera hipótesis formalizadas combinando features, regímenes de mercado y lecciones pasadas.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ai_trading_agent.strategy_lab.discovery.feature_universe import FeatureUniverseCatalog, feature_universe


class DiscoveryHypothesis(BaseModel):
    """Modelo de datos para una Hipótesis de Investigación reproducible."""
    hypothesis_id: str = Field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:8]}")
    description: str
    features: List[str]
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    expected_relationship: str
    target_market: str = "BTC/USDT"
    target_timeframe: str = "1h"
    priority: float = 1.0
    status: str = "PROPOSED"  # PROPOSED, TESTING, CONFIRMED, REJECTED
    rationale: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HypothesisGenerator:
    """Motor de Generación de Hipótesis de Trading cuantitativas."""

    def __init__(self, catalog: Optional[FeatureUniverseCatalog] = None):
        self.catalog = catalog or feature_universe

    def generate_hypothesis(
        self,
        strategy_type: str = "TREND_FOLLOWING",
        target_market: str = "BTC/USDT",
        target_timeframe: str = "1h",
        past_failed_features: Optional[List[str]] = None
    ) -> DiscoveryHypothesis:
        """Genera una hipótesis cualitativa y cuantitativa para guiarse en el laboratorio."""
        past_failed = set(past_failed_features or [])

        available_features = [f.feature_id for f in self.catalog.list_features() if f.feature_id not in past_failed]

        if strategy_type == "TREND_FOLLOWING":
            used_features = [f for f in ["ema_cross_9_21", "relative_volume_rvol", "atr_14"] if f in available_features]
            desc = f"Tendencia sostenida mediante cruce EMA 9/21 confirmado por alto volumen en {target_market}"
            rel = "Un cruce alcista de EMA9 sobre EMA21 acompañado de RVOL > 1.2 indica momentum alcista persistente."
            conditions = [
                {"feature": "ema_cross_9_21", "operator": "==", "value": True},
                {"feature": "relative_volume_rvol", "operator": ">", "value": 1.2}
            ]

        elif strategy_type == "MEAN_REVERSION":
            used_features = [f for f in ["rsi_14", "bollinger_band_width", "returns_1d"] if f in available_features]
            desc = f"Reversión a la media desde niveles extremos de RSI y bandas Bollinger en {target_market}"
            rel = "Un RSI(14) < 30 coincidiendo con contracción de volumen sugiere sobreventa y rebote inminente."
            conditions = [
                {"feature": "rsi_14", "operator": "<", "value": 30},
                {"feature": "returns_1d", "operator": "<", "value": -0.02}
            ]

        elif strategy_type == "VOLATILITY_BREAKOUT":
            used_features = [f for f in ["opening_range_breakout", "volume_surge", "atr_14"] if f in available_features]
            desc = f"Ruptura de volatilidad tras compresión de rango en {target_market}"
            rel = "Una ruptura del rango de apertura acompañada por volumen acelerado señala el inicio de un movimiento direccional."
            conditions = [
                {"feature": "opening_range_breakout", "operator": "==", "value": True},
                {"feature": "volume_surge", "operator": ">", "value": 1.5}
            ]

        elif strategy_type == "REGIME_FILTERED":
            used_features = [f for f in ["market_regime_type", "ema_cross_9_21", "price_vs_vwap"] if f in available_features]
            desc = f"Estrategia de tendencia condicionada al régimen de mercado BULL_TREND en {target_market}"
            rel = "Filtrar señales de compra para activarlas únicamente cuando el régimen global sea BULL_TREND reduce falsas rupturas."
            conditions = [
                {"feature": "market_regime_type", "operator": "==", "value": "BULL_TREND"},
                {"feature": "price_vs_vwap", "operator": ">", "value": 0.0}
            ]

        else:  # Custom / Hybrid
            used_features = available_features[:3]
            desc = f"Hipótesis combinatoria híbrida para {target_market}"
            rel = "La interacción de múltiples indicadores técnicos confirma sesgo de mercado."
            conditions = [
                {"feature": used_features[0], "operator": ">", "value": 0.0} if used_features else {}
            ]

        return DiscoveryHypothesis(
            description=desc,
            features=used_features,
            conditions=conditions,
            expected_relationship=rel,
            target_market=target_market,
            target_timeframe=target_timeframe,
            priority=1.0,
            rationale=f"Generada automáticamente para la familia {strategy_type}"
        )
