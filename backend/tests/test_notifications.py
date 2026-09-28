import pytest
from app.engines.options_engine import options_engine
from app.core.notifier import notifier
from app.database import init_db, SessionLocal
from app.models.db_models import SignalRecommendation

def test_options_engine_call_and_put():
    # 1. Test Call Contract (Bullish bias)
    call_res = options_engine.calculate_option_contract(
        symbol="SPY",
        current_price=560.25,
        bias="BULLISH",
        equity=100000.0,
        risk_pct=1.0
    )
    assert call_res["asset_type"] == "OPTION"
    assert call_res["option_type"] == "CALL"
    assert call_res["action"] == "BUY_CALL"
    assert call_res["strike_price"] >= 560.0
    assert call_res["premium_est"] > 0
    assert call_res["premium_stop_loss"] < call_res["premium_est"]
    assert call_res["premium_take_profit"] > call_res["premium_est"]
    assert call_res["contracts"] == 1
    assert call_res["total_cost"] <= 200.0
    assert call_res["risk_reward"] >= 1.5

    # 2. Test Put Contract (Bearish bias)
    put_res = options_engine.calculate_option_contract(
        symbol="QQQ",
        current_price=482.40,
        bias="BEARISH",
        equity=50000.0,
        risk_pct=1.0
    )
    assert put_res["option_type"] == "PUT"
    assert put_res["action"] == "BUY_PUT"
    assert put_res["strike_price"] <= 483.0
    assert put_res["premium_est"] > 0
    assert put_res["contracts"] == 1
    assert put_res["total_cost"] <= 200.0

import asyncio

def test_notifier_trade_recommendation_persistence():
    init_db()
    async def _run():
        with SessionLocal() as db:
            # Recomendación de Acciones
            stock_data = {
                "asset_type": "STOCK",
                "symbol": "NVDA",
                "action": "BUY_STOCK",
                "current_price": 128.50,
                "entry_target": 128.50,
                "stop_loss": 126.80,
                "take_profit": 133.00,
                "risk_reward": 2.65,
                "shares": 100,
                "confluence_score": 90,
                "setup_type": "VWAP_Bounce",
                "rationale": "Test NVDA Stock setup"
            }
            res_stock = await notifier.send_trade_recommendation(stock_data, db=db)
            assert res_stock["success"] is True
            assert res_stock["symbol"] == "NVDA"

            # Recomendación de Opciones
            opt_data = options_engine.calculate_option_contract(
                symbol="NVDA",
                current_price=128.50,
                bias="BULLISH"
            )
            res_opt = await notifier.send_trade_recommendation(opt_data, db=db)
            assert res_opt["success"] is True
            assert res_opt["asset_type"] == "OPTION"

            # Verificar que se persistieron en SQLite
            saved_items = db.query(SignalRecommendation).filter(SignalRecommendation.symbol == "NVDA").all()
            assert len(saved_items) >= 2

    asyncio.run(_run())

