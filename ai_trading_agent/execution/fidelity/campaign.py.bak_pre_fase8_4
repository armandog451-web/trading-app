"""
ai_trading_agent.execution.fidelity.campaign
===========================================
Seguimiento formal de la campaña de Paper Validation para D21_RangeCompress_5d.
Mantiene los dos contadores independientes:
1. calendar_days_since_original_start
2. verified_paper_observation_days (excluyendo estrictamente PAPER_OBSERVATION_GAP)

Asegura que el umbral de 90 días se evalúe con días de observación real verificados,
exigiendo además un mínimo de 12 trades cerrados en Paper sin fabricar historial.
"""

from datetime import date, datetime
from typing import Dict, Any, Optional
import json
import sqlite3

from database import get_connection

ORIGINAL_CAMPAIGN_START = date(2026, 10, 5)
GAP_START_DATE = date(2026, 10, 6)
GAP_END_DATE = date(2026, 10, 20)  # Fin inclusivo del periodo de desconexión
CANONICAL_RUNTIME_RESTORED = date(2026, 10, 21)

REQUIRED_VERIFIED_OBSERVATION_DAYS = 90
REQUIRED_CLOSED_PAPER_TRADES = 12


class PaperValidationCampaignTracker:
    """Rastreador determinista y auditable del reloj de validación en Paper."""

    def __init__(self, strategy_id: str = "D21_RangeCompress_5d"):
        self.strategy_id = strategy_id
        self.original_start = ORIGINAL_CAMPAIGN_START
        self.gap_start = GAP_START_DATE
        self.gap_end = GAP_END_DATE
        self.restored_date = CANONICAL_RUNTIME_RESTORED
        self.required_verified_days = REQUIRED_VERIFIED_OBSERVATION_DAYS
        self.required_closed_trades = REQUIRED_CLOSED_PAPER_TRADES
        self.paper_validation_active = True

    def calculate_metrics(self, current_date: Optional[date] = None) -> Dict[str, Any]:
        """Calcula los contadores de calendario y observación verificada."""
        today = current_date or datetime.now().date()
        if today < self.original_start:
            today = self.original_start

        # 1. Total días calendario transcurridos desde el inicio original (inclusivo)
        calendar_days = (today - self.original_start).days + 1

        # 2. Días de observación real verificada
        verified_days = 0
        from datetime import timedelta
        cursor_day = self.original_start
        while cursor_day <= today:
            # Excluir el rango del gap [GAP_START_DATE, GAP_END_DATE]
            if not (self.gap_start <= cursor_day <= self.gap_end):
                verified_days += 1
            cursor_day += timedelta(days=1)

        gap_days = (self.gap_end - self.gap_start).days + 1

        # 3. Contar trades cerrados reales en SQLite
        closed_trades = self._get_closed_paper_trades_count()

        # 4. Cálculo de las 4 métricas independientes institucionales
        calendar_days_active = calendar_days
        
        # Sesiones de mercado completadas (días hábiles lunes a viernes desde CANONICAL_RUNTIME_RESTORED hasta ayer)
        market_sessions_completed = 0
        cur_session = self.restored_date
        while cur_session < today:
            if cur_session.weekday() < 5:  # Lunes a Viernes
                market_sessions_completed += 1
            cur_session += timedelta(days=1)

        # Sesiones bursátiles con evaluación efectiva de D21 registradas
        d21_valid_evaluation_sessions = self._get_d21_valid_evaluations_count()
        paper_closed_trades = closed_trades

        # 5. Estado de cumplimiento
        meets_days = verified_days >= self.required_verified_days
        meets_trades = closed_trades >= self.required_closed_trades
        ready_for_committee_review = meets_days and meets_trades

        return {
            "strategy_id": self.strategy_id,
            "paper_validation_active": self.paper_validation_active,
            "original_campaign_start": self.original_start.isoformat(),
            "paper_observation_gap": {
                "start": self.gap_start.isoformat(),
                "end": self.gap_end.isoformat(),
                "duration_calendar_days": gap_days,
                "status": "GAP_EXCLUDED_FROM_VERIFIED_OBSERVATION"
            },
            "canonical_runtime_restored": self.restored_date.isoformat(),
            "calendar_days_since_original_start": calendar_days,
            "verified_paper_observation_days": verified_days,
            "target_verified_observation_days": self.required_verified_days,
            "verified_days_remaining": max(0, self.required_verified_days - verified_days),
            "closed_paper_trades_count": closed_trades,
            "target_closed_paper_trades": self.required_closed_trades,
            "trades_remaining": max(0, self.required_closed_trades - closed_trades),
            "validation_clock_counters": {
                "calendar_days_active": calendar_days_active,
                "market_sessions_completed": market_sessions_completed,
                "d21_valid_evaluation_sessions": d21_valid_evaluation_sessions,
                "paper_closed_trades": paper_closed_trades,
            },
            "calendar_days_active": calendar_days_active,
            "market_sessions_completed": market_sessions_completed,
            "d21_valid_evaluation_sessions": d21_valid_evaluation_sessions,
            "paper_closed_trades": paper_closed_trades,
            "meets_duration_gate": meets_days,
            "meets_trade_count_gate": meets_trades,
            "ready_for_committee_review": ready_for_committee_review,
            "as_of_date": today.isoformat()
        }

    def _get_d21_valid_evaluations_count(self) -> int:
        """Cuenta las sesiones de evaluación formal de D21 registradas en la persistencia."""
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_executions'")
            if c.fetchone():
                c.execute(
                    "SELECT count(DISTINCT execution_date) FROM task_executions "
                    "WHERE task_id LIKE 'daily_post_close_%' AND status='SUCCESS'"
                )
                row = c.fetchone()
                count = row[0] if row else 0
                conn.close()
                return count
            conn.close()
        except Exception:
            pass
        return 0

    def _get_closed_paper_trades_count(self) -> int:
        """Cuenta los trades cerrados persistidos en la base de datos sin fabricar historial."""
        try:
            conn = get_connection()
            c = conn.cursor()
            # Verificar si existe tabla de trades
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
            if c.fetchone():
                c.execute("SELECT count(*) FROM trades WHERE strategy = ? AND status = 'CLOSED'", (self.strategy_id,))
                count = c.fetchone()[0]
                conn.close()
                return count
            conn.close()
        except Exception:
            pass
        return 0

    def sync_to_db(self):
        """Persiste el estado del reloj de validación en la tabla settings de SQLite."""
        data = self.calculate_metrics()
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, ("d21_paper_campaign_status", json.dumps(data, indent=2)))
        conn.commit()
        conn.close()
        return data


d21_campaign_tracker = PaperValidationCampaignTracker()
