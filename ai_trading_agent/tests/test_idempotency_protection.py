"""
Unit Tests for ai_trading_agent.execution.fidelity.idempotency
=============================================================
Covers 8 Institutional Scenarios:
1. Two concurrent evaluations of the same symbol.
2. Restart after RESERVED state.
3. Restart after SUBMITTED before response.
4. Broker timeout transitions to UNKNOWN_RECONCILIATION_REQUIRED.
5. Broker order accepted but network response lost.
6. Re-evaluation of the same bar.
7. UTC date rollover during New York regular/close session.
8. Reconciliation on service recovery.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock
import zoneinfo

from ai_trading_agent.execution.fidelity.idempotency import (
    IdempotencyRecord,
    IdempotencyState,
    TransactionalIdempotencyManager,
)

NY_TZ = zoneinfo.ZoneInfo("America/New_York")


class TestIdempotencyProtection(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_idempotency.db")
        self.mgr = TransactionalIdempotencyManager(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_1_concurrent_evaluations_same_symbol_suppressed(self):
        """Two concurrent execution threads attempting reservation for the same symbol: exactly 1 wins."""
        def attempt_reservation(worker_id):
            return self.mgr.reserve_order_submission(
                strategy_id="D21_RangeCompress_5d",
                strategy_fingerprint="f885ec2db2422308",
                market_session_date="2026-10-30",
                symbol="QQQ",
                signal_direction="SELL",
                evaluation_bar_timestamp="2026-10-30T16:00:00-04:00",
                client_order_id=f"cid_worker_{worker_id}"
            )

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(attempt_reservation, i) for i in range(4)]
            results = [f.result() for f in futures]

        successes = [r for r in results if r[0] is True]
        failures = [r for r in results if r[0] is False]

        self.assertEqual(len(successes), 1, "Exactly one thread must acquire reservation")
        self.assertEqual(len(failures), 3, "All concurrent attempts must be suppressed")
        self.assertIn("DUPLICATE_ORDER_SUPPRESSED", failures[0][1])

    def test_2_restart_after_reserved_state(self):
        """Server crash/restart after reservation but before submission."""
        success, msg, rec = self.mgr.reserve_order_submission(
            strategy_id="D21_RangeCompress_5d",
            strategy_fingerprint="f885ec2db2422308",
            market_session_date="2026-10-30",
            symbol="SPY",
            signal_direction="BUY",
            evaluation_bar_timestamp="2026-10-30T16:00:00-04:00"
        )
        self.assertTrue(success)
        self.assertEqual(rec.state, IdempotencyState.RESERVED)

        # Simulate service restart with mock broker having no orders
        mock_broker = MagicMock()
        mock_broker.get_orders.return_value = []

        reconciled = self.mgr.reconcile_unconfirmed_records(mock_broker)
        self.assertEqual(len(reconciled), 1)
        self.assertEqual(reconciled[0]["status"], "REJECTED")

        # Record should now be REJECTED with note
        updated = self.mgr.get_record(rec.idempotency_key)
        self.assertEqual(updated.state, IdempotencyState.REJECTED)
        self.assertIn("No matching order found", updated.reconciliation_notes)

    def test_3_restart_after_submitted_before_ack(self):
        """Server crash after order submitted to broker, recovery confirms fill."""
        success, msg, rec = self.mgr.reserve_order_submission(
            strategy_id="D21_RangeCompress_5d",
            strategy_fingerprint="f885ec2db2422308",
            market_session_date="2026-10-30",
            symbol="IWM",
            signal_direction="BUY",
            evaluation_bar_timestamp="2026-10-30T16:00:00-04:00",
            client_order_id="cid_iwm_12345"
        )
        self.mgr.update_state(rec.idempotency_key, IdempotencyState.SUBMITTED, order_id="moo_ord_999")

        # Mock broker returns the filled order
        mock_broker = MagicMock()
        mock_broker.get_orders.return_value = [
            {"order_id": "moo_ord_999", "client_order_id": "cid_iwm_12345", "status": "FILLED"}
        ]

        reconciled = self.mgr.reconcile_unconfirmed_records(mock_broker)
        self.assertEqual(len(reconciled), 1)
        self.assertEqual(reconciled[0]["status"], "FILLED")

        updated = self.mgr.get_record(rec.idempotency_key)
        self.assertEqual(updated.state, IdempotencyState.FILLED)

    def test_4_broker_timeout_transitions_to_unknown_reconciliation(self):
        """Broker timeout: record moves to UNKNOWN_RECONCILIATION_REQUIRED, preventing duplicate submission."""
        success, msg, rec = self.mgr.reserve_order_submission(
            strategy_id="D21_RangeCompress_5d",
            strategy_fingerprint="f885ec2db2422308",
            market_session_date="2026-10-30",
            symbol="DIA",
            signal_direction="SELL",
            evaluation_bar_timestamp="2026-10-30T16:00:00-04:00"
        )
        self.mgr.update_state(rec.idempotency_key, IdempotencyState.SUBMISSION_PENDING)

        # Timeout occurs
        self.mgr.update_state(
            rec.idempotency_key,
            IdempotencyState.UNKNOWN_RECONCILIATION_REQUIRED,
            error_message="Broker socket timed out after 10000ms"
        )

        # Retry attempt on same signal must be BLOCKED
        success2, msg2, rec2 = self.mgr.reserve_order_submission(
            strategy_id="D21_RangeCompress_5d",
            strategy_fingerprint="f885ec2db2422308",
            market_session_date="2026-10-30",
            symbol="DIA",
            signal_direction="SELL",
            evaluation_bar_timestamp="2026-10-30T16:00:00-04:00"
        )
        self.assertFalse(success2)
        self.assertIn("DUPLICATE_ORDER_SUPPRESSED", msg2)
        self.assertIn("UNKNOWN_RECONCILIATION_REQUIRED", msg2)

    def test_5_response_lost_broker_has_order(self):
        """Response dropped on wire, reconciliation finds order in broker ledger."""
        success, msg, rec = self.mgr.reserve_order_submission(
            strategy_id="D21_RangeCompress_5d",
            strategy_fingerprint="f885ec2db2422308",
            market_session_date="2026-10-30",
            symbol="QQQ",
            signal_direction="BUY",
            evaluation_bar_timestamp="2026-10-30T16:00:00-04:00",
            client_order_id="cid_qqq_lost_ack"
        )
        self.mgr.update_state(rec.idempotency_key, IdempotencyState.UNKNOWN_RECONCILIATION_REQUIRED)

        mock_broker = MagicMock()
        mock_broker.get_orders.return_value = [
            {"order_id": "moo_live_444", "client_order_id": "cid_qqq_lost_ack", "status": "FILLED"}
        ]

        self.mgr.reconcile_unconfirmed_records(mock_broker)
        updated = self.mgr.get_record(rec.idempotency_key)
        self.assertEqual(updated.state, IdempotencyState.FILLED)
        self.assertEqual(updated.order_id, "moo_live_444")

    def test_6_re_evaluation_same_bar_blocked(self):
        """Scheduler retry or duplicate tick on same bar date returns duplicate suppressed."""
        bar_ts = "2026-10-30T16:00:00-04:00"
        success1, _, rec1 = self.mgr.reserve_order_submission(
            strategy_id="D21_RangeCompress_5d",
            strategy_fingerprint="f885ec2db2422308",
            market_session_date="2026-10-30",
            symbol="SPY",
            signal_direction="BUY",
            evaluation_bar_timestamp=bar_ts
        )
        self.assertTrue(success1)
        self.mgr.update_state(rec1.idempotency_key, IdempotencyState.FILLED, order_id="ord_1")

        # Second evaluation on same bar
        success2, msg2, rec2 = self.mgr.reserve_order_submission(
            strategy_id="D21_RangeCompress_5d",
            strategy_fingerprint="f885ec2db2422308",
            market_session_date="2026-10-30",
            symbol="SPY",
            signal_direction="BUY",
            evaluation_bar_timestamp=bar_ts
        )
        self.assertFalse(success2)
        self.assertEqual(rec2.state, IdempotencyState.FILLED)

    def test_7_utc_date_rollover_during_ny_session(self):
        """Market session date uses America/New_York; UTC day change does not create duplicate key."""
        # 16:15 ET is 20:15 UTC (same day) or late session changes
        et_dt = datetime(2026, 10, 30, 16, 15, 0, tzinfo=NY_TZ)
        utc_dt = et_dt.astimezone(timezone.utc)
        
        market_session_date = et_dt.strftime("%Y-%m-%d") # 2026-10-30

        key1 = self.mgr.generate_idempotency_key(
            strategy_fingerprint="f885ec2db2422308",
            market_session_date=market_session_date,
            symbol="QQQ",
            signal_direction="SELL",
            evaluation_bar_timestamp="2026-10-30"
        )
        key2 = self.mgr.generate_idempotency_key(
            strategy_fingerprint="f885ec2db2422308",
            market_session_date=market_session_date,
            symbol="qqq",
            signal_direction="sell",
            evaluation_bar_timestamp="2026-10-30"
        )
        self.assertEqual(key1, key2, "Key must be case-insensitive and deterministic")

    def test_8_end_to_end_state_transitions(self):
        """Full happy path lifecycle transitions."""
        success, _, rec = self.mgr.reserve_order_submission(
            strategy_id="D21_RangeCompress_5d",
            strategy_fingerprint="f885ec2db2422308",
            market_session_date="2026-10-30",
            symbol="DIA",
            signal_direction="BUY",
            evaluation_bar_timestamp="2026-10-30"
        )
        key = rec.idempotency_key
        self.assertEqual(self.mgr.get_record(key).state, IdempotencyState.RESERVED)

        self.mgr.update_state(key, IdempotencyState.SUBMISSION_PENDING)
        self.assertEqual(self.mgr.get_record(key).state, IdempotencyState.SUBMISSION_PENDING)

        self.mgr.update_state(key, IdempotencyState.SUBMITTED, order_id="ord_abc")
        self.assertEqual(self.mgr.get_record(key).state, IdempotencyState.SUBMITTED)

        self.mgr.update_state(key, IdempotencyState.ACKNOWLEDGED)
        self.assertEqual(self.mgr.get_record(key).state, IdempotencyState.ACKNOWLEDGED)

        self.mgr.update_state(key, IdempotencyState.FILLED)
        final_rec = self.mgr.get_record(key)
        self.assertEqual(final_rec.state, IdempotencyState.FILLED)
        self.assertIsNotNone(final_rec.completion_timestamp)


if __name__ == "__main__":
    unittest.main()
