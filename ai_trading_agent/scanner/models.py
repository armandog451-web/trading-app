"""
ai_trading_agent.scanner.models
===============================
Modelos de datos fuertemente tipados para el Weekend Market Scanner (Add-on Module).
Representa condiciones analíticas, escenarios preparatorios y reportes estructurados.
"""

from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CandidateCondition(str, Enum):
    TREND_CONTINUATION = "TREND_CONTINUATION"
    BREAKOUT_WATCH = "BREAKOUT_WATCH"
    ORB_CANDIDATE = "ORB_CANDIDATE"
    MOMENTUM_WATCH = "MOMENTUM_WATCH"
    MEAN_REVERSION_WATCH = "MEAN_REVERSION_WATCH"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    EARNINGS_RISK = "EARNINGS_RISK"
    NO_TRADE = "NO_TRADE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class MarketScenario(BaseModel):
    direction: str  # "BULLISH" o "BEARISH"
    trigger_level: float
    rationale: str
    invalidation_level: float
    invalidation_condition: str
    required_confirmation: str


class AssetWeekendPlan(BaseModel):
    symbol: str
    last_historical_price: float
    last_price_timestamp: datetime
    trend: str
    market_regime: str
    primary_condition: CandidateCondition
    secondary_conditions: List[CandidateCondition] = Field(default_factory=list)
    key_support: float
    key_resistance: float
    pivot_point: float
    relative_strength_vs_spy: float  # > 1.0 = más fuerte que SPY
    bullish_scenario: MarketScenario
    bearish_scenario: MarketScenario
    upcoming_events: List[str] = Field(default_factory=list)
    has_earnings_soon: bool = False
    liquidity_and_volatility_risk: str
    applicable_strategies: List[str] = Field(default_factory=list)
    data_quality_status: str
    options_candidate_contract: Optional[Dict[str, Any]] = None


class WeekendScanReport(BaseModel):
    scan_id: str
    timestamp: datetime
    execution_day: str  # "SATURDAY", "SUNDAY", "MANUAL"
    data_as_of_date: datetime
    universe_scanned: List[str]
    market_overview: str
    indices_regimes: Dict[str, str]  # SPY, QQQ, IWM regimes
    trend_and_volatility_shifts: List[str]
    candidates: List[AssetWeekendPlan]
    breakout_candidates: List[str]
    momentum_candidates: List[str]
    mean_reversion_candidates: List[str]
    economic_and_earnings_events: List[str]
    no_trade_risks: List[str]
    missing_data_limitations: List[str]
    system_status: str
    is_partial: bool = False
    strategy_version: str = "1.0.0"
