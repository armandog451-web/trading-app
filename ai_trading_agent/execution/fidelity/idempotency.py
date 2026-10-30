"""
ai_trading_agent.execution.fidelity.idempotency
===============================================
Institutional Transactional Idempotency Manager for Paper and Live Orders.
Prevents duplicate order submissions across server restarts, concurrency, and partial broker failures.

Deterministic Idempotency Key Structure:
SHA-256(strategy_fingerprint : market_session_date_NY : symbol : signal_direction : evaluation_bar_timestamp)

State Transitions:
RESERVED -> SUBMISSION_PENDING -> SUBMITTED -> ACKNOWLEDGED -> FILLED / REJECTED / UNKNOWN_RECONCILIATION_REQUIRED
"""

import hashlib
import json
import logging
import sqlite3
import zoneinfo
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, unique
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)
NY_TZ = zoneinfo.ZoneInfo("America/New_York")


@unique
class IdempotencyState(str, Enum):
    RESERVED = "RESERVED"
    SUBMISSION_PENDING = "SUBMISSION_PENDING"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    UNKNOWN_RECONCILIATION_REQUIRED = "UNKNOWN_RECONCILIATION_REQUIRED"


@dataclass
class IdempotencyRecord:
    idempotency_key: str
    strategy_id: str
    strategy_fingerprint: str
    market_session_date: str
    symbol: str
    signal_direction: str
    evaluation_bar_timestamp: str
    state: IdempotencyState
    order_id: Optional[str] = None
    client_order_id: Optional[str] = None
    broker: str = "moomoo"
    reservation_timestamp: str = ""
    submission_timestamp: Optional[str] = None
    completion_timestamp: Optional[str] = None
    error_message: Optional[str] = None
    reconciliation_notes: Optional[str] = None


class TransactionalIdempotencyManager:
    """Manages atomic reservation, state transitions, and broker reconciliation."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            from database import DB_PATH
            self.db_path = DB_PATH
        self._init_table()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self):
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS order_idempotency_records (
                        idempotency_key TEXT PRIMARY KEY,
                        strategy_id TEXT NOT NULL,
                        strategy_fingerprint TEXT NOT NULL,
                        market_session_date TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        signal_direction TEXT NOT NULL,
                        evaluation_bar_timestamp TEXT NOT NULL,
                        state TEXT NOT NULL,
                        order_id TEXT,
                        client_order_id TEXT,
                        broker TEXT NOT NULL,
                        reservation_timestamp TEXT NOT NULL,
                        submission_timestamp TEXT,
                        completion_timestamp TEXT,
                        error_message TEXT,
                        reconciliation_notes TEXT
                    )
                """)
        finally:
            conn.close()

    @staticmethod
    def generate_idempotency_key(
        strategy_fingerprint: str,
        market_session_date: str,
        symbol: str,
        signal_direction: str,
        evaluation_bar_timestamp: str
    ) -> str:
        """Computes deterministic 64-char SHA-256 idempotency key."""
        raw_token = f"{strategy_fingerprint}:{market_session_date}:{symbol.upper()}:{signal_direction.upper()}:{evaluation_bar_timestamp}"
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def reserve_order_submission(
        self,
        strategy_id: str,
        strategy_fingerprint: str,
        market_session_date: str,
        symbol: str,
        signal_direction: str,
        evaluation_bar_timestamp: str,
        broker: str = "moomoo",
        client_order_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[IdempotencyRecord]]:
        """
        Attempts atomic reservation in SQLite before submitting an order.
        Returns: (success: bool, message: str, record: Optional[IdempotencyRecord])
        """
        key = self.generate_idempotency_key(
            strategy_fingerprint=strategy_fingerprint,
            market_session_date=market_session_date,
            symbol=symbol,
            signal_direction=signal_direction,
            evaluation_bar_timestamp=evaluation_bar_timestamp
        )
        now_utc = datetime.now(timezone.utc).isoformat()
        cid = client_order_id or f"cid_{strategy_id[:8]}_{symbol}_{int(datetime.now(timezone.utc).timestamp())}"

        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    INSERT INTO order_idempotency_records (
                        idempotency_key, strategy_id, strategy_fingerprint,
                        market_session_date, symbol, signal_direction,
                        evaluation_bar_timestamp, state, order_id,
                        client_order_id, broker, reservation_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    key, strategy_id, strategy_fingerprint,
                    market_session_date, symbol.upper(), signal_direction.upper(),
                    str(evaluation_bar_timestamp), IdempotencyState.RESERVED.value,
                    None, cid, broker, now_utc
                ))
            rec = self.get_record(key)
            return True, "RESERVATION_ACQUIRED", rec

        except sqlite3.IntegrityError:
            # Duplicate key detected! Query existing state
            existing = self.get_record(key)
            if existing:
                return False, f"DUPLICATE_ORDER_SUPPRESSED: Already exists in state {existing.state.value} (Key: {key[:12]}...)", existing
            return False, "DUPLICATE_ORDER_SUPPRESSED", None
        finally:
            conn.close()

    def update_state(
        self,
        idempotency_key: str,
        new_state: IdempotencyState,
        order_id: Optional[str] = None,
        error_message: Optional[str] = None,
        reconciliation_notes: Optional[str] = None
    ) -> bool:
        """Transitions state of the idempotency record."""
        now_utc = datetime.now(timezone.utc).isoformat()
        updates = ["state = ?"]
        params = [new_state.value]

        if order_id:
            updates.append("order_id = ?")
            params.append(order_id)
        if error_message:
            updates.append("error_message = ?")
            params.append(error_message)
        if reconciliation_notes:
            updates.append("reconciliation_notes = ?")
            params.append(reconciliation_notes)

        if new_state == IdempotencyState.SUBMISSION_PENDING:
            updates.append("submission_timestamp = ?")
            params.append(now_utc)
        elif new_state in (IdempotencyState.FILLED, IdempotencyState.REJECTED):
            updates.append("completion_timestamp = ?")
            params.append(now_utc)

        params.append(idempotency_key)
        sql = f"UPDATE order_idempotency_records SET {', '.join(updates)} WHERE idempotency_key = ?"

        conn = self._get_connection()
        try:
            with conn:
                cur = conn.execute(sql, tuple(params))
                return cur.rowcount > 0
        finally:
            conn.close()

    def get_record(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        """Retrieves record by key."""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM order_idempotency_records WHERE idempotency_key = ?", (idempotency_key,))
            row = cur.fetchone()
            if not row:
                return None
            return IdempotencyRecord(
                idempotency_key=row["idempotency_key"],
                strategy_id=row["strategy_id"],
                strategy_fingerprint=row["strategy_fingerprint"],
                market_session_date=row["market_session_date"],
                symbol=row["symbol"],
                signal_direction=row["signal_direction"],
                evaluation_bar_timestamp=row["evaluation_bar_timestamp"],
                state=IdempotencyState(row["state"]),
                order_id=row["order_id"],
                client_order_id=row["client_order_id"],
                broker=row["broker"],
                reservation_timestamp=row["reservation_timestamp"],
                submission_timestamp=row["submission_timestamp"],
                completion_timestamp=row["completion_timestamp"],
                error_message=row["error_message"],
                reconciliation_notes=row["reconciliation_notes"]
            )
        finally:
            conn.close()

    def reconcile_unconfirmed_records(self, broker_client: Any) -> List[Dict[str, Any]]:
        """
        Reconciles records left in UNKNOWN_RECONCILIATION_REQUIRED, SUBMITTED or RESERVED after a restart or crash.
        Inquires the broker ledger before allowing any retry.
        """
        reconciled = []
        conn = self._get_connection()
        try:
            cur = conn.execute("""
                SELECT * FROM order_idempotency_records
                WHERE state IN ('RESERVED', 'SUBMISSION_PENDING', 'SUBMITTED', 'UNKNOWN_RECONCILIATION_REQUIRED')
            """)
            unconfirmed = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

        for r in unconfirmed:
            key = r["idempotency_key"]
            cid = r["client_order_id"]
            oid = r["order_id"]

            # Query broker for order existence
            broker_match = None
            if hasattr(broker_client, "get_orders"):
                orders = broker_client.get_orders()
                for o in orders:
                    if (oid and o.get("order_id") == oid) or (cid and o.get("client_order_id") == cid):
                        broker_match = o
                        break

            if broker_match:
                status = broker_match.get("status", "FILLED")
                fill_status = IdempotencyState.FILLED if status in ("FILLED", "SUBMITTED") else IdempotencyState.REJECTED
                self.update_state(
                    key,
                    fill_status,
                    order_id=broker_match.get("order_id"),
                    reconciliation_notes=f"Reconciled from broker ledger on recovery. Match found ({status})."
                )
                reconciled.append({"key": key, "action": "RECONCILED_MATCH", "status": fill_status.value})
            else:
                # No broker order was placed; safe to mark REJECTED / ABORTED
                self.update_state(
                    key,
                    IdempotencyState.REJECTED,
                    reconciliation_notes="Reconciled on recovery: No matching order found at broker. Reservation expired."
                )
                reconciled.append({"key": key, "action": "RECONCILED_ABORTED", "status": "REJECTED"})

        return reconciled
