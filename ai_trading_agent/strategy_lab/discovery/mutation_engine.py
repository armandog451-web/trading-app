"""
ai_trading_agent.strategy_lab.discovery.mutation_engine
========================================================
Motor Extendido de Mutación de Estrategias y Registro de Audit Lineage.
Soporta mutaciones de parámetros, filtros de régimen y reglas condicionales.
"""

import uuid
import copy
import random
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field

from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition
from ai_trading_agent.strategy_lab.strategies.composable import ComposableStrategy


class MutationRecord(BaseModel):
    """Registro explícito de auditoría para cada mutación aplicada a una estrategia."""
    mutation_id: str = Field(default_factory=lambda: f"mut_{uuid.uuid4().hex[:8]}")
    parent_strategy_id: str
    child_strategy_id: str
    field_mutated: str
    old_value: Any
    new_value: Any
    expected_effect: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExtendedMutationEngine:
    """Motor de Mutación Avanzado para la evolución de estrategias de trading."""

    def mutate_strategy(
        self,
        strategy: ComposableStrategy,
        definition: LabStrategyDefinition,
        mutation_type: str = "PARAMETER_PERTURBATION"
    ) -> Tuple[ComposableStrategy, LabStrategyDefinition, MutationRecord]:
        """Aplica una mutación controlada a la estrategia y genera un nuevo hijo con linaje completo."""
        child_id = f"mut_{strategy.strategy_id}_{uuid.uuid4().hex[:4]}"
        
        # Calcular nueva versión
        try:
            v_major, v_minor = definition.version.split(".")
            new_version = f"{v_major}.{int(v_minor) + 1}"
        except Exception:
            new_version = f"{definition.version}.1"

        new_params = copy.deepcopy(strategy.parameters)
        new_rules = copy.deepcopy(strategy.rules)
        field_mutated = ""
        old_val = None
        new_val = None
        effect = ""

        if mutation_type == "PARAMETER_PERTURBATION":
            # Elegir un parámetro numérico al azar para perturbar
            numeric_params = ["min_rvol", "atr_stop_mult", "rr_target", "min_rsi", "max_rsi"]
            field_mutated = random.choice(numeric_params)
            old_val = new_params.get(field_mutated, 1.5)

            if field_mutated == "min_rvol":
                delta = round(random.choice([-0.2, -0.1, 0.1, 0.2, 0.3]), 2)
                new_val = max(0.5, round(old_val + delta, 2))
                effect = f"Ajuste de filtro de volumen de {old_val} a {new_val}"
            elif field_mutated == "atr_stop_mult":
                delta = round(random.choice([-0.3, -0.15, 0.15, 0.3]), 2)
                new_val = max(0.5, round(old_val + delta, 2))
                effect = f"Modificación del Stop Loss ATR de {old_val} a {new_val}"
            elif field_mutated == "rr_target":
                delta = round(random.choice([-0.4, -0.2, 0.2, 0.4]), 2)
                new_val = max(1.0, round(old_val + delta, 2))
                effect = f"Modificación del objetivo Risk/Reward de {old_val} a {new_val}"
            elif field_mutated == "min_rsi":
                delta = random.choice([-5, -2, 2, 5])
                new_val = max(15.0, min(45.0, old_val + delta))
                effect = f"Ajuste de umbral inferior RSI de {old_val} a {new_val}"
            else:  # max_rsi
                delta = random.choice([-5, -2, 2, 5])
                new_val = max(55.0, min(85.0, old_val + delta))
                effect = f"Ajuste de umbral superior RSI de {old_val} a {new_val}"

            new_params[field_mutated] = new_val

        elif mutation_type == "REGIME_FILTER_ADJUSTMENT":
            field_mutated = "allowed_regimes"
            old_val = copy.deepcopy(new_params.get("allowed_regimes", ["BULL_TREND", "SIDEWAYS"]))
            all_regimes = ["BULL_TREND", "BEAR_TREND", "SIDEWAYS", "HIGH_VOLATILITY", "LOW_VOLATILITY"]
            
            if len(old_val) > 1 and random.random() < 0.5:
                # Eliminar un régimen
                regime_to_remove = random.choice(old_val)
                new_val = [r for r in old_val if r != regime_to_remove]
                effect = f"Restricción de régimen: se eliminó {regime_to_remove}"
            else:
                # Añadir un régimen
                candidates = [r for r in all_regimes if r not in old_val]
                if candidates:
                    added = random.choice(candidates)
                    new_val = old_val + [added]
                    effect = f"Expansión de régimen: se incluyó {added}"
                else:
                    new_val = old_val
                    effect = "Sin cambios en régiment (cobertura total)"
            
            new_params["allowed_regimes"] = new_val

        else:  # Default / General perturbation
            field_mutated = "rr_target"
            old_val = new_params.get("rr_target", 2.0)
            new_val = round(old_val * 1.15, 2)
            new_params["rr_target"] = new_val
            effect = f"Aumento general del Risk/Reward de {old_val} a {new_val}"

        # Actualizar linaje
        new_params["parent_strategy_id"] = strategy.strategy_id

        child_strategy = ComposableStrategy(
            strategy_id=child_id,
            name=f"{strategy.name}_v{new_version}",
            version=new_version,
            parameters=new_params,
            rules=new_rules
        )

        child_definition = LabStrategyDefinition(
            strategy_id=child_id,
            name=f"{definition.name}_v{new_version}",
            version=new_version,
            created_by=definition.created_by,
            description=f"Mutación ({mutation_type}) de {strategy.strategy_id}: {effect}",
            status=definition.status,
            parameters=new_params,
            rules=new_rules,
            parent_strategy_id=strategy.strategy_id
        )

        record = MutationRecord(
            parent_strategy_id=strategy.strategy_id,
            child_strategy_id=child_id,
            field_mutated=field_mutated,
            old_value=old_val,
            new_value=new_val,
            expected_effect=effect
        )

        return child_strategy, child_definition, record
