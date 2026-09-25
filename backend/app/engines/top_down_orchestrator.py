import logging
import pandas as pd
from app.engines.macro_engine import macro_engine
from app.engines.sentiment_engine import sentiment_engine
from app.engines.fundamental_engine import fundamental_engine
from app.engines.technical_engine import technical_engine
from app.engines.risk_engine import risk_engine

logger = logging.getLogger(__name__)

class TopDownOrchestrator:
    """
    Orquestador Cuantitativo Jerárquico:
    Capa 1: Macro & Política Monetaria
    Capa 2: Fundamentales y Resultados Corporativos
    Capa 3: Sentimiento, Opciones y COT
    Capa 4: Técnico, VWAP y Niveles de Liquidez
    Capa 5: Motor de Riesgo y R:R
    """

    async def evaluate_symbol_pipeline(
        self,
        symbol: str,
        intraday_df: pd.DataFrame,
        daily_df: pd.DataFrame,
        account_equity: float,
        daily_loss: float = 0.0
    ) -> dict:
        """
        Pasa un símbolo a través del filtro de 5 capas Top-Down.
        """
        # --- CAPA 1: MACRO & POLÍTICA MONETARIA ---
        macro_info = await macro_engine.fetch_macro_factors()
        macro_bias = macro_info.get("macro_bias", "NEUTRAL")

        # --- CAPA 2: FUNDAMENTALES & EARNINGS ---
        fund_profile = await fundamental_engine.get_fundamental_profile(symbol)
        eligible, fund_msg = fundamental_engine.is_eligible_for_intraday(symbol, fund_profile)
        if not eligible:
            return {"approved": False, "layer_failed": "FUNDAMENTAL", "reason": fund_msg}

        # --- CAPA 3: SENTIMIENTO, VIX & PUT/CALL ---
        sentiment_info = await sentiment_engine.fetch_sentiment_factors()
        vix_regime = sentiment_info.get("vix_regime", "MODERATE_NORMAL")
        put_call_sentiment = sentiment_info.get("put_call_sentiment", "NEUTRAL_BALANCED")

        # Regla de sentimiento: En volatilidad extrema (VIX > 35), pausar operaciones automáticas
        if vix_regime == "EXTREME_VOLATILITY":
            return {"approved": False, "layer_failed": "SENTIMENT", "reason": "VIX en régimen de pánico extremo (>35). Se suspenden entradas intraday."}

        # --- CAPA 4: TÉCNICO, VWAP & NIVELES DE LIQUIDEZ ---
        df_with_vwap = technical_engine.calculate_vwap(intraday_df)
        levels = technical_engine.extract_liquidity_levels(daily_df, intraday_df)
        setup = technical_engine.evaluate_setup(symbol, df_with_vwap, levels)

        if setup.get("signal") == "NONE":
            return {
                "approved": False,
                "layer_failed": "TECHNICAL_LIQUIDITY",
                "reason": setup.get("reason", "Sin confluencia de niveles"),
                "levels": levels,
                "macro_bias": macro_bias
            }

        signal_side = setup["signal"]

        # Filtrar confluencia Top-Down:
        # Si Macro es BEARISH y la señal es BUY, verificar que el setup sea un barrido fuerte de sobreventa
        if macro_bias == "BEARISH" and signal_side == "BUY" and setup.get("setup_type") != "BULLISH_LIQUIDITY_SWEEP":
            return {
                "approved": False,
                "layer_failed": "MACRO_DISCORDANCE",
                "reason": "Señal técnica de compra descartada por sesgo macro bajista restrictivo (falta confluencia)"
            }

        # --- CAPA 5: MOTOR DE RIESGO & R:R ---
        entry_price = setup["entry_price"]
        stop_loss = setup["stop_loss"]
        take_profit = setup["take_profit"]

        risk_approved, risk_reason, sizing = risk_engine.evaluate_and_size_order(
            equity=account_equity,
            daily_loss=daily_loss,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            side=signal_side
        )

        if not risk_approved:
            return {
                "approved": False,
                "layer_failed": "RISK_ENGINE",
                "reason": risk_reason,
                "setup": setup
            }

        # --- APROBACIÓN DE CONFLUENCIA COMPLETA ---
        return {
            "approved": True,
            "symbol": symbol,
            "side": signal_side,
            "setup_type": setup.get("setup_type"),
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "shares": sizing["shares"],
            "risk_dollars": sizing["total_risk_dollars"],
            "potential_profit": sizing["total_potential_profit"],
            "risk_reward_ratio": sizing["risk_reward_ratio"],
            "macro_bias": macro_bias,
            "vix_regime": vix_regime,
            "put_call_sentiment": put_call_sentiment,
            "levels": levels,
            "reason": f"{setup.get('reason')} | Confluencia jerárquica validada | R:R 1:{sizing['risk_reward_ratio']}"
        }

orchestrator = TopDownOrchestrator()
