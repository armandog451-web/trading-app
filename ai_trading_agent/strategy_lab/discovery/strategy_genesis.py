"""
ai_trading_agent.strategy_lab.discovery.strategy_genesis
=========================================================
Motor de Génesis de Estrategias para el Discovery Engine.
Convierte hipótesis cuantitativas y especificaciones declarativas DSL en instancias
ejecutables de ComposableStrategy y modelos de LabStrategyDefinition.
"""

import uuid
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition, StrategyLifecycleStatus
from ai_trading_agent.strategy_lab.strategies.composable import ComposableStrategy
from ai_trading_agent.strategy_lab.discovery.hypothesis_generator import DiscoveryHypothesis


class RuleConditionDSL(BaseModel):
    feature_id: str
    operator: str  # '>', '<', '==', '>=', '<=', 'CROSS_ABOVE', 'CROSS_BELOW'
    threshold: Any
    weight: float = 1.0


class StrategyRuleDSL(BaseModel):
    entry_conditions: List[RuleConditionDSL] = Field(default_factory=list)
    exit_conditions: List[RuleConditionDSL] = Field(default_factory=list)
    filter_conditions: List[RuleConditionDSL] = Field(default_factory=list)
    regime_filter: List[str] = Field(default_factory=lambda: ["BULL_TREND", "SIDEWAYS", "HIGH_VOLATILITY"])
    atr_stop_mult: float = 1.5
    rr_target: float = 2.0


class AutonomousStrategyGenesisEngine:
    """Motor de Génesis de Estrategias cuantitativas dinámicas."""

    def __init__(self):
        pass

    def generate_from_hypothesis(
        self,
        hypothesis: DiscoveryHypothesis,
        version: str = "1.0",
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[ComposableStrategy, LabStrategyDefinition]:
        """Crea una estrategia dinámica a partir de una hipótesis formalizada."""
        strategy_id = f"strat_disc_{uuid.uuid4().hex[:8]}"
        name = f"Autogen_{hypothesis.target_market.replace('/', '_')}_{hypothesis.hypothesis_id}"

        params = {
            "min_rsi": 30.0,
            "max_rsi": 70.0,
            "min_rvol": 1.2,
            "atr_stop_mult": 1.5,
            "rr_target": 2.0,
            "hypothesis_id": hypothesis.hypothesis_id,
            "target_market": hypothesis.target_market,
            "target_timeframe": hypothesis.target_timeframe,
        }
        if custom_params:
            params.update(custom_params)

        rules = {
            "conditions": hypothesis.conditions,
            "features": hypothesis.features,
            "description": hypothesis.description
        }

        # Instancia ejecutable de la estrategia
        strategy_instance = ComposableStrategy(
            strategy_id=strategy_id,
            name=name,
            version=version,
            parameters=params,
            rules=rules
        )

        # Registro formal para el StrategyRegistry
        definition = LabStrategyDefinition(
            strategy_id=strategy_id,
            name=name,
            version=version,
            created_by="DiscoveryEngine_v1.0",
            description=hypothesis.description,
            status=StrategyLifecycleStatus.RESEARCH,
            parameters=params,
            rules=rules
        )

        return strategy_instance, definition

    def generate_from_template(
        self,
        template_name: str,
        target_market: str = "BTC/USDT",
        target_timeframe: str = "1h",
        parameters_override: Optional[Dict[str, Any]] = None
    ) -> Tuple[ComposableStrategy, LabStrategyDefinition]:
        """Genera una estrategia de plantilla preconfigurada con variaciones de parámetros."""
        strategy_id = f"tmpl_{template_name.lower()}_{uuid.uuid4().hex[:6]}"
        name = f"Template_{template_name}_{uuid.uuid4().hex[:4]}"

        base_params = {
            "min_rsi": 30.0,
            "max_rsi": 70.0,
            "min_rvol": 1.2,
            "atr_stop_mult": 1.5,
            "rr_target": 2.0,
            "allowed_regimes": ["BULL_TREND", "SIDEWAYS", "HIGH_VOLATILITY"]
        }

        if template_name == "TREND_FOLLOWING":
            base_params.update({"min_rvol": 1.5, "atr_stop_mult": 2.0, "rr_target": 2.5})
        elif template_name == "MEAN_REVERSION":
            base_params.update({"min_rsi": 25.0, "max_rsi": 75.0, "atr_stop_mult": 1.2, "rr_target": 1.8})
        elif template_name == "VOLATILITY_BREAKOUT":
            base_params.update({"min_rvol": 2.0, "atr_stop_mult": 1.8, "rr_target": 3.0})

        if parameters_override:
            base_params.update(parameters_override)

        strategy_instance = ComposableStrategy(
            strategy_id=strategy_id,
            name=name,
            version="1.0",
            parameters=base_params,
            rules={"template": template_name}
        )

        definition = LabStrategyDefinition(
            strategy_id=strategy_id,
            name=name,
            version="1.0",
            created_by="GenesisEngine_Template",
            description=f"Estrategia basada en plantilla {template_name}",
            status=StrategyLifecycleStatus.RESEARCH,
            parameters=base_params,
            rules={"template": template_name}
        )

        return strategy_instance, definition
