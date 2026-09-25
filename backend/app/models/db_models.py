from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from app.database import Base

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    side = Column(String(10), nullable=False)  # BUY / SELL
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    risk_reward_ratio = Column(Float, nullable=False)  # e.g., 2.5
    
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    status = Column(String(20), default="OPEN")  # OPEN, CLOSED, CANCELLED
    
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime, nullable=True)
    exit_reason = Column(String(50), nullable=True)  # TP, SL, CIRCUIT_BREAKER, SQUARE_OFF, MANUAL
    
    macro_bias = Column(String(20), nullable=True)  # BULLISH, BEARISH, NEUTRAL
    strategy = Column(String(50), default="TopDown_Intraday_Liquidity")
    order_id = Column(String(100), nullable=True)

class DailyMetrics(Base):
    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), unique=True, index=True)  # YYYY-MM-DD
    starting_equity = Column(Float, default=100000.0)
    current_equity = Column(Float, default=100000.0)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    trades_count = Column(Integer, default=0)
    win_count = Column(Integer, default=0)
    loss_count = Column(Integer, default=0)
    circuit_breaker_tripped = Column(Boolean, default=False)

class BotSetting(Base):
    __tablename__ = "bot_settings"

    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BotLog(Base):
    __tablename__ = "bot_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(20), default="INFO")  # INFO, WARNING, ERROR, SIGNAL, TRADE
    module = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    extra_json = Column(Text, nullable=True)

class SignalRecommendation(Base):
    __tablename__ = "signal_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    asset_type = Column(String(20), nullable=False)  # "STOCK" or "OPTION"
    symbol = Column(String(20), index=True, nullable=False)
    action = Column(String(20), nullable=False)  # "BUY_STOCK", "BUY_CALL", "BUY_PUT"
    
    current_price = Column(Float, nullable=False)
    entry_target = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=True)
    risk_reward = Column(Float, nullable=False)
    
    # Campos específicos de Opciones Financieras
    strike_price = Column(Float, nullable=True)
    option_type = Column(String(10), nullable=True)  # "CALL" or "PUT"
    expiration_date = Column(String(20), nullable=True)  # "YYYY-MM-DD"
    premium_est = Column(Float, nullable=True)  # Prima estimada por acción ($2.50 = $250/contrato)
    premium_stop_loss = Column(Float, nullable=True)
    premium_take_profit = Column(Float, nullable=True)
    contracts_or_shares = Column(Integer, default=1)
    
    # Métricas y justificación
    confluence_score = Column(Integer, default=80)  # e.g., 85%
    setup_type = Column(String(50), default="TopDown_VWAP_Liquidity")
    rationale = Column(Text, nullable=False)
    
    # Estado de la notificación
    is_read = Column(Boolean, default=False)
    sent_to_telegram = Column(Boolean, default=False)
    telegram_message_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

