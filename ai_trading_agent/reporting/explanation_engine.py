"""
ai_trading_agent.reporting.explanation_engine
=============================================
Motor cuantitativo de explicabilidad y auditoría de decisiones (Instrucción 11 y 18).
Genera explicaciones estructuradas, comprensibles y sin sesgos para humanos y comités de riesgo.
REGLA CRÍTICA: Basado 100% en datos auditables, métricas calculadas y reglas evaluadas.
No inventa suposiciones subjetivas ni alucina eventos.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DecisionExplanation(BaseModel):
    decision_id: str
    symbol: str
    timestamp: datetime
    summary: str
    market_context: Dict[str, Any]
    technical_triggers: List[str]
    conflicts_or_warnings: List[str]
    risk_evaluation: Dict[str, Any]
    options_confluence: Optional[Dict[str, Any]] = None
    final_verdict: str


class QuantitativeExplanationEngine:
    """Generador determinista de explicaciones y diagnósticos institucionales."""

    @staticmethod
    def explain(pipeline_result: Dict[str, Any]) -> DecisionExplanation:
        """
        Produce un desglose explicativo completo y auditable a partir de la salida del Orchestrator.
        """
        decision_id = pipeline_result.get("decision_id", f"dec_{int(datetime.utcnow().timestamp())}")
        symbol = pipeline_result.get("symbol", "UNKNOWN")
        status = pipeline_result.get("status", "NO_TRADE")
        regime = pipeline_result.get("market_regime", "UNKNOWN")
        score = pipeline_result.get("score", 0.0)

        technical_triggers = []
        conflicts = []

        if status == "APPROVED":
            summary = (
                f"Propuesta de operación {pipeline_result.get('direction')} para {symbol} APROBADA con confluencia "
                f"alta ({score:.1f}/100) bajo régimen {regime}."
            )
            final_verdict = f"Aprobado deterministamente bajo modo {pipeline_result.get('trading_mode')}."
            technical_triggers.append(pipeline_result.get("rationale", "Setup técnico confirmado."))
        elif status == "CONFIRMATION_REJECTED":
            summary = f"Propuesta para {symbol} RECHAZADA por el motor de confirmación institucional."
            conflicts.append(pipeline_result.get("reason", "Filtro de confluencia activado."))
            final_verdict = "Bloqueado por filtros de seguridad antes de asignar capital."
        elif status == "RISK_REJECTED":
            summary = f"Propuesta para {symbol} RECHAZADA por el motor determinista de riesgo."
            for r in pipeline_result.get("reasons", []):
                conflicts.append(r)
            final_verdict = "Violación de parámetros de riesgo: orden denegada."
        else:
            summary = f"Sin operación (NO-TRADE) para {symbol} en el ciclo actual."
            conflicts.append(pipeline_result.get("reason", "Confluencia técnica insuficiente."))
            final_verdict = "Condiciones de mercado no cualifican para riesgo de capital."

        risk_eval = {
            "entry_price": pipeline_result.get("entry_price"),
            "stop_loss": pipeline_result.get("stop_loss"),
            "take_profit": pipeline_result.get("take_profit"),
            "approved_quantity": pipeline_result.get("quantity", 0),
            "rr_ratio": pipeline_result.get("rr_ratio"),
            "order_id": pipeline_result.get("order_id"),
            "execution_price": pipeline_result.get("execution_price")
        }

        opt_context = pipeline_result.get("option_contract")

        return DecisionExplanation(
            decision_id=decision_id,
            symbol=symbol,
            timestamp=datetime.utcnow(),
            summary=summary,
            market_context={"regime": regime, "confluence_score": score},
            technical_triggers=technical_triggers,
            conflicts_or_warnings=conflicts,
            risk_evaluation=risk_eval,
            options_confluence=opt_context,
            final_verdict=final_verdict
        )


explanation_engine = QuantitativeExplanationEngine()
