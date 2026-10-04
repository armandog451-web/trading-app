"""
ai_trading_agent.strategy_lab.reporting.generator
==================================================
Generador de Informes Cuantitativos y Registro de Investigaciones del Strategy Laboratory.
Integra la investigación autónoma con el Weekend Research Scan.
"""

from typing import Dict, Any, List
from datetime import datetime

from ai_trading_agent.strategy_lab.registry.registry import strategy_registry
from ai_trading_agent.strategy_lab.core.models import StrategyStatus
from database import get_connection


class LabReportingGenerator:
    """Genera reportes ejecutivos e informes semanales de investigación."""

    def generate_laboratory_overview(self) -> Dict[str, Any]:
        all_strats = strategy_registry.list_strategies()

        status_counts = {s.value: 0 for s in StrategyStatus}
        for st in all_strats:
            status_counts[st.status.value] += 1

        top_performers = sorted(all_strats, key=lambda x: x.strategy_score, reverse=True)[:3]

        return {
            "total_strategies": len(all_strats),
            "status_breakdown": status_counts,
            "top_strategies": [
                {
                    "strategy_id": s.strategy_id,
                    "name": s.name,
                    "version": s.version,
                    "status": s.status.value,
                    "strategy_score": s.strategy_score,
                    "robustness_score": s.robustness_score
                }
                for s in top_performers
            ],
            "generated_at": datetime.utcnow().isoformat()
        }

    def generate_weekly_research_report(self) -> Dict[str, Any]:
        overview = self.generate_laboratory_overview()

        # Consultar experimentos recientes de SQLite
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM lab_experiments")
        total_exp = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM lab_hypotheses")
        total_hyp = cursor.fetchone()[0]
        conn.close()

        report = {
            "title": "Weekly Strategy Research Report",
            "period_end": datetime.utcnow().strftime("%Y-%m-%d"),
            "total_experiments_run": total_exp,
            "total_hypotheses_generated": total_hyp,
            "laboratory_overview": overview,
            "executive_summary": (
                "El laboratorio autónomo de investigación ha completado las simulaciones de la semana. "
                f"Se registran {overview['total_strategies']} estrategias en catálogo con {overview['status_breakdown'].get('APPROVED', 0)} estrategias aprobadas para el Trading Agent."
            )
        }
        return report


lab_reporting_generator = LabReportingGenerator()
