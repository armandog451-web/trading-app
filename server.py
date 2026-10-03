import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config import (
    APP_NAME, HOST, PORT, BROKER, BASE_DIR,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, WATCHLIST
)
from database import init_db, get_connection, log_event
from broker import broker_manager
from telegram_service import telegram_service
from engine import strategy_engine
from guardian import guardian
from latency_guardian import latency_guardian

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando AlgortimTrading Robot v2.0 PRO...")
    init_db()
    telegram_service.start()
    strategy_engine.start()
    guardian.start()
    latency_guardian.start()
    from weekend_engine import weekend_engine
    weekend_engine.start_auto_scheduler()
    yield
    logger.info("Deteniendo AlgortimTrading Robot...")
    weekend_engine.stop_auto_scheduler()
    latency_guardian.stop()
    guardian.stop()
    strategy_engine.stop()
    telegram_service.stop()

app = FastAPI(title=APP_NAME, lifespan=lifespan)

# API ENDPOINTS
@app.get("/api/status")
def get_status():
    acc = broker_manager.get_account_summary()
    positions = broker_manager.get_positions()
    return {
        "bot_running": strategy_engine.is_running,
        "last_scan": strategy_engine.last_scan_time,
        "broker": broker_manager.active_broker.upper(),
        "account": acc,
        "positions": positions,
        "telegram_connected": bool(telegram_service.bot_token and telegram_service.chat_id),
        "telegram_chat_id": telegram_service.chat_id,
        "watchlist": WATCHLIST
    }

@app.post("/api/bot/toggle")
def toggle_bot():
    if strategy_engine.is_running:
        strategy_engine.stop()
        status = "Pausado"
    else:
        strategy_engine.start()
        status = "Activo"
    return {"success": True, "bot_running": strategy_engine.is_running, "status": status}

@app.post("/api/bot/scan-now")
async def scan_now():
    await strategy_engine.scan_market()
    return {"success": True, "message": "Escaneo ejecutado exitosamente"}

@app.get("/api/signals")
def get_signals():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 50")
    signals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return signals

@app.post("/api/orders/execute/{sig_id}")
def execute_order_api(sig_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM signals WHERE id = ?", (sig_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Señal no encontrada")
    
    if row["status"] != "PENDIENTE":
        conn.close()
        return {"success": False, "message": f"La señal ya está {row['status']}"}

    res = broker_manager.execute_order(
        symbol=row["symbol"],
        side=row["side"],
        qty=row["qty"],
        price=row["price"],
        stop_loss=row["stop_loss"],
        take_profit=row["take_profit"]
    )
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE signals SET status = 'EJECUTADA', executed_at = ? WHERE id = ?", (now, sig_id))
    conn.commit()
    conn.close()
    log_event("SUCCESS", f"Orden ID {sig_id} aprobada desde Dashboard Web para {row['symbol']}.")
    return {"success": True, "result": res}

@app.post("/api/orders/cancel/{sig_id}")
def cancel_order_api(sig_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE signals SET status = 'CANCELADA' WHERE id = ?", (sig_id,))
    conn.commit()
    conn.close()
    log_event("INFO", f"Señal ID {sig_id} cancelada desde Dashboard Web.")
    return {"success": True, "message": "Señal descartada"}

@app.get("/api/strategies")
def get_strategies():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM strategy_metrics ORDER BY weight DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

class FeedbackModel(BaseModel):
    strategy_code: str
    is_win: bool

@app.post("/api/strategies/feedback")
def strategy_feedback(fb: FeedbackModel):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM strategy_metrics WHERE name = ?", (fb.strategy_code,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")

    total = row["total_trades"] + 1
    wins = row["wins"] + (1 if fb.is_win else 0)
    losses = row["losses"] + (0 if fb.is_win else 1)
    win_rate = round((wins / total) * 100.0, 1)

    # Auto-ajuste de peso algorítmico (Aprendizaje Dinámico)
    # Aumenta peso si gana, reduce si pierde
    delta = 0.05 if fb.is_win else -0.05
    new_weight = max(0.4, min(2.0, round(row["weight"] + delta, 2)))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE strategy_metrics 
        SET total_trades = ?, wins = ?, losses = ?, win_rate = ?, weight = ?, last_updated = ?
        WHERE name = ?
    """, (total, wins, losses, win_rate, new_weight, now, fb.strategy_code))
    conn.commit()
    conn.close()
    log_event("INFO", f"Auto-aprendizaje: Estrategia {row['display_name']} ajustada a peso {new_weight} (WinRate: {win_rate}%).")
    return {"success": True, "new_weight": new_weight, "win_rate": win_rate}


@app.post("/api/telegram/send-balance")
async def send_balance_api():
    success = await telegram_service.send_balance_report()
    return {"success": success, "message": "Notificación de saldo enviada a Telegram" if success else "Error al enviar notificación"}

@app.post("/api/telegram/test")
async def telegram_test():
    test_sig = {
        "id": 9999,
        "symbol": "SPY",
        "side": "BUY",
        "qty": 15,
        "price": 585.40,
        "stop_loss": 580.70,
        "take_profit": 594.80,
        "rr_ratio": 2.0,
        "strategy": "Tendencia & Cruce EMA 20/50/200",
        "rationale": "Prueba de confirmación interactiva desde Dashboard de Trading.",
        "confidence": 92.0
    }
    msg_id = await telegram_service.send_signal_alert(test_sig)
    return {"success": bool(msg_id), "message_id": msg_id}

@app.post("/api/broker/switch")
def switch_broker(broker_name: str):
    if broker_name.lower() in ["alpaca", "moomoo"]:
        broker_manager.active_broker = broker_name.lower()
        log_event("INFO", f"Broker cambiado a {broker_name.upper()}.")
        return {"success": True, "active_broker": broker_manager.active_broker.upper()}
    return {"success": False, "message": "Broker no válido"}

@app.get("/api/logs")
def get_logs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 30")
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return logs

# DASHBOARD HTML INTERFACE

@app.get("/api/latency")
def get_latency():
    result = latency_guardian.check_and_optimize()
    return result

@app.post("/api/telegram/send-latency")
async def send_latency_telegram():
    result = latency_guardian.check_and_optimize()
    await latency_guardian._send_latency_alert(result)
@app.post("/api/weekend/optimize")
async def run_weekend_optimization_api():
    from weekend_engine import weekend_engine
    result = await weekend_engine.run_weekend_optimization(send_telegram=True)
    return result

@app.get("/api/weekend/report")
def get_weekend_report_api():
    from weekend_engine import weekend_engine
    return weekend_engine.last_report or {"status": "none", "message": "No se ha ejecutado optimización de fin de semana todavía."}

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    with open(BASE_DIR / "templates" / "dashboard.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=HOST, port=PORT, reload=False)
