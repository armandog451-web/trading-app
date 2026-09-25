from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import Trade
from app.core.bot_runner import bot_runner
from app.core.broker_manager import broker_manager

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/status")
async def get_dashboard_status():
    """Estado en tiempo real del cockpit de trading."""
    account = await broker_manager.get_account()
    positions = await broker_manager.get_positions()

    return {
        "is_running": bot_runner.is_running,
        "mode": account.get("mode", "PAPER"),
        "market_open": True,  # Monitoreo activo
        "circuit_breaker_tripped": bot_runner.circuit_breaker_tripped,
        "account_equity": account.get("equity", 100000.0),
        "buying_power": account.get("buying_power", 200000.0),
        "daily_pnl": account.get("daily_pnl", 0.0),
        "daily_pnl_pct": account.get("daily_pnl_pct", 0.0),
        "open_positions_count": len(positions),
        "monitored_symbols": bot_runner.active_universe,
        "active_broker": broker_manager.get_active_broker_name()
    }

@router.post("/bot/start")
async def start_bot():
    """Activa el bot de trading intraday."""
    await bot_runner.start()
    return {"success": True, "message": "Bot de trading activado", "is_running": bot_runner.is_running}

@router.post("/bot/stop")
async def stop_bot():
    """Pausa el bot de trading."""
    await bot_runner.stop()
    return {"success": True, "message": "Bot de trading pausado", "is_running": bot_runner.is_running}

@router.post("/panic")
async def panic_close_all():
    """BOTÓN DE PÁNICO: Cancela órdenes y cierra todas las posiciones de inmediato."""
    res = await broker_manager.close_all_positions()
    await bot_runner.stop()
    return {"success": True, "message": "Acción de pánico ejecutada. Todas las posiciones cerradas.", "broker_response": res}

@router.get("/positions")
async def get_active_positions():
    """Obtiene las posiciones abiertas."""
    return await broker_manager.get_positions()

@router.get("/trades")
def get_trade_history(db: Session = Depends(get_db)):
    """Historial de operaciones registradas en base de datos SQLite."""
    trades = db.query(Trade).order_by(Trade.entry_time.desc()).limit(50).all()
    return trades

@router.post("/test-trade")
async def trigger_test_trade(symbol: str = "SPY"):
    """Dispara una operación de prueba inmediata para validar la cadena de ejecución."""
    account = await broker_manager.get_account()
    equity = account.get("equity", 100000.0)

    order_res = await broker_manager.submit_bracket_order(
        symbol=symbol,
        qty=10,
        side="BUY",
        entry_price=560.20,
        stop_loss=558.00,
        take_profit=565.70,
        order_type="market"
    )
    return {"success": True, "order": order_res, "message": f"Orden Bracket de prueba enviada para {symbol}"}

