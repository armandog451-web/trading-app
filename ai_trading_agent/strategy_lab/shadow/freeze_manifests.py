"""
ai_trading_agent.strategy_lab.shadow.freeze_manifests
=====================================================
Generador y validador de manifiestos criptográficos de congelamiento (Bloque A).
Congela de forma inmutable el código fuente, hiperparámetros y políticas operativas.
"""

import json
import hashlib
import sys
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from .campaign_models import (
    CampaignFreezeManifest,
    ShadowCampaignStatus
)


def compute_sha256_of_file(file_path: Path) -> str:
    """Calcula el hash SHA-256 completo de 64 caracteres de un archivo."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_sha256_of_dict(data: Dict[str, Any]) -> str:
    """Calcula el hash SHA-256 completo de un diccionario canónico."""
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def generate_freeze_manifests(repo_root: Path) -> Dict[str, CampaignFreezeManifest]:
    """
    Genera y guarda los manifiestos oficiales de congelamiento para las dos estrategias líderes:
    - Candidate A: MR_VolCond_ZScore_V1 (H-MR-VOL-1)
    - Candidate B: CS_RelMom_VolAdj_V2 (H-MOM-REL-2)
    """
    discovery_code_path = repo_root / "ai_trading_agent" / "strategy_lab" / "discovery" / "discovery_engine_v2.py"
    assert discovery_code_path.exists(), f"Source code not found: {discovery_code_path}"

    code_sha256 = compute_sha256_of_file(discovery_code_path)
    now_utc = "2026-10-30T16:00:00Z"  # T0 formal post-cierre de sesión del 30 de Octubre de 2026
    t0_market_session = "2026-11-02"    # Próxima sesión hábil de mercado completa

    universe = ["SPY", "QQQ", "IWM", "DIA", "XLF", "XLE"]

    env_info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "execution_mode": "RESEARCH / ANALYSIS_ONLY",
        "live_trading_enabled": False,
        "broker_connection": "AIR_GAPPED_NONE",
        "d21_status": "PAPER_PROTECTED_ISOLATED"
    }

    # 1. CANDIDATE A: MR_VolCond_ZScore_V1
    params_a = {
        "z_lookback": 20,
        "z_threshold": -2.0,
        "atr_period": 14,
        "atr_expansion_mult": 1.10,
        "rsi_period": 4,
        "rsi_threshold": 20.0,
        "max_holding": 4,
        "stop_loss_pct": 0.025,
        "profit_target_pct": 0.035
    }
    params_a_sha256 = compute_sha256_of_dict(params_a)
    combined_fp_a = hashlib.sha256(f"{code_sha256}:{params_a_sha256}:MR_VolCond_ZScore_V1".encode('utf-8')).hexdigest()

    manifest_a = CampaignFreezeManifest(
        campaign_id="CAMP-SHADOW-20261030-MR-VOL-1",
        strategy_id="MR_VolCond_ZScore_V1",
        hypothesis_id="H-MR-VOL-1",
        strategy_name="Volatility-Conditioned Z-Score Reversion v1",
        family="VOLATILITY_CONDITIONED_REVERSION",
        thesis="Reversión a la media condicionada a sobreventa estadística extrema (Z-Score 20 <= -2.0) con expansión de ATR (>= 1.10) y RSI(4) <= 20.",
        parameters_frozen=params_a,
        code_file_path=str(discovery_code_path.relative_to(repo_root)),
        code_sha256=code_sha256,
        parameters_sha256=params_a_sha256,
        combined_strategy_fingerprint_sha256=combined_fp_a,
        t0_timestamp_utc=now_utc,
        t0_first_prospective_session=t0_market_session,
        universe_symbols=universe,
        capital_allocation_usd=100_000.0,
        risk_budget_per_trade_usd=250.0,
        max_concurrent_positions=6,  # 1 posición por activo máximo
        execution_policy="SIGNAL_AT_CLOSE_T_EXECUTE_AT_OPEN_T_PLUS_1",
        cost_tier_baseline="1x",
        status=ShadowCampaignStatus.COLLECTING_EVIDENCE,
        historical_benchmark_reference={
            "historical_trades_count": 53,
            "historical_net_pnl_usd": 6556.24,
            "historical_net_profit_factor": 2.94,
            "historical_sharpe": 1.43,
            "historical_max_drawdown_pct": 0.63,
            "historical_ranking_score": 0.923,
            "validation_note": "PREVIOUSLY_EXAMINED_HISTORICAL_DATA - NO CONSIDERAR EVIDENCIA FORWARD"
        },
        environment_info=env_info
    )

    # 2. CANDIDATE B: CS_RelMom_VolAdj_V2
    params_b = {
        "rebalance_period": 10,
        "momentum_lookback": 60,
        "top_n_assets": 2,
        "max_holding": 10,
        "stop_loss_pct": 0.030,
        "profit_target_pct": 0.050
    }
    params_b_sha256 = compute_sha256_of_dict(params_b)
    combined_fp_b = hashlib.sha256(f"{code_sha256}:{params_b_sha256}:CS_RelMom_VolAdj_V2".encode('utf-8')).hexdigest()

    manifest_b = CampaignFreezeManifest(
        campaign_id="CAMP-SHADOW-20261030-MOM-REL-2",
        strategy_id="CS_RelMom_VolAdj_V2",
        hypothesis_id="H-MOM-REL-2",
        strategy_name="Cross-Sectional Volatility-Adjusted Momentum v2",
        family="CROSS_SECTIONAL_MOMENTUM",
        thesis="Selección quincenal (10 barras) de los 2 activos con mayor Sharpe-Momentum a 60 días, con salidas asimétricas y stop protector.",
        parameters_frozen=params_b,
        code_file_path=str(discovery_code_path.relative_to(repo_root)),
        code_sha256=code_sha256,
        parameters_sha256=params_b_sha256,
        combined_strategy_fingerprint_sha256=combined_fp_b,
        t0_timestamp_utc=now_utc,
        t0_first_prospective_session=t0_market_session,
        universe_symbols=universe,
        capital_allocation_usd=100_000.0,
        risk_budget_per_trade_usd=250.0,
        max_concurrent_positions=2,
        execution_policy="SIGNAL_AT_CLOSE_T_EXECUTE_AT_OPEN_T_PLUS_1",
        cost_tier_baseline="1x",
        status=ShadowCampaignStatus.COLLECTING_EVIDENCE,
        historical_benchmark_reference={
            "historical_trades_count": 133,
            "historical_net_pnl_usd": 6115.96,
            "historical_net_profit_factor": 1.52,
            "historical_sharpe": 0.94,
            "historical_max_drawdown_pct": 1.60,
            "historical_ranking_score": 0.572,
            "validation_note": "PREVIOUSLY_EXAMINED_HISTORICAL_DATA - NO CONSIDERAR EVIDENCIA FORWARD"
        },
        environment_info=env_info
    )

    manifests = {
        "MR_VolCond_ZScore_V1": manifest_a,
        "CS_RelMom_VolAdj_V2": manifest_b
    }

    # Guardar en disco
    out_dir = repo_root / "ai_trading_agent" / "scratch" / "shadow_campaigns"
    out_dir.mkdir(parents=True, exist_ok=True)

    for sid, m in manifests.items():
        m_file = out_dir / f"freeze_manifest_{sid}.json"
        with open(m_file, "w", encoding="utf-8") as f:
            f.write(m.model_dump_json(indent=2))
        print(f"Manifiesto de congelamiento exportado: {m_file}")

    return manifests


if __name__ == "__main__":
    repo = Path(__file__).resolve().parent.parent.parent.parent
    generate_freeze_manifests(repo)
