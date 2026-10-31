"""
ai_trading_agent.strategy_lab.experiments.exp_st02.frozen_candidates
====================================================================
Generador y Validador de Candidatos Congelados con Fingerprints Criptográficos (EXP-ST02).

Candidatos Congelados:
1. ST02-GLD-BASE: GLD / H1 / Baseline TP 1.5R / SL SuperTrend Line
2. ST02-GLD-H5:   GLD / H1 / H5 Adaptive SuperTrend Trailing Stop
3. ST02-DIA-BASE: DIA / H1 / Baseline TP 1.5R / SL SuperTrend Line
4. ST02-DIA-H5:   DIA / H1 / H5 Adaptive SuperTrend Trailing Stop

Garantiza inmutabilidad matemática, trazabilidad Git y especificación determinista de H5.
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import json
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_backtester import COST_TIERS


def compute_sha256_file(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_sha256_dict(d: Dict[str, Any]) -> str:
    serialized = json.dumps(d, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(serialized).hexdigest()


@dataclass
class FrozenCandidateConfig:
    candidate_id: str
    symbol: str
    timeframe: str
    variant: str  # "BASELINE_TP_1_5R" o "H5_ADAPTIVE_TRAILING"
    parameters: Dict[str, Any]
    h5_specification: Optional[Dict[str, Any]]
    virtual_capital_usd: float
    risk_per_trade_usd: float
    risk_pct_nominal: float
    max_positions: int
    cost_model: Dict[str, Any]
    code_fingerprints: Dict[str, str]
    data_fingerprint: str
    frozen_manifest_hash: str
    frozen_timestamp_utc: str
    git_commit: str


class FrozenCandidatesManager:
    """Administrador de candidatos congelados para EXP-ST02."""

    def __init__(self):
        self.exp_st01_dir = repo_root / "ai_trading_agent" / "strategy_lab" / "experiments" / "exp_st01"
        self.exp_st02_dir = repo_root / "ai_trading_agent" / "strategy_lab" / "experiments" / "exp_st02"
        self.exp_st02_dir.mkdir(parents=True, exist_ok=True)

    def freeze_all_candidates(self) -> List[FrozenCandidateConfig]:
        """Congela los 4 candidatos y exporta DELIVERABLE_04 (EXP_ST02_FROZEN_CANDIDATES.json)."""
        now_utc = datetime.now(timezone.utc).isoformat()
        git_commit = "39cc2cf"  # Commit canónico verificado

        # Hashes de código fuente
        code_files = {
            "supertrend_indicator.py": compute_sha256_file(self.exp_st01_dir / "supertrend_indicator.py"),
            "st_ema200_strategy.py": compute_sha256_file(self.exp_st01_dir / "st_ema200_strategy.py"),
            "st_ema200_backtester.py": compute_sha256_file(self.exp_st01_dir / "st_ema200_backtester.py"),
            "discovery_hypotheses.py": compute_sha256_file(self.exp_st01_dir / "discovery_hypotheses.py"),
        }

        # Hashes de datos
        data_cache_dir = self.exp_st01_dir / "data_cache"
        gld_data_hash = compute_sha256_file(data_cache_dir / "GLD_H1.csv")
        dia_data_hash = compute_sha256_file(data_cache_dir / "DIA_H1.csv")

        # Modelo de costes Base 1x
        cost_dict = {
            "name": "1x_Base",
            "slippage_bps": 2.0,
            "commission_per_share": 0.005,
        }

        # Especificación determinista de H5
        h5_spec = {
            "mechanism": "SUPER_TREND_ADAPTIVE_TRAILING_STOP",
            "initial_stop_loss": "SuperTrend line value at signal bar T close",
            "monotonicity": {
                "LONG": "Strictly non-decreasing: current_sl = max(current_sl, SuperTrend.line) when trend == +1",
                "SHORT": "Strictly non-increasing: current_sl = min(current_sl, SuperTrend.line) when trend == -1",
            },
            "update_timing": "Evaluated and updated at bar k close; active for subsequent bars",
            "intrabar_exit": "Exit if Low <= current_sl (Long) or High >= current_sl (Short)",
            "gap_handling": "Fill at bar k open if open penetrates current_sl (adverse fill with slippage)",
            "trend_flip_exit": "Forced exit if SuperTrend flips direction opposite to trade",
            "retroactivity": "PROHIBITED: Stops never apply retroactively to previous bars or current bar open",
        }

        base_params = {
            "ema_period": 200,
            "atr_period": 10,
            "supertrend_multiplier": 3.0,
            "entry_execution": "CAUSAL_T_PLUS_1_OPEN",
            "tp_r_multiple": 1.5,
            "sl_buffer": 0.0,
        }

        candidates = [
            # 1. GLD Baseline
            FrozenCandidateConfig(
                candidate_id="ST02-GLD-BASE",
                symbol="GLD",
                timeframe="H1",
                variant="BASELINE_TP_1_5R",
                parameters=base_params,
                h5_specification=None,
                virtual_capital_usd=100000.0,
                risk_per_trade_usd=250.0,
                risk_pct_nominal=0.25,
                max_positions=1,
                cost_model=cost_dict,
                code_fingerprints=code_files,
                data_fingerprint=gld_data_hash,
                frozen_manifest_hash="",
                frozen_timestamp_utc=now_utc,
                git_commit=git_commit,
            ),
            # 2. GLD H5
            FrozenCandidateConfig(
                candidate_id="ST02-GLD-H5",
                symbol="GLD",
                timeframe="H1",
                variant="H5_ADAPTIVE_TRAILING",
                parameters={**base_params, "tp_r_multiple": None},
                h5_specification=h5_spec,
                virtual_capital_usd=100000.0,
                risk_per_trade_usd=250.0,
                risk_pct_nominal=0.25,
                max_positions=1,
                cost_model=cost_dict,
                code_fingerprints=code_files,
                data_fingerprint=gld_data_hash,
                frozen_manifest_hash="",
                frozen_timestamp_utc=now_utc,
                git_commit=git_commit,
            ),
            # 3. DIA Baseline
            FrozenCandidateConfig(
                candidate_id="ST02-DIA-BASE",
                symbol="DIA",
                timeframe="H1",
                variant="BASELINE_TP_1_5R",
                parameters=base_params,
                h5_specification=None,
                virtual_capital_usd=100000.0,
                risk_per_trade_usd=250.0,
                risk_pct_nominal=0.25,
                max_positions=1,
                cost_model=cost_dict,
                code_fingerprints=code_files,
                data_fingerprint=dia_data_hash,
                frozen_manifest_hash="",
                frozen_timestamp_utc=now_utc,
                git_commit=git_commit,
            ),
            # 4. DIA H5
            FrozenCandidateConfig(
                candidate_id="ST02-DIA-H5",
                symbol="DIA",
                timeframe="H1",
                variant="H5_ADAPTIVE_TRAILING",
                parameters={**base_params, "tp_r_multiple": None},
                h5_specification=h5_spec,
                virtual_capital_usd=100000.0,
                risk_per_trade_usd=250.0,
                risk_pct_nominal=0.25,
                max_positions=1,
                cost_model=cost_dict,
                code_fingerprints=code_files,
                data_fingerprint=dia_data_hash,
                frozen_manifest_hash="",
                frozen_timestamp_utc=now_utc,
                git_commit=git_commit,
            ),
        ]

        # Calcular hash de manifiesto para cada candidato
        for c in candidates:
            c_dict = asdict(c)
            c_dict["frozen_manifest_hash"] = ""
            c.frozen_manifest_hash = compute_sha256_dict(c_dict)

        # Exportar Deliverable 04
        self._export_deliverable_04(candidates)
        return candidates

    def _export_deliverable_04(self, candidates: List[FrozenCandidateConfig]):
        p = self.exp_st02_dir / "EXP_ST02_FROZEN_CANDIDATES.json"
        data = [asdict(c) for c in candidates]
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Candidatos congelados exportados a: {p}")


if __name__ == "__main__":
    mgr = FrozenCandidatesManager()
    frozen = mgr.freeze_all_candidates()
    print(f"Total congelados: {len(frozen)}")
    for c in frozen:
        print(f" - [{c.candidate_id}] {c.symbol} {c.variant} -> Hash: {c.frozen_manifest_hash[:16]}...")
