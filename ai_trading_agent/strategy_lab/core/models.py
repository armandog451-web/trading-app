"""
ai_trading_agent.strategy_lab.core.models
==========================================
Modelos de datos, enumeraciones y calculadores de complejidad del Strategy Laboratory.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import math


class StrategyStatus(str, Enum):
    RESEARCH = "RESEARCH"
    BACKTEST = "BACKTEST"
    VALIDATING = "VALIDATING"
    CANDIDATE = "CANDIDATE"
    PAPER = "PAPER"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    RETIRED = "RETIRED"


StrategyLifecycleStatus = StrategyStatus



class HypothesisStatus(str, Enum):
    NEW = "NEW"
    TESTING = "TESTING"
    SUPPORTED = "SUPPORTED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class DataSplitType(str, Enum):
    IN_SAMPLE = "IN_SAMPLE"
    OUT_OF_SAMPLE = "OUT_OF_SAMPLE"
    WALK_FORWARD = "WALK_FORWARD"
    FINAL_HOLDOUT = "FINAL_HOLDOUT"


class LabHypothesis(BaseModel):
    hypothesis_id: str
    description: str
    generated_by: str = "AI_RESEARCH_AGENT"  # SYSTEM, AI_RESEARCH_AGENT, HUMAN
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    features_used: List[str] = Field(default_factory=list)
    market_conditions: List[str] = Field(default_factory=list)
    expected_behavior: str
    experiment_plan: str
    result: str = ""
    status: HypothesisStatus = HypothesisStatus.NEW


class LabExperiment(BaseModel):
    experiment_id: str
    hypothesis_id: str
    strategy_id: str
    strategy_version: str
    dataset_version: str = "v1.0"
    universe: List[str] = Field(default_factory=lambda: ["SPY", "QQQ", "AAPL"])
    symbols: List[str] = Field(default_factory=lambda: ["SPY"])
    timeframe: str = "15m"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    features: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    status: str = "COMPLETED"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LabStrategyDefinition(BaseModel):
    strategy_id: str
    name: str
    version: str
    description: str
    parent_strategy_id: str = ""
    created_by: str = "AI_RESEARCH_AGENT"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: StrategyStatus = StrategyStatus.RESEARCH
    universe: List[str] = Field(default_factory=lambda: ["SPY", "QQQ"])
    timeframes: List[str] = Field(default_factory=lambda: ["15m"])
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rules: Dict[str, Any] = Field(default_factory=dict)
    robustness_score: float = 0.0
    economic_edge_score: float = 0.0
    strategy_quality_score: float = 0.0
    strategy_score: float = 0.0
    metrics: Dict[str, Any] = Field(default_factory=dict)


class StrategyLineage(BaseModel):
    parent_id: str
    child_id: str
    mutation_description: str
    reason: str
    experiment_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyComplexityCalculator:
    """Calcula el Score de Complejidad de una Estrategia (0 a 100)."""

    @staticmethod
    def calculate(parameters: Dict[str, Any], rules: Dict[str, Any], total_trades: int = 100) -> float:
        """
        Penaliza exceso de parámetros, sobreabundancia de reglas/filtros y escasez de operaciones.
        """
        num_params = len(parameters)
        entry_rules = len(rules.get("entry_conditions", []))
        exit_rules = len(rules.get("exit_conditions", []))
        filters = len(rules.get("filters", []))

        total_components = num_params + entry_rules + exit_rules + filters

        # Complejidad base por cantidad de componentes (0 - 50 pts)
        base_complexity = min(50.0, total_components * 4.0)

        # Penalización por escasez de operaciones (0 - 50 pts si trades < 30)
        trade_penalty = 0.0
        if total_trades < 30:
            trade_penalty = (30 - total_trades) * 1.5

        complexity_score = min(100.0, round(base_complexity + trade_penalty, 2))
        return complexity_score


class FailureAnalysisRecord(BaseModel):
    failure_type: str
    evidence: str
    severity: str  # HIGH, MEDIUM, LOW
    suspected_cause: str
    suggested_change: str
