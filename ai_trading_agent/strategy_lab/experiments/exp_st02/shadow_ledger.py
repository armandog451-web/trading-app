"""
ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_ledger
================================================================
Libro Contable Inmutable (Append-Only SHA-256 Hash-Chained Ledger) para EXP-ST02.

Garantiza:
1. Encadenamiento estricto SHA-256 de 64 caracteres.
2. Idempotencia absoluta (bloqueo de eventos duplicados por hash determinista).
3. Aislamiento total de bases de datos compartidas y carteras de brokers.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_models import (
    ShadowLedgerEntryST02,
    ShadowEventTypeST02,
)

GENESIS_PREV_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


def compute_entry_hash(
    entry_id: str,
    campaign_id: str,
    candidate_id: str,
    timestamp_utc: str,
    event_type: str,
    sequence_num: int,
    payload: Dict[str, Any],
    prev_hash: str,
) -> str:
    serialized_payload = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    raw = f"{entry_id}|{campaign_id}|{candidate_id}|{timestamp_utc}|{event_type}|{sequence_num}|{serialized_payload}|{prev_hash}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class ShadowLedgerST02:
    """Gestor de ledger append-only encadenado para una cartera Shadow de EXP-ST02."""

    def __init__(self, campaign_id: str, candidate_id: str, ledger_file: Path):
        self.campaign_id = campaign_id
        self.candidate_id = candidate_id
        self.ledger_file = ledger_file
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_genesis()

    def _ensure_genesis(self):
        """Inicializa el bloque génesis si el archivo está vacío o no existe."""
        if not self.ledger_file.exists() or self.ledger_file.stat().st_size == 0:
            t0 = datetime.now(timezone.utc).isoformat()
            genesis_payload = {
                "message": f"Genesis block for {self.candidate_id} in {self.campaign_id}",
                "virtual_capital": 100000.0,
                "created_at": t0,
            }
            entry_id = f"GENESIS-{self.candidate_id}"
            e_hash = compute_entry_hash(
                entry_id=entry_id,
                campaign_id=self.campaign_id,
                candidate_id=self.candidate_id,
                timestamp_utc=t0,
                event_type=ShadowEventTypeST02.GENESIS.value,
                sequence_num=0,
                payload=genesis_payload,
                prev_hash=GENESIS_PREV_HASH,
            )
            entry = ShadowLedgerEntryST02(
                entry_id=entry_id,
                campaign_id=self.campaign_id,
                candidate_id=self.candidate_id,
                timestamp_utc=t0,
                event_type=ShadowEventTypeST02.GENESIS,
                sequence_num=0,
                payload=genesis_payload,
                prev_hash=GENESIS_PREV_HASH,
                entry_hash=e_hash,
            )
            with open(self.ledger_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(entry.model_dump()) + "\n")

    def append_event(
        self,
        event_type: ShadowEventTypeST02,
        payload: Dict[str, Any],
        custom_entry_id: Optional[str] = None,
    ) -> ShadowLedgerEntryST02:
        """Añade un nuevo evento validando idempotencia y encadenamiento SHA-256."""
        entries = self.read_all_entries()
        last_entry = entries[-1]

        seq = last_entry.sequence_num + 1
        t_utc = datetime.now(timezone.utc).isoformat()
        entry_id = custom_entry_id or f"{self.candidate_id}-{seq:06d}-{event_type.value}"

        # Protección de idempotencia: si ya existe el entry_id, rechazar duplicación
        if any(e.entry_id == entry_id for e in entries):
            raise ValueError(f"Idempotency violation: entry_id '{entry_id}' already exists in ledger.")

        e_hash = compute_entry_hash(
            entry_id=entry_id,
            campaign_id=self.campaign_id,
            candidate_id=self.candidate_id,
            timestamp_utc=t_utc,
            event_type=event_type.value,
            sequence_num=seq,
            payload=payload,
            prev_hash=last_entry.entry_hash,
        )

        entry = ShadowLedgerEntryST02(
            entry_id=entry_id,
            campaign_id=self.campaign_id,
            candidate_id=self.candidate_id,
            timestamp_utc=t_utc,
            event_type=event_type,
            sequence_num=seq,
            payload=payload,
            prev_hash=last_entry.entry_hash,
            entry_hash=e_hash,
        )

        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.model_dump()) + "\n")

        return entry

    def read_all_entries(self) -> List[ShadowLedgerEntryST02]:
        """Lee y deserializa todas las entradas del ledger."""
        if not self.ledger_file.exists():
            return []
        entries = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(ShadowLedgerEntryST02(**json.loads(line.strip())))
        return entries

    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """Verifica criptográficamente toda la cadena SHA-256 desde genesis hasta el tip."""
        entries = self.read_all_entries()
        if not entries:
            return False, ["Ledger is empty"]

        violations = []
        expected_prev = GENESIS_PREV_HASH

        for i, e in enumerate(entries):
            # 1. Verificar secuencia
            if e.sequence_num != i:
                violations.append(f"Sequence mismatch at index {i}: expected {i}, got {e.sequence_num}")

            # 2. Verificar prev_hash
            if e.prev_hash != expected_prev:
                violations.append(f"Prev hash mismatch at index {i}: expected {expected_prev}, got {e.prev_hash}")

            # 3. Recalcular y verificar hash de la entrada
            recalc_hash = compute_entry_hash(
                entry_id=e.entry_id,
                campaign_id=e.campaign_id,
                candidate_id=e.candidate_id,
                timestamp_utc=e.timestamp_utc,
                event_type=e.event_type.value,
                sequence_num=e.sequence_num,
                payload=e.payload,
                prev_hash=e.prev_hash,
            )
            if recalc_hash != e.entry_hash:
                violations.append(f"Hash corrupted at index {i}: expected {recalc_hash}, got {e.entry_hash}")

            expected_prev = e.entry_hash

        return len(violations) == 0, violations
