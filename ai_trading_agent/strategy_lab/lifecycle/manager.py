"""
ai_trading_agent.strategy_lab.lifecycle.manager
================================================
Administrador del Ciclo de Vida Formal de Estrategias y Puertas de Promoción Seguras.
Garantiza que ninguna estrategia de investigación pueda ejecutar órdenes o saltarse el Risk Engine.
"""

from typing import Tuple, List, Optional
from datetime import datetime

from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition, StrategyStatus
from ai_trading_agent.strategy_lab.registry.registry import strategy_registry


class LifecycleManager:
    """Gestiona las transiciones formales de estado y valida las reglas de promoción."""

    ALLOWED_TRANSITIONS = {
        StrategyStatus.RESEARCH: [StrategyStatus.BACKTEST, StrategyStatus.REJECTED],
        StrategyStatus.BACKTEST: [StrategyStatus.VALIDATING, StrategyStatus.RESEARCH, StrategyStatus.REJECTED],
        StrategyStatus.VALIDATING: [StrategyStatus.CANDIDATE, StrategyStatus.RESEARCH, StrategyStatus.REJECTED],
        StrategyStatus.CANDIDATE: [StrategyStatus.PAPER, StrategyStatus.REJECTED],
        StrategyStatus.PAPER: [StrategyStatus.APPROVED, StrategyStatus.PAUSED, StrategyStatus.REJECTED],
        StrategyStatus.APPROVED: [StrategyStatus.PAUSED, StrategyStatus.RETIRED],
        StrategyStatus.PAUSED: [StrategyStatus.APPROVED, StrategyStatus.RESEARCH, StrategyStatus.RETIRED],
        StrategyStatus.REJECTED: [StrategyStatus.RESEARCH],
        StrategyStatus.RETIRED: []
    }

    def promote_strategy(
        self,
        strategy_id: str,
        target_status: StrategyStatus,
        reason: str,
        actor: str = "AI_RESEARCH_AGENT"
    ) -> Tuple[bool, str, Optional[LabStrategyDefinition]]:
        """
        Evalúa y aplica la transición de estado si cumple las reglas de la puerta de promoción.
        """
        strat = strategy_registry.get_strategy(strategy_id)
        if not strat:
            return False, f"Estrategia {strategy_id} no encontrada en el registro.", None

        current_status = strat.status
        allowed = self.ALLOWED_TRANSITIONS.get(current_status, [])

        if target_status not in allowed:
            return False, f"TRANSICIÓN DENEGADA: No se permite cambiar directamente de {current_status.value} a {target_status.value}.", strat

        # Puerta de Validación: CANDIDATE -> PAPER requiere Robustness Score >= 60.0
        if target_status == StrategyStatus.PAPER:
            if strat.robustness_score < 60.0:
                return False, f"PROMOCIÓN DENEGADA: Robustness Score ({strat.robustness_score:.1f}) es menor al mínimo requerido (60.0).", strat

        # Puerta de Aprobación: PAPER -> APPROVED requiere Strategy Score >= 70.0
        if target_status == StrategyStatus.APPROVED:
            if strat.strategy_score < 70.0:
                return False, f"APROBACIÓN DENEGADA: Strategy Score ({strat.strategy_score:.1f}) es menor al mínimo requerido (70.0).", strat

        # Aplicar transición
        strat.status = target_status
        strat.updated_at = datetime.utcnow()
        strategy_registry.register_strategy(strat)

        return True, f"Estrategia {strategy_id} promovida exitosamente a {target_status.value} por {actor}. Razón: {reason}", strat


lifecycle_manager = LifecycleManager()
