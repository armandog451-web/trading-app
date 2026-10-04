"""
ai_trading_agent.api.app
========================
Servidor API REST FastAPI para AI Trading Agent 1.0 (Instrucción 5 y 14).
Permite la inspección en tiempo real, análisis bajo demanda, ejecución de backtests y control del Kill Switch.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.enums import TradingMode
from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.data.synthetic import synthetic_generator
from ai_trading_agent.orchestrator import orchestrator
from ai_trading_agent.backtest.engine import backtest_engine
from ai_trading_agent.journal.trade_journal import trade_journal
from ai_trading_agent.execution.paper_broker import paper_broker
from ai_trading_agent.execution.brokers.unified_manager import unified_broker
from ai_trading_agent.reporting.explanation_engine import explanation_engine
from ai_trading_agent.notifications.telegram_service import telegram_notifier
from ai_trading_agent.scanner.scheduler import weekend_scheduler
from ai_trading_agent.scanner.report_formatter import format_report_to_markdown

templates_dir = Path(__file__).resolve().parent / "templates"
dashboard_html_path = templates_dir / "dashboard.html"


app = FastAPI(
    title="AI Trading Agent 1.0 — Core Engine API",
    version="1.2.0",
    description="Arquitectura cuantitativa determinista para análisis y Paper Trading sin riesgo de dinero real."
)


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard() -> HTMLResponse:
    """Panel de control visual institucional (SuperRobot Dashboard)."""
    if dashboard_html_path.exists():
        content = dashboard_html_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h1>Dashboard template not found</h1>", status_code=404)


class AnalyzeRequest(BaseModel):
    symbol: str = "AAPL"
    bars_count: int = 100
    regime: str = "BULL_TREND"
    has_earnings_today: bool = False
    options_pc_sentiment: Optional[str] = "BALANCED_NORMAL"


class BacktestRequest(BaseModel):
    symbol: str = "SPY"
    bars_count: int = 200
    regime: str = "BULL_TREND"
    train_ratio: float = 0.70
    initial_capital: float = 100000.0


class SwitchBrokerRequest(BaseModel):
    broker: str  # "moomoo", "alpaca", "paper"


class KillSwitchRequest(BaseModel):
    active: bool
    reason: str = "Intervención de operador"


@app.get("/health")
def health_check() -> Dict[str, Any]:
    """Estado operativo de salud, modo y kill switch."""
    return {
        "status": "HEALTHY",
        "system": "AI Trading Agent 1.0",
        "trading_mode": settings.TRADING_MODE,
        "kill_switch_active": settings.KILL_SWITCH_ACTIVE,
        "active_broker": unified_broker.active_broker_name,
        "telegram_enabled": telegram_notifier.is_configured,
        "risk_per_trade_pct": settings.RISK_PER_TRADE_PCT,
        "max_daily_loss_pct": settings.MAX_DAILY_LOSS_PCT,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/account")
def get_account() -> Dict[str, Any]:
    """Resumen de cuenta de simulación o en vivo según el broker activo."""
    return {
        "account": unified_broker.get_account_summary(),
        "positions": unified_broker.get_positions(),
        "active_broker": unified_broker.active_broker_name
    }


@app.post("/api/broker/switch")
def switch_broker(req: SwitchBrokerRequest) -> Dict[str, Any]:
    """Cambia dinámicamente el broker activo ('moomoo', 'alpaca', 'paper')."""
    new_broker = unified_broker.set_active_broker(req.broker)
    return {
        "active_broker": new_broker,
        "account": unified_broker.get_account_summary()
    }


@app.post("/api/telegram/test")
def test_telegram() -> Dict[str, Any]:
    """Envía un mensaje de prueba al chat de Telegram del usuario."""
    text = (
        "🤖 *SUPERROBOT — TEST DE CONEXIÓN A TELEGRAM*\n\n"
        "¡Conexión verificada con éxito!\n"
        f"• Broker Activo: `{unified_broker.active_broker_name.upper()}`\n"
        f"• Modo Operativo: `{settings.TRADING_MODE}`\n"
        f"• Fecha / Hora: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}`"
    )
    ok = telegram_notifier.send_message_sync(text)
    return {"success": ok, "bot_configured": telegram_notifier.is_configured}


@app.post("/api/telegram/balance")
def send_telegram_balance() -> Dict[str, Any]:
    """Envía el balance actual y posiciones abiertas a Telegram."""
    acc = unified_broker.get_account_summary()
    pos = unified_broker.get_positions()
    ok = telegram_notifier.send_balance_alert(acc, pos)
    return {"success": ok, "broker": unified_broker.active_broker_name}


@app.post("/api/analyze")
def analyze_symbol(req: AnalyzeRequest) -> Dict[str, Any]:
    """Ejecuta el pipeline completo de análisis, confirmación y explicabilidad."""
    bars = synthetic_generator.generate_bars(
        symbol=req.symbol,
        count=req.bars_count,
        regime=req.regime
    )

    calendar = {"has_earnings_today": req.has_earnings_today}
    options_ctx = {"sentiment": req.options_pc_sentiment}

    pipeline_result = orchestrator.process_symbol(
        symbol=req.symbol,
        bars=bars,
        options_context=options_ctx,
        event_calendar=calendar
    )

    explanation = explanation_engine.explain(pipeline_result)

    return {
        "result": pipeline_result,
        "explanation": explanation.model_dump()
    }


@app.post("/api/backtest")
def run_backtest(req: BacktestRequest) -> Dict[str, Any]:
    """Ejecuta un backtest cronológico barra a barra con división In-Sample vs Out-of-Sample."""
    bars = synthetic_generator.generate_bars(
        symbol=req.symbol,
        count=req.bars_count,
        regime=req.regime
    )

    train_bars, test_bars = backtest_engine.split_data(bars, train_ratio=req.train_ratio)

    is_report = backtest_engine.run(symbol=req.symbol, bars=train_bars, dataset_type="IN_SAMPLE")
    oos_report = backtest_engine.run(symbol=req.symbol, bars=test_bars, dataset_type="OUT_OF_SAMPLE")

    return {
        "symbol": req.symbol,
        "in_sample": is_report.model_dump(),
        "out_of_sample": oos_report.model_dump(),
        "split_ratio": req.train_ratio
    }


@app.get("/api/journal")
def get_journal(limit: int = 50) -> Dict[str, Any]:
    """Historial inmutable de auditoría de decisiones registradas."""
    history = trade_journal.get_history(limit=limit)
    return {
        "total_records": len(history),
        "records": [h.model_dump() for h in history]
    }


@app.post("/api/kill-switch")
def toggle_kill_switch(req: KillSwitchRequest) -> Dict[str, Any]:
    """Activa o desactiva de inmediato el Kill Switch general de seguridad y alerta a Telegram."""
    settings.KILL_SWITCH_ACTIVE = req.active
    try:
        telegram_notifier.send_kill_switch_alert(req.active, req.reason)
    except Exception:
        pass
    return {
        "kill_switch_active": settings.KILL_SWITCH_ACTIVE,
        "reason": req.reason,
        "timestamp": datetime.utcnow().isoformat()
    }


class RunScanRequest(BaseModel):
    force: bool = True
    send_telegram: bool = True


@app.post("/api/scanner/run")
def run_weekend_scan(req: RunScanRequest = Body(default=RunScanRequest())) -> Dict[str, Any]:
    """Ejecuta el escaneo del fin de semana (Analysis Only), genera escenarios y alerta a Telegram."""
    res = weekend_scheduler.run_scan(force=req.force, send_telegram=req.send_telegram)
    return res


@app.get("/api/scanner/latest")
def get_latest_weekend_scan() -> Dict[str, Any]:
    """Retorna el último informe de escaneo de fin de semana guardado."""
    report = weekend_scheduler.get_latest_report()
    if not report:
        return {"has_report": False, "report": None, "message": "No hay escaneos de fin de semana registrados aún."}
    return {"has_report": True, "report": report}


@app.get("/api/scanner/status")
def get_scanner_status() -> Dict[str, Any]:
    """Estado del programador de fin de semana, zona horaria y próxima ventana."""
    return weekend_scheduler.get_status()


@app.get("/api/scanner/export")
def export_weekend_scan(format: str = Query("markdown", description="'markdown' o 'json'")) -> Any:
    """Exporta el último reporte de fin de semana en formato Markdown institucional de 12 secciones o JSON."""
    report = weekend_scheduler.get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="No se encontró ningún reporte para exportar.")

    if format.lower() == "json":
        return report

    markdown_text = format_report_to_markdown(report)
    return PlainTextResponse(content=markdown_text, media_type="text/markdown")


class RunScheduleTaskRequest(BaseModel):
    task_name: str  # 'premarket_scan', 'weekend_scan', 'daily_report'
    force: bool = True


@app.get("/api/schedule/status")
def get_schedule_status() -> Dict[str, Any]:
    """Obtiene la visión completa del calendario bursátil, estado de sesión y tareas programadas."""
    from ai_trading_agent.schedule.scheduler_service import master_scheduler
    return master_scheduler.get_full_schedule_status()


@app.post("/api/schedule/run-task")
async def run_schedule_task(req: RunScheduleTaskRequest = Body(...)) -> Dict[str, Any]:
    """Ejecución manual de tareas programadas desde el Dashboard (premarket_scan, weekend_scan, daily_report)."""
    from ai_trading_agent.schedule.scheduler_service import master_scheduler
    t_name = req.task_name.lower()
    if t_name == "premarket_scan":
        return await master_scheduler.run_premarket_scan(force=req.force)
    elif t_name == "weekend_scan":
        return await master_scheduler.run_weekend_scan(force=req.force)
    elif t_name == "daily_report":
        return await master_scheduler.run_daily_report(force=req.force)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Tarea '{req.task_name}' no reconocida. Opciones válidas: 'premarket_scan', 'weekend_scan', 'daily_report'."
        )


# --- STRATEGY LABORATORY ENDPOINTS ---

class PromoteStrategyRequest(BaseModel):
    strategy_id: str
    target_status: str  # RESEARCH, BACKTEST, VALIDATING, CANDIDATE, PAPER, APPROVED, REJECTED, PAUSED
    reason: str = "Promoción vía API"


@app.get("/api/strategy-lab/overview")
def get_strategy_lab_overview() -> Dict[str, Any]:
    """Retorna el resumen ejecutivo del Strategy Laboratory."""
    from ai_trading_agent.strategy_lab.reporting.generator import lab_reporting_generator
    return lab_reporting_generator.generate_laboratory_overview()


@app.get("/api/strategy-lab/strategies")
def list_lab_strategies(status: Optional[str] = None) -> Dict[str, Any]:
    """Lista el catálogo de estrategias investigadas y registradas en SQLite."""
    from ai_trading_agent.strategy_lab.registry.registry import strategy_registry
    from ai_trading_agent.strategy_lab.core.models import StrategyStatus
    status_filter = StrategyStatus(status) if status else None
    strats = strategy_registry.list_strategies(status_filter=status_filter)
    return {
        "count": len(strats),
        "strategies": [s.model_dump() for s in strats]
    }


@app.post("/api/strategy-lab/research/run")
def run_autonomous_research(symbol: str = Query("SPY")) -> Dict[str, Any]:
    """Dispara un ciclo autónomo completo de investigación (Hipótesis ➔ Experimento ➔ Robustez ➔ Ranking)."""
    from ai_trading_agent.strategy_lab.research.agent import ai_research_agent
    res = ai_research_agent.run_autonomous_research_cycle(symbol=symbol)
    return res


@app.post("/api/strategy-lab/strategy/promote")
def promote_lab_strategy(req: PromoteStrategyRequest) -> Dict[str, Any]:
    """Evalúa y promueve una estrategia a través de las puertas del ciclo de vida."""
    from ai_trading_agent.strategy_lab.lifecycle.manager import lifecycle_manager
    from ai_trading_agent.strategy_lab.core.models import StrategyStatus

    try:
        target_enum = StrategyStatus(req.target_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Estado objetivo inválido: {req.target_status}")

    success, msg, strat = lifecycle_manager.promote_strategy(
        strategy_id=req.strategy_id,
        target_status=target_enum,
        reason=req.reason,
        actor="HUMAN_OPERATOR"
    )

    if not success:
        raise HTTPException(status_code=400, detail=msg)

    return {
        "success": True,
        "message": msg,
        "strategy": strat.model_dump() if strat else None
    }


# --- STRATEGY DISCOVERY ENGINE v1.0 ENDPOINTS ---

class RunDiscoveryRequest(BaseModel):
    max_experiments: int = 5
    max_time_seconds: int = 120
    target_market: str = "BTC/USDT"
    target_timeframe: str = "1h"


@app.get("/api/strategy-lab/discovery/features")
def list_discovery_features() -> Dict[str, Any]:
    """Lista el catálogo de features cuantitativos verificados del Discovery Engine."""
    from ai_trading_agent.strategy_lab.discovery.feature_universe import feature_universe
    features = feature_universe.list_features()
    return {
        "count": len(features),
        "features": [f.model_dump() for f in features]
    }


@app.get("/api/strategy-lab/discovery/memory")
def get_discovery_memory() -> Dict[str, Any]:
    """Obtiene el historial de memoria cuantitativa y los mejores features observados."""
    from ai_trading_agent.strategy_lab.discovery.orchestrator import DiscoveryOrchestrator
    orchestrator = DiscoveryOrchestrator()
    return {
        "top_features": orchestrator.memory.get_top_performing_features(top_n=5),
        "failed_patterns": orchestrator.memory.get_failed_patterns(),
        "total_observations": len(orchestrator.memory.get_all_observations())
    }


@app.post("/api/strategy-lab/discovery/run")
def run_discovery_session(req: RunDiscoveryRequest = Body(...)) -> Dict[str, Any]:
    """Ejecuta una sesión de descubrimiento autónomo cuantitativo con presupuesto controlado."""
    from ai_trading_agent.strategy_lab.discovery.orchestrator import DiscoveryOrchestrator, ResearchBudget
    budget = ResearchBudget(
        max_experiments=req.max_experiments,
        max_time_seconds=req.max_time_seconds
    )
    orchestrator = DiscoveryOrchestrator()
    report = orchestrator.run_autonomous_research_session(
        budget=budget,
        target_market=req.target_market,
        target_timeframe=req.target_timeframe
    )
    return report.model_dump()



