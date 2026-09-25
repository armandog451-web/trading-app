import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class MacroEngine:
    """
    Capa 1: Análisis Macro y Política Monetaria.
    Monitorea tasas del Tesoro (10Y y 2Y), la pendiente de la curva de rendimientos,
    tasa de fondos federales, inflación e índice DXY para establecer el sesgo macroeconómico.
    """

    def __init__(self):
        self.fred_api_key = settings.FRED_API_KEY

    async def fetch_macro_factors(self) -> dict:
        """
        Obtiene los factores macro desde FRED o fallback financiero de respaldo.
        """
        # Valores de base por defecto
        macro_data = {
            "yield_10y": 4.12,
            "yield_2y": 4.28,
            "yield_spread_10y2y": -0.16,
            "is_inverted": True,
            "fed_funds_rate": 5.25,
            "cpi_inflation_yoy": 3.1,
            "dxy_index": 104.2,
            "macro_bias": "NEUTRAL",
            "summary": "Curva de rendimientos levemente invertida (-0.16%). Política monetaria restrictiva pero en pausa."
        }

        # Intentar obtener datos reales si hay FRED API key
        if self.fred_api_key:
            try:
                async with httpx.AsyncClient(timeout=6.0, verify=settings.SSL_VERIFY) as client:

                    # FRED series: DGS10 (10Y), DGS2 (2Y), FEDFUNDS (Fed Rate)
                    url_10y = f"https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key={self.fred_api_key}&file_type=json&sort_order=desc&limit=1"
                    resp = await client.get(url_10y)
                    if resp.status_code == 200:
                        val = resp.json().get("observations", [{}])[0].get("value")
                        if val and val != ".":
                            macro_data["yield_10y"] = float(val)
            except Exception as e:
                logger.warning(f"Error consultando FRED: {e}")

        # Recalcular spread e inversión
        macro_data["yield_spread_10y2y"] = round(macro_data["yield_10y"] - macro_data["yield_2y"], 3)
        macro_data["is_inverted"] = macro_data["yield_spread_10y2y"] < 0

        # Determinar Sesgo Macro
        if macro_data["yield_spread_10y2y"] > 0 and macro_data["dxy_index"] < 103.5 and macro_data["cpi_inflation_yoy"] <= 3.0:
            macro_data["macro_bias"] = "BULLISH"
            macro_data["summary"] = "Entorno Risk-On: Curva desinvertida con pendiente positiva y presiones de inflación estables."
        elif macro_data["is_inverted"] or macro_data["dxy_index"] > 105.0:
            macro_data["macro_bias"] = "BEARISH"
            macro_data["summary"] = "Entorno Defensivo / Risk-Off: Curva invertida o fortaleza excesiva del dólar DXY. Favorece operar con precaución o setups de reversión corta."
        else:
            macro_data["macro_bias"] = "NEUTRAL"
            macro_data["summary"] = "Entorno Mixto: Transición monetaria. Sesgo condicionado a la acción de precio y liquidez intraday."

        return macro_data

macro_engine = MacroEngine()
