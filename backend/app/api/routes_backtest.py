from fastapi import APIRouter
from app.models.schemas import BacktestRequest, BacktestResultResponse, MT5BacktestRequest
from app.backtest.engine import backtest_engine
from app.backtest.mt5_backtest_engine import mt5_backtest_engine
from app.mt5.mt5_connector import mt5_connector

router = APIRouter(prefix="/api/backtest", tags=["Backtesting Studio"])

@router.post("/run", response_model=BacktestResultResponse)
async def run_backtest_simulation(req: BacktestRequest):
    """Ejecuta una simulación histórica intraday basada en confluencia Top-Down."""
    result = await backtest_engine.run_backtest(
        symbols=req.symbols,
        days_back=req.days_back,
        initial_capital=req.initial_capital,
        risk_per_trade_pct=req.risk_per_trade_pct,
        min_rr_ratio=req.min_rr_ratio
    )
    return result

@router.get("/mt5/status")
async def get_mt5_status():
    """Devuelve el estado de conexión del terminal local de MetaTrader 5."""
    return mt5_connector.get_terminal_status()

@router.post("/mt5/run")
async def run_mt5_backtest(req: MT5BacktestRequest):
    """
    Ejecuta backtesting de alta fidelidad con datos históricos nativos de MetaTrader 5
    y estrategia de Order Blocks (OB) + RVOL + EMA 50/200.
    """
    res = await mt5_backtest_engine.run_mt5_backtest(
        symbols=req.symbols,
        timeframe=req.timeframe,
        bars_count=req.bars_count,
        initial_capital=req.initial_capital,
        risk_per_trade_pct=req.risk_per_trade_pct,
        rvol_threshold=req.rvol_threshold,
        tp1_rr=req.tp1_rr,
        tp2_rr=req.tp2_rr
    )

    if req.send_telegram:
        import asyncio
        asyncio.create_task(mt5_backtest_engine.send_telegram_backtest_report(res))

    return res

@router.post("/mt5/send-telegram")
async def send_mt5_telegram_report(payload: dict):
    """Envía un reporte de resultados de MT5 por Telegram."""
    return await mt5_backtest_engine.send_telegram_backtest_report(payload)

