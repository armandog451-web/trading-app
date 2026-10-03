"""
ai_trading_agent.data.storage.repository
========================================
Capa de repositorio para operaciones transaccionales seguras sobre la base de datos (Instrucción 13).
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session

from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.models import DecisionRecord, PaperOrder
from ai_trading_agent.data.storage.models import (
    Base, DBDecisionRecord, DBPaperOrder, DBAccountSnapshot, DBWeekendScan, DBTaskLog
)


class AuditStorageRepository:
    """Repositorio transaccional para auditoría e histórico."""

    def __init__(self, db_url: str = None):
        self.db_url = db_url or settings.DATABASE_URL
        # Si es sqlite, configurar check_same_thread=False
        connect_args = {"check_same_thread": False} if "sqlite" in self.db_url else {}
        self.engine = create_engine(self.db_url, connect_args=connect_args)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.init_db()

    def init_db(self) -> None:
        """Crea las tablas si no existen."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def save_decision(self, record: DecisionRecord) -> None:
        """Guarda un registro inmutable de decisión."""
        with self.get_session() as session:
            db_rec = DBDecisionRecord(
                decision_id=record.decision_id,
                timestamp=record.timestamp,
                symbol=record.symbol,
                market_regime=record.market_regime.value if hasattr(record.market_regime, "value") else str(record.market_regime),
                signal_direction=record.signal_direction.value if hasattr(record.signal_direction, "value") else str(record.signal_direction),
                signal_score=record.signal_score,
                reasons_json=json.dumps(record.reasons),
                risk_decision=record.risk_decision.value if hasattr(record.risk_decision, "value") else str(record.risk_decision),
                risk_reasons_json=json.dumps(record.risk_reasons),
                order_id=record.order_id,
                order_status=record.order_status.value if record.order_status and hasattr(record.order_status, "value") else str(record.order_status),
                execution_price=record.execution_price
            )
            session.merge(db_rec)
            session.commit()

    def get_decisions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Recupera el historial cronológico inverso de decisiones."""
        with self.get_session() as session:
            rows = session.query(DBDecisionRecord).order_by(desc(DBDecisionRecord.timestamp)).limit(limit).all()
            result = []
            for r in rows:
                result.append({
                    "decision_id": r.decision_id,
                    "timestamp": r.timestamp.isoformat(),
                    "symbol": r.symbol,
                    "market_regime": r.market_regime,
                    "signal_direction": r.signal_direction,
                    "signal_score": r.signal_score,
                    "reasons": json.loads(r.reasons_json),
                    "risk_decision": r.risk_decision,
                    "risk_reasons": json.loads(r.risk_reasons_json),
                    "order_id": r.order_id,
                    "order_status": r.order_status,
                    "execution_price": r.execution_price
                })
            return result

    def save_order(self, order: PaperOrder) -> None:
        """Guarda o actualiza una orden del Paper Broker."""
        with self.get_session() as session:
            db_order = DBPaperOrder(
                order_id=order.order_id,
                decision_id=order.decision_id,
                symbol=order.symbol,
                side=order.side.value if hasattr(order.side, "value") else str(order.side),
                order_type=order.order_type.value if hasattr(order.order_type, "value") else str(order.order_type),
                quantity=order.quantity,
                requested_price=order.requested_price,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                status=order.status.value if hasattr(order.status, "value") else str(order.status),
                avg_fill_price=order.avg_fill_price,
                commission=order.commission,
                slippage=order.slippage,
                created_at=order.created_at,
                filled_at=order.filled_at
            )
            session.merge(db_order)
            session.commit()

    def save_account_snapshot(
        self,
        equity: float,
        cash: float,
        realized_pnl: float,
        unrealized_pnl: float,
        positions_count: int = 0
    ) -> None:
        """Guarda una instantánea de cuenta."""
        with self.get_session() as session:
            snapshot = DBAccountSnapshot(
                equity=equity,
                cash=cash,
                realized_pnl=realized_pnl,
                unrealized_pnl=unrealized_pnl,
                positions_count=positions_count
            )
            session.add(snapshot)
            session.commit()

    def save_weekend_scan(self, report_dict: Dict[str, Any]) -> None:
        """Almacena el reporte del escaneo de fin de semana en la base de datos."""
        with self.get_session() as session:
            ts_str = report_dict.get("timestamp")
            dt_ts = datetime.fromisoformat(ts_str) if isinstance(ts_str, str) else datetime.utcnow()
            dt_as_of = datetime.fromisoformat(report_dict.get("data_as_of_date")) if isinstance(report_dict.get("data_as_of_date"), str) else datetime.utcnow()

            db_scan = DBWeekendScan(
                scan_id=report_dict.get("scan_id"),
                timestamp=dt_ts,
                execution_day=report_dict.get("execution_day", "MANUAL"),
                data_as_of_date=dt_as_of,
                universe_json=json.dumps(report_dict.get("universe_scanned", [])),
                report_json=json.dumps(report_dict),
                is_partial=report_dict.get("is_partial", False),
                status="SUCCESS"
            )
            session.merge(db_scan)
            session.commit()

    def get_latest_weekend_scan(self) -> Optional[Dict[str, Any]]:
        """Recupera el último reporte de escaneo de fin de semana guardado."""
        with self.get_session() as session:
            row = session.query(DBWeekendScan).order_by(desc(DBWeekendScan.timestamp)).first()
            if row:
                return json.loads(row.report_json)
            return None

    def save_task_execution(self, task_id: str, date_str: str, status: str, payload: str = None) -> None:
        """Registra la ejecución de una tarea del programador de horarios."""
        with self.get_session() as session:
            task_log = DBTaskLog(
                task_id=task_id,
                date_str=date_str,
                status=status,
                payload_json=payload
            )
            session.add(task_log)
            session.commit()

    def get_task_logs(self, task_id: str = None, date_str: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Recupera los logs de ejecuciones de tareas del programador."""
        with self.get_session() as session:
            query = session.query(DBTaskLog)
            if task_id:
                query = query.filter(DBTaskLog.task_id == task_id)
            if date_str:
                query = query.filter(DBTaskLog.date_str == date_str)
            rows = query.order_by(desc(DBTaskLog.timestamp)).limit(limit).all()
            res = []
            for r in rows:
                res.append({
                    "id": r.id,
                    "task_id": r.task_id,
                    "date_str": r.date_str,
                    "timestamp": r.timestamp.isoformat(),
                    "status": r.status,
                    "payload": json.loads(r.payload_json) if r.payload_json else None
                })
            return res


audit_repo = AuditStorageRepository()
