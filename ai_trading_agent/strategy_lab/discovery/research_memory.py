"""
ai_trading_agent.strategy_lab.discovery.research_memory
========================================================
Memoria de Investigación Cuantitativa Persistente.
Almacena resultados de experimentos, evita duplicados, rastrea la utilidad de los features
y documenta patrones de fallos pasados para aprendizaje acumulativo.
"""

import sqlite3
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MemoryObservation(BaseModel):
    """Observación individual registrada en la Memoria de Investigación."""
    observation_id: str = Field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:8]}")
    hypothesis_id: str
    strategy_id: str
    features_used: List[str]
    metrics: Dict[str, Any]
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    failure_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ResearchMemory:
    """Gestor de Memoria Persistente para el Strategy Discovery Engine."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self._in_memory_observations: List[MemoryObservation] = []
        self._tested_signatures: set = set()
        if self.db_path:
            self._init_db()

    def _init_db(self):
        """Inicializa la tabla lab_research_memory en la base de datos SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS lab_research_memory (
                        observation_id TEXT PRIMARY KEY,
                        hypothesis_id TEXT,
                        strategy_id TEXT,
                        features_used TEXT,
                        signature TEXT,
                        sharpe_ratio REAL,
                        win_rate REAL,
                        max_drawdown REAL,
                        failure_reason TEXT,
                        metrics_json TEXT,
                        created_at TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[ResearchMemory] Advertencia: No se pudo inicializar SQLite ({e}). Usando modo in-memory.")
            self.db_path = None

    def _compute_signature(self, features: List[str], parameters: Dict[str, Any]) -> str:
        """Calcula la firma hash única de una combinación de features y parámetros claves."""
        sorted_features = sorted(features)
        key_params = {k: parameters[k] for k in sorted(parameters.keys()) if k in ["min_rvol", "atr_stop_mult", "rr_target", "min_rsi", "max_rsi"]}
        sig_str = f"feat:{','.join(sorted_features)}|params:{json.dumps(key_params, sort_keys=True)}"
        return hashlib.md5(sig_str.encode('utf-8')).hexdigest()

    def record_experiment(
        self,
        hypothesis_id: str,
        strategy_id: str,
        features: List[str],
        parameters: Dict[str, Any],
        metrics: Dict[str, Any],
        failure_reason: Optional[str] = None
    ) -> MemoryObservation:
        """Registra un nuevo resultado de experimento en la memoria."""
        sharpe = float(metrics.get("sharpe_ratio", 0.0))
        win_rate = float(metrics.get("win_rate", 0.0))
        max_dd = float(metrics.get("max_drawdown", 0.0))

        obs = MemoryObservation(
            hypothesis_id=hypothesis_id,
            strategy_id=strategy_id,
            features_used=features,
            metrics=metrics,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            max_drawdown=max_dd,
            failure_reason=failure_reason
        )

        signature = self._compute_signature(features, parameters)
        self._tested_signatures.add(signature)
        self._in_memory_observations.append(obs)

        if self.db_path:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO lab_research_memory 
                        (observation_id, hypothesis_id, strategy_id, features_used, signature, sharpe_ratio, win_rate, max_drawdown, failure_reason, metrics_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        obs.observation_id,
                        obs.hypothesis_id,
                        obs.strategy_id,
                        json.dumps(features),
                        signature,
                        sharpe,
                        win_rate,
                        max_dd,
                        failure_reason,
                        json.dumps(metrics, default=str),
                        obs.created_at
                    ))
                    conn.commit()
            except Exception as e:
                print(f"[ResearchMemory] Error guardando en SQLite: {e}")

        return obs

    def is_duplicate_experiment(self, features: List[str], parameters: Dict[str, Any], similarity_threshold: float = 0.95) -> bool:
        """Comprueba si una combinación de features y parámetros ya fue evaluada previamente."""
        sig = self._compute_signature(features, parameters)
        if sig in self._tested_signatures:
            return True
        return False

    def get_top_performing_features(self, top_n: int = 5) -> List[str]:
        """Devuelve los n features con mejor desempeño promedio acumulado."""
        feature_scores: Dict[str, List[float]] = {}
        for obs in self._in_memory_observations:
            if obs.sharpe_ratio > 0:
                for f in obs.features_used:
                    feature_scores.setdefault(f, []).append(obs.sharpe_ratio)

        if not feature_scores:
            return ["ema_cross_9_21", "relative_volume_rvol", "rsi_14"]

        avg_scores = {f: sum(scores)/len(scores) for f, scores in feature_scores.items()}
        sorted_feats = sorted(avg_scores.keys(), key=lambda k: avg_scores[k], reverse=True)
        return sorted_feats[:top_n]

    def get_failed_patterns(self) -> List[Dict[str, Any]]:
        """Retorna lista de patrones y combinaciones que produjeron fallos o bajo Sharpe."""
        failed = []
        for obs in self._in_memory_observations:
            if obs.failure_reason or obs.sharpe_ratio < 0.5:
                failed.append({
                    "strategy_id": obs.strategy_id,
                    "features": obs.features_used,
                    "reason": obs.failure_reason or "Sharpe ratio < 0.5",
                    "sharpe": obs.sharpe_ratio
                })
        return failed

    def get_all_observations(self) -> List[MemoryObservation]:
        """Devuelve el historial completo de observaciones."""
        return list(self._in_memory_observations)

    def record_dataset_usage(
        self,
        dataset_name: str,
        query_type: str = "ranking"  # ranking, selection, mutation, exploitation
    ) -> Dict[str, int]:
        """
        Registra el uso adaptativo de particiones de datos (Fase 9).
        Si un dataset se utiliza para ranking, selección o explotación repetida,
        queda automáticamente marcado como RESEARCH_VALIDATION.
        """
        if not hasattr(self, "_dataset_usage"):
            self._dataset_usage: Dict[str, Dict[str, int]] = {}

        if dataset_name not in self._dataset_usage:
            self._dataset_usage[dataset_name] = {
                "number_of_queries": 0,
                "number_of_rankings": 0,
                "number_of_selection_decisions": 0,
                "number_of_mutation_decisions": 0,
                "number_of_exploitations": 0
            }

        counts = self._dataset_usage[dataset_name]
        counts["number_of_queries"] += 1
        if query_type == "ranking":
            counts["number_of_rankings"] += 1
        elif query_type == "selection":
            counts["number_of_selection_decisions"] += 1
        elif query_type == "mutation":
            counts["number_of_mutation_decisions"] += 1
        elif query_type == "exploitation":
            counts["number_of_exploitations"] += 1

        return counts

    def get_dataset_usage(self, dataset_name: Optional[str] = None) -> Dict[str, Any]:
        """Devuelve el conteo de uso adaptativo acumulado por dataset."""
        if not hasattr(self, "_dataset_usage"):
            self._dataset_usage = {}
        if dataset_name:
            return self._dataset_usage.get(dataset_name, {
                "number_of_queries": 0,
                "number_of_rankings": 0,
                "number_of_selection_decisions": 0,
                "number_of_mutation_decisions": 0,
                "number_of_exploitations": 0
            })
        return dict(self._dataset_usage)

