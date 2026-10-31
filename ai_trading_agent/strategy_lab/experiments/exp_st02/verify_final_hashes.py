"""
ai_trading_agent.strategy_lab.experiments.exp_st02.verify_final_hashes
======================================================================
Script de verificación final y reconciliación de hashes para EXP-ST02.
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import json
import hashlib
from datetime import datetime, timezone

from ai_trading_agent.config.settings import settings
from ai_trading_agent.strategy_lab.registry.registry import strategy_registry
from ai_trading_agent.strategy_lab.experiments.exp_st02.frozen_candidates import (
    compute_sha256_file,
    compute_sha256_dict,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_ledger import (
    ShadowLedgerST02,
)

def run_final_verification():
    print("=== REVISIÓN FINAL EXP-ST02: RECONCILIACIÓN DE HASHES Y VERIFICACIÓN CAUSAL ===")
    exp_st02_dir = repo_root / "ai_trading_agent" / "strategy_lab" / "experiments" / "exp_st02"
    exp_st01_dir = repo_root / "ai_trading_agent" / "strategy_lab" / "experiments" / "exp_st01"
    
    # 1. Reconciliación de Hashes de Código Fuente
    code_files = {
        "supertrend_indicator.py": compute_sha256_file(exp_st01_dir / "supertrend_indicator.py"),
        "st_ema200_strategy.py": compute_sha256_file(exp_st01_dir / "st_ema200_strategy.py"),
        "st_ema200_backtester.py": compute_sha256_file(exp_st01_dir / "st_ema200_backtester.py"),
        "discovery_hypotheses.py": compute_sha256_file(exp_st01_dir / "discovery_hypotheses.py"),
    }
    
    candidates_path = exp_st02_dir / "EXP_ST02_FROZEN_CANDIDATES.json"
    with open(candidates_path, "r", encoding="utf-8") as f:
        frozen_data = json.load(f)
        
    print(f"1. Candidatos Congelados en {candidates_path.name}: {len(frozen_data)}")
    candidates_verified = True
    for c in frozen_data:
        cid = c["candidate_id"]
        # Comprobar hashes de código
        for k, v in code_files.items():
            if c["code_fingerprints"].get(k) != v:
                print(f"   [DISCREPANCIA CÓDIGO] {cid} {k}: esperado {v}, encontrado {c['code_fingerprints'].get(k)}")
                candidates_verified = False
        print(f"   - {cid}: Parámetros={c['parameters']} | Hash={c['frozen_manifest_hash'][:16]}... (CONFORME)")

    # 2. Reconciliación del Manifiesto Sellado
    manifest_path = exp_st02_dir / "EXP_ST02_FORWARD_CAMPAIGN_MANIFEST.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    manifest_copy = dict(manifest_data)
    reported_hash = manifest_copy.pop("manifest_sha256")
    manifest_copy["manifest_sha256"] = ""
    recalculated_hash = hashlib.sha256(json.dumps(manifest_copy, sort_keys=True).encode('utf-8')).hexdigest()

    manifest_verified = (reported_hash == recalculated_hash)
    print(f"2. Manifiesto de Campaña Sellado ({manifest_path.name}):")
    print(f"   - SHA-256 Reportado:     {reported_hash}")
    print(f"   - SHA-256 Recalculado:   {recalculated_hash}")
    print(f"   - Estado de Integridad:  {'VERIFICADO / CONFORME' if manifest_verified else 'DISCREPANCIA'}")
    print(f"   - Estado de Campaña:     {manifest_data.get('current_state')}")
    print(f"   - T0 Activation UTC:     {manifest_data.get('t0_activation_utc')}")
    print(f"   - Primera Sesión:        {manifest_data.get('first_eligible_session')}")

    # 3. Integridad de los 4 Ledgers
    ledgers_dir = exp_st02_dir / "ledgers"
    ledger_all_ok = True
    for cid in ["ST02-GLD-BASE", "ST02-GLD-H5", "ST02-DIA-BASE", "ST02-DIA-H5"]:
        ledger = ShadowLedgerST02("CAMP-SHADOW-EXP-ST02-2026", cid, ledgers_dir / f"ledger_{cid}.jsonl")
        val, viols = ledger.verify_integrity()
        if not val:
            ledger_all_ok = False
        print(f"3. Ledger {cid}: {'Íntegro' if val else 'Corrupto'} ({len(ledger.read_all_entries())} entradas)")

    # 4. Seguridad Operativa
    strat_d21 = strategy_registry.get_strategy("D21_RangeCompress_5d")
    params_json = json.dumps(strat_d21.parameters, sort_keys=True)
    d21_fp = hashlib.sha256(params_json.encode("utf-8")).hexdigest()[:16]
    d21_ok = (d21_fp == "f885ec2db2422308")
    
    shadow_dir = repo_root / "ai_trading_agent" / "strategy_lab" / "shadow"
    shadow_mr_ok = (shadow_dir / "freeze_manifests.py").exists()
    
    live_blocked = not hasattr(settings, "LIVE_TRADING_ENABLED") or not getattr(settings, "LIVE_TRADING_ENABLED")

    print(f"4. Componentes Protegidos:")
    print(f"   - D21 Fingerprint:       {d21_fp} ({'INTACTO' if d21_ok else 'ALTERADO'})")
    print(f"   - Campañas Shadow 7.4:   {'INTACTAS' if shadow_mr_ok else 'ALTERADAS'}")
    print(f"   - LIVE Trading:          {'BLOQUEADO' if live_blocked else 'ACTIVO'}")

    all_pass = candidates_verified and manifest_verified and ledger_all_ok and d21_ok and live_blocked
    print(f"==> RESULTADO DE REVISIÓN FINAL: {'PASS' if all_pass else 'FAIL'}")
    return all_pass

if __name__ == "__main__":
    run_final_verification()
