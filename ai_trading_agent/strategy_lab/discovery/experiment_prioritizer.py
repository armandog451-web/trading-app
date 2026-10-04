"""
ai_trading_agent.strategy_lab.discovery.experiment_prioritizer
===============================================================
Motor de Priorización de Experimentos, Novedad, Sobreajuste y Balance 70/30.
Calcula Similarity Index, Novelty Score (0-100), Overfitting Risk (0-100) y
Prioridad Combinada (Exploration 70% vs Exploitation 30%).
"""

import math
from typing import List, Dict, Any, Tuple, Optional
from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition
from ai_trading_agent.strategy_lab.discovery.research_memory import ResearchMemory


class StrategySimilarityEngine:
    """Motor para evaluar la similitud estructural entre dos estrategias cuantitativas."""

    @staticmethod
    def calculate_feature_overlap(features1: List[str], features2: List[str]) -> float:
        """Calcula el índice de Jaccard entre dos listas de features (0.0 a 1.0)."""
        if not features1 or not features2:
            return 0.0
        set1 = set(features1)
        set2 = set(features2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    @classmethod
    def calculate_strategy_similarity(cls, def1: LabStrategyDefinition, def2: LabStrategyDefinition) -> float:
        """Calcula el puntaje de similitud compuesto entre 0 y 100."""
        feats1 = def1.rules.get("features", []) or list(def1.parameters.keys())
        feats2 = def2.rules.get("features", []) or list(def2.parameters.keys())
        
        feature_sim = cls.calculate_feature_overlap(feats1, feats2)
        
        # Similitud de plantilla o tipo
        tmpl1 = def1.rules.get("template", "")
        tmpl2 = def2.rules.get("template", "")
        template_sim = 1.0 if (tmpl1 and tmpl1 == tmpl2) else 0.0

        # Similitud compuesta de 0 a 100
        composite = (feature_sim * 0.7 + template_sim * 0.3) * 100.0
        return round(composite, 2)


def calculate_novelty_score(
    strategy_def: LabStrategyDefinition,
    existing_definitions: List[LabStrategyDefinition]
) -> float:
    """
    Calcula el Novelty Score (0 a 100).
    Estrategias con bajo solapamiento frente al catálogo existente reciben puntajes altos (cercanos a 100).
    """
    if not existing_definitions:
        return 100.0

    similarities = [
        StrategySimilarityEngine.calculate_strategy_similarity(strategy_def, existing)
        for existing in existing_definitions
    ]
    max_similarity = max(similarities) if similarities else 0.0
    novelty = max(0.0, 100.0 - max_similarity)
    return round(novelty, 2)


def calculate_overfitting_risk_score(strategy_def: LabStrategyDefinition) -> float:
    """
    Calcula el Overfitting Risk Score (0 a 100).
    Penaliza estrategias con alta densidad de parámetros, reglas complejas o excesivos grados de libertad.
    """
    params = strategy_def.parameters or {}
    rules = strategy_def.rules or {}
    conditions = rules.get("conditions", [])

    num_params = len(params)
    num_conditions = len(conditions)

    # Evaluación de complejidad
    base_risk = (num_params * 5.0) + (num_conditions * 10.0)

    # Penalización si se usan rangos extremadamente estrechos
    min_rsi = params.get("min_rsi", 30)
    max_rsi = params.get("max_rsi", 70)
    if (max_rsi - min_rsi) < 15:
        base_risk += 25.0  # Sobreajuste por ventana estrecha

    rr_target = params.get("rr_target", 2.0)
    if rr_target > 5.0 or rr_target < 1.0:
        base_risk += 15.0

    risk_score = min(100.0, max(0.0, base_risk))
    return round(risk_score, 2)


class ExperimentPriorityEngine:
    """
    Motor de Priorización de Experimentos con asignación balanceada:
    70% Exploración (novedad) / 30% Explotación (optimización de mejores features).
    """

    def __init__(self, exploration_weight: float = 0.70, exploitation_weight: float = 0.30):
        self.exploration_weight = exploration_weight
        self.exploitation_weight = exploitation_weight

    def prioritize_experiments(
        self,
        candidate_definitions: List[LabStrategyDefinition],
        existing_definitions: List[LabStrategyDefinition],
        memory: Optional[ResearchMemory] = None
    ) -> List[Tuple[LabStrategyDefinition, float]]:
        """
        Prioriza las estrategias candidatas asignándoles una puntuación de prioridad.
        Retorna la lista ordenada descendentemente por puntuación.
        """
        top_features = set(memory.get_top_performing_features(top_n=5)) if memory else set()
        ranked: List[Tuple[LabStrategyDefinition, float]] = []

        for cand in candidate_definitions:
            novelty = calculate_novelty_score(cand, existing_definitions)
            overfit_risk = calculate_overfitting_risk_score(cand)

            # Cálculo de Explotación (uso de features con alto rendimiento comprobado)
            cand_feats = cand.rules.get("features", [])
            exploitation_score = 0.0
            if cand_feats:
                matches = sum(1 for f in cand_feats if f in top_features)
                exploitation_score = (matches / len(cand_feats)) * 100.0
            else:
                exploitation_score = 50.0

            # Score combinado: (70% Novelty + 30% Exploitation) - (0.5 * Overfitting Risk)
            combined_score = (
                (novelty * self.exploration_weight) +
                (exploitation_score * self.exploitation_weight) -
                (overfit_risk * 0.3)
            )
            final_score = max(0.0, round(combined_score, 2))

            ranked.append((cand, final_score))

        # Ordenar descendentemente por score
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
