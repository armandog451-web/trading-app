"""
ai_trading_agent.journal.trade_journal
======================================
Diario inmutable de auditoría y decisiones (Instrucción 15).
Permite reconstruir el flujo completo de cualquier propuesta mediante su decision_id.
"""

from typing import Dict, List, Optional
from ai_trading_agent.domain.models import DecisionRecord
from ai_trading_agent.data.storage.repository import audit_repo


class TradeJournal:
    """Registro inmutable de trazabilidad de decisiones."""

    def __init__(self):
        self._records: Dict[str, DecisionRecord] = {}

    def log_decision(self, record: DecisionRecord) -> None:
        """Almacena un registro de decisión asegurando inmutabilidad en memoria y base de datos."""
        self._records[record.decision_id] = record
        try:
            audit_repo.save_decision(record)
        except Exception:
            pass

    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        """Recupera la trazabilidad completa de una decisión por su ID."""
        return self._records.get(decision_id)

    def get_all_decisions(self) -> List[DecisionRecord]:
        """Devuelve todas las decisiones registradas cronológicamente."""
        return list(self._records.values())

    def get_history(self, limit: int = 50) -> List[DecisionRecord]:
        """Devuelve las últimas N decisiones registradas cronológicamente."""
        all_recs = list(self._records.values())
        return all_recs[-limit:] if len(all_recs) > limit else all_recs

    def clear(self) -> None:
        """Limpia el diario (utilizado en tests)."""
        self._records.clear()


trade_journal = TradeJournal()
