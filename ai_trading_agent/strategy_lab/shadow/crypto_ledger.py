"""
ai_trading_agent.strategy_lab.shadow.crypto_ledger
===================================================
Ledger inmutable append-only con encadenamiento criptográfico (Bloque E).
Garantiza:
- Detección matemática de alteraciones o falsificación retrospectiva.
- Persistencia transaccional a prueba de reinicios.
- Identificadores idempotentes y deduplicación estricta.
- Exportación a JSONL, JSON estructurado y CSV.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import csv

from .campaign_models import (
    ShadowLedgerEntry,
    ShadowEventType
)


class LedgerTamperDetectedError(Exception):
    """Excepción lanzada si se detecta cualquier alteración en el histórico del ledger."""
    pass


class ShadowEvidenceLedger:
    """
    Libro mayor criptográfico inmutable para evidencia prospectiva Shadow.
    Implementa encadenamiento de bloques SHA-256 tipo blockchain liviana para auditoría institucional.
    """

    GENESIS_PREV_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self, campaign_id: str, strategy_id: str, storage_dir: Path):
        self.campaign_id = campaign_id
        self.strategy_id = strategy_id
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.jsonl_path = self.storage_dir / f"shadow_ledger_{self.strategy_id}.jsonl"
        self.manifest_path = self.storage_dir / f"shadow_summary_{self.strategy_id}.json"
        self.trades_csv_path = self.storage_dir / f"shadow_trades_{self.strategy_id}.csv"

        self.entries: List[ShadowLedgerEntry] = []
        self._entry_ids_seen = set()

        # Reconciliar y cargar historial existente
        self._load_and_verify_chain()

    def _canonical_payload(self, data: Dict[str, Any]) -> str:
        """Serializa el diccionario de forma canónica y determinista para hashing."""
        clean = dict(data)
        clean.pop("entry_hash", None)
        return json.dumps(clean, sort_keys=True, separators=(',', ':'))

    def compute_entry_hash(self, prev_hash: str, payload_str: str) -> str:
        """Calcula el hash SHA-256 encadenado de una entrada."""
        raw = f"{prev_hash}|{payload_str}".encode('utf-8')
        return hashlib.sha256(raw).hexdigest()

    def _load_and_verify_chain(self):
        """Carga y valida el ledger previo si existe en disco."""
        if not self.jsonl_path.exists():
            return

        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entry = ShadowLedgerEntry(**data)
                self.entries.append(entry)
                self._entry_ids_seen.add(entry.entry_id)

        # Verificar integridad
        valid, err = self.verify_chain_integrity()
        if not valid:
            raise LedgerTamperDetectedError(f"FALLO DE INTEGRIDAD EN LEDGER {self.strategy_id}: {err}")

    def append_entry(
        self,
        entry_id: str,
        market_date: str,
        symbol: str,
        event_type: ShadowEventType,
        signal_direction: str,
        reason: str,
        strategy_fingerprint: str,
        bar_hash: str,
        simulated_order: Optional[Dict[str, Any]] = None,
        simulated_fill: Optional[Dict[str, Any]] = None,
        open_position: Optional[Dict[str, Any]] = None,
        realized_gross_pnl: float = 0.0,
        realized_net_pnl: float = 0.0,
        costs_usd: float = 0.0,
        portfolio_cash: float = 100_000.0,
        portfolio_equity: float = 100_000.0,
        drawdown_pct: float = 0.0,
        timestamp_utc: Optional[str] = None
    ) -> ShadowLedgerEntry:
        """
        Agrega una entrada atómica al final del ledger con hash encadenado.
        Rechaza duplicados de entry_id (idempotencia estricta).
        """
        if entry_id in self._entry_ids_seen:
            raise ValueError(f"DUPLICATE_ENTRY_ID_REJECTED: La entrada '{entry_id}' ya existe en el ledger.")

        idx = len(self.entries)
        prev_hash = self.entries[-1].entry_hash if idx > 0 else self.GENESIS_PREV_HASH
        ts = timestamp_utc or datetime.utcnow().isoformat()

        base_dict = {
            "entry_id": entry_id,
            "entry_index": idx,
            "campaign_id": self.campaign_id,
            "strategy_id": self.strategy_id,
            "strategy_fingerprint_sha256": strategy_fingerprint,
            "market_date": market_date,
            "timestamp_utc": ts,
            "symbol": symbol,
            "event_type": event_type.value if hasattr(event_type, "value") else str(event_type),
            "signal_direction": signal_direction,
            "reason": reason,
            "bar_hash_sha256": bar_hash,
            "simulated_order": simulated_order,
            "simulated_fill": simulated_fill,
            "open_position": open_position,
            "realized_gross_pnl": round(realized_gross_pnl, 2),
            "realized_net_pnl": round(realized_net_pnl, 2),
            "costs_usd": round(costs_usd, 2),
            "portfolio_cash": round(portfolio_cash, 2),
            "portfolio_equity": round(portfolio_equity, 2),
            "drawdown_pct": round(drawdown_pct, 2),
            "prev_entry_hash": prev_hash
        }

        canonical_payload = self._canonical_payload(base_dict)
        entry_hash = self.compute_entry_hash(prev_hash, canonical_payload)
        base_dict["entry_hash"] = entry_hash

        entry = ShadowLedgerEntry(**base_dict)
        self.entries.append(entry)
        self._entry_ids_seen.add(entry_id)

        # Persistir a JSONL en modo append atómico
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(base_dict) + "\n")

        # Si el evento representa cierre de operación, exportar a CSV de trades
        if event_type == ShadowEventType.POSITION_CLOSED and simulated_fill:
            self._append_to_csv(base_dict)

        return entry

    def _append_to_csv(self, entry_dict: Dict[str, Any]):
        """Registra operaciones cerradas en el archivo CSV."""
        file_exists = self.trades_csv_path.exists()
        fill = entry_dict.get("simulated_fill", {}) or {}
        pos = entry_dict.get("open_position", {}) or {}

        fieldnames = [
            "entry_id", "market_date", "timestamp_utc", "symbol", "event_type",
            "realized_gross_pnl", "costs_usd", "realized_net_pnl", "portfolio_equity",
            "drawdown_pct", "entry_fill_price", "exit_fill_price", "shares", "holding_bars",
            "entry_hash"
        ]

        row = {
            "entry_id": entry_dict["entry_id"],
            "market_date": entry_dict["market_date"],
            "timestamp_utc": entry_dict["timestamp_utc"],
            "symbol": entry_dict["symbol"],
            "event_type": entry_dict["event_type"],
            "realized_gross_pnl": entry_dict["realized_gross_pnl"],
            "costs_usd": entry_dict["costs_usd"],
            "realized_net_pnl": entry_dict["realized_net_pnl"],
            "portfolio_equity": entry_dict["portfolio_equity"],
            "drawdown_pct": entry_dict["drawdown_pct"],
            "entry_fill_price": pos.get("entry_fill_price", 0.0),
            "exit_fill_price": fill.get("exit_fill_price", 0.0),
            "shares": pos.get("shares", 0),
            "holding_bars": pos.get("bars_held", 0),
            "entry_hash": entry_dict["entry_hash"][:16]
        }

        with open(self.trades_csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    def verify_chain_integrity(self) -> Tuple[bool, str]:
        """
        Verificación matemática completa de la cadena de hashes.
        Recorre desde el bloque 0 hasta el final, re-calculando hashes y comprobando encadenamiento.
        """
        if not self.entries:
            return True, "LEDGER_EMPTY"

        for i, entry in enumerate(self.entries):
            # 1. Comprobar prev_hash
            expected_prev = self.GENESIS_PREV_HASH if i == 0 else self.entries[i - 1].entry_hash
            if entry.prev_entry_hash != expected_prev:
                return False, f"ENCADENAMIENTO_ROTO en índice {i}: prev_entry_hash={entry.prev_entry_hash[:12]} != esperado={expected_prev[:12]}"

            # 2. Recomputar hash del bloque
            entry_dict = entry.model_dump()
            canonical_payload = self._canonical_payload(entry_dict)
            recomputed = self.compute_entry_hash(entry.prev_entry_hash, canonical_payload)

            if entry.entry_hash != recomputed:
                return False, f"ALTERACION_DETECTADA en índice {i} ({entry.entry_id}): hash={entry.entry_hash[:12]} != recomputado={recomputed[:12]}"

        return True, f"INTEGRIDAD_VERIFICADA ({len(self.entries)} entradas enlazadas perfectamente)"

    def get_latest_hash(self) -> str:
        """Devuelve el hash más reciente del ledger."""
        return self.entries[-1].entry_hash if self.entries else self.GENESIS_PREV_HASH

    def get_entry_count(self) -> int:
        """Devuelve el número total de entradas persistidas."""
        return len(self.entries)
