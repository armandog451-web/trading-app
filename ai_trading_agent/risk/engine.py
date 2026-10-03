from typing import List, Optional, Dict, Any
import math
import logging

from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.enums import RiskDecision, SignalDirection
from ai_trading_agent.domain.models import TradeProposal, RiskAssessment, Position
from database import get_setting, set_setting

logger = logging.getLogger(__name__)


class DeterministicRiskEngine:
    """Motor matemático de evaluación de riesgo determinista e independiente ($1,000,000 USD Paper Profile)."""

    def __init__(
        self,
        risk_per_trade_pct: float = None,
        max_planned_risk_per_trade: float = None,
        max_aggregate_open_risk: float = None,
        max_daily_loss: float = None,
        max_consecutive_losses: int = None,
        min_rr_ratio: float = None,
        max_open_positions: int = None,
        max_single_stock_exposure: float = None
    ):
        self.risk_per_trade_pct = risk_per_trade_pct or settings.RISK_PER_TRADE_PCT
        self.max_planned_risk_per_trade = max_planned_risk_per_trade or settings.MAX_PLANNED_RISK_PER_TRADE
        self.max_aggregate_open_risk = max_aggregate_open_risk or settings.MAX_AGGREGATE_OPEN_RISK
        self.max_daily_loss = max_daily_loss or settings.MAX_DAILY_LOSS
        self.max_consecutive_losses = max_consecutive_losses or settings.MAX_CONSECUTIVE_LOSSES
        self.min_rr_ratio = min_rr_ratio or settings.MIN_RR_RATIO
        self.max_open_positions = max_open_positions or settings.MAX_OPEN_POSITIONS
        self.max_single_stock_exposure = max_single_stock_exposure or (settings.PAPER_INITIAL_CAPITAL * 0.10) # $100,000 USD

    def get_high_water_mark(self, current_equity: float) -> float:
        """Obtiene y actualiza persistentemente el máximo histórico de equity (High Water Mark)."""
        saved_hwm = get_setting("risk_high_water_mark", str(settings.PAPER_INITIAL_CAPITAL))
        try:
            hwm_val = float(saved_hwm)
        except (ValueError, TypeError):
            hwm_val = float(settings.PAPER_INITIAL_CAPITAL)
        hwm = max(hwm_val, current_equity)
        set_setting("risk_high_water_mark", str(hwm))
        return hwm

    def get_consecutive_losses(self, strategy_code: str) -> int:
        """Recupera persistentemente las pérdidas consecutivas de una estrategia."""
        val = get_setting(f"consecutive_losses_{strategy_code}", "0")
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def record_trade_result(self, strategy_code: str, is_win: bool):
        """Actualiza persistentemente el contador de pérdidas consecutivas tras cada operación salvada."""
        if is_win:
            set_setting(f"consecutive_losses_{strategy_code}", "0")
        else:
            curr = self.get_consecutive_losses(strategy_code) + 1
            set_setting(f"consecutive_losses_{strategy_code}", str(curr))

    def record_daily_pnl(self, net_pnl: float):
        """Registra persistentemente el P&L acumulado del día para evitar reinicios inadvertidos."""
        curr_pnl_str = get_setting("daily_pnl_accumulated", "0.0")
        try:
            curr_pnl = float(curr_pnl_str)
        except (ValueError, TypeError):
            curr_pnl = 0.0
        new_pnl = curr_pnl + net_pnl
        set_setting("daily_pnl_accumulated", str(new_pnl))

    def get_persisted_daily_pnl(self, current_daily_pnl: float) -> float:
        """Combina el PnL del runtime con la base de datos para resistir cierres o reinicios de servicio."""
        stored = get_setting("daily_pnl_accumulated", "0.0")
        try:
            stored_val = float(stored)
        except (ValueError, TypeError):
            stored_val = 0.0
        return min(current_daily_pnl, stored_val)

    def assess_proposal(
        self,
        proposal: TradeProposal,
        equity: float,
        daily_pnl: float,
        open_positions: List[Position],
        pending_orders: Optional[List[Any]] = None,
        kill_switch_active: bool = False
    ) -> RiskAssessment:
        """
        Evalúa de forma determinista si una propuesta cumple todas las reglas de riesgo.
        Soporta defensas contra errores de datos, reinicios de servicio y órdenes pendientes.
        """
        reasons = []
        pending_orders = pending_orders or []

        # 0. Defensa Estricta Contra Errores de Datos o Precios Obsoletos/Corruptos
        if not proposal or not hasattr(proposal, "entry_price") or not hasattr(proposal, "stop_loss") or not hasattr(proposal, "take_profit"):
            return RiskAssessment(
                decision_id=getattr(proposal, "decision_id", "INVALID"),
                decision=RiskDecision.REJECTED,
                reasons=["ERROR DE DATOS: Estructura de la propuesta incompleta o inválida."]
            )

        entry = proposal.entry_price
        sl = proposal.stop_loss
        tp = proposal.take_profit

        if (
            entry is None or sl is None or tp is None or
            math.isnan(entry) or math.isnan(sl) or math.isnan(tp) or
            math.isinf(entry) or math.isinf(sl) or math.isinf(tp) or
            entry <= 0 or sl <= 0 or tp <= 0
        ):
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"ERROR DE DATOS / PRECIO CORRUPTO: Entrada (${entry}), Stop Loss (${sl}) o Take Profit (${tp}) son nulos, obsoletos o menores/iguales a cero."]
            )

        # 1. Kill Switch Global
        if kill_switch_active or settings.KILL_SWITCH_ACTIVE:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=["KILL SWITCH ACTIVO: Bloqueo de emergencia activado en todo el sistema."],
                circuit_breaker_active=True
            )

        # 2. Control de Drawdown desde High Water Mark (HWM) Persistente
        hwm = self.get_high_water_mark(equity)
        drawdown_dollars = max(0.0, hwm - equity)
        drawdown_pct = round((drawdown_dollars / hwm) * 100.0, 2)

        if drawdown_pct >= settings.DRAWDOWN_HALT_PCT:  # 10.0% ($100,000 USD)
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"DRAWDOWN HALT ACTIVO ({drawdown_pct:.1f}%): Pérdida desde HWM (${drawdown_dollars:,.2f}) superó el límite del {settings.DRAWDOWN_HALT_PCT}%. Se requiere autorización humana para reanudar."],
                circuit_breaker_active=True
            )

        # 3. Circuit Breaker de Pérdida Diaria Máxima ($10,000 USD - Persistente ante Reinicios)
        effective_daily_pnl = self.get_persisted_daily_pnl(daily_pnl)
        if effective_daily_pnl <= -self.max_daily_loss:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"CIRCUIT BREAKER DIARIO (${self.max_daily_loss:,.2f}): Pérdida del día (${abs(effective_daily_pnl):,.2f}) alcanzó o superó el límite diario."],
                circuit_breaker_active=True
            )

        # 4. Pausa de Estrategia por Pérdidas Consecutivas (>= 3 - Persistente ante Reinicios)
        strat_code = getattr(proposal, "strategy_code", "generic")
        consec_losses = self.get_consecutive_losses(strat_code)
        if consec_losses >= self.max_consecutive_losses:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"ESTRATEGIA PAUSADA ({strat_code}): {consec_losses} pérdidas consecutivas registradas (máximo permitido: {self.max_consecutive_losses}). Exige revisión técnica."]
            )

        # 5. Límite de Posiciones Abiertas y Exposición Duplicada (Posiciones + Órdenes Pendientes)
        total_open_and_pending = len(open_positions) + len(pending_orders)
        if total_open_and_pending >= self.max_open_positions:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"LÍMITE DE POSICIONES/ÓRDENES: Existen {len(open_positions)} posiciones abiertas y {len(pending_orders)} órdenes pendientes (máximo permitido: {self.max_open_positions})."]
            )

        if any(p.symbol == proposal.symbol for p in open_positions):
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"EXPOSICIÓN DUPLICADA: Ya existe una posición abierta en {proposal.symbol}."]
            )

        if any(getattr(o, "symbol", None) == proposal.symbol for o in pending_orders):
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"ÓRDEN PENDIENTE EXISTENTE: Ya existe una orden pendiente de entrada para {proposal.symbol}."]
            )

        # 6. Validación de Geometría de Precios y Ratio R:R Mínimo 1:2
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

        # 7. Cálculo Determinista de Tamaño de Posición (Fórmula Exacta: position_size = floor(risk_budget / risk_per_share))
        slippage_cost = entry * 0.0005
        commission_cost = settings.ESTIMATED_COMMISSION_PER_SHARE
        risk_per_share = risk_dist + slippage_cost + commission_cost

        # Presupuesto de riesgo por operación (0.25% de equity, máx $2,500 USD)
        risk_budget = min(equity * (self.risk_per_trade_pct / 100.0), self.max_planned_risk_per_trade)

        # Si estamos en advertencia de Drawdown (>= 5%), aplicar escala defensiva (-50% riesgo)
        if drawdown_pct >= settings.DRAWDOWN_WARNING_PCT:
            risk_budget *= 0.50
            reasons.append(f"ADVERTENCIA DRAWDOWN ({drawdown_pct:.1f}%): Presupuesto de riesgo reducido al 50%.")

        shares_by_risk = math.floor(risk_budget / risk_per_share)

        # Restricción por exposición máxima por activo ($100,000 USD / 10% de $1M)
        shares_by_cap = math.floor(self.max_single_stock_exposure / entry)
        shares = min(shares_by_risk, shares_by_cap)

        if shares < 1:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=["TAMAÑO DE POSICIÓN NULO: La posición calculada es menor a 1 acción tras aplicar los filtros de riesgo y costes."]
            )

        planned_risk = round(shares * risk_dist, 2)

        # 8. Verificación de Riesgo Abierto Agregado (Posiciones Abiertas + Órdenes Pendientes <= $15,000 USD / 1.50% eq)
        existing_open_risk = sum(
            abs(p.quantity * (p.entry_price - p.stop_loss))
            for p in open_positions
            if hasattr(p, "stop_loss") and p.stop_loss and hasattr(p, "entry_price") and p.entry_price
        )

        pending_open_risk = sum(
            abs(getattr(o, "quantity", 0) * (getattr(o, "entry_price", 0) - getattr(o, "stop_loss", 0)))
            for o in pending_orders
            if getattr(o, "stop_loss", None) and getattr(o, "entry_price", None)
        )

        total_aggregate_risk = existing_open_risk + pending_open_risk + planned_risk

        if total_aggregate_risk > self.max_aggregate_open_risk:
            return RiskAssessment(
                decision_id=proposal.decision_id,
                decision=RiskDecision.REJECTED,
                reasons=[f"EXCESO DE RIESGO AGREGADO: El riesgo total abierto (${total_aggregate_risk:,.2f}, incluyendo órdenes pendientes) excedería el límite máximo de ${self.max_aggregate_open_risk:,.2f} USD."]
            )

        capital_allocated = round(shares * entry, 2)
        reasons.append(
            f"Aprobado: {shares} acciones | Riesgo planificado: ${planned_risk:,.2f} ({self.risk_per_trade_pct}% eq) | Capital asignado: ${capital_allocated:,.2f} | R:R: 1:{rr_actual:.1f}"
        )

        return RiskAssessment(
            decision_id=proposal.decision_id,
            decision=RiskDecision.APPROVED,
            approved_quantity=shares,
            estimated_risk_dollars=planned_risk,
            max_capital_allocation=capital_allocated,
            reasons=reasons,
            circuit_breaker_active=False
        )


risk_engine = DeterministicRiskEngine()

