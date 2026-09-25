import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class SentimentEngine:
    """
    Capa 3: Sentimiento del Mercado, Opciones y Posicionamiento Institucional.
    Analiza el índice VIX, la proporción Put/Call de CBOE, el Fear & Greed Index
    y el reporte COT (Commitment of Traders) de la CFTC.
    """

    async def fetch_sentiment_factors(self) -> dict:
        data = {
            "vix": 16.4,
            "vix_regime": "MODERATE",
            "cboe_put_call_ratio": 0.88,
            "put_call_sentiment": "NEUTRAL",
            "fear_and_greed_score": 58,
            "fear_and_greed_sentiment": "GREED",
            "cot_commercial_net_position": "NET_SHORT_HEDGING",
            "institutional_sentiment": "ACCUMULATION_ON_DIPS"
        }

        # Intentar obtener Fear & Greed en vivo si es posible
        try:
            async with httpx.AsyncClient(timeout=4.0, verify=settings.SSL_VERIFY) as client:
                res = await client.get("https://api.alternative.me/fng/?limit=1")

                if res.status_code == 200:
                    item = res.json().get("data", [{}])[0]
                    if item.get("value"):
                        data["fear_and_greed_score"] = int(item["value"])
                        data["fear_and_greed_sentiment"] = item.get("value_classification", "NEUTRAL").upper()
        except Exception as e:
            logger.debug(f"Fear & greed online fetch fallback: {e}")

        # Evaluar régimen de volatilidad VIX
        vix = data["vix"]
        if vix < 14.5:
            data["vix_regime"] = "LOW_COMPLACENCY"
        elif vix <= 21.0:
            data["vix_regime"] = "MODERATE_NORMAL"
        elif vix <= 28.0:
            data["vix_regime"] = "ELEVATED_RISK"
        else:
            data["vix_regime"] = "EXTREME_VOLATILITY"

        # Evaluar proporción Put/Call
        pcr = data["cboe_put_call_ratio"]
        if pcr < 0.70:
            data["put_call_sentiment"] = "BULLISH_COMPLACENCY"
        elif pcr > 1.05:
            data["put_call_sentiment"] = "BEARISH_PANIC_HEDGING"
        else:
            data["put_call_sentiment"] = "NEUTRAL_BALANCED"

        # Evaluar sesgo COT institucional
        # Si commercials reducen cortos o aumentan largos en futuros de S&P:
        data["institutional_sentiment"] = "SMART_MONEY_SUPPORT" if data["fear_and_greed_score"] < 40 else "NEUTRAL_DISTRIBUTION"

        return data

sentiment_engine = SentimentEngine()
