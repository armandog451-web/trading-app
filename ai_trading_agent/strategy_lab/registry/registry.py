"""
ai_trading_agent.strategy_lab.registry.registry
================================================
Registro Central de Estrategias con Versionado Inmutable y Persistencia SQLite.
Gestiona el catálogo de estrategias investigadas, candidatas y aprobadas.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition, StrategyStatus, StrategyLineage
from database import get_connection


class StrategyRegistry:
    """Registro central con soporte de versionado y persistencia relacional."""

    def register_strategy(self, strat: LabStrategyDefinition):
        """Registra o actualiza una estrategia en SQLite."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lab_strategy_registry
            (strategy_id, name, version, description, parent_strategy_id, created_by, created_at, updated_at, status, universe_json, timeframes_json, parameters_json, rules_json, robustness_score, strategy_score, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(strategy_id) DO UPDATE SET
            status = excluded.status,
            robustness_score = excluded.robustness_score,
            strategy_score = excluded.strategy_score,
            metrics_json = excluded.metrics_json,
            updated_at = excluded.updated_at
        """, (
            strat.strategy_id,
            strat.name,
            strat.version,
            strat.description,
            strat.parent_strategy_id,
            strat.created_by,
            strat.created_at.isoformat(),
            strat.updated_at.isoformat(),
            strat.status.value,
            json.dumps(strat.universe),
            json.dumps(strat.timeframes),
            json.dumps(strat.parameters),
            json.dumps(strat.rules),
            strat.robustness_score,
            strat.strategy_score,
            json.dumps(strat.metrics)
        ))
        conn.commit()
        conn.close()

    def record_lineage(self, lineage: StrategyLineage):
        """Registra la relación padre-hijo (mutación evolutiva) en SQLite."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lab_strategy_lineage (parent_id, child_id, mutation_description, reason, experiment_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            lineage.parent_id,
            lineage.child_id,
            lineage.mutation_description,
            lineage.reason,
            lineage.experiment_id,
            lineage.created_at.isoformat()
        ))
        conn.commit()
        conn.close()

    def get_strategy(self, strategy_id: str) -> Optional[LabStrategyDefinition]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lab_strategy_registry WHERE strategy_id = ?", (strategy_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return LabStrategyDefinition(
            strategy_id=row["strategy_id"],
            name=row["name"],
            version=row["version"],
            description=row["description"],
            parent_strategy_id=row["parent_strategy_id"] or "",
            created_by=row["created_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            status=StrategyStatus(row["status"]),
            universe=json.loads(row["universe_json"]),
            timeframes=json.loads(row["timeframes_json"]),
            parameters=json.loads(row["parameters_json"]),
            rules=json.loads(row["rules_json"]),
            robustness_score=row["robustness_score"],
            strategy_score=row["strategy_score"],
            metrics=json.loads(row["metrics_json"] or "{}")
        )

    def list_strategies(self, status_filter: Optional[StrategyStatus] = None) -> List[LabStrategyDefinition]:
        conn = get_connection()
        cursor = conn.cursor()
        if status_filter:
            cursor.execute("SELECT * FROM lab_strategy_registry WHERE status = ? ORDER BY strategy_score DESC", (status_filter.value,))
        else:
            cursor.execute("SELECT * FROM lab_strategy_registry ORDER BY strategy_score DESC")
        rows = cursor.fetchall()
        conn.close()

        strategies = []
        for r in rows:
            strategies.append(LabStrategyDefinition(
                strategy_id=r["strategy_id"],
                name=r["name"],
                version=r["version"],
                description=r["description"],
                parent_strategy_id=r["parent_strategy_id"] or "",
                created_by=r["created_by"],
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
                status=StrategyStatus(r["status"]),
                universe=json.loads(r["universe_json"]),
                timeframes=json.loads(r["timeframes_json"]),
                parameters=json.loads(r["parameters_json"]),
                rules=json.loads(r["rules_json"]),
                robustness_score=r["robustness_score"],
                strategy_score=r["strategy_score"],
                metrics=json.loads(r["metrics_json"] or "{}")
            ))
        return strategies


strategy_registry = StrategyRegistry()
