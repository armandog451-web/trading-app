from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import SignalRecommendation
from app.models.schemas import SignalRecommendationResponse, CreateSignalRequest, TestTelegramRequest
from app.engines.options_engine import options_engine
from app.core.notifier import notifier
from app.core.broker_manager import broker_manager
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/notifications", tags=["Notificaciones y Señales"])

@router.get("", response_model=dict)
def get_notifications(unread_only: bool = False, limit: int = 50, db: Session = Depends(get_db)):
    """
    Obtiene el historial de recomendaciones de compra (Acciones y Opciones)
    y el número total de alertas no leídas para la campana de la app.
    Elimina automáticamente las alertas que tengan más de 10 minutos de antigüedad.
    """
    cutoff_time = datetime.utcnow() - timedelta(minutes=10)
    db.query(SignalRecommendation).filter(SignalRecommendation.created_at < cutoff_time).delete()
    db.commit()

    query = db.query(SignalRecommendation)
    if unread_only:
        query = query.filter(SignalRecommendation.is_read == False)
    
    total_unread = db.query(SignalRecommendation).filter(SignalRecommendation.is_read == False).count()
    items = query.order_by(SignalRecommendation.created_at.desc()).limit(limit).all()
    
    return {
        "unread_count": total_unread,
        "items": [SignalRecommendationResponse.model_validate(item) for item in items]
    }

@router.post("/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    """Marca una recomendación específica como leída."""
    item = db.query(SignalRecommendation).filter(SignalRecommendation.id == notification_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    item.is_read = True
    db.commit()
    return {"success": True, "id": notification_id}

@router.post("/read-all")
def mark_all_notifications_read(db: Session = Depends(get_db)):
    """Marca todas las recomendaciones como leídas."""
    db.query(SignalRecommendation).filter(SignalRecommendation.is_read == False).update({"is_read": True})
    db.commit()
    return {"success": True, "message": "Todas las notificaciones marcadas como leídas"}

@router.post("/{notification_id}/execute")
async def execute_notification_trade(notification_id: int, db: Session = Depends(get_db)):
    """
    Envia la orden de compra de la recomendación directamente al Broker Activo (Moomoo u Alpaca).
    """
    from app.models.db_models import Trade
    from app.core.position_guardian import position_guardian

    item = db.query(SignalRecommendation).filter(SignalRecommendation.id == notification_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    is_option = (item.asset_type or "STOCK").upper() == "OPTION"
    if is_option:
        exp_clean = (item.expiration_date or "2026-10-16").replace("-", "")[2:]
        opt_char = "C" if (item.option_type or "CALL").upper() == "CALL" else "P"
        strike_val = item.strike_price or item.current_price or 100.0
        strike_code = str(int(strike_val * 1000))
        trade_symbol = f"US.{item.symbol.upper()}{exp_clean}{opt_char}{strike_code}"
        
        trade_qty = max(1, item.contracts_or_shares or 1)
        trade_entry = float(item.premium_est or 1.0)
        trade_sl = float(item.premium_stop_loss or round(trade_entry * 0.72, 2))
        trade_tp = float(item.premium_take_profit or round(trade_entry * 1.50, 2))
    else:
        trade_symbol = item.symbol.upper()
        trade_qty = max(1, item.contracts_or_shares or 1)
        trade_entry = float(item.entry_target or item.current_price or 100.0)
        trade_sl = float(item.stop_loss or round(trade_entry * 0.98, 2))
        trade_tp = float(item.take_profit or round(trade_entry * 1.05, 2))

    res = await broker_manager.submit_bracket_order(
        symbol=trade_symbol,
        qty=trade_qty,
        side="BUY",
        entry_price=trade_entry,
        stop_loss=trade_sl,
        take_profit=trade_tp,
        order_type="market"
    )

    order_id = res.get("order_id", "OK")

    # Registrar en PositionGuardian para monitoreo automático de SL/TP
    position_guardian.register_target(
        symbol=trade_symbol,
        stop_loss=trade_sl,
        take_profit=trade_tp,
        qty=trade_qty,
        side="BUY",
        entry_price=trade_entry,
        asset_type="OPTION" if is_option else "STOCK"
    )

    try:
        open_trade = Trade(
            symbol=trade_symbol,
            side="BUY",
            entry_price=trade_entry,
            quantity=trade_qty,
            stop_loss=trade_sl,
            take_profit=trade_tp,
            risk_reward_ratio=float(item.risk_reward or 1.8),
            status="OPEN",
            macro_bias="BULLISH" if (item.option_type or "CALL").upper() == "CALL" else "BEARISH",
            strategy=item.setup_type or "TopDown_Confluence",
            order_id=order_id
        )
        db.add(open_trade)
    except Exception as tr_err:
        pass

    item.is_read = True
    db.commit()

    return {
        "success": True,
        "broker": broker_manager.get_active_broker_name(),
        "order_result": res,
        "message": f"Orden enviada a Moomoo para {trade_symbol}. SL (${trade_sl:.2f}) y TP (${trade_tp:.2f}) activos 100% automáticos."
    }

@router.post("/trigger-demo-signal")
async def trigger_demo_signal(req: CreateSignalRequest, db: Session = Depends(get_db)):
    """
    Genera y despacha de forma inmediata una recomendación de compra
    tanto para la App como para Telegram (para pruebas o emisión manual).
    Soporta asset_type = 'STOCK' o 'OPTION'.
    """
    symbol = req.symbol.upper()
    asset_type = req.asset_type.upper()

    base_prices = {"SPY": 560.20, "QQQ": 482.50, "NVDA": 229.20, "TSLA": 242.10, "AMD": 156.80, "AAPL": 224.30}
    current_price = base_prices.get(symbol, 150.00)

    account = await broker_manager.get_account()
    equity = account.get("equity", 100000.0)

    if asset_type == "OPTION":
        # Generar contrato de opción estructurado (CALL o PUT según req.bias)
        opt_data = options_engine.calculate_option_contract(
            symbol=symbol,
            current_price=current_price,
            bias=req.bias or "BULLISH",
            equity=equity,
            risk_pct=1.0
        )
        if req.custom_note:
            opt_data["rationale"] = f"{req.custom_note} | {opt_data['rationale']}"

        result = await notifier.send_trade_recommendation(opt_data, db=db)
        return {"success": True, "data": opt_data, "dispatch": result}
    else:
        # Generar setup de compra de acciones
        risk_dist = round(current_price * 0.005, 2)  # ~0.5% riesgo
        entry_target = current_price
        stop_loss = round(entry_target - risk_dist, 2)
        take_profit = round(entry_target + (risk_dist * 2.4), 2)
        take_profit_2 = round(entry_target + (risk_dist * 3.6), 2)

        cash_to_risk = equity * 0.01
        shares = max(1, int(cash_to_risk / risk_dist))

        stock_data = {
            "asset_type": "STOCK",
            "symbol": symbol,
            "action": "BUY_STOCK",
            "current_price": current_price,
            "entry_target": entry_target,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "take_profit_2": take_profit_2,
            "risk_reward": 2.4,
            "shares": shares,
            "confluence_score": 88,
            "setup_type": "TopDown_VWAP_Sweep",
            "rationale": req.custom_note or f"Rebote en VWAP de {symbol} con confirmación de volumen y ratio R:R 1:2.4."
        }

        result = await notifier.send_trade_recommendation(stock_data, db=db)
        return {"success": True, "data": stock_data, "dispatch": result}

@router.post("/test-telegram")
async def test_telegram(req: TestTelegramRequest):
    """Prueba la conexión y envío de mensaje a Telegram."""
    res = await notifier.test_telegram_connection(
        token=req.telegram_bot_token,
        chat_id=req.telegram_chat_id,
        custom_msg=req.custom_message
    )
    return res

