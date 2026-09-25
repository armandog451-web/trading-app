from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel

class TradeBase(BaseModel):
    symbol: str
    side: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    strategy: str = "TopDown_Intraday_Liquidity"

class TradeResponse(TradeBase):
    id: int
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    status: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    macro_bias: Optional[str] = None
    order_id: Optional[str] = None

    class Config:
        from_attributes = True

class BotStatusResponse(BaseModel):
    is_running: bool
    mode: str  # "PAPER" or "LIVE"
    market_open: bool
    circuit_breaker_tripped: bool
    account_equity: float
    buying_power: float
    daily_pnl: float
    daily_pnl_pct: float
    open_positions_count: int
    monitored_symbols: list[str]

class MacroFactors(BaseModel):
    yield_10y: float
    yield_2y: float
    yield_spread_10y2y: float
    is_inverted: bool
    fed_funds_rate: float
    cpi_inflation_yoy: float
    dxy_index: float
    macro_bias: str  # BULLISH, BEARISH, NEUTRAL
    summary: str

class SentimentFactors(BaseModel):
    vix: float
    vix_regime: str  # LOW, MODERATE, ELEVATED, EXTREME
    cboe_put_call_ratio: float
    put_call_sentiment: str  # BULLISH_COMPLACENCY, NEUTRAL, BEARISH_HEDGING
    fear_and_greed_score: int
    fear_and_greed_sentiment: str
    cot_commercial_net_position: str
    institutional_sentiment: str

class TechnicalLevels(BaseModel):
    symbol: str
    current_price: float
    vwap: float
    pdh: float  # Previous Day High
    pdl: float  # Previous Day Low
    pmh: float  # Pre-Market High
    pml: float  # Pre-Market Low
    rvol: float  # Relative Volume
    atr: float
    trend_bias: str
    liquidity_state: str  # AT_PDH_RESISTANCE, SWEEP_PDL_REVERSAL, ABOVE_VWAP, etc.

class ScreenedStock(BaseModel):
    symbol: str
    price: float
    change_pct: float
    rvol: float
    volume: int
    has_earnings: bool
    catalyst: str
    bias: str

class BacktestRequest(BaseModel):
    symbols: list[str] = ["SPY", "QQQ"]
    days_back: int = 30
    initial_capital: float = 100000.0
    risk_per_trade_pct: float = 1.0
    min_rr_ratio: float = 2.0

class BacktestResultResponse(BaseModel):
    symbols: list[str]
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_net_profit: float
    total_return_pct: float
    total_trades: int
    win_rate_pct: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trades: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]

class RiskConfigUpdate(BaseModel):
    max_daily_loss_pct: float
    risk_per_trade_pct: float
    min_rr_ratio: float
    auto_square_off_time: str
    max_open_positions: int

class BrokerConfigUpdate(BaseModel):
    active_broker: Optional[str] = "ALPACA"
    auto_execute_trades: Optional[bool] = False
    alpaca_api_key: Optional[str] = ""
    alpaca_secret_key: Optional[str] = ""
    alpaca_paper: Optional[bool] = True
    moomoo_host: Optional[str] = "127.0.0.1"
    moomoo_port: Optional[int] = 11111
    moomoo_trade_pwd: Optional[str] = ""
    moomoo_paper: Optional[bool] = True
    moomoo_acc_id: Optional[int] = 0


class TestMoomooRequest(BaseModel):
    moomoo_host: str = "127.0.0.1"
    moomoo_port: int = 11111
    moomoo_trade_pwd: str = ""
    moomoo_paper: bool = True
    moomoo_acc_id: int = 0

class TelegramConfigUpdate(BaseModel):
    telegram_bot_token: str
    telegram_chat_id: str

class TestTelegramRequest(BaseModel):
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    custom_message: Optional[str] = None


class SignalRecommendationResponse(BaseModel):
    id: int
    asset_type: str  # "STOCK" or "OPTION"
    symbol: str
    action: str  # "BUY_STOCK", "BUY_CALL", "BUY_PUT"
    current_price: float
    entry_target: float
    stop_loss: float
    take_profit: float
    take_profit_2: Optional[float] = None
    risk_reward: float
    
    # Opciones
    strike_price: Optional[float] = None
    option_type: Optional[str] = None
    expiration_date: Optional[str] = None
    premium_est: Optional[float] = None
    premium_stop_loss: Optional[float] = None
    premium_take_profit: Optional[float] = None
    contracts_or_shares: int
    
    confluence_score: int
    setup_type: str
    rationale: str
    is_read: bool
    sent_to_telegram: bool
    created_at: datetime

    class Config:
        from_attributes = True

class CreateSignalRequest(BaseModel):
    asset_type: str = "STOCK"  # "STOCK" or "OPTION"
    symbol: str = "SPY"
    bias: str = "BULLISH"  # "BULLISH" (CALL) or "BEARISH" (PUT)
    action: Optional[str] = None  # Auto-calculated if not provided
    custom_note: Optional[str] = None


