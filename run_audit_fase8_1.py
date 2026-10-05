"""
run_audit_fase8_1.py
====================
Script de auditoría exhaustiva para la Fase 8.1:
Generalization & Adaptive Selection Audit.

Audita rigurosamente:
1. Huellas digitales de estrategias congeladas (Ex24 y Ex26).
2. Cuantificación de uso adaptativo de OOS (RESEARCH_VALIDATION_SET).
3. Generalización temporal en múltiples ventanas independientes pre-holdout.
4. Rolling Walk-Forward sin optimización.
5. Atribución por régimen de mercado (BULL, BEAR, SIDEWAYS, HIGH_VOL, LOW_VOL).
6. Generalización por activo (SPY, QQQ, IWM, DIA).
7. Leave-One-Symbol-Out cross-validation.
8. Frontera de costes (0, 2, 5, 7.5, 10 bps).
9. Atribución contrafactual de Time Stop.
10. Atribución de política de concurrencia (Ex24 vs Ex26).
"""

import sys
import json
import math
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.data.providers.yfinance_provider import YFinanceMarketDataProvider
from ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer import DateBasedDataSplitter
from ai_trading_agent.strategy_lab.backtesting.execution_aware_simulator import (
    ExecutionAwareStrategyEvaluator,
    ExecutionAwareSimulator,
    FeaturePrecomputer
)
from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import (
    calculate_economic_edge_score,
    classify_statistical_evidence
)


def compute_frozen_fingerprint(spec: Dict[str, Any]) -> str:
    serialized = json.dumps(spec, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def run_audit_fase8_1():
    print("=" * 85)
    print(" INICIANDO FASE 8.1: GENERALIZATION & ADAPTIVE SELECTION AUDIT")
    print("=" * 85)

    provider = YFinanceMarketDataProvider(fallback_to_synthetic=False)
    target_symbols = ["SPY", "QQQ", "IWM", "DIA"]

    print("\n[1/10] DESCARGANDO DATOS Y CONSTRUYENDO PARTICIÓN PRE-HOLDOUT...")
    raw_data: Dict[str, Dict[str, List[OHLCVBar]]] = {"1d": {}, "1h": {}}
    for sym in target_symbols:
        raw_data["1d"][sym] = provider.get_historical_bars(symbol=sym, count=1500, interval="1d")
        raw_data["1h"][sym] = provider.get_historical_bars(symbol=sym, count=6000, interval="1h")

    common_start, common_end = DateBasedDataSplitter.find_common_date_range([
        raw_data["1d"]["SPY"],
        raw_data["1h"]["SPY"]
    ])
    splits_cal = DateBasedDataSplitter.create_calendar_splits(common_start, common_end)
    is_start, is_end = splits_cal["in_sample"]
    oos_start, oos_end = splits_cal["out_sample"]
    h_start, h_end = splits_cal["holdout"]

    # Rango pre-holdout estricto: common_start hasta oos_end (excluyendo completamente holdout)
    pre_holdout_start = common_start
    pre_holdout_end = oos_end
    print(f"  Rango Pre-Holdout Total: {pre_holdout_start.strftime('%Y-%m-%d')} -> {pre_holdout_end.strftime('%Y-%m-%d')}")
    print(f"  Holdout (LOCKED 20%):     {h_start.strftime('%Y-%m-%d')} -> {h_end.strftime('%Y-%m-%d')}")

    # =========================================================================
    # 1. CONGELAMIENTO Y FINGERPRINTS DE ESTRATEGIAS LÍDERES
    # =========================================================================
    print("\n[2/10] REGISTRANDO FINGERPRINTS DE ESTRATEGIAS CONGELADAS...")
    spec_ex24 = {
        "id": "Ex24_Lead_MultiSymbol_OneGlobal",
        "family": "failed_breakout_reversal",
        "context_1d": True,
        "exit_geometry": "time_stop",
        "time_stop_bars": 15,
        "rr_ratio": 2.5,
        "atr_mult": 1.5,
        "concurrency_policy": "ONE_POSITION_GLOBAL",
        "max_concurrent_positions": 1,
        "commission_per_share": 0.005,
        "slippage_pct": 0.0005,
        "risk_per_trade_pct": 0.01
    }
    spec_ex26 = {
        "id": "Ex26_Lead_MultiSymbol_ReplaceStronger",
        "family": "failed_breakout_reversal",
        "context_1d": True,
        "exit_geometry": "time_stop",
        "time_stop_bars": 15,
        "rr_ratio": 2.5,
        "atr_mult": 1.5,
        "concurrency_policy": "REPLACE_IF_STRONGER",
        "max_concurrent_positions": 2,
        "commission_per_share": 0.005,
        "slippage_pct": 0.0005,
        "risk_per_trade_pct": 0.01
    }

    fp_ex24 = compute_frozen_fingerprint(spec_ex24)
    fp_ex26 = compute_frozen_fingerprint(spec_ex26)
    print(f"  Fingerprint Ex24: {fp_ex24}")
    print(f"  Fingerprint Ex26: {fp_ex26}")

    # Evaluadores congelados
    eval_frozen = ExecutionAwareStrategyEvaluator(
        entry_family="failed_breakout_reversal",
        use_1d_context=True,
        exit_geometry="time_stop",
        time_stop_bars=15,
        rr_ratio=2.5,
        atr_mult=1.5
    )

    # Precalcular features pre-holdout para acelerar simulaciones
    pre_data: Dict[str, Dict[str, List[OHLCVBar]]] = {}
    for sym in target_symbols:
        pre_d_bars = [b for b in raw_data["1d"][sym] if b.timestamp <= pre_holdout_end]
        pre_h_bars = [b for b in raw_data["1h"][sym] if b.timestamp <= pre_holdout_end]
        pre_data[sym] = {"1d": pre_d_bars, "1h": pre_h_bars}

    print("  Precalculando matrices vectorizadas pre-holdout...")
    pre_features = {sym: FeaturePrecomputer.precompute(pre_data[sym]["1h"], pre_data[sym]["1d"]) for sym in target_symbols}

    # =========================================================================
    # 2. AUDITORÍA DE USO ADAPTATIVO DEL OOS DE FASE 8
    # =========================================================================
    print("\n[3/10] AUDITORÍA DE USO ADAPTATIVO DE OOS EN FASE 8...")
    oos_audit = {
        "dataset_label": "RESEARCH_VALIDATION_SET",
        "original_label": "OUT_OF_SAMPLE",
        "total_queries_in_phase_8": 30,
        "ranking_queries": 21,
        "exploitation_queries": 9,
        "selection_bias_risk": "HIGH",
        "reclassification_rationale": (
            "El subconjunto 2025-08-05 a 2026-03-06 fue consultado 30 veces para selección "
            "de familias, comparación de políticas de concurrencia y estrés de costes. "
            "Por ende, actúa formalmente como un Validation Set iterativo, no como Test Set ciego."
        )
    }
    print(f"  Clasificación corregida: {oos_audit['dataset_label']} (Consultas totales: {oos_audit['total_queries_in_phase_8']})")

    # =========================================================================
    # 3. TEMPORAL GENERALIZATION: 3 VENTANAS INDEPENDIENTES PRE-HOLDOUT
    # =========================================================================
    print("\n[4/10] EVALUANDO GENERALIZACIÓN TEMPORAL (VENTANAS A, B, C)...")
    # Ventana A: 2023-11-06 a 2024-08-15 (9 meses, Bull Trend inicial)
    # Ventana B: 2024-08-16 a 2025-05-15 (9 meses, Rotación / Pullbacks)
    # Ventana C: 2025-05-16 a 2026-03-06 (9.5 meses, Tramo reciente pre-holdout)
    w_dates = [
        ("Window_A", datetime(2023, 11, 6), datetime(2024, 8, 15)),
        ("Window_B", datetime(2024, 8, 16), datetime(2025, 5, 15)),
        ("Window_C", datetime(2025, 5, 16), datetime(2026, 3, 6))
    ]

    sim_ex24 = ExecutionAwareSimulator(evaluator=eval_frozen, concurrency_policy="ONE_POSITION_GLOBAL", max_concurrent_positions=1)
    sim_ex26 = ExecutionAwareSimulator(evaluator=eval_frozen, concurrency_policy="REPLACE_IF_STRONGER", max_concurrent_positions=2)

    temporal_results: Dict[str, Any] = {"Ex24": {}, "Ex26": {}}
    for w_name, w_start, w_end in w_dates:
        w_data = {}
        w_feat = {}
        for sym in target_symbols:
            w_h = [b for b in pre_data[sym]["1h"] if w_start <= b.timestamp <= w_end]
            w_d = [b for b in pre_data[sym]["1d"] if b.timestamp <= w_end]
            w_data[sym] = {"1h": w_h, "1d": w_d}
            w_feat[sym] = FeaturePrecomputer.precompute(w_h, w_d)

        r24 = sim_ex24.run_simulation(w_data, precomputed_features=w_feat)
        r26 = sim_ex26.run_simulation(w_data, precomputed_features=w_feat)

        ees24, c24 = calculate_economic_edge_score(r24["profit_factor"], r24["expectancy"], r24["sharpe_ratio"], r24["sharpe_ratio"], r24["total_trades"])
        ees26, c26 = calculate_economic_edge_score(r26["profit_factor"], r26["expectancy"], r26["sharpe_ratio"], r26["sharpe_ratio"], r26["total_trades"])

        temporal_results["Ex24"][w_name] = {**r24, "ees_score": ees24, "ees_class": c24.value}
        temporal_results["Ex26"][w_name] = {**r26, "ees_score": ees26, "ees_class": c26.value}

        print(f"  {w_name} ({w_start.strftime('%Y-%m')}->{w_end.strftime('%Y-%m')}):")
        print(f"    Ex24: Trades={r24['total_trades']}, PF={r24['profit_factor']:.2f}, PnL=${r24['total_net_pnl']:,.2f}, Sharpe={r24['sharpe_ratio']:.2f}, EES={ees24}")
        print(f"    Ex26: Trades={r26['total_trades']}, PF={r26['profit_factor']:.2f}, PnL=${r26['total_net_pnl']:,.2f}, Sharpe={r26['sharpe_ratio']:.2f}, EES={ees26}")

    # =========================================================================
    # 4. ROLLING WALK-FORWARD SIN OPTIMIZACIÓN (4 VENTANAS MÓVILES)
    # =========================================================================
    print("\n[5/10] ROLLING WALK-FORWARD (VENTANAS SECUENCIALES DE 6 MESES)...")
    # Generar 4 ventanas móviles secuenciales de 6 meses
    rw_dates = [
        ("RW_1", datetime(2023, 11, 6), datetime(2024, 5, 6)),
        ("RW_2", datetime(2024, 5, 7), datetime(2024, 11, 6)),
        ("RW_3", datetime(2024, 11, 7), datetime(2025, 5, 6)),
        ("RW_4", datetime(2025, 5, 7), datetime(2025, 11, 6)),
    ]
    rolling_wf_results: Dict[str, Any] = {"Ex24": {}, "Ex26": {}}
    for rw_name, rw_start, rw_end in rw_dates:
        rw_data = {}
        rw_feat = {}
        for sym in target_symbols:
            rw_h = [b for b in pre_data[sym]["1h"] if rw_start <= b.timestamp <= rw_end]
            rw_d = [b for b in pre_data[sym]["1d"] if b.timestamp <= rw_end]
            rw_data[sym] = {"1h": rw_h, "1d": rw_d}
            rw_feat[sym] = FeaturePrecomputer.precompute(rw_h, rw_d)

        r24 = sim_ex24.run_simulation(rw_data, precomputed_features=rw_feat)
        r26 = sim_ex26.run_simulation(rw_data, precomputed_features=rw_feat)

        rolling_wf_results["Ex24"][rw_name] = r24
        rolling_wf_results["Ex26"][rw_name] = r26
        print(f"  {rw_name}: Ex24 PF={r24['profit_factor']:.2f} (PnL=${r24['total_net_pnl']:,.2f}) | Ex26 PF={r26['profit_factor']:.2f} (PnL=${r26['total_net_pnl']:,.2f})")

    # =========================================================================
    # 5. ATRIBUCIÓN POR RÉGIMEN DE MERCADO
    # =========================================================================
    print("\n[6/10] ATRIBUCIÓN POR RÉGIMEN DE MERCADO...")
    # Correr sobre todo el pre-holdout con Ex26 para obtener trades con contexto diario
    full_pre_res26 = sim_ex26.run_simulation(pre_data, precomputed_features=pre_features)
    trades_all = full_pre_res26["closed_trades"]

    # Clasificar trades por régimen en la entrada
    regime_buckets: Dict[str, List[Dict[str, Any]]] = {
        "BULL_TREND": [],
        "BEAR_TREND": [],
        "SIDEWAYS": [],
        "HIGH_VOL": [],
        "LOW_VOL": []
    }

    for tr in trades_all:
        sym = tr["symbol"]
        entry_t = tr["entry_time"]
        # Buscar contexto de régimen en esa fecha
        d_ctx = pre_features[sym]["get_d_ctx"](entry_t.date())
        # Identificar volatilidad mediante ATR relativo
        entry_bar_idx = None
        for idx, b in enumerate(pre_data[sym]["1h"]):
            if b.timestamp == entry_t:
                entry_bar_idx = idx
                break
        atr_val = pre_features[sym]["atr"][entry_bar_idx] if entry_bar_idx is not None else 1.0
        avg_atr = pre_features[sym]["avg_atr_20"][entry_bar_idx] if entry_bar_idx is not None else 1.0

        if d_ctx.get("daily_bullish"):
            regime_buckets["BULL_TREND"].append(tr)
        elif d_ctx.get("daily_bearish"):
            regime_buckets["BEAR_TREND"].append(tr)
        else:
            regime_buckets["SIDEWAYS"].append(tr)

        if atr_val > avg_atr * 1.15:
            regime_buckets["HIGH_VOL"].append(tr)
        else:
            regime_buckets["LOW_VOL"].append(tr)

    regime_stats = {}
    for r_name, r_trades in regime_buckets.items():
        n = len(r_trades)
        wins = [t for t in r_trades if t["net_pnl"] > 0]
        losses = [t for t in r_trades if t["net_pnl"] <= 0]
        gw = sum(t["net_pnl"] for t in wins)
        gl = abs(sum(t["net_pnl"] for t in losses))
        pf = round(gw / max(1e-6, gl), 2) if gl > 0 else (999.0 if gw > 0 else 0.0)
        pnl = round(sum(t["net_pnl"] for t in r_trades), 2)
        wr = round(len(wins) / max(1, n) * 100.0, 2)
        regime_stats[r_name] = {"n_trades": n, "pf": pf, "net_pnl": pnl, "win_rate": wr}
        print(f"  Régimen {r_name:10s} -> Trades={n:3d} | PF={pf:.2f} | Net PnL=${pnl:,.2f} | WR={wr:.1f}%")

    # =========================================================================
    # 6. GENERALIZACIÓN POR ACTIVO INDIVIDUAL
    # =========================================================================
    print("\n[7/10] GENERALIZACIÓN POR ACTIVO INDIVIDUAL (SPY, QQQ, IWM, DIA)...")
    symbol_stats = {}
    for sym in target_symbols:
        sim_single = ExecutionAwareSimulator(evaluator=eval_frozen, concurrency_policy="FIRST_SIGNAL", max_concurrent_positions=1)
        r_single = sim_single.run_simulation({sym: pre_data[sym]}, precomputed_features={sym: pre_features[sym]})
        symbol_stats[sym] = {
            "trades": r_single["total_trades"],
            "pf": r_single["profit_factor"],
            "pnl": r_single["total_net_pnl"],
            "sharpe": r_single["sharpe_ratio"],
            "win_rate": r_single["win_rate"],
            "payoff": r_single["realized_payoff_ratio"]
        }
        print(f"  {sym:4s} -> Trades={r_single['total_trades']:3d} | PF={r_single['profit_factor']:.2f} | PnL=${r_single['total_net_pnl']:,.2f} | Payoff={r_single['realized_payoff_ratio']:.2f}")

    # =========================================================================
    # 7. LEAVE-ONE-SYMBOL-OUT CROSS-VALIDATION
    # =========================================================================
    print("\n[8/10] LEAVE-ONE-SYMBOL-OUT CROSS-VALIDATION...")
    loso_stats = {}
    for excluded_sym in target_symbols:
        included_syms = [s for s in target_symbols if s != excluded_sym]
        loso_data = {s: pre_data[s] for s in included_syms}
        loso_feat = {s: pre_features[s] for s in included_syms}
        r_loso = sim_ex26.run_simulation(loso_data, precomputed_features=loso_feat)
        loso_stats[f"Exclude_{excluded_sym}"] = {
            "excluded": excluded_sym,
            "included": included_syms,
            "trades": r_loso["total_trades"],
            "pf": r_loso["profit_factor"],
            "pnl": r_loso["total_net_pnl"],
            "sharpe": r_loso["sharpe_ratio"]
        }
        print(f"  Excluyendo {excluded_sym:4s} (opera {', '.join(included_syms)}) -> Trades={r_loso['total_trades']:3d} | PF={r_loso['profit_factor']:.2f} | PnL=${r_loso['total_net_pnl']:,.2f}")

    # =========================================================================
    # 8. FRONTERA DE COSTES (0, 2, 5, 7.5, 10 BPS)
    # =========================================================================
    print("\n[9/10] FRONTERA DE COSTES Y SLIPPAGE BREAK-EVEN...")
    slippage_levels = [0.0, 0.0002, 0.0005, 0.00075, 0.0010]
    cost_frontier = []
    for slip in slippage_levels:
        sim_cost = ExecutionAwareSimulator(
            evaluator=eval_frozen,
            concurrency_policy="REPLACE_IF_STRONGER",
            max_concurrent_positions=2,
            commission_per_share=0.005,
            slippage_pct=slip
        )
        r_cost = sim_cost.run_simulation(pre_data, precomputed_features=pre_features)
        bps_val = slip * 10000.0
        cost_frontier.append({
            "slippage_bps": bps_val,
            "slippage_pct": slip,
            "trades": r_cost["total_trades"],
            "pf": r_cost["profit_factor"],
            "pnl": r_cost["total_net_pnl"],
            "expectancy": r_cost["expectancy"],
            "sharpe": r_cost["sharpe_ratio"]
        })
        print(f"  Slippage {bps_val:4.1f} bps -> PF={r_cost['profit_factor']:.2f} | Net PnL=${r_cost['total_net_pnl']:,.2f} | Exp=${r_cost['expectancy']:.2f} | Sharpe={r_cost['sharpe_ratio']:.2f}")

    # =========================================================================
    # 9. ATRIBUCIÓN CONTRAFACTUAL DE TIME STOP
    # =========================================================================
    print("\n[10/10] ATRIBUCIÓN CONTRAFACTUAL DE TIME STOP Y CONCURRENCIA...")
    time_stop_trades = [t for t in trades_all if t.get("exit_reason") == "TIME_STOP"]
    n_ts = len(time_stop_trades)
    ts_pnl = sum(t["net_pnl"] for t in time_stop_trades)
    ts_wins = [t for t in time_stop_trades if t["net_pnl"] > 0]
    ts_losses = [t for t in time_stop_trades if t["net_pnl"] <= 0]
    ts_exp = ts_pnl / max(1, n_ts)

    # Evaluación posterior: si no hubieran salido en 15 barras, ¿qué habrían tocado después?
    would_hit_sl = 0
    would_hit_tp = 0
    neither = 0

    for tr in time_stop_trades:
        sym = tr["symbol"]
        exit_t = tr["exit_time"]
        side = tr["side"]
        entry_p = tr["entry_price"]
        h_bars = pre_data[sym]["1h"]
        exit_idx = None
        for idx, b in enumerate(h_bars):
            if b.timestamp == exit_t:
                exit_idx = idx
                break
        if exit_idx is None:
            continue

        # Target y stop teóricos
        sl_dist = tr["entry_price"] * 0.015
        tp_dist = sl_dist * 2.5
        sl_price = entry_p - sl_dist if side == "BUY" else entry_p + sl_dist
        tp_price = entry_p + tp_dist if side == "BUY" else entry_p - tp_dist

        forward_hit = None
        for f_idx in range(exit_idx + 1, min(len(h_bars), exit_idx + 40)):
            fb = h_bars[f_idx]
            if side == "BUY":
                if fb.low <= sl_price:
                    forward_hit = "SL"
                    break
                elif fb.high >= tp_price:
                    forward_hit = "TP"
                    break
            else:
                if fb.high >= sl_price:
                    forward_hit = "SL"
                    break
                elif fb.low <= tp_price:
                    forward_hit = "TP"
                    break
        if forward_hit == "SL":
            would_hit_sl += 1
        elif forward_hit == "TP":
            would_hit_tp += 1
        else:
            neither += 1

    pct_sl = round((would_hit_sl / max(1, n_ts)) * 100.0, 2)
    pct_tp = round((would_hit_tp / max(1, n_ts)) * 100.0, 2)
    print(f"  Time Stop Trades: {n_ts} ({n_ts/len(trades_all)*100:.1f}% del total)")
    print(f"  PnL de Time Stop Trades: ${ts_pnl:,.2f} | Exp=${ts_exp:.2f}")
    print(f"  Análisis Contrafactual posterior si se mantuvieran: Hit SL={pct_sl}% | Hit TP={pct_tp}% | Neither={neither}")

    # Guardar todos los resultados de la auditoría en JSON
    audit_summary = {
        "frozen_fingerprints": {
            "Ex24": fp_ex24,
            "Ex26": fp_ex26,
            "spec_ex24": spec_ex24,
            "spec_ex26": spec_ex26
        },
        "oos_adaptive_audit": oos_audit,
        "temporal_generalization": temporal_results,
        "rolling_walk_forward": rolling_wf_results,
        "regime_attribution": regime_stats,
        "symbol_generalization": symbol_stats,
        "leave_one_symbol_out": loso_stats,
        "cost_frontier": cost_frontier,
        "time_stop_attribution": {
            "total_time_stops": n_ts,
            "pnl": ts_pnl,
            "expectancy": ts_exp,
            "pct_would_hit_sl": pct_sl,
            "pct_would_hit_tp": pct_tp
        }
    }

    out_file = root_dir / "ai_trading_agent" / "scratch" / "fase8_1_audit_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2, default=str)

    print(f"\n[OK] Auditoría completada. Resultados guardados en {out_file}")


if __name__ == "__main__":
    run_audit_fase8_1()
