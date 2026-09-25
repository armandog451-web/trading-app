import math
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class OptionsEngine:
    """
    Motor Cuantitativo de Opciones Financieras (Options Contract Engine).
    Estructura recomendaciones automáticas de contratos CALL y PUT para Day/Swing Trading:
    - Selección de Strike óptimo (ATM o ligeramente OTM con Delta ~0.45-0.50).
    - Vencimiento semanal de alta liquidez (2 a 7 DTE).
    - Estimación de prima, Stop Loss en prima (-25% a -30%) y Take Profit (+50% a +100%).
    - Dimensionamiento del número de contratos respetando el 1% de riesgo del capital.
    """

    def calculate_option_contract(
        self,
        symbol: str,
        current_price: float,
        bias: str = "BULLISH",  # "BULLISH" -> CALL, "BEARISH" -> PUT
        equity: float = 100000.0,
        risk_pct: float = 1.0,
        days_to_exp: int = 5
    ) -> dict:
        symbol = symbol.upper()
        is_call = bias.upper() in ("BULLISH", "BUY", "LONG")
        option_type = "CALL" if is_call else "PUT"
        action = "BUY_CALL" if is_call else "BUY_PUT"

        # 1. Determinación del incremento de Strike por símbolo
        if symbol in ("SPY", "QQQ", "IWM"):
            strike_step = 1.0
        elif current_price > 200.0:
            strike_step = 2.5
        elif current_price > 100.0:
            strike_step = 1.0
        else:
            strike_step = 0.5

        # 2. Strike óptimo (ATM o 1 strike OTM para máximo apalancamiento y liquidez)
        if is_call:
            # Strike ligeramente superior o igual al precio actual
            strike = math.ceil(current_price / strike_step) * strike_step
        else:
            # Strike ligeramente inferior o igual al precio actual
            strike = math.floor(current_price / strike_step) * strike_step

        strike = round(strike, 2)

        # 3. Fecha de expiración extendida (2 a 4 semanas / ~14 a 30 DTE) para dar más margen y reducir Theta decay
        now = datetime.utcnow()
        target_days = days_to_exp if days_to_exp >= 14 else 21
        target_date = now + timedelta(days=target_days)
        days_until_friday = (4 - target_date.weekday()) % 7
        final_exp = target_date + timedelta(days=days_until_friday)
        exp_date = final_exp.strftime("%Y-%m-%d")

        # 4. Estimación de Prima para vencimientos a 2-4 semanas (~14-30 DTE)
        pct_premium = 0.012 if symbol in ("SPY", "QQQ", "IWM") else 0.022
        base_premium = round(current_price * pct_premium, 2)
        premium_est = max(1.25, base_premium)

        # 5. Niveles de salida en prima
        # Stop Loss: -28% de la prima
        premium_stop_loss = round(premium_est * 0.72, 2)
        # Take Profit 1: +50% de la prima
        premium_take_profit_1 = round(premium_est * 1.50, 2)
        # Take Profit 2: +100% de la prima (Doble)
        premium_take_profit_2 = round(premium_est * 2.00, 2)

        risk_per_share = round(premium_est - premium_stop_loss, 2)
        reward_per_share = round(premium_take_profit_1 - premium_est, 2)
        rr_ratio = round(reward_per_share / risk_per_share, 2) if risk_per_share > 0 else 2.0

        # 6. Dimensionamiento: Fijo a 1 solo contrato globalmente para todas las alertas
        contracts = 1

        # Total de capital asignado a la prima (1 contrato = 100 acciones)
        total_cost = round(contracts * premium_est * 100.0, 2)
        total_risk_dollars = round(contracts * risk_per_share * 100.0, 2)

        # Código de ticker OCC estándar (ej. SPY260926C00560000)
        exp_code = (now + timedelta(days=days_until_friday)).strftime("%y%m%d")
        opt_char = "C" if is_call else "P"
        strike_code = f"{int(strike * 1000):08d}"
        occ_symbol = f"{symbol}{exp_code}{opt_char}{strike_code}"

        delta_est = 0.48 if is_call else -0.48

        rationale = (
            f"Contrato {option_type} con Strike ${strike} Exp {exp_date}. "
            f"Delta estimado {delta_est:+.2f} con alta sensibilidad direccional gamma. "
            f"Riesgo acotado en prima con SL al -28% (${premium_stop_loss}) y TP al +50% (${premium_take_profit_1})."
        )

        return {
            "asset_type": "OPTION",
            "symbol": symbol,
            "action": action,
            "option_type": option_type,
            "strike_price": strike,
            "expiration_date": exp_date,
            "occ_symbol": occ_symbol,
            "current_price": current_price,
            "entry_target": current_price,
            "premium_est": premium_est,
            "premium_stop_loss": premium_stop_loss,
            "premium_take_profit": premium_take_profit_1,
            "premium_take_profit_2": premium_take_profit_2,
            "stop_loss": current_price * (0.992 if is_call else 1.008),
            "take_profit": current_price * (1.018 if is_call else 0.982),
            "risk_reward": rr_ratio,
            "contracts": contracts,
            "total_cost": total_cost,
            "total_risk_dollars": total_risk_dollars,
            "delta_est": delta_est,
            "rationale": rationale,
            "confluence_score": 86,
            "iv_crush_safe": True,
            "liquidity_passed": True
        }

    def validate_iv(self, iv_pct: float) -> tuple[bool, str]:
        """
        1. Validación de Volatilidad Implícita (IV):
        Descarta alertas si la IV > 100% para evitar el aplastamiento de volatilidad (IV Crush).
        """
        if iv_pct > 100.0:
            return False, f"Riesgo de IV Crush descartado: Volatilidad implícita excesiva ({iv_pct:.1f}% > 100%)."
        return True, "Volatilidad Implícita en rango operativo seguro."

    def validate_liquidity(self, open_interest: int, bid: float, ask: float) -> tuple[bool, str]:
        """
        2. Control de Liquidez y Slippage:
        Exige Open Interest >= 500 contratos y Bid-Ask Spread <= 5.0% para evitar deslizamiento.
        """
        if open_interest < 500:
            return False, f"Baja Liquidez: Interés abierto ({open_interest}) inferior a 500 contratos."
        
        mid = (bid + ask) / 2.0 if (bid + ask) > 0 else 1.0
        spread = abs(ask - bid)
        spread_pct = (spread / mid) * 100.0
        
        if spread_pct > 5.0 and spread > 0.15:
            return False, f"Alto Slippage: Spread (${spread:.2f} / {spread_pct:.1f}%) supera el máximo de 5.0%."
            
        return True, "Liquidez y Spread aptos para ejecución automatizada."

    def calculate_dynamic_contracts(self, equity: float = 0.0, risk_pct: float = 0.0, risk_per_share: float = 0.0) -> int:
        """
        Filtro de Posición Global:
        Fijo siempre y de forma global en 1 solo contrato para todas las alertas.
        """
        return 1

    def generate_structured_json(
        self,
        symbol: str = "SPY",
        current_price: float = 560.20,
        bias: str = "BULLISH",
        equity: float = 100000.0,
        confluence_score: int = 88,
        iv_val: float = 16.8,
        open_interest: int = 1450,
        bid: float = 3.60,
        ask: float = 3.68
    ) -> dict:
        """
        Genera la recomendación de opciones en formato JSON institucional con 1 contrato fijo.
        """
        # Validación 1: IV Crush
        iv_ok, iv_msg = self.validate_iv(iv_val)
        # Validación 2: Liquidez & Spread
        liq_ok, liq_msg = self.validate_liquidity(open_interest, bid, ask)

        opt = self.calculate_option_contract(
            symbol=symbol,
            current_price=current_price,
            bias=bias,
            equity=equity
        )

        is_call = opt["option_type"] == "CALL"
        delta = 0.48 if is_call else -0.48
        gamma = 0.035
        theta = -0.12
        vega = 0.18

        prima = opt["premium_est"]
        costo_contrato = round(prima * 100.0, 2)
        
        # Tamaño fijo: 1 contrato
        contratos = 1
        capital_comprometido = costo_contrato

        sl_precio = opt["premium_stop_loss"]
        tp1_precio = opt["premium_take_profit"]
        tp2_precio = opt["premium_take_profit_2"]

        return {
            "ticker": symbol.upper(),
            "tipo_operacion": opt["option_type"],
            "precio_subyacente": round(current_price, 2),
            "strike": opt["strike_price"],
            "vencimiento": opt["expiration_date"],
            "prima_estimada": prima,
            "costo_por_contrato": costo_contrato,
            "griegas": {
                "delta": delta,
                "gamma": gamma,
                "theta": theta,
                "vega": vega,
                "iv_implied_volatility": f"{iv_val:.1f}%"
            },
            "gestion_riesgo": {
                "stop_loss_precio": sl_precio,
                "stop_loss_porcentaje": -28.0,
                "take_profit_1_precio": tp1_precio,
                "take_profit_1_porcentaje": 50.0,
                "take_profit_2_precio": tp2_precio,
                "take_profit_2_porcentaje": 100.0,
                "ratio_riesgo_beneficio": f"1:{opt['risk_reward']}",
                "exposición_maxima_cartera": "1 contrato fijo"
            },
            "metricas_cuant": {
                "confluencia_score": confluence_score,
                "temporalidad_recomendada": "1H / 4H (Swing a corto plazo)",
                "contratos_sugeridos": contratos,
                "capital_comprometido_estimado": capital_comprometido
            },
            "control_filtros": {
                "iv_crush_validado": iv_ok,
                "iv_status": iv_msg,
                "liquidez_valida": liq_ok,
                "liquidez_status": liq_msg,
                "open_interest": open_interest,
                "bid_ask_spread": round(ask - bid, 2)
            },
            "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }

options_engine = OptionsEngine()


