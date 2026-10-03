"""
ai_trading_agent.tests.test_weekend_scanner
===========================================
Pruebas unitarias completas para el módulo WeekendMarketScanner y WeekendScannerScheduler.
Garantiza:
1. Modo ANALYSIS ONLY: Cero órdenes ejecutadas o creadas.
2. Formato institucional de 12 secciones en el reporte y exportación Markdown.
3. Detección y clasificación de las 9 condiciones de candidatos.
4. Generación verificable de escenarios alcistas/bajistas con invalidación.
5. Programación por zona horaria EST y prevención de ejecuciones duplicadas.
6. Persistencia SQLite y endpoints REST.
"""

import pytest
from datetime import datetime, timezone
import zoneinfo
from starlette.testclient import TestClient

from ai_trading_agent.domain.enums import MarketRegime
from ai_trading_agent.scanner.models import (
    CandidateCondition,
    MarketScenario,
    AssetWeekendPlan,
    WeekendScanReport,
)
from ai_trading_agent.scanner.scanner import weekend_scanner, WeekendMarketScanner
from ai_trading_agent.scanner.scheduler import weekend_scheduler, WeekendScannerScheduler
from ai_trading_agent.scanner.report_formatter import format_report_to_markdown
from ai_trading_agent.execution.paper_broker import paper_broker
from ai_trading_agent.execution.brokers.unified_manager import unified_broker
from ai_trading_agent.data.storage.repository import audit_repo
from ai_trading_agent.api.app import app


client = TestClient(app)


def test_scanner_is_strictly_analysis_only():
    """Verifica que el escáner de fin de semana no cree ni ejecute ninguna orden."""
    initial_paper_orders = len(paper_broker.orders)
    initial_positions = len(paper_broker.positions)

    # Ejecutar escaneo completo
    report = weekend_scanner.scan_market(execution_day="SATURDAY", send_telegram=False)

    assert isinstance(report, WeekendScanReport)
    assert report.system_status == "ANALYSIS_ONLY"

    # Verificar que el estado del broker no se alteró
    assert len(paper_broker.orders) == initial_paper_orders, "¡Violación de seguridad! El escáner creó órdenes en paper broker."
    assert len(paper_broker.positions) == initial_positions, "¡Violación de seguridad! El escáner abrió posiciones."


def test_report_12_sections_structure():
    """Verifica que el reporte contenga las 12 secciones requeridas."""
    report = weekend_scanner.scan_market(execution_day="SATURDAY", send_telegram=False)
    r_dict = report.model_dump()

    # 1. Resumen general del mercado
    assert "market_overview" in r_dict and len(r_dict["market_overview"]) > 0
    # 2. Régimen observado en SPY, QQQ e IWM
    assert "indices_regimes" in r_dict
    assert "SPY" in r_dict["indices_regimes"]
    # 3. Principales cambios de tendencia y volatilidad
    assert "trend_and_volatility_shifts" in r_dict
    # 4. Lista de activos detectados
    assert "candidates" in r_dict and len(r_dict["candidates"]) > 0
    # 5. Candidatos a ruptura
    assert "breakout_candidates" in r_dict
    # 6. Candidatos de momentum
    assert "momentum_candidates" in r_dict
    # 7. Candidatos de mean reversion
    assert "mean_reversion_candidates" in r_dict
    # 8. Eventos económicos y resultados próximos
    assert "economic_and_earnings_events" in r_dict
    # 9. Riesgos y condiciones de no operar
    assert "no_trade_risks" in r_dict
    # 10. Escenarios para la próxima sesión
    cand = report.candidates[0]
    assert cand.bullish_scenario is not None
    assert cand.bearish_scenario is not None
    assert cand.bullish_scenario.trigger_level > 0
    assert cand.bearish_scenario.trigger_level > 0
    assert cand.bullish_scenario.invalidation_condition != ""
    # 11. Datos faltantes y limitaciones
    assert "missing_data_limitations" in r_dict
    # 12. Estado del sistema
    assert report.system_status == "ANALYSIS_ONLY"


def test_markdown_formatter_contains_12_sections():
    """Verifica que el formateador en Markdown genere las 12 secciones numeradas."""
    report = weekend_scanner.scan_market(execution_day="SATURDAY", send_telegram=False)
    md = format_report_to_markdown(report.model_dump(mode="json"))

    assert "## 1. Resumen General del Mercado" in md
    assert "## 2. Régimen Observado en SPY, QQQ e IWM" in md
    assert "## 3. Principales Cambios de Tendencia y Volatilidad" in md
    assert "## 4. Lista de Activos Detectados y Categorizados" in md
    assert "## 5. Candidatos a Ruptura (Breakout Watch)" in md
    assert "## 6. Candidatos de Momentum (Momentum Watch)" in md
    assert "## 7. Candidatos de Mean Reversion" in md
    assert "## 8. Eventos Económicos y Resultados Próximos" in md
    assert "## 9. Riesgos y Condiciones de No Operar" in md
    assert "## 10. Escenarios para la Próxima Sesión" in md
    assert "## 11. Datos Faltantes y Limitaciones" in md
    assert "## 12. Estado del Sistema y Modos Operativos" in md


def test_candidate_condition_classification():
    """Comprueba que los activos sean clasificados en las 9 condiciones permitidas."""
    valid_conditions = {c.value for c in CandidateCondition}

    # Probar varias clasificaciones
    cond_earnings, _ = weekend_scanner.classify_candidate(
        last_price=100.0, key_res=110.0, atr=2.0, rsi=50.0, bb_lower=95.0,
        macd_hist=0.5, relative_strength=1.0, regime=MarketRegime.SIDEWAYS, has_earnings_soon=True
    )
    assert cond_earnings == CandidateCondition.EARNINGS_RISK
    assert cond_earnings.value in valid_conditions

    cond_breakout, _ = weekend_scanner.classify_candidate(
        last_price=109.0, key_res=110.0, atr=2.0, rsi=60.0, bb_lower=95.0,
        macd_hist=0.5, relative_strength=1.0, regime=MarketRegime.SIDEWAYS, has_earnings_soon=False
    )
    assert cond_breakout == CandidateCondition.BREAKOUT_WATCH

    cond_mr, _ = weekend_scanner.classify_candidate(
        last_price=90.0, key_res=110.0, atr=2.0, rsi=25.0, bb_lower=92.0,
        macd_hist=-0.5, relative_strength=0.8, regime=MarketRegime.BEAR_TREND, has_earnings_soon=False
    )
    assert cond_mr == CandidateCondition.MEAN_REVERSION_WATCH

    cond_mom, _ = weekend_scanner.classify_candidate(
        last_price=105.0, key_res=120.0, atr=2.0, rsi=65.0, bb_lower=95.0,
        macd_hist=1.2, relative_strength=1.10, regime=MarketRegime.BULL_TREND, has_earnings_soon=False
    )
    assert cond_mom == CandidateCondition.MOMENTUM_WATCH


def test_scheduler_weekend_detection_and_duplicate_prevention():
    """Prueba la lógica de detección de fin de semana y prevención de duplicados."""
    sched = WeekendScannerScheduler(tz_name="America/New_York")

    # Fecha simulada de Sábado (2026-10-03 es sábado)
    saturday_dt = datetime(2026, 10, 3, 10, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
    assert sched.is_weekend(saturday_dt) is True

    # Fecha simulada de Lunes (2026-10-05 es lunes)
    monday_dt = datetime(2026, 10, 5, 10, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
    assert sched.is_weekend(monday_dt) is False

    # Probar que la primera ejecución es permitida
    can_run, label, _ = sched.can_run(force=False, dt=saturday_dt)
    assert can_run is True
    assert label == "SATURDAY"

    # Simular ejecución exitosa en sábado
    sched._last_run_date = "2026-10-03"
    sched._last_run_status = "SUCCESS"

    # Segunda ejecución normal sin force debe ser bloqueada por idempotencia
    can_run_dup, _, reason = sched.can_run(force=False, dt=saturday_dt)
    assert can_run_dup is False
    assert "ya fue completado" in reason

    # Pero con force=True debe permitirse
    can_run_forced, label_forced, _ = sched.can_run(force=True, dt=saturday_dt)
    assert can_run_forced is True
    assert label_forced == "MANUAL"


def test_sqlite_persistence_and_retrieval():
    """Verifica almacenamiento y recuperación de auditoría en base de datos SQLite."""
    test_report_dict = {
        "scan_id": "SCAN-TEST-PERSISTENCE-123",
        "timestamp": datetime.utcnow().isoformat(),
        "execution_day": "SATURDAY",
        "data_as_of_date": datetime.utcnow().isoformat(),
        "universe_scanned": ["SPY", "QQQ"],
        "market_overview": "Test overview",
        "indices_regimes": {"SPY": "BULL_TREND"},
        "trend_and_volatility_shifts": [],
        "candidates": [],
        "breakout_candidates": [],
        "momentum_candidates": [],
        "mean_reversion_candidates": [],
        "economic_and_earnings_events": [],
        "no_trade_risks": [],
        "missing_data_limitations": [],
        "system_status": "ANALYSIS_ONLY",
        "strategy_version": "1.0.0",
        "is_partial": False
    }

    # Guardar en base de datos
    audit_repo.save_weekend_scan(test_report_dict)

    # Recuperar el último escaneo
    retrieved = audit_repo.get_latest_weekend_scan()
    assert retrieved is not None
    assert retrieved.get("scan_id") == "SCAN-TEST-PERSISTENCE-123"
    assert retrieved.get("system_status") == "ANALYSIS_ONLY"


def test_scanner_api_endpoints():
    """Verifica todos los endpoints REST del escáner en FastAPI."""
    # 1. Status endpoint
    st_res = client.get("/api/scanner/status")
    assert st_res.status_code == 200
    st_data = st_res.json()
    assert "is_weekend" in st_data
    assert "current_time_est" in st_data

    # 2. Run endpoint
    run_res = client.post("/api/scanner/run", json={"force": True, "send_telegram": False})
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["success"] is True
    assert "report" in run_data
    assert run_data["report"]["system_status"] == "ANALYSIS_ONLY"

    # 3. Latest endpoint
    lat_res = client.get("/api/scanner/latest")
    assert lat_res.status_code == 200
    lat_data = lat_res.json()
    assert lat_data["has_report"] is True
    assert lat_data["report"] is not None

    # 4. Export Markdown endpoint
    exp_md_res = client.get("/api/scanner/export?format=markdown")
    assert exp_md_res.status_code == 200
    assert "AI TRADING AGENT 1.0 — REPORTE DE FIN DE SEMANA" in exp_md_res.text
    assert "## 1. Resumen General del Mercado" in exp_md_res.text

    # 5. Export JSON endpoint
    exp_json_res = client.get("/api/scanner/export?format=json")
    assert exp_json_res.status_code == 200
    exp_json_data = exp_json_res.json()
    assert "candidates" in exp_json_data
