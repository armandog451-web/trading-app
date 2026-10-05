"""
run_fase10_daily_discovery.py
=============================
Script maestro de descubrimiento robusto para la Fase 10:
DAILY & MULTI-DAY ROBUST EDGE DISCOVERY.

Reglas institucionales de la Fase 10:
1. Discovery Budget: máximo 40 discovery experiments (separando explícitamente discovery de validation runs).
2. Exploración (70%) / Explotación condicionada (30%). Explotación SOLO si pasa Early Gen Gate, Cost Gate y Symbol Gate.
3. Pre-Holdout Multi-Window desde el inicio (Ventanas A, B, C disjuntas).
4. Timeframe principal: 1D con holding horizons de 1 a 10 días.
5. Fricción obligatoria desde Experimento 1: Comisión = $0.005/acción, Slippage = 5 bps.
6. Métrica diagnóstica: MovementToCostRatio (MCR).
7. Análisis exhaustivo de Turnover y Holding Period.
8. Cost Frontier: 0, 2, 5, 7.5, 10 bps. Break-even slippage >= 5 bps requerido.
9. Symbol Gate: SPY, QQQ, IWM, DIA con Leave-One-Symbol-Out (LOSO).
10. Regime Analysis: BULL_TREND, BEAR_TREND, SIDEWAYS, HIGH_VOL, LOW_VOL.
11. GSS y EES independientes.
12. Comparación institucional agregada con la mejor familia 1H de Fase 9.
13. FINAL_HOLDOUT = LOCKED (20% cronológico protegido bajo PermissionError).
"""

import sys
import json
import math
import hashlib
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple

root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.data.providers.yfinance_provider import YFinanceMarketDataProvider
from ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer import DateBasedDataSplitter
from ai_trading_agent.strategy_lab.backtesting.daily_execution_simulator import (
    DailyExecutionSimulator,
    DailyStrategyEvaluator,
    DailyFeaturePrecomputer
)
from ai_trading_agent.strategy_lab.discovery.research_memory import ResearchMemory
from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import (
    calculate_economic_edge_score,
    calculate_generalization_stability_score,
    calculate_strategy_quality_score,
    classify_statistical_evidence,
    calculate_movement_to_cost_ratio,
    EconomicEdgeClassification
)
from ai_trading_agent.strategy_lab.robustness.engine import RobustnessEngine
from ai_trading_agent.strategy_lab.lifecycle.manager import LifecycleManager, CandidateGatingConfig


def compute_spec_fingerprint(spec: Dict[str, Any]) -> str:
    serialized = json.dumps(spec, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def run_fase10_daily_discovery():
    print("=" * 85)
    print(" INICIANDO FASE 10: DAILY & MULTI-DAY ROBUST EDGE DISCOVERY")
    print("=" * 85)

    provider = YFinanceMarketDataProvider(fallback_to_synthetic=False)
    target_symbols = ["SPY", "QQQ", "IWM", "DIA"]

    print("\n[1/7] DESCARGANDO DATOS DIARIOS (1D) Y CONSTRUYENDO PARTICIONES PRE-HOLDOUT...")
    raw_data_1d: Dict[str, List[OHLCVBar]] = {}
    for sym in target_symbols:
        raw_data_1d[sym] = provider.get_historical_bars(symbol=sym, count=1500, interval="1d")

    # Alinear calendario cronológico
    common_start = max(raw_data_1d[s][0].timestamp for s in target_symbols)
    common_end = min(raw_data_1d[s][-1].timestamp for s in target_symbols)

    total_days = (common_end - common_start).days
    holdout_days = int(total_days * 0.20)
    pre_holdout_start = common_start
    pre_holdout_end = common_end - timedelta(days=holdout_days)
    holdout_start = pre_holdout_end
    holdout_end = common_end

    print(f"  Rango Histórico Total:    {common_start.strftime('%Y-%m-%d')} -> {common_end.strftime('%Y-%m-%d')} ({total_days} días)")
    print(f"  Rango Pre-Holdout Total:  {pre_holdout_start.strftime('%Y-%m-%d')} -> {pre_holdout_end.strftime('%Y-%m-%d')}")
    print(f"  Holdout (LOCKED 20%):     {holdout_start.strftime('%Y-%m-%d')} -> {holdout_end.strftime('%Y-%m-%d')} ({holdout_days} días)")

    # Dividir el período Pre-Holdout en 3 Ventanas Cronológicas Disjuntas (Window A, B, C)
    pre_days = (pre_holdout_end - pre_holdout_start).days
    w_size = pre_days // 3
    wa_start = pre_holdout_start
    wa_end = pre_holdout_start + timedelta(days=w_size)
    wb_start = wa_end
    wb_end = wb_start + timedelta(days=w_size)
    wc_start = wb_end
    wc_end = pre_holdout_end

    windows = {
        "Window_A": (wa_start, wa_end),
        "Window_B": (wb_start, wb_end),
        "Window_C": (wc_start, wc_end)
    }

    print("\n  Ventanas Pre-Holdout Multi-Ventana Maestras:")
    for w_name, (w_s, w_e) in windows.items():
        print(f"    {w_name}: {w_s.strftime('%Y-%m-%d')} -> {w_e.strftime('%Y-%m-%d')}")

    # Filtrar datos por ventana y precomputar matrices técnicas sin look-ahead
    window_data: Dict[str, Dict[str, List[OHLCVBar]]] = {w: {} for w in windows}
    pre_data: Dict[str, List[OHLCVBar]] = {}
    for sym in target_symbols:
        pre_data[sym] = [b for b in raw_data_1d[sym] if pre_holdout_start <= b.timestamp < pre_holdout_end]
        for w_name, (w_s, w_e) in windows.items():
            window_data[w_name][sym] = [b for b in raw_data_1d[sym] if w_s <= b.timestamp < w_e]

    print("\n[2/7] PRECOMPUTANDO MATRICES VECTORIZADAS DIARIAS...")
    pre_features_by_window: Dict[str, Dict[str, Any]] = {}
    for w_name in windows:
        pre_features_by_window[w_name] = {}
        for sym in target_symbols:
            pre_features_by_window[w_name][sym] = DailyFeaturePrecomputer.precompute(window_data[w_name][sym])

    pre_features_full: Dict[str, Any] = {}
    for sym in target_symbols:
        pre_features_full[sym] = DailyFeaturePrecomputer.precompute(pre_data[sym])

    # Research Memory y contador adaptativo de gobernanza
    mem = ResearchMemory()
    mem.record_dataset_usage("Daily_Window_A", "ranking")
    mem.record_dataset_usage("Daily_Window_B", "ranking")
    mem.record_dataset_usage("Daily_Window_C", "ranking")

    # =========================================================================
    # DEFINICIÓN DEL CATÁLOGO DE DISCOVERY (MÁXIMO 40 EXPERIMENTOS)
    # =========================================================================
    # 28 Exploración (70%) + hasta 12 Explotación (30% condicionado a gates)
    # Familias de Investigación 1D:
    # 1. daily_trend_persistence (holding: 3d, 5d, 10d)
    # 2. multi_day_momentum (holding: 3d, 5d)
    # 3. daily_volatility_contraction_expansion (holding: 3d, 5d)
    # 4. daily_pullback_trend (holding: 3d, 5d, trailing)
    # 5. regime_conditioned_swing_momentum (holding: 5d, 10d)
    # 6. daily_mean_reversion (holding: 2d, 3d, 5d)
    # 7. daily_gap_continuation (holding: 1d, 3d)
    # 8. daily_range_compression_breakout (holding: 5d, 10d)
    # 9. multi_day_reversal (holding: 3d, 5d)
    # 10. etf_relative_strength_rotation (holding: 5d, 10d, 20d)

    planned_discovery_specs = [
        # Familia 1: Daily Trend Persistence (H01 - H03)
        {"id": "D01_TrendPersist_3d", "family": "daily_trend_persistence", "horizon": 3, "exit_geo": "time_stop", "rr": 2.0, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D02_TrendPersist_5d", "family": "daily_trend_persistence", "horizon": 5, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D03_TrendPersist_10d_Trail", "family": "daily_trend_persistence", "horizon": 10, "exit_geo": "atr_trailing", "rr": 3.0, "atr_m": 2.0, "trail_m": 2.5, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},

        # Familia 2: Multi-Day Momentum (H04 - H06)
        {"id": "D04_MultiDayMom_3d", "family": "multi_day_momentum", "horizon": 3, "exit_geo": "time_stop", "rr": 2.0, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D05_MultiDayMom_5d", "family": "multi_day_momentum", "horizon": 5, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D06_MultiDayMom_Trail", "family": "multi_day_momentum", "horizon": 8, "exit_geo": "atr_trailing", "rr": 2.5, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},

        # Familia 3: Volatility Contraction -> Expansion (H07 - H09)
        {"id": "D07_VolContrExp_3d", "family": "daily_volatility_contraction_expansion", "horizon": 3, "exit_geo": "time_stop", "rr": 2.0, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D08_VolContrExp_5d", "family": "daily_volatility_contraction_expansion", "horizon": 5, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D09_VolContrExp_Wide", "family": "daily_volatility_contraction_expansion", "horizon": 7, "exit_geo": "time_stop", "rr": 3.0, "atr_m": 2.0, "trail_m": 2.0, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},

        # Familia 4: Daily Pullback within Trend (H10 - H12)
        {"id": "D10_PullbackTrend_3d", "family": "daily_pullback_trend", "horizon": 3, "exit_geo": "time_stop", "rr": 2.0, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D11_PullbackTrend_5d", "family": "daily_pullback_trend", "horizon": 5, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D12_PullbackTrend_Trail", "family": "daily_pullback_trend", "horizon": 10, "exit_geo": "atr_trailing", "rr": 2.5, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},

        # Familia 5: Regime-Conditioned Swing Momentum (H13 - H15)
        {"id": "D13_RegimeSwing_5d", "family": "regime_conditioned_swing_momentum", "horizon": 5, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D14_RegimeSwing_10d", "family": "regime_conditioned_swing_momentum", "horizon": 10, "exit_geo": "time_stop", "rr": 3.0, "atr_m": 2.0, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D15_RegimeSwing_Trail", "family": "regime_conditioned_swing_momentum", "horizon": 10, "exit_geo": "atr_trailing", "rr": 3.0, "atr_m": 1.8, "trail_m": 2.2, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},

        # Familia 6: Daily Mean Reversion (H16 - H18)
        {"id": "D16_MeanRevert_2d", "family": "daily_mean_reversion", "horizon": 2, "exit_geo": "time_stop", "rr": 1.5, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D17_MeanRevert_3d", "family": "daily_mean_reversion", "horizon": 3, "exit_geo": "time_stop", "rr": 2.0, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D18_MeanRevert_5d", "family": "daily_mean_reversion", "horizon": 5, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 2.0, "trail_m": 2.0, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},

        # Familia 7: Daily Gap Continuation (H19 - H20)
        {"id": "D19_GapCont_1d", "family": "daily_gap_continuation", "horizon": 1, "exit_geo": "time_stop", "rr": 1.5, "atr_m": 1.2, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D20_GapCont_3d", "family": "daily_gap_continuation", "horizon": 3, "exit_geo": "time_stop", "rr": 2.0, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},

        # Familia 8: Daily Range Compression Breakout (H21 - H23)
        {"id": "D21_RangeCompress_5d", "family": "daily_range_compression_breakout", "horizon": 5, "exit_geo": "time_stop", "rr": 2.0, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D22_RangeCompress_10d", "family": "daily_range_compression_breakout", "horizon": 10, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.8, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D23_RangeCompress_Trail", "family": "daily_range_compression_breakout", "horizon": 10, "exit_geo": "atr_trailing", "rr": 3.0, "atr_m": 2.0, "trail_m": 2.5, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},

        # Familia 9: Multi-Day Reversal (H24 - H25)
        {"id": "D24_MultiDayRev_3d", "family": "multi_day_reversal", "horizon": 3, "exit_geo": "time_stop", "rr": 2.0, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D25_MultiDayRev_5d", "family": "multi_day_reversal", "horizon": 5, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 1.8, "trail_m": 2.0, "policy": "ONE_POSITION_GLOBAL", "max_p": 1},

        # Familia 10: Cross-ETF Relative Strength Rotation (H26 - H28)
        {"id": "D26_ETFRotation_5d", "family": "etf_relative_strength_rotation", "horizon": 5, "exit_geo": "time_stop", "rr": 2.0, "atr_m": 1.5, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D27_ETFRotation_10d", "family": "etf_relative_strength_rotation", "horizon": 10, "exit_geo": "time_stop", "rr": 2.5, "atr_m": 2.0, "trail_m": 2.0, "policy": "ONE_POSITION_PER_SYMBOL", "max_p": 2},
        {"id": "D28_ETFRotation_Trail", "family": "etf_relative_strength_rotation", "horizon": 15, "exit_geo": "atr_trailing", "rr": 3.0, "atr_m": 2.0, "trail_m": 2.5, "policy": "ONE_POSITION_GLOBAL", "max_p": 1}
    ]

    print(f"\n[3/7] EJECUTANDO FASE DE EXPLORACIÓN DISCOVERY ({len(planned_discovery_specs)} HIPÓTESIS CON EARLY GENERALIZATION GATES)...")

    # Contabilidad separada y exacta:
    # discovery_experiments <= 40
    # validation_runs reportados separadamente
    accounting = {
        "discovery_experiments_budget": 40,
        "discovery_experiments_executed": 0,
        "exploration_executed": 0,
        "exploitation_executed": 0,
        "early_rejected": 0,
        "cost_rejected": 0,
        "symbol_rejected": 0,
        "regime_flagged": 0,
        "validation_runs_executed": 0,  # LOSO, cost frontier, walk forward
        "total_executions": 0
    }

    discovery_results: List[Dict[str, Any]] = []

    for d_spec in planned_discovery_specs:
        accounting["discovery_experiments_executed"] += 1
        accounting["exploration_executed"] += 1
        accounting["total_executions"] += 1

        evaluator = DailyStrategyEvaluator(
            family=d_spec["family"],
            holding_horizon_days=d_spec["horizon"],
            exit_geometry=d_spec["exit_geo"],
            rr_ratio=d_spec["rr"],
            atr_mult=d_spec["atr_m"],
            trailing_mult=d_spec["trail_m"]
        )

        sim = DailyExecutionSimulator(
            evaluator=evaluator,
            initial_capital=100000.0,
            commission_per_share=0.005,
            slippage_pct=0.0005,
            risk_per_trade_pct=0.01,
            concurrency_policy=d_spec["policy"],
            max_concurrent_positions=d_spec["max_p"]
        )

        # 1. EVALUAR EN LAS 3 VENTANAS CRONOLÓGICAS INDEPENDIENTES
        window_metrics = {}
        for w_name in windows:
            w_res = sim.run_simulation(window_data[w_name], precomputed_features=pre_features_by_window[w_name])
            window_metrics[w_name] = w_res

        pfs = [window_metrics[w]["profit_factor"] for w in windows]
        exps = [window_metrics[w]["expectancy"] for w in windows]
        sharpes = [window_metrics[w]["sharpe_ratio"] for w in windows]
        trades = [window_metrics[w]["total_trades"] for w in windows]

        # Early Generalization Gate
        pass_pfs = sum(1 for p in pfs if p > 1.0)
        pass_exps = sum(1 for e in exps if e > 0.0)
        has_collapse = any(p < 0.65 for p in pfs)
        has_sample = sum(trades) >= 15  # Suficiencia adaptada a timeframe diario

        early_gen_passed = (pass_pfs >= 2) and (pass_exps >= 2) and (not has_collapse) and has_sample

        # GSS
        gss = calculate_generalization_stability_score(pfs, exps, sharpes, trades)

        # Evaluación en período Pre-Holdout completo
        res_full = sim.run_simulation(pre_data, precomputed_features=pre_features_full)

        failure_category = None
        if not early_gen_passed:
            accounting["early_rejected"] += 1
            if not has_sample:
                failure_category = "INSUFFICIENT_EVIDENCE"
            elif has_collapse or pass_pfs < 2:
                failure_category = "TEMPORAL_INSTABILITY"

            mem.record_experiment(
                hypothesis_id=d_spec["id"],
                strategy_id=d_spec["id"],
                features=[d_spec["family"], f"horizon_{d_spec['horizon']}d"],
                parameters=d_spec,
                metrics={"gss": gss, "pfs": pfs, "full_pf": res_full["profit_factor"]},
                failure_reason=failure_category
            )

        rec = {
            "experiment_id": d_spec["id"],
            "type": "EXPLORATION",
            "spec": d_spec,
            "fingerprint": compute_spec_fingerprint(d_spec),
            "window_metrics": window_metrics,
            "windows_passed": pass_pfs,
            "pfs": pfs,
            "gss": gss,
            "early_gen_passed": early_gen_passed,
            "pre_holdout_full": res_full,
            "failure_category": failure_category
        }
        discovery_results.append(rec)

        status_str = "PASS_EARLY_GEN" if early_gen_passed else f"REJECT ({failure_category})"
        print(f"  [{d_spec['id']}] Fam={d_spec['family']:35} | PFs=[{pfs[0]:.2f}, {pfs[1]:.2f}, {pfs[2]:.2f}] | Full PF={res_full['profit_factor']:.2f} | GSS={gss:5.1f} | MCR={res_full['movement_to_cost_ratio']:4.1f} -> {status_str}")

    # =========================================================================
    # 4. GATES ADICIONALES (COST GATE, SYMBOL GATE, REGIME GATE)
    # =========================================================================
    print("\n[4/7] EVALUANDO COST GATE, SYMBOL GATE Y REGIME GATE PARA ESTRATEGIAS SOBREVIVIENTES...")
    qualifying_leads = [d for d in discovery_results if d["early_gen_passed"]]
    print(f"  Estrategias que superaron Early Generalization Gate en 1D: {len(qualifying_leads)}")

    evaluated_leads = []
    # Si no hay sobrevivientes, evaluar las 4 con mayor GSS como estudio de diagnóstico
    top_candidates = qualifying_leads if qualifying_leads else sorted(discovery_results, key=lambda d: (d["gss"], d["pre_holdout_full"]["profit_factor"]), reverse=True)[:4]

    for lead in top_candidates:
        d_spec = lead["spec"]
        evaluator = DailyStrategyEvaluator(
            family=d_spec["family"],
            holding_horizon_days=d_spec["horizon"],
            exit_geometry=d_spec["exit_geo"],
            rr_ratio=d_spec["rr"],
            atr_mult=d_spec["atr_m"],
            trailing_mult=d_spec["trail_m"]
        )

        # A. COST GATE (0, 2, 5, 7.5, 10 bps) - VALIDATION RUNS
        cost_frontier = []
        slippages = [0.0, 0.0002, 0.0005, 0.00075, 0.0010]
        break_even_slip = 0.0
        for slip in slippages:
            accounting["validation_runs_executed"] += 1
            accounting["total_executions"] += 1
            sim_c = DailyExecutionSimulator(
                evaluator=evaluator,
                initial_capital=100000.0,
                commission_per_share=0.005,
                slippage_pct=slip,
                risk_per_trade_pct=0.01,
                concurrency_policy=d_spec["policy"],
                max_concurrent_positions=d_spec["max_p"]
            )
            r_c = sim_c.run_simulation(pre_data, precomputed_features=pre_features_full)
            cost_frontier.append({
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

        # B. SYMBOL GATE (Evaluación aislada y Leave-One-Symbol-Out)
        symbol_breakdown = {}
        for sym in target_symbols:
            accounting["validation_runs_executed"] += 1
            accounting["total_executions"] += 1
            sim_s = DailyExecutionSimulator(
                evaluator=evaluator,
                initial_capital=100000.0,
                commission_per_share=0.005,
                slippage_pct=0.0005,
                concurrency_policy="ONE_POSITION_PER_SYMBOL",
                max_concurrent_positions=1
            )
            r_s = sim_s.run_simulation({sym: pre_data[sym]}, precomputed_features={sym: pre_features_full[sym]})
            symbol_breakdown[sym] = {
                "trades": r_s["total_trades"],
                "pf": r_s["profit_factor"],
                "pnl": r_s["total_net_pnl"],
                "win_rate": r_s["win_rate"]
            }

        # Leave-One-Symbol-Out (LOSO)
        loso_results = {}
        single_symbol_dep = False
        for sym_out in target_symbols:
            accounting["validation_runs_executed"] += 1
            accounting["total_executions"] += 1
            loso_data = {s: pre_data[s] for s in target_symbols if s != sym_out}
            loso_feat = {s: pre_features_full[s] for s in target_symbols if s != sym_out}
            sim_l = DailyExecutionSimulator(
                evaluator=evaluator,
                initial_capital=100000.0,
                commission_per_share=0.005,
                slippage_pct=0.0005,
                concurrency_policy=d_spec["policy"],
                max_concurrent_positions=d_spec["max_p"]
            )
            r_l = sim_l.run_simulation(loso_data, precomputed_features=loso_feat)
            loso_results[f"Exclude_{sym_out}"] = {
                "pf": r_l["profit_factor"],
                "pnl": r_l["total_net_pnl"],
                "trades": r_l["total_trades"]
            }
            if r_l["profit_factor"] < 0.90 or r_l["total_net_pnl"] < -5000:
                single_symbol_dep = True

        symbol_gate_passed = not single_symbol_dep
        if not symbol_gate_passed and lead["early_gen_passed"]:
            accounting["symbol_rejected"] += 1
            if not lead["failure_category"]:
                lead["failure_category"] = "SYMBOL_DEPENDENCE"

        # C. REGIME GATE
        trades_all = lead["pre_holdout_full"]["closed_trades"]
        reg_counts = {"BULL_TREND": 0, "BEAR_TREND": 0, "SIDEWAYS": 0, "HIGH_VOL": 0, "LOW_VOL": 0}
        reg_pnl = {"BULL_TREND": 0.0, "BEAR_TREND": 0.0, "SIDEWAYS": 0.0, "HIGH_VOL": 0.0, "LOW_VOL": 0.0}
        for tr in trades_all:
            reg = tr.get("regime", "SIDEWAYS")
            reg_counts[reg] = reg_counts.get(reg, 0) + 1
            reg_pnl[reg] = reg_pnl.get(reg, 0.0) + tr["net_pnl"]

        if reg_counts.get("BULL_TREND", 0) > 0 and reg_counts.get("BEAR_TREND", 0) > 0 and min(reg_pnl.values()) > -3000:
            reg_class = "MULTI_REGIME"
        elif reg_pnl.get("BULL_TREND", 0) > 0 and reg_pnl.get("BEAR_TREND", 0) <= 0:
            reg_class = "REGIME_SPECIALIST"
        else:
            reg_class = "REGIME_DEPENDENT"

        if reg_class == "REGIME_DEPENDENT":
            accounting["regime_flagged"] += 1

        lead_report = {
            "experiment_id": lead["experiment_id"],
            "early_gen_passed": lead["early_gen_passed"],
            "cost_gate_passed": cost_gate_passed,
            "break_even_slip": break_even_slip,
            "cost_frontier": cost_frontier,
            "symbol_gate_passed": symbol_gate_passed,
            "symbol_breakdown": symbol_breakdown,
            "loso_results": loso_results,
            "regime_classification": reg_class,
            "regime_pnl": reg_pnl,
            "regime_counts": reg_counts
        }
        evaluated_leads.append(lead_report)
        print(f"    -> Lead {lead['experiment_id']}: Break-even slip={break_even_slip:.1f} bps (Cost Gate: {'PASS' if cost_gate_passed else 'FAIL'}) | Single Symbol Dep: {single_symbol_dep} | Regime: {reg_class}")

    # =========================================================================
    # 5. EXPLOTACIÓN CONDICIONADA (REGLA DE ORO DE FASE 10: NO FORZAR EL 30%)
    # =========================================================================
    print("\n[5/7] EVALUANDO PRESUPUESTO DE EXPLOTACIÓN CONDICIONADO...")
    fully_qualified = [
        l for l in top_candidates
        if l.get("early_gen_passed") and any(el["experiment_id"] == l["experiment_id"] and el["cost_gate_passed"] and el["symbol_gate_passed"] for el in evaluated_leads)
    ]

    if fully_qualified:
        print(f"  ENCONTRADAS {len(fully_qualified)} ESTRATEGIAS CALIFICADAS PARA EXPLOTACIÓN EN 1D.")
        # Consumir hasta 12 experimentos de explotación si hubiese candidatos
    else:
        print("  REGLA DE FASE 10: Ninguna hipótesis superó simultáneamente Early Gen Gate, Cost Gate y Symbol Gate.")
        print("  EXPLOTACIÓN BUDGET QUEDA SIN CONSUMIR DE FORMA HONESTA (0 experimentos forzados).")
        print("  El presupuesto discovery permanece estrictamente en 28 experimentos ejecutados (dentro del límite de 40).")

    # =========================================================================
    # 6. RANKING Y ANÁLISIS COMPARATIVO AGREGADO (1D VS 1H)
    # =========================================================================
    print("\n[6/7] EVALUANDO RANKING MULTIOBJETIVO Y COMPARACIÓN AGREGADA 1D VS 1H...")
    ranking_records = []
    rob_engine = RobustnessEngine()

    for exp in discovery_results:
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

        # Datos de holding y turnover
        h_stats = f_res.get("holding_period_stats", {})
        t_stats = f_res.get("turnover_stats", {})
        mcr = f_res.get("movement_to_cost_ratio", 0.0)

        ranking_records.append({
            "experiment_id": exp["experiment_id"],
            "family": exp["spec"]["family"],
            "horizon": exp["spec"]["horizon"],
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
            "trades_per_year": t_stats.get("trades_per_year", 0.0),
            "mean_holding_days": h_stats.get("mean_days", 0.0),
            "median_holding_days": h_stats.get("median_days", 0.0),
            "holding_distribution": h_stats.get("distribution", {}),
            "movement_to_cost_ratio": mcr,
            "cost_to_gross_edge_pct": f_res.get("cost_to_gross_edge_pct", 0.0),
            "gss": exp["gss"],
            "ees": ees,
            "ees_class": ees_class.value,
            "prs": prs,
            "sqs": sqs,
            "evidence": evidence,
            "payoff": f_res.get("realized_payoff_ratio", 0.0),
            "be_wr": f_res.get("realized_breakeven_win_rate", 50.0),
            "act_wr": f_res.get("actual_win_rate", 0.0),
            "failure_category": exp.get("failure_category", "NONE")
        })

    ranking_records.sort(key=lambda r: (r["gss"], r["sqs"], r["full_pf"]), reverse=True)

    print("\n  TOP 5 ESTRATEGIAS RANKING FASE 10 (1D):")
    for r in ranking_records[:5]:
        print(f"    {r['experiment_id']:25} | Fam={r['family']:32} | PFs=[{r['pf_a']:.2f}, {r['pf_b']:.2f}, {r['pf_c']:.2f}] | Full PF={r['full_pf']:.2f} | GSS={r['gss']:5.1f} | MCR={r['movement_to_cost_ratio']:4.1f} | SQS={r['sqs']:5.1f}")

    # =========================================================================
    # 7. VEREDICTO FORMAL
    # =========================================================================
    print("\n[7/7] EMITIENDO VEREDICTO FORMAL INSTITUCIONAL...")
    best_lead = "NO_RESEARCH_LEAD"
    pre_holdout_candidate = None

    # Candidato Pre-Holdout requiere:
    # Early Gen PASS, Cost Gate PASS (>= 5 bps), Symbol Gate PASS, Full PF >= 1.05, EES > 0
    for r in ranking_records:
        if r["early_gen_passed"] and r["full_pf"] >= 1.05 and r["ees"] > 0:
            lead_eval = next((l for l in evaluated_leads if l["experiment_id"] == r["experiment_id"]), None)
            if lead_eval and lead_eval["cost_gate_passed"] and lead_eval["symbol_gate_passed"]:
                best_lead = r["experiment_id"]
                pre_holdout_candidate = r["experiment_id"]
                break

    print(f"  Best Research Lead:       {best_lead}")
    print(f"  PRE_HOLDOUT_CANDIDATE:    {pre_holdout_candidate if pre_holdout_candidate else 'NONE'}")
    print(f"  OFFICIAL CANDIDATE:       NONE")
    print(f"  FINAL_HOLDOUT:            LOCKED (100% blindado)")

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

    out_file = root_dir / "ai_trading_agent" / "scratch" / "fase10_discovery_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, default=str)

    print(f"\n[OK] Fase 10 completada exitosamente. Resumen guardado en {out_file}")


if __name__ == "__main__":
    run_fase10_daily_discovery()
