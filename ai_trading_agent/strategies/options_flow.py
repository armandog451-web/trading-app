"""
ai_trading_agent.strategies.options_flow
========================================
Módulo cuantitativo de análisis de flujo de opciones (Options Flow - Instrucción 9E).
Estructura contratos CALL/PUT, evalúa ratios Put/Call, liquidez y niveles de Gamma/Strike.
REGLA CRÍTICA: No deduce automáticamente dirección alcista o bajista únicamente por el
tamaño de una transacción de opciones (las órdenes grandes institucionales suelen ser coberturas).
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class OptionContractProposal(BaseModel):
    underlying_symbol: str
    option_type: str        # 'CALL' o 'PUT'
    strike_price: float
    expiration_date: str
    days_to_expiration: int
    estimated_premium_per_share: float
    total_contract_cost: float
    delta_approx: float
    max_budget_usd: float = 200.0
    is_hedging_warning: bool = False
    rationale: str


class OptionsFlowAnalyzer:
    """Motor de confluencia y estructuración de derivados financieros."""

    def __init__(self, max_contract_cost: float = 200.0):
        self.max_contract_cost = max_contract_cost

    def evaluate_flow_sentiment(
        self,
        put_volume: float,
        call_volume: float,
        put_open_interest: float,
        call_open_interest: float
    ) -> Dict[str, Any]:
        """
        Evalúa el sentimiento de opciones evitando sesgos ingenuos de tamaño (Instrucción 9E).
        """
        total_vol = put_volume + call_volume
        if total_vol <= 0:
            return {
                "sentiment": "NEUTRAL_BALANCED",
                "put_call_ratio": 1.0,
                "confidence": 0.0,
                "warning": "Volumen de opciones nulo o no disponible"
            }

        pc_ratio = round(put_volume / (call_volume + 1e-9), 2)
        oi_ratio = round(put_open_interest / (call_open_interest + 1e-9), 2)

        # Regla cuantitativa: un PC Ratio muy alto (> 1.6) indica cobertura masiva institucional o pánico,
        # mientras que un PC Ratio muy bajo (< 0.6) indica euforia compradora.
        if pc_ratio > 1.6:
            sentiment = "HIGH_HEDGING_PUT_PRESSURE"
            warning = "Alto volumen en PUTs detectado: Puede representar cobertura de cartera institucional en lugar de especulación direccional directa."
        elif pc_ratio < 0.6:
            sentiment = "AGGRESSIVE_CALL_BUYING"
            warning = "Demanda activa de CALLs detectada: Verificar si no coincide con techos de sobrecompra."
        else:
            sentiment = "BALANCED_NORMAL"
            warning = "Flujo de opciones en equilibrio normal."

        return {
            "sentiment": sentiment,
            "put_call_ratio": pc_ratio,
            "oi_ratio": oi_ratio,
            "warning": warning
        }

    def structure_option_contract(
        self,
        symbol: str,
        current_price: float,
        direction: str,  # 'BUY' (para CALL) o 'SELL' (para PUT)
        days_to_exp: int = 21
    ) -> OptionContractProposal:
        """
        Estructura una recomendación de contrato de opciones acotada a presupuesto máximo ($200 USD).
        Vencimientos de 14 a 30 DTE para mitigar la erosión Theta acelerada.
        """
        is_call = direction.upper() in ("BUY", "LONG", "BULLISH")
        option_type = "CALL" if is_call else "PUT"

        # 1. Determinación de paso de Strike según precio subyacente
        if current_price > 200.0:
            strike_step = 2.5
        elif current_price > 100.0:
            strike_step = 1.0
        else:
            strike_step = 0.5

        # 2. Strike ATM inicial
        raw_strike = round(current_price / strike_step) * strike_step

        # 3. Fecha de vencimiento a viernes (~2 a 4 semanas)
        now = datetime.utcnow()
        target_days = max(14, min(35, days_to_exp))
        target_date = now + timedelta(days=target_days)
        days_to_friday = (4 - target_date.weekday()) % 7
        exp_date = (target_date + timedelta(days=days_to_friday)).strftime("%Y-%m-%d")

        # 4. Estimación de prima y ajuste presupuestario (máx $200 USD por contrato = $2.00 por acción)
        max_premium_allowed = self.max_contract_cost / 100.0  # $2.00
        pct_premium = 0.015  # ~1.5% del precio subyacente estimado
        est_atm_premium = round(current_price * pct_premium, 2)

        selected_strike = raw_strike
        final_premium = est_atm_premium

        # Si el contrato ATM excede $200 USD, desplazarse OTM de forma prudente
        if est_atm_premium > max_premium_allowed:
            otm_steps = int((est_atm_premium - max_premium_allowed) / (strike_step * 0.2)) + 1
            if is_call:
                selected_strike = raw_strike + (otm_steps * strike_step)
            else:
                selected_strike = max(strike_step, raw_strike - (otm_steps * strike_step))
            final_premium = min(max_premium_allowed, round(est_atm_premium * 0.65, 2))

        total_cost = round(final_premium * 100.0, 2)
        delta_approx = 0.45 if selected_strike == raw_strike else (0.35 if is_call else -0.35)

        return OptionContractProposal(
            underlying_symbol=symbol,
            option_type=option_type,
            strike_price=selected_strike,
            expiration_date=exp_date,
            days_to_expiration=target_days,
            estimated_premium_per_share=final_premium,
            total_contract_cost=total_cost,
            delta_approx=delta_approx,
            max_budget_usd=self.max_contract_cost,
            is_hedging_warning=False,
            rationale=(
                f"Contrato {option_type} Strike ${selected_strike:.2f} con vencimiento {exp_date} ({target_days} DTE). "
                f"Costo total estimado: ${total_cost:,.2f} USD (acotado al límite institucional de ${self.max_contract_cost:,.2f})."
            )
        )


options_flow_analyzer = OptionsFlowAnalyzer()
