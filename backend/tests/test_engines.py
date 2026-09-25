import asyncio
import pandas as pd
import numpy as np

from app.engines.macro_engine import macro_engine
from app.engines.sentiment_engine import sentiment_engine
from app.engines.technical_engine import technical_engine
from app.engines.risk_engine import risk_engine
from app.core.alpaca_client import alpaca_broker
from app.backtest.engine import backtest_engine

def test_macro_engine():
    data = asyncio.run(macro_engine.fetch_macro_factors())
    assert "macro_bias" in data
    assert "yield_10y" in data
    assert "yield_2y" in data
    assert "yield_spread_10y2y" in data
    assert data["yield_spread_10y2y"] == round(data["yield_10y"] - data["yield_2y"], 3)

def test_sentiment_engine():
    sent = asyncio.run(sentiment_engine.fetch_sentiment_factors())
    assert "vix" in sent
    assert "cboe_put_call_ratio" in sent
    assert "fear_and_greed_score" in sent
    assert 0 <= sent["fear_and_greed_score"] <= 100

def test_technical_engine_vwap():
    df = pd.DataFrame({
        "open": [100.0, 101.0, 102.0],
        "high": [102.0, 103.0, 104.0],
        "low": [99.0, 100.5, 101.5],
        "close": [101.5, 102.5, 103.5],
        "volume": [1000, 2000, 1500]
    })
    df_vwap = technical_engine.calculate_vwap(df)
    assert "vwap" in df_vwap.columns
    assert "vwap_upper1" in df_vwap.columns
    assert "vwap_lower1" in df_vwap.columns
    assert df_vwap["vwap"].iloc[-1] > 0

def test_risk_engine_validation():
    equity = 100000.0
    
    # Caso 1: R:R insuficiente (< 1:2.0) -> Debe RECHAZARSE
    approved, reason, _ = risk_engine.evaluate_and_size_order(
        equity=equity,
        daily_loss=0.0,
        entry_price=100.0,
        stop_loss=98.0,
        take_profit=102.0,
        side="BUY"
    )
    assert approved is False
    assert "Ratio R:R insuficiente" in reason

    # Caso 2: R:R válido (>= 1:2.0) -> Debe APROBARSE
    approved, reason, sizing = risk_engine.evaluate_and_size_order(
        equity=equity,
        daily_loss=0.0,
        entry_price=100.0,
        stop_loss=98.0,
        take_profit=105.0,
        side="BUY"
    )
    assert approved is True
    assert sizing["risk_reward_ratio"] == 2.5
    assert sizing["shares"] == 500
    assert sizing["total_risk_dollars"] == 1000.0

    # Caso 3: Circuit Breaker activado por pérdida del 2% ($2,000)
    approved, reason, _ = risk_engine.evaluate_and_size_order(
        equity=equity,
        daily_loss=2100.0,
        entry_price=100.0,
        stop_loss=98.0,
        take_profit=105.0,
        side="BUY"
    )
    assert approved is False
    assert "CIRCUIT BREAKER" in reason

def test_alpaca_broker_bracket_and_panic():
    res = asyncio.run(alpaca_broker.submit_bracket_order(
        symbol="SPY",
        qty=10,
        side="BUY",
        entry_price=560.0,
        stop_loss=558.0,
        take_profit=565.0
    ))
    assert res["success"] is True
    assert res["symbol"] == "SPY"

    # Verificar que la posición está abierta
    positions = asyncio.run(alpaca_broker.get_positions())
    assert any(p["symbol"] == "SPY" for p in positions)

    # Probar Botón de Pánico
    panic_res = asyncio.run(alpaca_broker.close_all_positions())
    assert panic_res["success"] is True
    empty_positions = asyncio.run(alpaca_broker.get_positions())
    assert len(empty_positions) == 0

def test_backtest_simulation():
    res = asyncio.run(backtest_engine.run_backtest(
        symbols=["SPY", "QQQ"],
        days_back=15,
        initial_capital=100000.0,
        risk_per_trade_pct=1.0,
        min_rr_ratio=2.0
    ))
    assert res["total_trades"] > 0
    assert "win_rate_pct" in res
    assert "profit_factor" in res
    assert "equity_curve" in res
    assert len(res["equity_curve"]) > 1

def test_moomoo_broker_and_manager():
    from app.core.moomoo_client import moomoo_broker
    from app.core.broker_manager import broker_manager
    from app.config import settings

    # Test Moomoo bracket order submission and panic
    res = asyncio.run(moomoo_broker.submit_bracket_order(
        symbol="QQQ",
        qty=5,
        side="BUY",
        entry_price=480.0,
        stop_loss=476.0,
        take_profit=490.0
    ))
    assert res["success"] is True
    assert "order_id" in res

    panic_res = asyncio.run(moomoo_broker.close_all_positions())
    assert panic_res["success"] is True

    # Test BrokerManager routing to Moomoo
    settings.ACTIVE_BROKER = "MOOMOO"
    acc = asyncio.run(broker_manager.get_account())
    assert acc["active_broker"] == "MOOMOO"
    assert "equity" in acc


    # Reset back to ALPACA
    settings.ACTIVE_BROKER = "ALPACA"

def test_signal_only_mode():
    from app.core.bot_runner import bot_runner
    from app.config import settings

    settings.AUTO_EXECUTE_TRADES = False
    eval_mock = {
        "symbol": "SPY",
        "side": "BUY",
        "entry_price": 560.0,
        "stop_loss": 558.0,
        "take_profit": 565.0,
        "shares": 10,
        "risk_reward_ratio": 2.5,
        "approved": True
    }
    # Ejecutar sin enviar orden al broker
    asyncio.run(bot_runner._execute_approved_trade(eval_mock, 100000.0))
    assert settings.AUTO_EXECUTE_TRADES is False


