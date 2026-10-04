"""
ai_trading_agent.strategy_lab.lifecycle.manager
================================================
Administrador del Ciclo de Vida Formal de Estrategias, Puertas de Promoción Seguras
y Candidate Gating con Política de Evidencia Mínima (Minimum Evidence Gate).
Garantiza que ninguna estrategia con evidencia insuficiente (ej. 0 trades) pueda ser CANDIDATE o APPROVED.
"""

from typing import Tuple, List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel

from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition, StrategyStatus
from ai_trading_agent.strategy_lab.registry.registry import strategy_registry


class CandidateGatingConfig(BaseModel):
    """Configuración parametrizable para la Puerta de Validación de Candidatos."""
    min_is_trades: int = 5
    min_oos_trades: int = 3
    min_total_trades: int = 8
    min_sharpe_is: float = 0.50
    min_sharpe_oos: float = 0.20
    min_profit_factor: float = 1.0
    max_overfitting_risk: float = 75.0
    min_robustness_score: float = 50.0


class LifecycleManager:
    """Gestiona las transiciones formales de estado y valida las puertas de evidencia mínima."""

    ALLOWED_TRANSITIONS = {
        StrategyStatus.RESEARCH: [StrategyStatus.BACKTEST, StrategyStatus.VALIDATING, StrategyStatus.REJECTED],
        StrategyStatus.BACKTEST: [StrategyStatus.VALIDATING, StrategyStatus.RESEARCH, StrategyStatus.REJECTED],
        StrategyStatus.VALIDATING: [StrategyStatus.CANDIDATE, StrategyStatus.RESEARCH, StrategyStatus.REJECTED],
        StrategyStatus.CANDIDATE: [StrategyStatus.PAPER, StrategyStatus.REJECTED],
        StrategyStatus.PAPER: [StrategyStatus.APPROVED, StrategyStatus.PAUSED, StrategyStatus.REJECTED],
        StrategyStatus.APPROVED: [StrategyStatus.PAUSED, StrategyStatus.RETIRED],
        StrategyStatus.PAUSED: [StrategyStatus.APPROVED, StrategyStatus.RESEARCH, StrategyStatus.REJECTED, StrategyStatus.RETIRED],
        StrategyStatus.REJECTED: [StrategyStatus.RESEARCH],
        StrategyStatus.RETIRED: []
    }

    def __init__(self, gating_config: Optional[CandidateGatingConfig] = None):
        self.config = gating_config or CandidateGatingConfig()

    def evaluate_candidate_gating(
        self,
        strat: LabStrategyDefinition,
        config: Optional[CandidateGatingConfig] = None
    ) -> Tuple[bool, str]:
        """
        Evalúa si la estrategia cumple todos los requisitos de evidencia estadística mínima
        para ser elegible como CANDIDATE.
        """
        cfg = config or self.config
        metrics = strat.metrics or {}
        
        total_trades = int(metrics.get("total_trades", 0))
        is_trades = int(metrics.get("is_trades", total_trades))
        oos_trades = int(metrics.get("oos_trades", 0))

        # 1. Puerta de Evidencia Mínima de Operaciones
        if total_trades < cfg.min_total_trades:
            return False, f"EVIDENCIA INSUFICIENTE: Total de trades ({total_trades}) es menor al mínimo requerido ({cfg.min_total_trades})."

        if is_trades < cfg.min_is_trades:
            return False, f"EVIDENCIA INSUFICIENTE: Trades In-Sample ({is_trades}) es menor al mínimo requerido ({cfg.min_is_trades})."

        if oos_trades < cfg.min_oos_trades and oos_trades > 0:
            return False, f"EVIDENCIA INSUFICIENTE: Trades Out-Of-Sample ({oos_trades}) es menor al mínimo requerido ({cfg.min_oos_trades})."

        # 2. Puerta de Robustez y Degradación
        if strat.robustness_score < cfg.min_robustness_score:
            return False, f"ROBUSTEZ INSUFICIENTE: Robustness Score ({strat.robustness_score:.1f}) es menor al mínimo requerido ({cfg.min_robustness_score:.1f})."

        # 3. Puerta de Profit Factor, Sharpe y Economic Edge
        pf = float(metrics.get("profit_factor", 0.0))
        if pf < cfg.min_profit_factor and total_trades > 0:
            return False, f"EXPECTATIVA NEGATIVA: Profit Factor ({pf:.2f}) es menor al mínimo requerido ({cfg.min_profit_factor:.2f})."

        from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import (
            calculate_economic_edge_score,
            EconomicEdgeClassification
        )
        _, edge_class = calculate_economic_edge_score(
            profit_factor=pf,
            expectancy=float(metrics.get("expectancy", metrics.get("expected_value", 0.0))),
            is_sharpe=float(metrics.get("is_sharpe", metrics.get("sharpe_ratio", 0.0))),
            oos_sharpe=float(metrics.get("oos_sharpe", 0.0)),
            trade_count=total_trades
        )

        if edge_class == EconomicEdgeClassification.NO_EDGE:
            return False, f"VENTAJA ECONÓMICA NULA: Economic Edge Classification es {edge_class.value} (Profit Factor={pf:.2f})."

        return True, "CANDIDATE_GATING_PASSED"

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

        if target_status not in allowed and target_status != current_status:
            return False, f"TRANSICIÓN DENEGADA: No se permite cambiar directamente de {current_status.value} a {target_status.value}.", strat

        # Puerta de Candidato: Transición a CANDIDATE requiere Candidate Gating
        if target_status == StrategyStatus.CANDIDATE:
            gating_passed, msg = self.evaluate_candidate_gating(strat)
            if not gating_passed:
                return False, f"PROMOCIÓN A CANDIDATE DENEGADA: {msg}", strat

        # Puerta de Validación a Paper Trading: CANDIDATE -> PAPER requiere Robustness Score >= 60.0
        if target_status == StrategyStatus.PAPER:
            if strat.robustness_score < 60.0:
                return False, f"PROMOCIÓN DENEGADA: Robustness Score ({strat.robustness_score:.1f}) es menor al mínimo requerido (60.0).", strat

        # Puerta de Aprobación Final: PAPER -> APPROVED requiere Strategy Score >= 70.0 y trades mínimos
        if target_status == StrategyStatus.APPROVED:
            if strat.strategy_score < 70.0:
                return False, f"APROBACIÓN DENEGADA: Strategy Score ({strat.strategy_score:.1f}) es menor al mínimo requerido (70.0).", strat
            gating_passed, msg = self.evaluate_candidate_gating(strat)
            if not gating_passed:
                return False, f"APROBACIÓN DENEGADA: {msg}", strat

        # Aplicar transición
        strat.status = target_status
        strat.updated_at = datetime.now(timezone.utc)
        strategy_registry.register_strategy(strat)

        return True, f"Estrategia {strategy_id} promovida exitosamente a {target_status.value} por {actor}. Razón: {reason}", strat

    def transition(self, strategy_id: str, target_status: StrategyStatus, reason: str = "Transición directa"):
        """Método helper compatible para efectuar transiciones directas."""
        success, msg, strat = self.promote_strategy(strategy_id, target_status, reason=reason)
        if not success:
            raise ValueError(msg)
        return strat


lifecycle_manager = LifecycleManager()
