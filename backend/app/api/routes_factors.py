from fastapi import APIRouter
from app.engines.macro_engine import macro_engine
from app.engines.sentiment_engine import sentiment_engine
from app.core.screener import screener
from app.engines.technical_engine import technical_engine
from app.core.bot_runner import bot_runner

router = APIRouter(prefix="/api/factors", tags=["Factores Top-Down"])

@router.get("/macro")
async def get_macro_factors():
    """Factores de la Capa 1: Macro y Política Monetaria."""
    return await macro_engine.fetch_macro_factors()

@router.get("/sentiment")
async def get_sentiment_factors():
    """Factores de la Capa 3: Sentimiento, Opciones y COT."""
    return await sentiment_engine.fetch_sentiment_factors()

@router.get("/screener")
async def get_screener_stocks():
    """Factores de la Capa 2 y Selección de Universo: Acciones con RVOL y catalizador."""
    return await screener.get_screener_results()

@router.get("/technical/{symbol}")
async def get_technical_analysis(symbol: str):
    """
    Factores de la Capa 4: Velas intraday, VWAP, Bandas y Niveles de Liquidez (PDH/PDL/PMH/PML)
    para alimentar los gráficos de velas japonesas TradingView.
    """
    symbol = symbol.upper()
    intraday_df, daily_df = bot_runner._generate_sample_market_data(symbol)
    df_vwap = technical_engine.calculate_vwap(intraday_df)
    levels = technical_engine.extract_liquidity_levels(daily_df, intraday_df)
    setup = technical_engine.evaluate_setup(symbol, df_vwap, levels)

    # Convertir a formato compatible con Lightweight Charts y Canvas enriquecido
    candles = []
    for i, row in df_vwap.iterrows():
        total_minutes = 9 * 60 + 30 + (i * 5)
        hh = total_minutes // 60
        mm = total_minutes % 60
        time_str = f"{hh:02d}:{mm:02d}"

        candles.append({
            "time": int(1726740000 + (i * 300)),  # Timestamps espaciados en 5m
            "time_str": time_str,
            "open": round(float(row['open']), 2),
            "high": round(float(row['high']), 2),
            "low": round(float(row['low']), 2),
            "close": round(float(row['close']), 2),
            "volume": int(row['volume']),
            "vwap": round(float(row['vwap']), 2),
            "vwap_upper": round(float(row['vwap_upper1']), 2),
            "vwap_lower": round(float(row['vwap_lower1']), 2),
            "vwap_upper2": round(float(row.get('vwap_upper2', row['vwap_upper1'])), 2),
            "vwap_lower2": round(float(row.get('vwap_lower2', row['vwap_lower1'])), 2),
        })

    return {
        "symbol": symbol,
        "current_price": levels["current_price"],
        "levels": levels,
        "setup": setup,
        "candles": candles
    }
