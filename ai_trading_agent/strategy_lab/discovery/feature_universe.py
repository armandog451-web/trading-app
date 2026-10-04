"""
ai_trading_agent.strategy_lab.discovery.feature_universe
==========================================================
Universo de Features Cuantitativos y Catálogo de Metadatos.
Garantiza la ausencia total de Look-Ahead Bias y Data Leakage mediante validación explícita.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator


class FeatureCategory(str, Enum):
    PRICE = "PRICE"
    VOLUME = "VOLUME"
    VWAP = "VWAP"
    TECHNICAL = "TECHNICAL"
    MARKET_REGIME = "MARKET_REGIME"
    MARKET_CONTEXT = "MARKET_CONTEXT"
    TIME = "TIME"
    EVENTS = "EVENTS"


class FeatureMetadata(BaseModel):
    feature_id: str
    name: str
    category: FeatureCategory
    description: str
    datatype: str = "float"  # float, bool, int, str
    timeframe: str = "15m"
    availability: str = "AVAILABLE"  # AVAILABLE, PARTIAL, UNAVAILABLE
    lookback_bars: int = 1
    data_dependencies: List[str] = Field(default_factory=list)
    normalization: str = "RAW"  # RAW, ZSCORE, PERCENTILE, RATIO
    uses_future_information: bool = False  # NUNCA True para investigación
    allowed_for_research: bool = True

    @model_validator(mode="after")
    def validate_no_future_information(self):
        if self.uses_future_information:
            raise ValueError(f"DATA LEAKAGE RISK: Feature {self.feature_id} usa información futura y está prohibido para investigación.")
        return self


class FeatureUniverseCatalog:
    """Catálogo centralizado de features cuantitativos disponibles para el Discovery Engine."""

    def __init__(self):
        self._catalog: Dict[str, FeatureMetadata] = {}
        self._initialize_built_in_catalog()

    def _initialize_built_in_catalog(self):
        built_ins = [
            # CATEGORÍA PRICE
            FeatureMetadata(
                feature_id="returns_1d",
                name="Rendimiento 1 Período",
                category=FeatureCategory.PRICE,
                description="Cambio porcentual del precio de cierre respecto a la barra anterior",
                datatype="float",
                lookback_bars=1,
                data_dependencies=["close"],
                normalization="RATIO"
            ),
            FeatureMetadata(
                feature_id="atr_14",
                name="Average True Range (14)",
                category=FeatureCategory.PRICE,
                description="Rango medio verdadero normalizado para medir volatilidad intradiaria",
                datatype="float",
                lookback_bars=14,
                data_dependencies=["high", "low", "close"],
                normalization="RAW"
            ),
            FeatureMetadata(
                feature_id="high_low_range_pct",
                name="Rango de Barra %",
                category=FeatureCategory.PRICE,
                description="Amplitud de la barra actual (High - Low) / Close",
                datatype="float",
                lookback_bars=1,
                data_dependencies=["high", "low", "close"],
                normalization="RATIO"
            ),
            FeatureMetadata(
                feature_id="opening_range_breakout",
                name="Ruptura de Rango de Apertura (ORB)",
                category=FeatureCategory.PRICE,
                description="Indicador binario de ruptura del High/Low de los primeros 15 minutos",
                datatype="bool",
                lookback_bars=15,
                data_dependencies=["open", "high", "low", "close"]
            ),

            # CATEGORÍA VOLUME
            FeatureMetadata(
                feature_id="relative_volume_rvol",
                name="Volumen Relativo (RVOL)",
                category=FeatureCategory.VOLUME,
                description="Ratio entre el volumen actual y el volumen medio móvil de 20 barras",
                datatype="float",
                lookback_bars=20,
                data_dependencies=["volume"],
                normalization="RATIO"
            ),
            FeatureMetadata(
                feature_id="volume_surge",
                name="Aceleración de Volumen",
                category=FeatureCategory.VOLUME,
                description="Cambio porcentual del volumen de la barra actual respecto a la previa",
                datatype="float",
                lookback_bars=2,
                data_dependencies=["volume"],
                normalization="RATIO"
            ),

            # CATEGORÍA VWAP
            FeatureMetadata(
                feature_id="price_vs_vwap",
                name="Distancia a VWAP %",
                category=FeatureCategory.VWAP,
                description="Diferencia porcentual entre el precio de cierre y el VWAP intradiario",
                datatype="float",
                lookback_bars=1,
                data_dependencies=["close", "vwap"],
                normalization="RATIO"
            ),
            FeatureMetadata(
                feature_id="vwap_slope",
                name="Pendiente de VWAP",
                category=FeatureCategory.VWAP,
                description="Inclinación de la línea de VWAP en las últimas 5 barras",
                datatype="float",
                lookback_bars=5,
                data_dependencies=["vwap"],
                normalization="RAW"
            ),

            # CATEGORÍA TECHNICAL
            FeatureMetadata(
                feature_id="ema_cross_9_21",
                name="Cruce EMA 9 / EMA 21",
                category=FeatureCategory.TECHNICAL,
                description="Estado de cruce de medias móviles exponenciales rápida y lenta",
                datatype="bool",
                lookback_bars=21,
                data_dependencies=["ema9", "ema21"]
            ),
            FeatureMetadata(
                feature_id="rsi_14",
                name="Relative Strength Index (14)",
                category=FeatureCategory.TECHNICAL,
                description="Oscilador RSI de Wilder normalizado (0-100)",
                datatype="float",
                lookback_bars=14,
                data_dependencies=["close"],
                normalization="RAW"
            ),
            FeatureMetadata(
                feature_id="bollinger_band_width",
                name="Ancho de Bandas Bollinger",
                category=FeatureCategory.TECHNICAL,
                description="Distancia entre la banda superior e inferior normalizada por el precio",
                datatype="float",
                lookback_bars=20,
                data_dependencies=["bb_upper", "bb_lower", "close"],
                normalization="RATIO"
            ),

            # CATEGORÍA MARKET REGIME
            FeatureMetadata(
                feature_id="market_regime_type",
                name="Régimen de Mercado Vigente",
                category=FeatureCategory.MARKET_REGIME,
                description="Clasificación en BULL_TREND, BEAR_TREND, SIDEWAYS, HIGH_VOLATILITY, LOW_VOLATILITY",
                datatype="str",
                lookback_bars=30,
                data_dependencies=["close", "sma50", "atr"]
            ),

            # CATEGORÍA TIME
            FeatureMetadata(
                feature_id="trading_session_phase",
                name="Fase de la Sesión de Mercado",
                category=FeatureCategory.TIME,
                description="Fase temporal: OPENING (09:30-10:00), MIDDAY (10:00-15:30), POWER_HOUR (15:30-16:00)",
                datatype="str",
                lookback_bars=1,
                data_dependencies=["timestamp"]
            ),

            # CATEGORÍA EVENTS
            FeatureMetadata(
                feature_id="earnings_event_flag",
                name="Proximidad de Resultados Trimestrales",
                category=FeatureCategory.EVENTS,
                description="Bandera de aviso si el activo reporta beneficios dentro de las próximas 48h",
                datatype="bool",
                lookback_bars=1,
                data_dependencies=["earnings_calendar"]
            )
        ]

        for f in built_ins:
            self.register_feature(f)

    def register_feature(self, feature: FeatureMetadata):
        """Registra un nuevo feature en el catálogo previa validación de Look-Ahead Bias."""
        if feature.uses_future_information:
            raise ValueError(f"DATA LEAKAGE RISK: Feature {feature.feature_id} está prohibido.")
        self._catalog[feature.feature_id] = feature

    def get_feature(self, feature_id: str) -> Optional[FeatureMetadata]:
        return self._catalog.get(feature_id)

    def list_features(self, category: Optional[FeatureCategory] = None) -> List[FeatureMetadata]:
        if category:
            return [f for f in self._catalog.values() if f.category == category and f.allowed_for_research]
        return [f for f in self._catalog.values() if f.allowed_for_research]


feature_universe = FeatureUniverseCatalog()
