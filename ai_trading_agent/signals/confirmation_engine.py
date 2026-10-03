"""
ai_trading_agent.signals.confirmation_engine
============================================
Motor avanzado de confirmación y confluencia multidimensional (Instrucción 10).
Filtra señales contra eventos de alto impacto, contradicciones de opciones y regímenes anómalos.
"""

from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from ai_trading_agent.domain.enums import SignalDirection, MarketRegime
from ai_trading_agent.domain.models import AggregatedSignal, TradeProposal


class AdvancedConfirmationEngine:
    """Validador de confluencia institucional multidimensional."""

    def __init__(self, block_on_earnings: bool = True, block_on_extreme_vix: bool = True):
        self.block_on_earnings = block_on_earnings
        self.block_on_extreme_vix = block_on_extreme_vix

    def confirm_proposal(
        self,
        proposal: TradeProposal,
        agg_signal: AggregatedSignal,
        regime: MarketRegime,
        options_context: Dict[str, Any] = None,
        event_calendar: Dict[str, Any] = None
    ) -> Tuple[bool, Optional[TradeProposal], str]:
        """
        Valida que la propuesta no viole filtros de eventos macroeconómicos,
        volatilidad descontrolada ni contradicciones de flujo institucional.
        """
        options_context = options_context or {}
        event_calendar = event_calendar or {}

        # 1. Filtro de Calendario de Eventos Corporativos / Earnings (Instrucción 10)
        has_earnings_today = event_calendar.get("has_earnings_today", False)
        if self.block_on_earnings and has_earnings_today:
            return False, None, (
                f"NO-TRADE POR EVENTOS: {proposal.symbol} tiene reporte de beneficios (Earnings) hoy. "
                "Se bloquean operaciones para evitar riesgo de gap binario incontrolable."
            )

        # 2. Filtro de Régimen de Volatilidad Extrema (VIX en pánico)
        if self.block_on_extreme_vix and regime == MarketRegime.HIGH_VOLATILITY:
            # En régimen de alta volatilidad extrema, solo se permiten propuestas con confluencia > 80
            if agg_signal.score < 80.0:
                return False, None, (
                    f"NO-TRADE POR VOLATILIDAD: Mercado en régimen HIGH_VOLATILITY. "
                    f"Puntuación de confluencia ({agg_signal.score:.1f}) inferior al umbral exigido de 80.0."
                )

        # 3. Filtro de Confluencia de Opciones
        pc_sentiment = options_context.get("sentiment", "BALANCED_NORMAL")
        if proposal.direction == SignalDirection.BUY and pc_sentiment == "HIGH_HEDGING_PUT_PRESSURE":
            # Añadir advertencia y exigir confluencia más alta
            if agg_signal.score < 75.0:
                return False, None, (
                    "NO-TRADE POR DIVERGENCIA DE DERIVADOS: Fuerte presión de cobertura en PUTs institucionales. "
                    "Señal técnica de compra descartada por discordancia con el mercado de opciones."
                )

        # Confirmación exitosa
        confirmed_rationale = (
            f"{proposal.rationale} | Confluencia confirmada bajo régimen {regime.value} "
            f"(Score: {agg_signal.score:.1f}/100)"
        )
        confirmed_proposal = proposal.model_copy(update={"rationale": confirmed_rationale})

        return True, confirmed_proposal, "Propuesta confirmada satisfactoriamente por todas las capas."


confirmation_engine = AdvancedConfirmationEngine()
