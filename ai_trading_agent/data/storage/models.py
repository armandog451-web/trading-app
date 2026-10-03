"""
ai_trading_agent.data.storage.models
====================================
Modelos ORM de SQLAlchemy 2.0 para persistencia inmutable y auditoría (Instrucción 13).
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DBDecisionRecord(Base):
    """Registro inmutable de cada evaluación cuantitativa y decisión de trading."""
    __tablename__ = "decisions_audit"

    decision_id = Column(String(64), primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    symbol = Column(String(16), index=True, nullable=False)
    market_regime = Column(String(32), nullable=False)
    signal_direction = Column(String(16), nullable=False)
    signal_score = Column(Float, nullable=False)
    reasons_json = Column(Text, nullable=False)
    risk_decision = Column(String(16), nullable=False)
    risk_reasons_json = Column(Text, nullable=False)
    order_id = Column(String(64), nullable=True)
    order_status = Column(String(32), nullable=True)
    execution_price = Column(Float, nullable=True)


class DBPaperOrder(Base):
    """Registro de órdenes simuladas enviadas al Paper Broker."""
    __tablename__ = "paper_orders_audit"

    order_id = Column(String(64), primary_key=True, index=True)
    decision_id = Column(String(64), index=True, nullable=False)
    symbol = Column(String(16), index=True, nullable=False)
    side = Column(String(8), nullable=False)
    order_type = Column(String(16), nullable=False)
    quantity = Column(Integer, nullable=False)
    requested_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    status = Column(String(32), nullable=False)
    avg_fill_price = Column(Float, nullable=True)
    commission = Column(Float, default=0.0)
    slippage = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)


class DBAccountSnapshot(Base):
    """Instantáneas periódicas del balance y riesgo de cartera."""
    __tablename__ = "account_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    equity = Column(Float, nullable=False)
    cash = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    positions_count = Column(Integer, default=0)


class DBWeekendScan(Base):
    """Historial persistente de escaneos de preparación de fin de semana."""
    __tablename__ = "weekend_scans_audit"

    scan_id = Column(String(64), primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    execution_day = Column(String(16), nullable=False)
    data_as_of_date = Column(DateTime, nullable=False)
    universe_json = Column(Text, nullable=False)
    report_json = Column(Text, nullable=False)
    is_partial = Column(Boolean, default=False)
    status = Column(String(32), default="SUCCESS")


class DBTaskLog(Base):
    """Registro persistente de ejecuciones del programador de horarios."""
    __tablename__ = "task_logs_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), index=True, nullable=False)
    date_str = Column(String(16), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(32), nullable=False)
    payload_json = Column(Text, nullable=True)

