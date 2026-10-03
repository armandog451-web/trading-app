"""
ai_trading_agent.domain.enums
=============================
Enumeraciones fuertemente tipadas para todo el ciclo de vida cuantitativo y operativo.
"""

from enum import Enum


class DataQualityStatus(str, Enum):
    VALID = "VALID"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    STALE_DATA = "STALE_DATA"
    INVALID_DATA = "INVALID_DATA"


class MarketRegime(str, Enum):
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    UNKNOWN = "UNKNOWN"


class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NO_TRADE = "NO_TRADE"


class TradingMode(str, Enum):
    ANALYSIS_ONLY = "ANALYSIS_ONLY"
    SIGNALS_ONLY = "SIGNALS_ONLY"
    PAPER_TRADING = "PAPER_TRADING"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class RiskDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TimeFrame(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    D1 = "1d"
