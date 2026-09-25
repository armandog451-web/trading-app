import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.strategies.strategy_orb import orb_strategy, CONFIG_PATH

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orb", tags=["ORB Strategy"])

class ORBConfigRequest(BaseModel):
    opening_range_minutes: Optional[int] = 15
    market_open_time: Optional[str] = "09:30"
    range_close_time: Optional[str] = "09:45"
    end_trading_time: Optional[str] = "15:45"
    volume_multiplier: Optional[float] = 1.5
    volume_ma_period: Optional[int] = 20
    tickers: Optional[list] = ["QQQ", "SPY", "TSLA", "AAPL", "MSFT"]
    fixed_contracts: Optional[int] = 1
    stop_loss_pct: Optional[float] = -28.0
    take_profit_1_pct: Optional[float] = 50.0
    take_profit_2_pct: Optional[float] = 100.0
    auto_dispatch_telegram: Optional[bool] = True

class ORBTestBreakoutRequest(BaseModel):
    symbol: str = "SPY"
    direction: str = "LONG"  # "LONG" o "SHORT"
    price: Optional[float] = None
    volume_ratio: Optional[float] = 2.1  # 2.1x > 1.5x
    custom_note: Optional[str] = "Prueba de Ruptura ORB 15m con Filtro de Volumen"

@router.get("/config")
def get_orb_config():
    """Obtiene la configuración actual de la estrategia ORB."""
    return orb_strategy.config

@router.post("/config")
def update_orb_config(req: ORBConfigRequest):
    """Actualiza la configuración de la estrategia ORB y la persiste en disco."""
    try:
        new_cfg = orb_strategy.config.copy()
        req_dict = req.dict(exclude_unset=True)
        new_cfg.update(req_dict)
        
        # Guardar en archivo JSON
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(new_cfg, f, indent=2)

        orb_strategy.reload_config()
        return {"success": True, "message": "Configuración de ORB actualizada exitosamente.", "config": new_cfg}
    except Exception as e:
        logger.error(f"Error actualizando configuración ORB: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def get_orb_status():
    """Retorna el estado de la estrategia y las rupturas detectadas en la sesión."""
    return {
        "strategy_name": orb_strategy.config.get("strategy_name"),
        "enabled": orb_strategy.config.get("enabled", True),
        "range_minutes": orb_strategy.config.get("opening_range_minutes", 15),
        "volume_threshold": f"{orb_strategy.config.get('volume_multiplier', 1.5)}x de SMA{orb_strategy.config.get('volume_ma_period', 20)}",
        "fixed_contracts": orb_strategy.config.get("fixed_contracts", 1),
        "detected_breakouts": orb_strategy.detected_breakouts
    }

@router.post("/trigger-test-breakout")
async def trigger_test_breakout(req: ORBTestBreakoutRequest, db: Session = Depends(get_db)):
    """
    Simula una ruptura ORB válida (con volumen suficiente) y dispara
    la recomendación de opción a Telegram y a la base de datos con 1 contrato fijo.
    """
    sym = req.symbol.upper()
    dir_upper = req.direction.upper()
    is_long = dir_upper in ("LONG", "CALL", "BUY")

    base_prices = {"SPY": 560.50, "QQQ": 483.20, "NVDA": 230.10, "TSLA": 243.50, "AAPL": 225.40, "AMD": 157.20}
    current_price = req.price or base_prices.get(sym, 150.00)

    # Definir rango simulado coherente
    if is_long:
        or_high = round(current_price * 0.997, 2)
        or_low = round(current_price * 0.990, 2)
        breakout_type = "LONG"
    else:
        or_high = round(current_price * 1.010, 2)
        or_low = round(current_price * 1.003, 2)
        breakout_type = "SHORT"

    breakout_data = {
        "symbol": sym,
        "direction": breakout_type,
        "bias": "BULLISH" if is_long else "BEARISH",
        "option_type": "CALL" if is_long else "PUT",
        "breakout_price": current_price,
        "or_high": or_high,
        "or_low": or_low,
        "candle_volume": 45000,
        "avg_volume": 20000,
        "volume_ratio": req.volume_ratio,
        "volume_filter_passed": True,
        "timestamp": "09:47:00 EST"
    }

    signal_payload = orb_strategy.generate_signal_payload(breakout_data)
    if req.custom_note:
        signal_payload["rationale"] = f"{req.custom_note} | {signal_payload['rationale']}"

    from app.core.notifier import notifier
    dispatch_res = await notifier.send_trade_recommendation(signal_payload, db=db)

    return {
        "success": True,
        "message": f"Ruptura ORB {breakout_type} simulada con éxito para {sym}.",
        "signal": signal_payload,
        "dispatch": dispatch_res
    }
