import hashlib
import json
import os
from datetime import datetime

spec_path = r'C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\EXP_MTF01_SCIENTIFIC_SPECIFICATION.md'
with open(spec_path, 'rb') as f:
    spec_sha256 = hashlib.sha256(f.read()).hexdigest()

manifest = {
    "manifest_version": "1.0.0",
    "experiment_id": "EXP-MTF01",
    "strategy_id": "MTF_ExtremeReversal_V1",
    "created_at": "2026-10-31T15:00:00Z",
    "status": "SPECIFICATION_FROZEN",
    "classification": "RESEARCH_ONLY / ANALYSIS_ONLY",
    "specification_document": "EXP_MTF01_SCIENTIFIC_SPECIFICATION.md",
    "specification_sha256": spec_sha256,
    "universe": [
        "SPY",
        "QQQ",
        "DIA",
        "IWM",
        "GLD",
        "TLT"
    ],
    "timeframes": {
        "context": "D1",
        "structure": "H1",
        "trigger": "M5"
    },
    "parameters": {
        "d1_context": {
            "extreme_lookback": 60,
            "extreme_atr_tolerance": 0.50,
            "atr_period": 14,
            "accel_lookback": 5,
            "accel_atr_multiple": 2.50,
            "decel_body_ratio_threshold": 0.45,
            "decel_rejection_wick_threshold": 0.35,
            "require_closed_prior_day": True
        },
        "h1_structure": {
            "swing_left": 3,
            "swing_right": 3,
            "ema_period": 50,
            "fib_retracement": 0.618,
            "fib_stop_reference": 0.75,
            "confluence_tolerance_atr_multiple": 0.25,
            "require_bos_confirmation": True
        },
        "m5_execution": {
            "m5_swing_left": 2,
            "m5_swing_right": 2,
            "timeout_bars": 24,
            "execution_delay": "1_bar_open",
            "slippage_bps_base": 2.0,
            "commission_per_share": 0.005,
            "sl_buffer_atr_multiple": 0.10
        },
        "risk_model": {
            "initial_equity": 100000.0,
            "risk_per_trade_pct": 0.0025,
            "max_position_equity_pct": 0.20,
            "max_concurrent_positions_per_asset": 1
        },
        "target_variants": {
            "V1A": "Structure_Target (High/Low P1)",
            "V1B": "Fixed_R_Target (2.0R)"
        }
    },
    "isolation_guards": {
        "live_trading_enabled": False,
        "paper_broker_enabled": False,
        "moomoo_connection_prohibited": True,
        "protected_components": [
            "D21_RangeCompress_5d",
            "CAMP-SHADOW-20261030-MR-VOL-1",
            "CAMP-SHADOW-20261030-MOM-REL-2",
            "CAMP-SHADOW-EXP-ST02-2026"
        ]
    }
}

manifest_json_str = json.dumps(manifest, indent=2)
manifest_sha256 = hashlib.sha256(manifest_json_str.encode('utf-8')).hexdigest()
manifest["manifest_sha256"] = manifest_sha256

manifest_out_path = r'C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\EXP_MTF01_PARAMETER_MANIFEST.json'
with open(manifest_out_path, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)

print(f"Manifest written successfully. Spec SHA: {spec_sha256}, Manifest SHA: {manifest_sha256}")
