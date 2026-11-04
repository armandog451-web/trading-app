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
        self.last_d21_read_status = "UNINITIALIZED"
        self.last_d21_error_details = None

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

        # Distinguir disponibilidad de telemetría vs madurez de campaña
        if self.last_d21_read_status != "OK":
            evidence_availability = "EVIDENCE_UNAVAILABLE"
        else:
            evidence_availability = "EVIDENCE_AVAILABLE"

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
                "d21_evaluation_read_status": self.last_d21_read_status,
            },
            "d21_evaluation_read_status": self.last_d21_read_status,
            "evidence_availability": evidence_availability,
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
        """
        Cuenta exclusivamente evaluaciones ordinarias en tiempo real con evidencia científica completa.
        Garantiza:
        1. Resolución de BD absoluta vía configuración canónica (settings.DATABASE_URL).
        2. Tarea canónica exact: daily_post_close_{date_str} con status = 'SUCCESS'.
        3. Fecha de mercado válida y fuera de la brecha [2026-10-06, 2026-10-20].
        4. Cobertura efectiva obligatoria de SPY, QQQ, IWM y DIA en evaluated_symbols.
        5. Resultados individuales válidos (NO_TRADE, BUY, SELL) sin errores.
        6. Telemetría obligatoria con d21_last_evaluated_bar == date_str y status == SUCCESS.
        7. Validación temporal completa:
           - Timestamp con zona horaria inequívoca (offset o 'Z').
           - Ejecutado en el mismo día bursátil (exec_dt_et.date() == d_obj).
           - Estrictamente posterior al cierre bursátil oficial aplicable (exec_dt_et > close_dt_et).
        8. Deduplicación por fecha de sesión.
        9. Distinción explícita de estados de persistencia: OK, DB_NOT_FOUND, TABLE_NOT_FOUND, READ_ERROR.
        """
        try:
            from pathlib import Path
            import sqlite3
            import json
            import pytz
            from datetime import time
            from ai_trading_agent.config.settings import settings
            from ai_trading_agent.schedule.market_calendar import market_calendar

            # 1. Resolución canónica absoluta
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            db_rel = settings.DATABASE_URL.replace("sqlite:///", "")
            db_path = (repo_root / db_rel).resolve()

            if not db_path.exists():
                self.last_d21_read_status = "DB_NOT_FOUND"
                self.last_d21_error_details = f"File not found: {db_path}"
                return 0

            conn = sqlite3.connect(str(db_path), timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_logs_audit'")
            if not cursor.fetchone():
                self.last_d21_read_status = "TABLE_NOT_FOUND"
                self.last_d21_error_details = "Table task_logs_audit missing"
                conn.close()
                return 0

            query = """
            SELECT id, task_id, date_str, timestamp, status, payload_json
            FROM task_logs_audit
            WHERE task_id LIKE 'daily_post_close_%' AND status = 'SUCCESS'
            ORDER BY id ASC
            """
            rows = cursor.execute(query).fetchall()
            conn.close()

            tz = pytz.timezone("America/New_York")
            required_symbols = {"SPY", "QQQ", "IWM", "DIA"}
            valid_decisions = {"NO_TRADE", "BUY", "SELL"}
            valid_dates = set()

            for row_id, task_id, date_str, ts_str, status, payload_raw in rows:
                try:
                    d_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    continue

                if self.gap_start <= d_obj <= self.gap_end:
                    continue

                expected_task_id = f"daily_post_close_{date_str}"
                if task_id != expected_task_id:
                    continue

                try:
                    payload = json.loads(payload_raw) if payload_raw else {}
                except (json.JSONDecodeError, TypeError):
                    continue

                d21_eval = payload.get("d21_evaluation")
                if not isinstance(d21_eval, dict):
                    continue

                eval_symbols = d21_eval.get("evaluated_symbols")
                if not isinstance(eval_symbols, dict) or not required_symbols.issubset(set(eval_symbols.keys())):
                    continue

                if any(eval_symbols.get(s) not in valid_decisions for s in required_symbols):
                    continue

                telemetry = d21_eval.get("telemetry")
                if not isinstance(telemetry, dict) or not telemetry:
                    continue

                last_bar = telemetry.get("d21_last_evaluated_bar")
                if not last_bar or last_bar != date_str:
                    continue

                if telemetry.get("d21_last_evaluation_status") != "SUCCESS":
                    continue

                # Validación temporal completa con zona horaria inequívoca
                exec_ts_str = payload.get("timestamp") or ts_str
                if not exec_ts_str or not isinstance(exec_ts_str, str):
                    continue

                try:
                    ts_clean = exec_ts_str.replace("Z", "+00:00")
                    dt_parsed = datetime.fromisoformat(ts_clean)
                    if dt_parsed.tzinfo is None:
                        continue
                    exec_dt_et = dt_parsed.astimezone(tz)
                except Exception:
                    continue

                # Evaluación ordinaria debe ejecutarse el mismo día de mercado
                if exec_dt_et.date() != d_obj:
                    continue

                # Horario oficial de cierre aplicable
                dt_noon = tz.localize(datetime.combine(d_obj, time(12, 0)))
                is_early, _ = market_calendar.is_early_close(dt_noon)
                applicable_close_time = time(13, 0) if is_early else time(16, 0)
                official_close_dt = tz.localize(datetime.combine(d_obj, applicable_close_time))

                # Causalidad estricta: posterior al cierre bursátil
                if exec_dt_et <= official_close_dt:
                    continue

                valid_dates.add(date_str)

            self.last_d21_read_status = "OK"
            self.last_d21_error_details = None
            return len(valid_dates)
        except Exception as e:
            self.last_d21_read_status = "READ_ERROR"
            self.last_d21_error_details = str(e)
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
