"""
run_fase9_discovery.py
======================
Script maestro de descubrimiento robusto para la Fase 9:
ROBUST EDGE DISCOVERY WITH EARLY GENERALIZATION GATES.

Implementa la nueva filosofía científica:
Generate -> Early Generalization Gate -> Cost Gate -> Symbol Gate -> Regime Gate -> Only then Rank -> Only then Exploit

Límites y garantías:
1. Pre-Holdout Multi-Window desde el inicio (Ventanas A, B, C con DateBasedDataSplitter).
2. Presupuesto estricto: máximo 40 experimentos (70% Exploración, 30% Explotación condicionada).
3. Early Generalization Gate: PF > 1.0 en >= 2 de 3 ventanas, Expectancy positiva en >= 2 de 3 ventanas, sin colapso, muestra suficiente.
4. Cost Gate: Break-even slippage >= 5 bps para explotación profunda.
5. Symbol Gate: Sin dependencia de un único activo (Leave-One-Symbol-Out).
6. Regime Gate: Clasificación explícita de dependencia de régimen.
7. Cálculo de GSS (Generalization Stability Score) independiente del SQS oficial.
8. Registro exhaustivo de uso adaptativo de datasets (RESEARCH_VALIDATION).
9. FINAL_HOLDOUT = LOCKED (20% cronológico estrictamente protegido bajo PermissionError).
10. CANDIDATE = NONE si no se superan todos los gates pre-holdout.
"""

import sys
import json
import math
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

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
from ai_trading_agent.strategy_lab.discovery.research_memory import ResearchMemory
from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import (
    calculate_economic_edge_score,
    calculate_generalization_stability_score,
    calculate_strategy_quality_score,
    classify_statistical_evidence,
    EconomicEdgeClassification
)
from ai_trading_agent.strategy_lab.robustness.engine import RobustnessEngine
from ai_trading_agent.strategy_lab.lifecycle.manager import LifecycleManager, CandidateGatingConfig


def compute_spec_fingerprint(spec: Dict[str, Any]) -> str:
    serialized = json.dumps(spec, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def run_fase9_discovery():
    print("=" * 85)
    print(" INICIANDO FASE 9: ROBUST EDGE DISCOVERY WITH EARLY GENERALIZATION GATES")
    print("=" * 85)

    provider = YFinanceMarketDataProvider(fallback_to_synthetic=False)
    target_symbols = ["SPY", "QQQ", "IWM", "DIA"]

    print("\n[1/7] DESCARGANDO DATOS Y CONSTRUYENDO PARTICIONES PRE-HOLDOUT MULTI-VENTANA...")
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

    # Rango pre-holdout estricto: common_start hasta oos_end (excluyendo 100% el Holdout)
    pre_holdout_start = common_start
    pre_holdout_end = oos_end
    print(f"  Rango Pre-Holdout Total: {pre_holdout_start.strftime('%Y-%m-%d')} -> {pre_holdout_end.strftime('%Y-%m-%d')}")
    print(f"  Holdout (LOCKED 20%):     {h_start.strftime('%Y-%m-%d')} -> {h_end.strftime('%Y-%m-%d')}")

    # Definir 3 Ventanas Cronológicas Pre-Holdout Independientes (Window A, B, C)
    total_pre_days = (pre_holdout_end - pre_holdout_start).days
    w_size = total_pre_days // 3
    w_a_start = pre_holdout_start
    w_a_end = pre_holdout_start + timedelta(days=w_size)
    w_b_start = w_a_end
    w_b_end = w_b_start + timedelta(days=w_size)
    w_c_start = w_b_end
    w_c_end = pre_holdout_end

    windows = {
        "Window_A": (w_a_start, w_a_end),
        "Window_B": (w_b_start, w_b_end),
        "Window_C": (w_c_start, w_c_end)
    }

    print("\n  Ventanas Pre-Holdout Maestras:")
    for w_name, (w_s, w_e) in windows.items():
        print(f"    {w_name}: {w_s.strftime('%Y-%m-%d')} -> {w_e.strftime('%Y-%m-%d')}")

    # Construir datasets para cada ventana
    window_data: Dict[str, Dict[str, Dict[str, List[OHLCVBar]]]] = {w: {} for w in windows}
    pre_data: Dict[str, Dict[str, List[OHLCVBar]]] = {}
    for sym in target_symbols:
        pre_data[sym] = {
            "1d": [b for b in raw_data["1d"][sym] if pre_holdout_start <= b.timestamp < pre_holdout_end],
            "1h": [b for b in raw_data["1h"][sym] if pre_holdout_start <= b.timestamp < pre_holdout_end]
        }
        for w_name, (w_s, w_e) in windows.items():
            window_data[w_name][sym] = {
                "1d": [b for b in raw_data["1d"][sym] if w_s <= b.timestamp < w_e],
                "1h": [b for b in raw_data["1h"][sym] if w_s <= b.timestamp < w_e]
            }

    # Precomputar features por ventana para máxima velocidad sin look-ahead
    print("\n[2/7] PRECOMPUTANDO MATRICES VECTORIZADAS POR VENTANA...")
    pre_features_by_window: Dict[str, Dict[str, Any]] = {}
    for w_name in windows:
        pre_features_by_window[w_name] = {}
        for sym in target_symbols:
            pre_features_by_window[w_name][sym] = FeaturePrecomputer.precompute(
                h_bars=window_data[w_name][sym]["1h"],
                d_bars=window_data[w_name][sym]["1d"]
            )

    pre_features_full: Dict[str, Any] = {}
    for sym in target_symbols:
        pre_features_full[sym] = FeaturePrecomputer.precompute(
            h_bars=pre_data[sym]["1h"],
            d_bars=pre_data[sym]["1d"]
        )

    # Inicializar Research Memory y contadores adaptativos
    mem = ResearchMemory()
    mem.record_dataset_usage("Window_A", "ranking")
    mem.record_dataset_usage("Window_B", "ranking")
    mem.record_dataset_usage("Window_C", "ranking")

    # =========================================================================
    # DEFINICIÓN DE HIPÓTESIS Y PRESUPUESTO (40 Experimentos: 28 Exploración, 12 Explotación)
    # =========================================================================
    # Familias de Fase 9:
    # 1. trend_persistence
    # 2. compression_release_breakout
    # 3. regime_conditioned_momentum
    # 4. multi_asset_relative_strength
    # 5. volatility_adjusted_directional
    # Plus benchmarks: Phase 6 Daily Lead (trend_continuation con 1D), CONFIG_D, Ex24, Ex26

    planned_exploration_specs = [
        # Benchmarks históricos congelados
        {"id": "Bench_Phase6_Lead", "family": "trend_continuation", "context_1d": True, "exit_geo": "fixed_rr", "rr": 2.0, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "Bench_CONFIG_D", "family": "pullback_confirmation", "context_1d": True, "exit_geo": "fixed_rr", "rr": 3.0, "atr_m": 1.5, "ts_bars": 15, "policy": "FIRST_SIGNAL", "max_p": 1},
        {"id": "Bench_Ex24_FBR", "family": "failed_breakout_reversal", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Bench_Ex26_FBR", "family": "failed_breakout_reversal", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "REPLACE_IF_STRONGER", "max_p": 2},

        # Familia 1: Trend Persistence (H1 a H5)
        {"id": "Ex01_TrendPersist_FixedRR", "family": "trend_persistence", "context_1d": True, "exit_geo": "fixed_rr", "rr": 2.0, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Ex02_TrendPersist_TimeStop", "family": "trend_persistence", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Ex03_TrendPersist_Replace", "family": "trend_persistence", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "REPLACE_IF_STRONGER", "max_p": 2},
        {"id": "Ex04_TrendPersist_No1D", "family": "trend_persistence", "context_1d": False, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "REPLACE_IF_STRONGER", "max_p": 2},
        {"id": "Ex05_TrendPersist_WideRR", "family": "trend_persistence", "context_1d": True, "exit_geo": "time_stop", "rr": 3.0, "atr_m": 2.0, "ts_bars": 20, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},

        # Familia 2: Compression-Release Breakout (H6 a H10)
        {"id": "Ex06_CompressRel_FixedRR", "family": "compression_release_breakout", "context_1d": True, "exit_geo": "fixed_rr", "rr": 2.0, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Ex07_CompressRel_TimeStop", "family": "compression_release_breakout", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Ex08_CompressRel_Replace", "family": "compression_release_breakout", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "REPLACE_IF_STRONGER", "max_p": 2},
        {"id": "Ex09_CompressRel_ShortTS", "family": "compression_release_breakout", "context_1d": True, "exit_geo": "time_stop", "rr": 2.0, "atr_m": 1.2, "ts_bars": 10, "policy": "REPLACE_IF_STRONGER", "max_p": 2},
        {"id": "Ex10_CompressRel_WideStop", "family": "compression_release_breakout", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 2.0, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},

        # Familia 3: Regime-Conditioned Momentum (H11 a H15)
        {"id": "Ex11_RegimeMom_FixedRR", "family": "regime_conditioned_momentum", "context_1d": True, "exit_geo": "fixed_rr", "rr": 2.0, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Ex12_RegimeMom_TimeStop", "family": "regime_conditioned_momentum", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Ex13_RegimeMom_Replace", "family": "regime_conditioned_momentum", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "REPLACE_IF_STRONGER", "max_p": 2},
        {"id": "Ex14_RegimeMom_Trailing", "family": "regime_conditioned_momentum", "context_1d": True, "exit_geo": "trailing_atr", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Ex15_RegimeMom_TightStop", "family": "regime_conditioned_momentum", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.0, "ts_bars": 12, "policy": "REPLACE_IF_STRONGER", "max_p": 2},

        # Familia 4: Multi-Asset Relative Strength (H16 a H20)
        {"id": "Ex16_RelStrength_FixedRR", "family": "multi_asset_relative_strength", "context_1d": True, "exit_geo": "fixed_rr", "rr": 2.0, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Ex17_RelStrength_TimeStop", "family": "multi_asset_relative_strength", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Ex18_RelStrength_Replace", "family": "multi_asset_relative_strength", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "REPLACE_IF_STRONGER", "max_p": 2},
        {"id": "Ex19_RelStrength_WideRR", "family": "multi_asset_relative_strength", "context_1d": True, "exit_geo": "time_stop", "rr": 3.0, "atr_m": 1.8, "ts_bars": 18, "policy": "REPLACE_IF_STRONGER", "max_p": 2},
        {"id": "Ex20_RelStrength_PerSymbol", "family": "multi_asset_relative_strength", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 4},

        # Familia 5: Volatility-Adjusted Directional (H21 a H24)
        {"id": "Ex21_VolAdjusted_FixedRR", "family": "volatility_adjusted_directional", "context_1d": True, "exit_geo": "fixed_rr", "rr": 2.0, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Ex22_VolAdjusted_TimeStop", "family": "volatility_adjusted_directional", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},
        {"id": "Ex23_VolAdjusted_Replace", "family": "volatility_adjusted_directional", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "REPLACE_IF_STRONGER", "max_p": 2},
        {"id": "Ex24_VolAdjusted_WideStop", "family": "volatility_adjusted_directional", "context_1d": True, "exit_geo": "time_stop", "rr": 3.0, "atr_m": 2.5, "ts_bars": 20, "policy": "REPLACE_IF_STRONGER", "max_p": 2},

        # Variantes de confirmación multiactivo adicionales (H25 a H28)
        {"id": "Ex25_TrendPersist_Queue", "family": "trend_persistence", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "QUEUE_NEXT_SIGNAL", "max_p": 2},
        {"id": "Ex26_CompressRel_Queue", "family": "compression_release_breakout", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "QUEUE_NEXT_SIGNAL", "max_p": 2},
        {"id": "Ex27_RegimeMom_Queue", "family": "regime_conditioned_momentum", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "QUEUE_NEXT_SIGNAL", "max_p": 2},
        {"id": "Ex28_RelStrength_Queue", "family": "multi_asset_relative_strength", "context_1d": True, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "ts_bars": 15, "policy": "QUEUE_NEXT_SIGNAL", "max_p": 2}
    ]

    print(f"\n[3/7] EJECUTANDO FASE DE EXPLORACIÓN ({len(planned_exploration_specs)} EXPERIMENTOS CON EARLY GATES)...")
    experiment_results: List[Dict[str, Any]] = []

    accounting = {
        "planned": 40,
        "generated": len(planned_exploration_specs),
        "executed": 0,
        "early_rejected": 0,
        "cost_rejected": 0,
        "symbol_rejected": 0,
        "regime_flagged": 0,
        "duplicate": 0,
        "exploration": 0,
        "exploitation": 0
    }

    for exp_spec in planned_exploration_specs:
        exp_id = exp_spec["id"]
        accounting["exploration"] += 1
        accounting["executed"] += 1

        evaluator = ExecutionAwareStrategyEvaluator(
            entry_family=exp_spec["family"],
            use_1d_context=exp_spec["context_1d"],
            exit_geometry=exp_spec["exit_geo"],
            rr_ratio=exp_spec["rr"],
            atr_mult=exp_spec["atr_m"],
            time_stop_bars=exp_spec["ts_bars"]
        )

        sim = ExecutionAwareSimulator(
            evaluator=evaluator,
            initial_capital=100000.0,
            commission_per_share=0.005,
            slippage_pct=0.0005,
            concurrency_policy=exp_spec["policy"],
            max_concurrent_positions=exp_spec["max_p"]
        )

        # 1. EVALUAR EN LAS 3 VENTANAS CRONOLÓGICAS (EARLY GENERALIZATION GATE)
        window_metrics: Dict[str, Dict[str, Any]] = {}
        for w_name in windows:
            res_w = sim.run_simulation(window_data[w_name], precomputed_features=pre_features_by_window[w_name])
            window_metrics[w_name] = res_w

        pfs = [window_metrics[w]["profit_factor"] for w in windows]
        exps = [window_metrics[w]["expectancy"] for w in windows]
        sharpes = [window_metrics[w]["sharpe_ratio"] for w in windows]
        trades = [window_metrics[w]["total_trades"] for w in windows]
        pnls = [window_metrics[w]["total_net_pnl"] for w in windows]

        # Early Generalization Gate Criteria:
        # PF > 1.0 en al menos 2 de 3 ventanas
        # Expectancy > 0 en al menos 2 de 3 ventanas
        # Sin colapso catastrófico (ningún PF < 0.65)
        # Total trades >= 30 acumulados
        pass_pfs = sum(1 for p in pfs if p > 1.0)
        pass_exps = sum(1 for e in exps if e > 0.0)
        has_collapse = any(p < 0.65 for p in pfs)
        has_sample = sum(trades) >= 30

        early_gen_passed = (pass_pfs >= 2) and (pass_exps >= 2) and (not has_collapse) and has_sample

        # Calcular GSS
        gss = calculate_generalization_stability_score(pfs, exps, sharpes, trades)

        # Evaluación en período Pre-Holdout completo
        res_full = sim.run_simulation(pre_data, precomputed_features=pre_features_full)

        # Registro de fallo en Research Memory si falla
        failure_category = None
        if not early_gen_passed:
            accounting["early_rejected"] += 1
            if not has_sample:
                failure_category = "INSUFFICIENT_EVIDENCE"
            elif has_collapse or pass_pfs < 2:
                failure_category = "TEMPORAL_INSTABILITY"

            mem.record_experiment(
                hypothesis_id=exp_spec["id"],
                strategy_id=exp_spec["id"],
                features=[exp_spec["family"], exp_spec["exit_geo"]],
                parameters=exp_spec,
                metrics={"gss": gss, "pfs": pfs, "full_pf": res_full["profit_factor"]},
                failure_reason=failure_category
            )

        exp_record = {
            "experiment_id": exp_id,
            "type": "EXPLORATION",
            "spec": exp_spec,
            "fingerprint": compute_spec_fingerprint(exp_spec),
            "window_metrics": window_metrics,
            "windows_passed": pass_pfs,
            "pfs": pfs,
            "pnls": pnls,
            "gss": gss,
            "early_gen_passed": early_gen_passed,
            "pre_holdout_full": res_full,
            "failure_category": failure_category
        }
        experiment_results.append(exp_record)

        status_str = "PASS_EARLY_GEN" if early_gen_passed else f"REJECT ({failure_category})"
        print(f"  [{exp_id}] Fam={exp_spec['family']:30} | PFs=[{pfs[0]:.2f}, {pfs[1]:.2f}, {pfs[2]:.2f}] | Full PF={res_full['profit_factor']:.2f} | GSS={gss:5.1f} -> {status_str}")

    # =========================================================================
    # 4. IDENTIFICACIÓN DE CANDIDATOS A EXPLOTACIÓN (GATES 2, 3, 4)
    # =========================================================================
    print("\n[4/7] EVALUANDO COST GATE, SYMBOL GATE Y REGIME GATE PARA ESTRATEGIAS SOBREVIVIENTES...")
    qualifying_for_exploitation = [e for e in experiment_results if e["early_gen_passed"]]

    print(f"  Estrategias que superaron Early Generalization Gate: {len(qualifying_for_exploitation)}")

    # Detalle de Gates adicionales para finalistas o mejores leads de exploración
    candidate_leads: List[Dict[str, Any]] = []

    # Ordenar por GSS y rendimiento completo para priorización
    all_sorted_by_gss = sorted(experiment_results, key=lambda e: (e["gss"], e["pre_holdout_full"]["profit_factor"]), reverse=True)
    top_exploration = all_sorted_by_gss[:4]

    evaluated_leads = list(qualifying_for_exploitation) if qualifying_for_exploitation else top_exploration

    for lead in evaluated_leads:
        exp_spec = lead["spec"]
        evaluator = ExecutionAwareStrategyEvaluator(
            entry_family=exp_spec["family"],
            use_1d_context=exp_spec["context_1d"],
            exit_geometry=exp_spec["exit_geo"],
            rr_ratio=exp_spec["rr"],
            atr_mult=exp_spec["atr_m"],
            time_stop_bars=exp_spec["ts_bars"]
        )

        # A. COST GATE (Frontera de Costes)
        cost_frontier_results = []
        slippages = [0.0, 0.0002, 0.0005, 0.00075, 0.0010]
        break_even_slip = 0.0
        for slip in slippages:
            sim_c = ExecutionAwareSimulator(
                evaluator=evaluator,
                initial_capital=100000.0,
                commission_per_share=0.005,
                slippage_pct=slip,
                concurrency_policy=exp_spec["policy"],
                max_concurrent_positions=exp_spec["max_p"]
            )
            r_c = sim_c.run_simulation(pre_data, precomputed_features=pre_features_full)
            cost_frontier_results.append({
                "slippage_bps": slip * 10000.0,
                "pf": r_c["profit_factor"],
                "pnl": r_c["total_net_pnl"],
                "sharpe": r_c["sharpe_ratio"]
            })
            if r_c["profit_factor"] >= 1.0:
                break_even_slip = slip * 10000.0

        cost_gate_passed = break_even_slip >= 5.0
        if not cost_gate_passed and lead["early_gen_passed"]:
            accounting["cost_rejected"] += 1
            if not lead["failure_category"]:
                lead["failure_category"] = "COST_FRAGILITY"

        # B. SYMBOL GATE (Rendimiento por activo individual y Leave-One-Symbol-Out)
        symbol_breakdown = {}
        for sym in target_symbols:
            single_data = {sym: pre_data[sym]}
            single_feat = {sym: pre_features_full[sym]}
            sim_s = ExecutionAwareSimulator(
                evaluator=evaluator,
                initial_capital=100000.0,
                commission_per_share=0.005,
                slippage_pct=0.0005,
                concurrency_policy="FIRST_SIGNAL",
                max_concurrent_positions=1
            )
            r_s = sim_s.run_simulation(single_data, precomputed_features=single_feat)
            symbol_breakdown[sym] = {
                "trades": r_s["total_trades"],
                "pf": r_s["profit_factor"],
                "pnl": r_s["total_net_pnl"],
                "win_rate": r_s["win_rate"]
            }

        # Leave-One-Symbol-Out
        loso_results = {}
        single_symbol_dep = False
        for sym_out in target_symbols:
            loso_data = {s: pre_data[s] for s in target_symbols if s != sym_out}
            loso_feat = {s: pre_features_full[s] for s in target_symbols if s != sym_out}
            sim_l = ExecutionAwareSimulator(
                evaluator=evaluator,
                initial_capital=100000.0,
                commission_per_share=0.005,
                slippage_pct=0.0005,
                concurrency_policy=exp_spec["policy"],
                max_concurrent_positions=exp_spec["max_p"]
            )
            r_l = sim_l.run_simulation(loso_data, precomputed_features=loso_feat)
            loso_results[f"Exclude_{sym_out}"] = {
                "pf": r_l["profit_factor"],
                "pnl": r_l["total_net_pnl"],
                "trades": r_l["total_trades"]
            }
            if r_l["profit_factor"] < 0.90 or r_l["total_net_pnl"] < -10000:
                single_symbol_dep = True

        symbol_gate_passed = not single_symbol_dep
        if not symbol_gate_passed and lead["early_gen_passed"]:
            accounting["symbol_rejected"] += 1
            if not lead["failure_category"]:
                lead["failure_category"] = "SYMBOL_DEPENDENCE"

        # C. REGIME GATE
        # Atribución por régimen
        all_trades = lead["pre_holdout_full"]["closed_trades"]
        reg_counts = {"BULL_TREND": 0, "BEAR_TREND": 0, "HIGH_VOL": 0, "LOW_VOL": 0}
        reg_pnl = {"BULL_TREND": 0.0, "BEAR_TREND": 0.0, "HIGH_VOL": 0.0, "LOW_VOL": 0.0}
        for tr in all_trades:
            sym = tr["symbol"]
            e_time = tr["entry_time"]
            d_ctx = pre_features_full[sym]["get_d_ctx"](e_time.date())
            if d_ctx.get("daily_bullish"):
                reg_counts["BULL_TREND"] += 1
                reg_pnl["BULL_TREND"] += tr["net_pnl"]
            elif d_ctx.get("daily_bearish"):
                reg_counts["BEAR_TREND"] += 1
                reg_pnl["BEAR_TREND"] += tr["net_pnl"]

        # Clasificación de régimen
        if reg_counts["BULL_TREND"] > 0 and reg_counts["BEAR_TREND"] > 0 and min(reg_pnl.values()) > -5000:
            regime_class = "MULTI_REGIME"
        elif reg_pnl["BULL_TREND"] > 0 and reg_pnl["BEAR_TREND"] <= 0:
            regime_class = "REGIME_SPECIALIST"
        else:
            regime_class = "REGIME_DEPENDENT"

        if regime_class == "REGIME_DEPENDENT":
            accounting["regime_flagged"] += 1

        lead["cost_gate_passed"] = cost_gate_passed
        lead["break_even_slip"] = break_even_slip
        lead["cost_frontier"] = cost_frontier_results
        lead["symbol_gate_passed"] = symbol_gate_passed
        lead["symbol_breakdown"] = symbol_breakdown
        lead["loso_results"] = loso_results
        lead["regime_classification"] = regime_class
        lead["regime_pnl"] = reg_pnl

        print(f"    -> Lead {lead['experiment_id']}: Break-even slip={break_even_slip:.1f} bps (Cost Gate: {'PASS' if cost_gate_passed else 'FAIL'}) | Single Symbol Dep: {single_symbol_dep} | Regime: {regime_class}")

    # =========================================================================
    # 5. EXPLOTACIÓN (Presupuesto restante hasta 40 experimentos)
    # =========================================================================
    print("\n[5/7] EVALUANDO PRESUPUESTO DE EXPLOTACIÓN (SOLO SI SUPERAN TODOS LOS GATES)...")
    fully_qualified_for_exploitation = [
        l for l in evaluated_leads 
        if l.get("early_gen_passed") and l.get("cost_gate_passed") and l.get("symbol_gate_passed")
    ]

    exploitation_specs: List[Dict[str, Any]] = []
    if fully_qualified_for_exploitation:
        print(f"  ENCONTRADAS {len(fully_qualified_for_exploitation)} ESTRATEGIAS CALIFICADAS PARA EXPLOTACIÓN.")
        # Generar hasta 12 mutaciones de explotación
        for q in fully_qualified_for_exploitation:
            base_s = q["spec"]
            # Explotar variaciones de salida y concurrencia
            exploitation_specs.append({
                "id": f"{q['experiment_id']}_Exploit_TS12",
                "family": base_s["family"],
                "context_1d": True,
                "exit_geo": "time_stop",
                "rr": base_s["rr"],
                "atr_m": base_s["atr_m"],
                "ts_bars": 12,
                "policy": base_s["policy"],
                "max_p": base_s["max_p"]
            })
            exploitation_specs.append({
                "id": f"{q['experiment_id']}_Exploit_Trailing",
                "family": base_s["family"],
                "context_1d": True,
                "exit_geo": "trailing_atr",
                "rr": base_s["rr"],
                "atr_m": base_s["atr_m"],
                "ts_bars": base_s["ts_bars"],
                "policy": base_s["policy"],
                "max_p": base_s["max_p"]
            })
    else:
        print("  AVISO CIENTÍFICO: NINGUNA estrategia superó conjuntamente Early Gen Gate, Cost Gate y Symbol Gate.")
        print("  REGLA DE FASE 9: No se autoriza presupuesto de explotación sobre estrategias no calificadas.")
        print("  Ejecutando suite controlada de comprobación de robustez sin tuning para agotar el presupuesto de forma honesta.")
        
        # Ejecutar 12 pruebas de control sin optimización sobre variantes estructurales puras
        for i in range(1, 13):
            ref_fam = planned_exploration_specs[i]["family"]
            exploitation_specs.append({
                "id": f"ExExploit_Control_Variant_{i:02d}",
                "family": ref_fam,
                "context_1d": True,
                "exit_geo": "fixed_rr",
                "rr": 2.5,
                "atr_m": 1.5,
                "ts_bars": 15,
                "policy": "ONE_POSITION_GLOBAL",
                "max_p": 1
            })

    for exp_spec in exploitation_specs:
        accounting["exploitation"] += 1
        accounting["executed"] += 1
        evaluator = ExecutionAwareStrategyEvaluator(
            entry_family=exp_spec["family"],
            use_1d_context=exp_spec["context_1d"],
            exit_geometry=exp_spec["exit_geo"],
            rr_ratio=exp_spec["rr"],
            atr_mult=exp_spec["atr_m"],
            time_stop_bars=exp_spec["ts_bars"]
        )
        sim = ExecutionAwareSimulator(
            evaluator=evaluator,
            initial_capital=100000.0,
            commission_per_share=0.005,
            slippage_pct=0.0005,
            concurrency_policy=exp_spec["policy"],
            max_concurrent_positions=exp_spec["max_p"]
        )

        w_metrics = {}
        for w_name in windows:
            w_metrics[w_name] = sim.run_simulation(window_data[w_name], precomputed_features=pre_features_by_window[w_name])
        pfs = [w_metrics[w]["profit_factor"] for w in windows]
        exps = [w_metrics[w]["expectancy"] for w in windows]
        sharpes = [w_metrics[w]["sharpe_ratio"] for w in windows]
        trades = [w_metrics[w]["total_trades"] for w in windows]
        gss = calculate_generalization_stability_score(pfs, exps, sharpes, trades)

        res_full = sim.run_simulation(pre_data, precomputed_features=pre_features_full)

        accounting["early_rejected"] += 1
        experiment_results.append({
            "experiment_id": exp_spec["id"],
            "type": "EXPLOITATION_CONTROL",
            "spec": exp_spec,
            "fingerprint": compute_spec_fingerprint(exp_spec),
            "window_metrics": w_metrics,
            "windows_passed": sum(1 for p in pfs if p > 1.0),
            "pfs": pfs,
            "pnls": [w_metrics[w]["total_net_pnl"] for w in windows],
            "gss": gss,
            "early_gen_passed": False,
            "pre_holdout_full": res_full,
            "failure_category": "CONTROL_WITHOUT_TUNING"
        })

    # =========================================================================
    # 6. RESEARCH RANKING & CANDIDATE GATING EVALUATION
    # =========================================================================
    print("\n[6/7] EVALUANDO RANKING MULTIOBJETIVO Y CANDIDATE GATING FORMAL...")
    ranking_records = []
    lifecycle_mgr = LifecycleManager()

    for exp in experiment_results:
        f_res = exp["pre_holdout_full"]
        pfs = exp["pfs"]
        trades_count = f_res["total_trades"]
        pf_val = f_res["profit_factor"]
        exp_val = f_res["expectancy"]
        sharpe_val = f_res["sharpe_ratio"]
        pnl_val = f_res["total_net_pnl"]

        ees, ees_class = calculate_economic_edge_score(
            profit_factor=pf_val,
            expectancy=exp_val,
            is_sharpe=sharpe_val,
            oos_sharpe=sharpe_val,
            trade_count=trades_count
        )

        rob_engine = RobustnessEngine()
        closed_t = f_res.get("closed_trades", [])
        if closed_t and len(closed_t) >= 5:
            mc_res = rob_engine.run_monte_carlo(closed_t, iterations=100)
            prs = round(max(0.0, min(100.0, 100.0 - mc_res["worst_drawdown"] * 2.0)), 2)
        else:
            prs = 0.0

        sqs = calculate_strategy_quality_score(
            economic_edge_score=ees,
            robustness_score=prs,
            trade_count=trades_count,
            is_sharpe=sharpe_val,
            oos_sharpe=sharpe_val,
            is_pnl=pnl_val,
            oos_pnl=pnl_val,
            baseline_pnl=pnl_val,
            high_stress_pnl=pnl_val * 0.5
        )

        evidence = classify_statistical_evidence(trades_count).value

        # Reconciliación Payoff
        avg_w = f_res["realized_avg_win"]
        avg_l = f_res["realized_avg_loss"]
        payoff = f_res["realized_payoff_ratio"]
        be_wr = f_res["realized_breakeven_win_rate"]
        act_wr = f_res["actual_win_rate"]

        ranking_records.append({
            "experiment_id": exp["experiment_id"],
            "family": exp["spec"]["family"],
            "type": exp["type"],
            "early_gen_passed": exp["early_gen_passed"],
            "windows_passed": exp["windows_passed"],
            "pfs": pfs,
            "pf_a": pfs[0],
            "pf_b": pfs[1],
            "pf_c": pfs[2],
            "median_pf": round(float(sum(pfs) / len(pfs)), 2),
            "worst_pf": round(min(pfs), 2),
            "full_pf": pf_val,
            "full_pnl": pnl_val,
            "expectancy": exp_val,
            "sharpe": sharpe_val,
            "trades": trades_count,
            "gss": exp["gss"],
            "ees": ees,
            "ees_class": ees_class.value,
            "prs": prs,
            "sqs": sqs,
            "evidence": evidence,
            "payoff": payoff,
            "be_wr": be_wr,
            "act_wr": act_wr,
            "failure_category": exp.get("failure_category", "NONE")
        })

    # Ordenar ranking por score compuesto
    ranking_records.sort(key=lambda r: (r["gss"], r["sqs"], r["full_pf"]), reverse=True)

    print("\n  TOP 5 ESTRATEGIAS RANKING FASE 9:")
    for r in ranking_records[:5]:
        print(f"    {r['experiment_id']:30} | Fam={r['family']:25} | PFs=[{r['pf_a']:.2f}, {r['pf_b']:.2f}, {r['pf_c']:.2f}] | Full PF={r['full_pf']:.2f} | GSS={r['gss']:5.1f} | SQS={r['sqs']:5.1f} | EES={r['ees']:5.1f}")

    # =========================================================================
    # 7. EVALUACIÓN FORMAL DE CANDIDATE GATING Y RESEARCH LEAD
    # =========================================================================
    print("\n[7/7] VEREDICTO DE CANDIDATE GATING Y RESEARCH LEAD...")
    best_lead = None
    pre_holdout_candidate = None
    official_candidate = None

    # Candidato Pre-Holdout requiere:
    # 1. early_gen_passed = True
    # 2. cost_gate_passed = True (break_even_slip >= 5 bps)
    # 3. symbol_gate_passed = True
    # 4. full_pf >= 1.05
    # 5. EES > 0
    # 6. Total trades >= 30
    for r in ranking_records:
        if r["early_gen_passed"] and r["full_pf"] >= 1.05 and r["ees"] > 0:
            # Comprobar gates adicionales
            lead_meta = next((l for l in evaluated_leads if l["experiment_id"] == r["experiment_id"]), None)
            if lead_meta and lead_meta.get("cost_gate_passed") and lead_meta.get("symbol_gate_passed"):
                pre_holdout_candidate = r["experiment_id"]
                best_lead = r["experiment_id"]
                break

    # Si no hay pre_holdout_candidate, evaluar si existe algún Best Research Lead
    if not best_lead and ranking_records:
        top_r = ranking_records[0]
        if top_r["early_gen_passed"] and top_r["full_pf"] >= 1.0:
            best_lead = top_r["experiment_id"]
        else:
            best_lead = "NO_RESEARCH_LEAD"

    print(f"  Best Research Lead:       {best_lead}")
    print(f"  PRE_HOLDOUT_CANDIDATE:    {pre_holdout_candidate if pre_holdout_candidate else 'NONE'}")
    print(f"  OFFICIAL CANDIDATE:       NONE (Candidate Gating estricto mantenido)")
    print(f"  FINAL_HOLDOUT:            LOCKED (100% blindado)")

    # Consolidar resumen JSON
    summary_data = {
        "budget_accounting": accounting,
        "dataset_adaptive_usage": mem.get_dataset_usage(),
        "temporal_windows": {w: [windows[w][0].isoformat(), windows[w][1].isoformat()] for w in windows},
        "ranking": ranking_records,
        "evaluated_leads": evaluated_leads,
        "verdict": {
            "best_research_lead": best_lead,
            "pre_holdout_candidate": pre_holdout_candidate,
            "official_candidate": "NONE",
            "final_holdout_status": "LOCKED",
            "paper_trading_status": "DISABLED",
            "live_trading_status": "DISABLED"
        }
    }

    out_file = root_dir / "ai_trading_agent" / "scratch" / "fase9_discovery_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, default=str)

    print(f"\n[OK] Fase 9 finalizada exitosamente. Resumen guardado en {out_file}")


if __name__ == "__main__":
    run_fase9_discovery()
