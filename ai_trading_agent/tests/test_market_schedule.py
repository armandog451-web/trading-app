"""
ai_trading_agent.tests.test_market_schedule
============================================
Pruebas unitarias completas para el módulo centralizado MarketScheduleService y MarketCalendarService.
Prueba:
1. Zona horaria America/New_York (zoneinfo) y cálculo dinámico de festivos.
2. Días hábiles, festivos de EE. UU. (Independence Day, Good Friday) y cierres anticipados.
3. Transición de estados de mercado (PREMARKET, REGULAR, AFTER_HOURS, CLOSED, HOLIDAY).
4. Próxima apertura y próximo cierre del mercado.
5. Idempotencia y prevención de ejecuciones duplicadas de tareas.
6. API Endpoints (/api/schedule/status y /api/schedule/run-task).
7. Invariancia del modo de operación (ANALYSIS_ONLY por defecto).
"""

import pytest
from datetime import datetime, date, time, timedelta
import zoneinfo
from starlette.testclient import TestClient

from ai_trading_agent.schedule.market_calendar import MarketCalendarService
from ai_trading_agent.schedule.scheduler_service import MarketScheduleService
from ai_trading_agent.api.app import app
from ai_trading_agent.config.settings import settings


class TestMarketScheduleSuite:
    """Suite de pruebas unitarias para programación horaria y calendario bursátil."""

    @pytest.fixture
    def calendar(self):
        return MarketCalendarService(tz_name="America/New_York")

    @pytest.fixture
    def scheduler(self, calendar):
        return MarketScheduleService(calendar=calendar)

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_timezone_is_america_new_york(self, calendar):
        """Verifica que la zona horaria esté configurada en America/New_York."""
        now_local = calendar.get_now()
        assert now_local.tzinfo is not None
        assert "New_York" in str(now_local.tzinfo)

    def test_us_holidays_calculation(self, calendar):
        """Verifica la detección de festivos oficiales (NYSE/NASDAQ)."""
        # 4 de Julio 2026 (Sábado -> Observado el Viernes 3 de Julio)
        holidays_2026 = calendar.get_us_holidays(2026)
        assert any(d.month == 7 and d.year == 2026 for d in holidays_2026.keys())
        
        # Test con una fecha de festivo fija: Navidad 2025 (25 Diciembre 2025 - Jueves)
        xmas_2025 = datetime(2025, 12, 25, 10, 0, tzinfo=calendar.tz)
        is_hol, hol_name = calendar.is_holiday(xmas_2025)
        assert is_hol is True
        assert "Christmas" in hol_name
        assert calendar.is_trading_day(xmas_2025) is False

    def test_early_close_calculation(self, calendar):
        """Verifica la detección de días con cierre anticipado (1:00 PM ET)."""
        # Black Friday 2026 (Viernes 27 de Noviembre 2026)
        black_friday_2026 = datetime(2026, 11, 27, 10, 0, tzinfo=calendar.tz)
        is_early, reason = calendar.is_early_close(black_friday_2026)
        assert is_early is True
        assert "Black Friday" in reason

        m_state = calendar.get_market_state(black_friday_2026)
        assert m_state["regular_close"] == "13:00"

    def test_market_state_transitions(self, calendar):
        """Verifica las transacciones de ventanas horarias en un día laborable normal."""
        # Un Miércoles normal (15 de Octubre de 2025)
        dt_base = date(2025, 10, 15)

        # 1. Premarket Prep (8:00 AM ET)
        dt_prem = datetime.combine(dt_base, time(8, 0), tzinfo=calendar.tz)
        st_prem = calendar.get_market_state(dt_prem)
        assert st_prem["status"] == "PREMARKET"
        assert st_prem["window"] == "PREMARKET_PREP"

        # 2. Opening ORB (9:45 AM ET)
        dt_orb = datetime.combine(dt_base, time(9, 45), tzinfo=calendar.tz)
        st_orb = calendar.get_market_state(dt_orb)
        assert st_orb["status"] == "REGULAR"
        assert st_orb["window"] == "OPENING_ORB"

        # 3. Regular Session (2:00 PM ET)
        dt_reg = datetime.combine(dt_base, time(14, 0), tzinfo=calendar.tz)
        st_reg = calendar.get_market_state(dt_reg)
        assert st_reg["status"] == "REGULAR"
        assert st_reg["window"] == "REGULAR_SESSION"

        # 4. Closing Prep (3:45 PM ET)
        dt_close_prep = datetime.combine(dt_base, time(15, 45), tzinfo=calendar.tz)
        st_close_prep = calendar.get_market_state(dt_close_prep)
        assert st_close_prep["status"] == "REGULAR"
        assert st_close_prep["window"] == "CLOSING_PREP"

        # 5. Post Close Review (4:30 PM ET)
        dt_post = datetime.combine(dt_base, time(16, 30), tzinfo=calendar.tz)
        st_post = calendar.get_market_state(dt_post)
        assert st_post["status"] == "AFTER_HOURS"
        assert st_post["window"] == "POST_CLOSE_REVIEW"

    def test_next_market_open_and_close(self, calendar):
        """Verifica el cálculo de la próxima apertura y cierre regular."""
        # Viernes 10 de Octubre de 2025 a las 5:00 PM ET (Mercado cerrado por fin de semana)
        dt_fri_night = datetime(2025, 10, 10, 17, 0, tzinfo=calendar.tz)
        next_open = calendar.get_next_market_open(dt_fri_night)
        
        # El próximo día de apertura debe ser Lunes 13 de Octubre a las 9:30 AM ET
        assert next_open.date() == date(2025, 10, 13)
        assert next_open.time() == time(9, 30)

        next_close = calendar.get_next_market_close(dt_fri_night)
        assert next_close.date() == date(2025, 10, 13)
        assert next_close.time() == time(16, 0)

    def test_scheduler_task_execution_and_idempotency(self, scheduler):
        """Verifica la prevención de tareas duplicadas en el mismo día."""
        import asyncio
        import uuid
        # Miércoles 14 de Mayo de 2025 (Día Hábil de Mercado garantizado)
        run_id = uuid.uuid4().hex[:6]
        dt_test = datetime(2025, 5, 14, 9, 20, tzinfo=scheduler.calendar.tz)
        scheduler.calendar.set_mock_clock(lambda: dt_test)

        # Limpiar cualquier log previo de la prueba
        from ai_trading_agent.data.storage.repository import audit_repo
        from ai_trading_agent.data.storage.models import DBTaskLog
        with audit_repo.get_session() as session:
            session.query(DBTaskLog).filter(DBTaskLog.task_id.like("%premarket_scan%")).delete(synchronize_session=False)
            session.commit()
        scheduler._last_executions.clear()

        # 1. Primera ejecución premarket
        res1 = asyncio.run(scheduler.run_premarket_scan(force=False))
        assert res1["success"] is True
        assert res1["status"] == "SUCCESS"

        # 2. Segunda ejecución (debe ser bloqueada como duplicada)
        res2 = asyncio.run(scheduler.run_premarket_scan(force=False))
        assert res2["success"] is False
        assert res2["status"] == "DUPLICATE_SKIPPED"

        # 3. Ejecución forzada manual (debe omitir el filtro de duplicados)
        res3 = asyncio.run(scheduler.run_premarket_scan(force=True))
        assert res3["success"] is True

    def test_api_schedule_endpoints(self, client):
        """Verifica los endpoints /api/schedule/status y /api/schedule/run-task."""
        # Status GET
        response = client.get("/api/schedule/status")
        assert response.status_code == 200
        data = response.json()
        assert "current_time_et" in data
        assert "market_state" in data
        assert "operating_mode" in data

        # Run Task POST
        post_resp = client.post(
            "/api/schedule/run-task",
            json={"task_name": "premarket_scan", "force": True}
        )
        assert post_resp.status_code == 200
        post_data = post_resp.json()
        assert post_data["success"] is True

    def test_operating_mode_default_analysis_only(self):
        """Garantiza que el modo operativo predeterminado permanezca inviolable en ANALYSIS_ONLY."""
        assert settings.TRADING_MODE.value == "ANALYSIS_ONLY"
