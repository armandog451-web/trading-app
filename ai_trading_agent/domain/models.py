"""
ai_trading_agent.domain.models
==============================
Modelos de dominio tipados y validados con Pydantic para auditoría y reproducibilidad.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

from ai_trading_agent.domain.enums import (
    DataQualityStatus, MarketRegime, SignalDirection,
    OrderStatus, OrderType, OrderSide, RiskDecision
)


class BaseDomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class OHLCVBar(BaseDomainModel):
    timestamp: datetime
    symbol: str
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)
    source: str = "synthetic"
    quality_status: DataQualityStatus = DataQualityStatus.VALID

    @model_validator(mode="after")
    def validate_geometry(self):
        if self.high < self.low:
            raise ValueError("High cannot be lower than Low")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("OHLC geometry inconsistent: High must be >= Open and Close, Low must be <= Open and Close")
        return self


class Quote(BaseDomainModel):
    timestamp: datetime
    symbol: str
    bid: float = Field(..., gt=0)
    ask: float = Field(..., gt=0)
    bid_size: float = Field(default=100.0, ge=0)
    ask_size: float = Field(default=100.0, ge=0)
    quality_status: DataQualityStatus = DataQualityStatus.VALID

    @model_validator(mode="after")
    def validate_spread(self):
        if self.ask < self.bid:
            raise ValueError("Ask cannot be lower than Bid")
        return self

    @property
    def spread(self) -> float:
        return self.ask - self.bid

    @property
    def mid_price(self) -> float:
        return (self.bid + self.ask) / 2.0


class StrategySignal(BaseDomainModel):
    strategy_id: str
    strategy_version: str = "1.0.0"
    symbol: str
    direction: SignalDirection
    score: float = Field(..., ge=0.0, le=100.0)  # Score normalizado 0-100 (NO es probabilidad de acierto)
    timestamp: datetime
    data_quality: DataQualityStatus = DataQualityStatus.VALID
    reasons: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class AggregatedSignal(BaseDomainModel):
    decision_id: str
    symbol: str
    direction: SignalDirection
    score: float = Field(..., ge=0.0, le=100.0)
    timestamp: datetime
    contributing_strategies: List[str]
    conflicts_detected: List[str] = Field(default_factory=list)
    is_actionable: bool
    rejection_reason: Optional[str] = None


class TradeProposal(BaseDomainModel):
    decision_id: str
    symbol: str
    direction: SignalDirection
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: float = Field(..., gt=0)
    rr_ratio: float = Field(..., ge=1.0)
    timestamp: datetime
    rationale: str
    strategy_code: Optional[str] = "generic"


class RiskAssessment(BaseDomainModel):
    decision_id: str
    decision: RiskDecision
    approved_quantity: int = Field(default=0, ge=0)
    estimated_risk_dollars: float = Field(default=0.0, ge=0.0)
    max_capital_allocation: float = Field(default=0.0, ge=0.0)
    reasons: List[str] = Field(default_factory=list)
    circuit_breaker_active: bool = False


class PaperOrder(BaseDomainModel):
    order_id: str
    decision_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int = Field(..., gt=0)
    requested_price: float = Field(..., gt=0)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime
    filled_at: Optional[datetime] = None
    avg_fill_price: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0


class Position(BaseModel):
    # Mutable para seguimiento en PortfolioMonitor
    model_config = ConfigDict(extra="forbid")

    symbol: str
    side: OrderSide
    quantity: int = Field(..., gt=0)
    avg_entry_price: float = Field(..., gt=0)
    current_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: float = Field(..., gt=0)
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    opened_at: datetime
    updated_at: datetime
    break_even_active: bool = False


class DecisionRecord(BaseDomainModel):
    decision_id: str
    timestamp: datetime
    symbol: str
    market_regime: MarketRegime
    signal_direction: SignalDirection
    signal_score: float
    reasons: List[str]
    risk_decision: RiskDecision
    risk_reasons: List[str]
    order_id: Optional[str] = None
    order_status: Optional[OrderStatus] = None
    execution_price: Optional[float] = None
