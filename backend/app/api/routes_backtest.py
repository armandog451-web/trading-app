from fastapi import APIRouter
from app.models.schemas import BacktestRequest, BacktestResultResponse
from app.backtest.engine import backtest_engine

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
