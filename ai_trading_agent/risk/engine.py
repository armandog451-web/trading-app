"""
ai_trading_agent.risk.engine
============================
Motor de riesgo determinista e independiente (Instrucción 12).
Calcula dimensionamiento exacto de posiciones y aplica filtros matemáticos inviolables.
La IA no tiene permisos para eludir ni modificar las políticas de este motor.
"""

from typing import List
from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.enums import RiskDecision, SignalDirection
from ai_trading_agent.domain.models import TradeProposal, RiskAssessment, Position


class DeterministicRiskEngine:
    """Motor matemático de evaluación de riesgo y control de pérdidas."""

    def __init__(
        self,
        risk_per_trade_pct: float = None,
        max_daily_loss_pct: float = None,
        min_rr_ratio: float = None,
        max_open_positions: int = None,
        max_capital_allocation_pct: float = None
    ):
        self.risk_per_trade_pct = risk_per_trade_pct or settings.RISK_PER_TRADE_PCT
        self.max_daily_loss_pct = max_daily_loss_pct or settings.MAX_DAILY_LOSS_PCT
        self.min_rr_ratio = min_rr_ratio or settings.MIN_RR_RATIO
        self.max_open_positions = max_open_positions or settings.MAX_OPEN_POSITIONS
        self.max_capital_allocation_pct = max_capital_allocation_pct or settings.MAX_CAPITAL_ALLOCATION_PCT

    def assess_proposal(
        self,
        proposal: TradeProposal,
        equity: float,
        daily_pnl: float,
        open_positions: List[Position],
        kill_switch_active: bool = False
    ) -> RiskAssessment:
        """
        Evalúa de forma determinista si una propuesta cumple todas las reglas de riesgo.
        """
        reasons = []

        # 1. Kill Switch Global
        if kill_switch_active or settings.KILL_SWITCH_ACTIVE:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=["KILL SWITCH ACTIVO: Bloqueo de emergencia activado en todo el sistema."],
                circuit_breaker_active=True
            )

        # 2. Circuit Breaker de Pérdida Diaria Máxima
        daily_loss_limit = equity * (self.max_daily_loss_pct / 100.0)
        if daily_pnl <= -daily_loss_limit:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"CIRCUIT BREAKER DIARIO: Pérdida del día (${abs(daily_pnl):,.2f}) alcanzó el límite (${daily_loss_limit:,.2f})."],
                circuit_breaker_active=True
            )

        # 3. Límite de Posiciones Abiertas
        if len(open_positions) >= self.max_open_positions:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"LÍMITE DE POSICIONES: Ya existen {len(open_positions)} posiciones abiertas (máximo: {self.max_open_positions})."]
            )

        # 3.1 Posición ya existente en el mismo activo
        if any(p.symbol == proposal.symbol for p in open_positions):
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"EXPOSICIÓN DUPLICADA: Ya existe una posición abierta en {proposal.symbol}."]
            )

        # 4. Validación de Geometría de Precios y Ratio R:R
        entry = proposal.entry_price
        sl = proposal.stop_loss
        tp = proposal.take_profit

        if proposal.direction == SignalDirection.BUY:
            if not (sl < entry < tp):
                return RiskAssessment(
                    decision_id=proposal.decision_id,
                    decision=RiskDecision.REJECTED,
                    reasons=[f"GEOMETRÍA INVÁLIDA (BUY): Stop Loss (${sl}) debe ser menor que entrada (${entry}) y menor que Take Profit (${tp})."]
                )
        elif proposal.direction == SignalDirection.SELL:
            if not (tp < entry < sl):
                return RiskAssessment(
                    decision_id=proposal.decision_id,
                    decision=RiskDecision.REJECTED,
                    reasons=[f"GEOMETRÍA INVÁLIDA (SELL): Take Profit (${tp}) debe ser menor que entrada (${entry}) y menor que Stop Loss (${sl})."]
                )

        risk_dist = abs(entry - sl)
        reward_dist = abs(tp - entry)
        if risk_dist <= 0:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=["DISTANCIA DE RIESGO NULA: El Stop Loss no puede ser igual al precio de entrada."]
            )

        rr_actual = round(reward_dist / risk_dist, 2)

        if rr_actual < self.min_rr_ratio:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"RATIO R:R INSUFICIENTE: {rr_actual:.2f} es menor que el mínimo requerido de {self.min_rr_ratio:.1f}."]
            )

        # 5. Cálculo Matemático de Tamaño de Posición (Position Sizing)
        max_risk_dollar = equity * (self.risk_per_trade_pct / 100.0)
        shares_by_risk = int(max_risk_dollar / risk_dist)

        # Restricción por asignación máxima de capital
        max_capital_for_trade = equity * (self.max_capital_allocation_pct / 100.0)
        shares_by_cap = int(max_capital_for_trade / entry)

        shares = min(shares_by_risk, shares_by_cap)

        if shares < 1:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=["CAPITAL INSUFICIENTE: El tamaño de posición calculado es menor a 1 acción bajo los parámetros de riesgo."]
            )

        estimated_risk = round(shares * risk_dist, 2)
        capital_allocated = round(shares * entry, 2)

        reasons.append(
            f"Aprobado: {shares} acciones | Riesgo máx: ${estimated_risk:,.2f} ({self.risk_per_trade_pct}% eq) | Capital asignado: ${capital_allocated:,.2f} | R:R: 1:{rr_actual:.1f}"
        )

        return RiskAssessment(
            decision_id=proposal.decision_id,
            decision=RiskDecision.APPROVED,
            approved_quantity=shares,
            estimated_risk_dollars=estimated_risk,
            max_capital_allocation=capital_allocated,
            reasons=reasons,
            circuit_breaker_active=False
        )


risk_engine = DeterministicRiskEngine()
