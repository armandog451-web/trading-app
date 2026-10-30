"""
ai_trading_agent.strategy_lab.shadow.campaign_models
=====================================================
Modelos de datos y estados para la campaña prospectiva congelada (Fase 7.4).
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ShadowCampaignStatus(str, Enum):
    """Estados canónicos permitidos para una campaña Shadow (Bloque A)."""
    FROZEN = "FROZEN"
    COLLECTING_EVIDENCE = "COLLECTING_EVIDENCE"
    PAUSED_DATA_QUALITY = "PAUSED_DATA_QUALITY"
    PAUSED_RUNTIME = "PAUSED_RUNTIME"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    RESEARCH_REJECTED = "RESEARCH_REJECTED"


class CostScenario(str, Enum):
    """Escenarios de costes paralelos del laboratorio (Bloque H)."""
    TIER_1X = "1x"  # $0.005/acción, 5 bps slippage
    TIER_2X = "2x"  # $0.010/acción, 10 bps slippage
    TIER_3X = "3x"  # $0.015/acción, 15 bps slippage


class ShadowEventType(str, Enum):
    """Tipos de eventos auditables en el ledger."""
    GENESIS = "GENESIS"
    EVALUATION_PASS = "EVALUATION_PASS"
    NO_SIGNAL = "NO_SIGNAL"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    ORDER_PENDING = "ORDER_PENDING"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    POSITION_HELD = "POSITION_HELD"
    POSITION_CLOSED = "POSITION_CLOSED"
    GAP_EVENT = "GAP_EVENT"
    DATA_QUALITY_ALERT = "DATA_QUALITY_ALERT"
    MILESTONE_REACHED = "MILESTONE_REACHED"


class ShadowValidationClock(BaseModel):
    """Reloj de validación forward con contadores independientes (Bloque F)."""
    strategy_id: str
    t0_timestamp_utc: str
    t0_market_session: str
    calendar_days_since_t0: int = 0
    market_sessions_elapsed: int = 0
    valid_shadow_evaluation_sessions: int = 0
    shadow_signals_generated: int = 0
    shadow_positions_opened: int = 0
    shadow_positions_closed: int = 0
    data_quality_failures: int = 0
    runtime_gaps: int = 0
    milestone_20_sessions_reached: bool = False
    milestone_60_sessions_reached: bool = False
    milestone_90_sessions_reached: bool = False
    last_evaluated_session: Optional[str] = None
    last_evaluated_at_utc: Optional[str] = None


class ShadowPosition(BaseModel):
    """Posición hipotética abierta en el simulador Shadow."""
    position_id: str
    campaign_id: str
    strategy_id: str
    symbol: str
    shares: int
    entry_signal_date: str
    entry_execution_date: str
    entry_open_price: float
    entry_fill_price: float
    stop_loss_price: float
    profit_target_price: float
    max_holding_bars: int
    bars_held: int = 0
    accumulated_slippage_usd: float = 0.0
    accumulated_commissions_usd: float = 0.0
    current_mark_price: float = 0.0
    unrealized_gross_pnl: float = 0.0
    unrealized_net_pnl: float = 0.0
    status: str = "OPEN"  # OPEN, CLOSED


class ShadowLedgerEntry(BaseModel):
    """Registro append-only inmutable con encadenamiento criptográfico (Bloque E)."""
    entry_id: str
    entry_index: int
    campaign_id: str
    strategy_id: str
    strategy_fingerprint_sha256: str
    market_date: str
    timestamp_utc: str
    symbol: str
    event_type: ShadowEventType
    signal_direction: str  # BUY, SELL, HOLD, NO_TRADE
    reason: str
    bar_hash_sha256: str
    simulated_order: Optional[Dict[str, Any]] = None
    simulated_fill: Optional[Dict[str, Any]] = None
    open_position: Optional[Dict[str, Any]] = None
    realized_gross_pnl: float = 0.0
    realized_net_pnl: float = 0.0
    costs_usd: float = 0.0
    portfolio_cash: float = 100_000.0
    portfolio_equity: float = 100_000.0
    drawdown_pct: float = 0.0
    prev_entry_hash: str
    entry_hash: str


class CampaignFreezeManifest(BaseModel):
    """Manifiesto de congelamiento criptográfico inmutable (Bloque A)."""
    campaign_id: str
    strategy_id: str
    hypothesis_id: str
    strategy_name: str
    family: str
    thesis: str
    parameters_frozen: Dict[str, Any]
    code_file_path: str
    code_sha256: str
    parameters_sha256: str
    combined_strategy_fingerprint_sha256: str
    t0_timestamp_utc: str
    t0_first_prospective_session: str
    universe_symbols: List[str]
    capital_allocation_usd: float = 100_000.0
    risk_budget_per_trade_usd: float = 250.0
    max_concurrent_positions: int = 2
    execution_policy: str = "SIGNAL_AT_CLOSE_T_EXECUTE_AT_OPEN_T_PLUS_1"
    cost_tier_baseline: str = "1x"
    status: ShadowCampaignStatus = ShadowCampaignStatus.FROZEN
    historical_benchmark_reference: Dict[str, Any] = Field(default_factory=dict)
    environment_info: Dict[str, Any] = Field(default_factory=dict)
