"""
run_experiment_fase8.py
=======================
Ejecutor integral de la campaña de investigación experimental de la Fase 8:
Executable Edge Conversion Research.

Presupuesto estricto:
- Máximo 30 experimentos
- 70% Exploración (21 experimentos)
- 30% Explotación (9 experimentos)
- Accounting exacto: Planned, Executed, Skipped, Duplicates.
"""

import sys
import json
import math
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Root setup
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.data.providers.yfinance_provider import YFinanceMarketDataProvider
from ai_trading_agent.strategy_lab.backtesting.data_splitter import LabDataSplitter, DataSplitType
from ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer import (
    DateBasedDataSplitter,
    MultiTimeframeStrategyEvaluator,
    MultiTimeframeBacktestSimulator
)
from ai_trading_agent.strategy_lab.backtesting.execution_aware_simulator import (
    ExecutionAwareStrategyEvaluator,
    ExecutionAwareSimulator,
    FeaturePrecomputer
)
from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import (
    calculate_economic_edge_score,
    calculate_strategy_quality_score,
    classify_statistical_evidence,
    EconomicEdgeClassification,
    StatisticalEvidenceLevel
)


def run_fase8_campaign():
    print("=" * 85)
    print(" INICIANDO FASE 8: EXECUTABLE EDGE CONVERSION RESEARCH")
    print("=" * 85)

    provider = YFinanceMarketDataProvider(fallback_to_synthetic=False)
    target_symbols = ["SPY", "QQQ", "IWM", "DIA"]

    print("\n[1/5] DESCARGANDO DATOS Y CONSTRUYENDO CALENDAR MASTER SPLITS...")
    raw_data: Dict[str, Dict[str, List[OHLCVBar]]] = {"1d": {}, "1h": {}}
    for sym in target_symbols:
        raw_data["1d"][sym] = provider.get_historical_bars(symbol=sym, count=1500, interval="1d")
        raw_data["1h"][sym] = provider.get_historical_bars(symbol=sym, count=6000, interval="1h")

    # Fechas comunes alineadas
    common_start, common_end = DateBasedDataSplitter.find_common_date_range([
        raw_data["1d"]["SPY"],
        raw_data["1h"]["SPY"]
    ])
    splits_cal = DateBasedDataSplitter.create_calendar_splits(common_start, common_end)
    is_start, is_end = splits_cal["in_sample"]
    oos_start, oos_end = splits_cal["out_sample"]
    h_start, h_end = splits_cal["holdout"]

    print(f"  Ventana Maestro (1D/1H): {common_start.strftime('%Y-%m-%d')} -> {common_end.strftime('%Y-%m-%d')}")
    print(f"  IS:  {is_start.strftime('%Y-%m-%d')} -> {is_end.strftime('%Y-%m-%d')}")
    print(f"  OOS: {oos_start.strftime('%Y-%m-%d')} -> {oos_end.strftime('%Y-%m-%d')}")
    print(f"  HOLDOUT (LOCKED 20%): {h_start.strftime('%Y-%m-%d')} -> {h_end.strftime('%Y-%m-%d')}")

    # Separar datos
    data_is: Dict[str, Dict[str, List[OHLCVBar]]] = {}
    data_oos: Dict[str, Dict[str, List[OHLCVBar]]] = {}

    for sym in target_symbols:
        d_split = DateBasedDataSplitter.split_by_dates(raw_data["1d"][sym], is_start, is_end, oos_start, oos_end, h_start, h_end)
        h_split = DateBasedDataSplitter.split_by_dates(raw_data["1h"][sym], is_start, is_end, oos_start, oos_end, h_start, h_end)
        data_is[sym] = {"1d": d_split["in_sample"], "1h": h_split["in_sample"]}
        data_oos[sym] = {"1d": d_split["out_sample"], "1h": h_split["out_sample"]}

    print("  Precalculando matrices técnicas vectorizadas para todos los símbolos...")
    features_is = {sym: FeaturePrecomputer.precompute(data_is[sym]["1h"], data_is[sym]["1d"]) for sym in target_symbols}
    features_oos = {sym: FeaturePrecomputer.precompute(data_oos[sym]["1h"], data_oos[sym]["1d"]) for sym in target_symbols}
    print("  [PASS] Features precalculados exitosamente.")

    print("\n[2/5] EVALUANDO BASELINES HISTÓRICOS (FASE 6, CONFIG_D, BASELINE 1H)...")
    # CONFIG_D baseline en OOS SPY
    eval_cfg_d = MultiTimeframeStrategyEvaluator(config_type="CONFIG_D", parameters={"rvol_threshold": 1.1, "atr_mult": 1.2, "rr_ratio": 3.0})
    sim_cfg_d = MultiTimeframeBacktestSimulator(evaluator=eval_cfg_d, commission_per_share=0.005, slippage_pct=0.0005)
    tr_cfg_d = sim_cfg_d.run_simulation("SPY", data_oos["SPY"]["1h"], data_oos["SPY"]["1d"], min_warmup=30)
    net_cfg_d = sum(t["net_pnl"] for t in tr_cfg_d)
    wins_d = [t for t in tr_cfg_d if t["net_pnl"] > 0]
    losses_d = [t for t in tr_cfg_d if t["net_pnl"] <= 0]
    pf_cfg_d = (sum(t["net_pnl"] for t in wins_d) / max(1e-6, abs(sum(t["net_pnl"] for t in losses_d)))) if losses_d else 0.0

    print(f"  Baseline CONFIG_D (OOS SPY): Trades={len(tr_cfg_d)}, PnL=${net_cfg_d:,.2f}, PF={pf_cfg_d:.2f}")

    # =========================================================================
    # PRESUPUESTO EXPERIMENTAL: 30 EXPERIMENTOS (21 EXPLORACIÓN + 9 EXPLOTACIÓN)
    # =========================================================================
    print("\n[3/5] EJECUTANDO PRESUPUESTO EXPERIMENTAL: 30 EXPERIMENTOS...")
    budget_stats = {
        "planned": 30,
        "executed": 0,
        "skipped": 0,
        "duplicates": 0,
        "exploration": 0,
        "exploitation": 0
    }

    results: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # EXPLORACIÓN: 21 EXPERIMENTOS (Ex01 - Ex21)
    # Variando: Entry Family (6), Context (WITH/WITHOUT 1D), Exit Geometry (5), Concurrency (6)
    # -------------------------------------------------------------------------
    exploration_configs = [
        # Familia 1: trend_continuation
        {"name": "Ex01_TrendCont_With1D_FixedRR_FirstSig", "fam": "trend_continuation", "c1d": True, "exit": "fixed_rr", "rr": 2.5, "conc": "FIRST_SIGNAL"},
        {"name": "Ex02_TrendCont_No1D_FixedRR_FirstSig", "fam": "trend_continuation", "c1d": False, "exit": "fixed_rr", "rr": 2.5, "conc": "FIRST_SIGNAL"},
        {"name": "Ex03_TrendCont_With1D_TrailingATR_BestSig", "fam": "trend_continuation", "c1d": True, "exit": "trailing_atr", "rr": 3.0, "conc": "BEST_SIGNAL"},
        {"name": "Ex04_TrendCont_With1D_PartialExit_Replace", "fam": "trend_continuation", "c1d": True, "exit": "partial_exit", "rr": 3.0, "conc": "REPLACE_IF_STRONGER"},

        # Familia 2: pullback_confirmation
        {"name": "Ex05_PullbackConf_With1D_FixedRR_FirstSig", "fam": "pullback_confirmation", "c1d": True, "exit": "fixed_rr", "rr": 2.5, "conc": "FIRST_SIGNAL"},
        {"name": "Ex06_PullbackConf_No1D_FixedRR_FirstSig", "fam": "pullback_confirmation", "c1d": False, "exit": "fixed_rr", "rr": 2.5, "conc": "FIRST_SIGNAL"},
        {"name": "Ex07_PullbackConf_With1D_TimeStop_BestSig", "fam": "pullback_confirmation", "c1d": True, "exit": "time_stop", "rr": 2.0, "conc": "BEST_SIGNAL"},
        {"name": "Ex08_PullbackConf_With1D_TrailingATR_Replace", "fam": "pullback_confirmation", "c1d": True, "exit": "trailing_atr", "rr": 3.0, "conc": "REPLACE_IF_STRONGER"},

        # Familia 3: breakout_retest
        {"name": "Ex09_BreakoutRet_With1D_FixedRR_FirstSig", "fam": "breakout_retest", "c1d": True, "exit": "fixed_rr", "rr": 2.5, "conc": "FIRST_SIGNAL"},
        {"name": "Ex10_BreakoutRet_No1D_FixedRR_FirstSig", "fam": "breakout_retest", "c1d": False, "exit": "fixed_rr", "rr": 2.5, "conc": "FIRST_SIGNAL"},
        {"name": "Ex11_BreakoutRet_With1D_PartialExit_Queue", "fam": "breakout_retest", "c1d": True, "exit": "partial_exit", "rr": 3.0, "conc": "QUEUE_NEXT_SIGNAL"},

        # Familia 4: volatility_expansion
        {"name": "Ex12_VolExpand_With1D_FixedRR_FirstSig", "fam": "volatility_expansion", "c1d": True, "exit": "fixed_rr", "rr": 2.5, "conc": "FIRST_SIGNAL"},
        {"name": "Ex13_VolExpand_No1D_FixedRR_FirstSig", "fam": "volatility_expansion", "c1d": False, "exit": "fixed_rr", "rr": 2.5, "conc": "FIRST_SIGNAL"},
        {"name": "Ex14_VolExpand_With1D_TimeStop_Replace", "fam": "volatility_expansion", "c1d": True, "exit": "time_stop", "rr": 2.5, "conc": "REPLACE_IF_STRONGER"},

        # Familia 5: momentum_persistence
        {"name": "Ex15_MomPersist_With1D_FixedRR_FirstSig", "fam": "momentum_persistence", "c1d": True, "exit": "fixed_rr", "rr": 2.5, "conc": "FIRST_SIGNAL"},
        {"name": "Ex16_MomPersist_No1D_FixedRR_FirstSig", "fam": "momentum_persistence", "c1d": False, "exit": "fixed_rr", "rr": 2.5, "conc": "FIRST_SIGNAL"},
        {"name": "Ex17_MomPersist_With1D_TrailingATR_BestSig", "fam": "momentum_persistence", "c1d": True, "exit": "trailing_atr", "rr": 3.0, "conc": "BEST_SIGNAL"},
        {"name": "Ex18_MomPersist_With1D_PartialExit_FirstSig", "fam": "momentum_persistence", "c1d": True, "exit": "partial_exit", "rr": 2.5, "conc": "FIRST_SIGNAL"},

        # Familia 6: failed_breakout_reversal
        {"name": "Ex19_FailedBreakRev_With1D_FixedRR_FirstSig", "fam": "failed_breakout_reversal", "c1d": True, "exit": "fixed_rr", "rr": 2.0, "conc": "FIRST_SIGNAL"},
        {"name": "Ex20_FailedBreakRev_No1D_FixedRR_FirstSig", "fam": "failed_breakout_reversal", "c1d": False, "exit": "fixed_rr", "rr": 2.0, "conc": "FIRST_SIGNAL"},
        {"name": "Ex21_FailedBreakRev_With1D_TimeStop_BestSig", "fam": "failed_breakout_reversal", "c1d": True, "exit": "time_stop", "rr": 2.0, "conc": "BEST_SIGNAL"}
    ]

    for cfg in exploration_configs:
        budget_stats["executed"] += 1
        budget_stats["exploration"] += 1

        evaluator = ExecutionAwareStrategyEvaluator(
            entry_family=cfg["fam"],
            use_1d_context=cfg["c1d"],
            exit_geometry=cfg["exit"],
            rr_ratio=cfg["rr"]
        )
        sim_is = ExecutionAwareSimulator(
            evaluator=evaluator,
            concurrency_policy=cfg["conc"],
            commission_per_share=0.005,
            slippage_pct=0.0005
        )
        sim_oos = ExecutionAwareSimulator(
            evaluator=evaluator,
            concurrency_policy=cfg["conc"],
            commission_per_share=0.005,
            slippage_pct=0.0005
        )

        res_is = sim_is.run_simulation({"SPY": data_is["SPY"]}, precomputed_features={"SPY": features_is["SPY"]})
        res_oos = sim_oos.run_simulation({"SPY": data_oos["SPY"]}, precomputed_features={"SPY": features_oos["SPY"]})

        ees_score, ees_class = calculate_economic_edge_score(
            profit_factor=res_oos["profit_factor"],
            expectancy=res_oos["expectancy"],
            is_sharpe=res_is["sharpe_ratio"],
            oos_sharpe=res_oos["sharpe_ratio"],
            trade_count=res_oos["total_trades"]
        )
        evidence_level = classify_statistical_evidence(res_oos["total_trades"])

        results.append({
            "id": cfg["name"],
            "type": "EXPLORATION",
            "family": cfg["fam"],
            "context_1d": cfg["c1d"],
            "exit_geometry": cfg["exit"],
            "concurrency": cfg["conc"],
            "symbol": "SPY",
            "stress": "BASELINE",
            "is_trades": res_is["total_trades"],
            "is_pf": res_is["profit_factor"],
            "is_sharpe": res_is["sharpe_ratio"],
            "is_pnl": res_is["total_net_pnl"],
            "oos_trades": res_oos["total_trades"],
            "oos_pf": res_oos["profit_factor"],
            "oos_sharpe": res_oos["sharpe_ratio"],
            "oos_pnl": res_oos["total_net_pnl"],
            "oos_wr": res_oos["win_rate"],
            "realized_payoff": res_oos["realized_payoff_ratio"],
            "breakeven_wr": res_oos["realized_breakeven_win_rate"],
            "ees_score": ees_score,
            "ees_class": ees_class.value,
            "evidence": evidence_level.value,
            "overlap_rate": res_oos["overlap_rate"]
        })
        print(f"  [{budget_stats['executed']:02d}/30] {cfg['name']} -> IS PF={res_is['profit_factor']:.2f} | OOS PF={res_oos['profit_factor']:.2f} | OOS PnL=${res_oos['total_net_pnl']:,.2f} | Payoff={res_oos['realized_payoff_ratio']:.2f} | EES={ees_score} ({ees_class.value})")

    # Identificar la mejor rama de exploración
    valid_leads = [r for r in results if r["oos_trades"] >= 15]
    best_lead = max(valid_leads, key=lambda r: (r["oos_pf"], r["oos_sharpe"])) if valid_leads else results[0]
    lead_fam = best_lead["family"]
    lead_exit = best_lead["exit_geometry"]
    print(f"\n  ==> MEJOR LEAD DE EXPLORACIÓN: {best_lead['id']} (Fam: {lead_fam}, Exit: {lead_exit}, OOS PF: {best_lead['oos_pf']:.2f})")

    # -------------------------------------------------------------------------
    # EXPLOTACIÓN: 9 EXPERIMENTOS (Ex22 - Ex30)
    # Profundización sobre el lead líder:
    # 1. Stress de costos: Baseline, Normal Stress (10 bps, $0.01), High Stress (20 bps, $0.02) (Ex22, Ex23)
    # 2. Concurrencia de cartera multi-símbolo (SPY, QQQ, IWM, DIA) (Ex24, Ex25, Ex26)
    # 3. Prueba de generalización cruzada en QQQ, IWM, DIA individuales (Ex27, Ex28, Ex29)
    # 4. Walk-Forward window validation (Ex30)
    # -------------------------------------------------------------------------
    # Ex22: Normal Cost Stress (10 bps slippage, $0.01 comm) en SPY
    budget_stats["executed"] += 1
    budget_stats["exploitation"] += 1
    eval_lead = ExecutionAwareStrategyEvaluator(entry_family=lead_fam, use_1d_context=True, exit_geometry=lead_exit, rr_ratio=2.5)
    sim_normal_stress = ExecutionAwareSimulator(evaluator=eval_lead, commission_per_share=0.010, slippage_pct=0.0010)
    r_is_ns = sim_normal_stress.run_simulation({"SPY": data_is["SPY"]}, precomputed_features={"SPY": features_is["SPY"]})
    r_oos_ns = sim_normal_stress.run_simulation({"SPY": data_oos["SPY"]}, precomputed_features={"SPY": features_oos["SPY"]})
    ees_ns, ees_c_ns = calculate_economic_edge_score(r_oos_ns["profit_factor"], r_oos_ns["expectancy"], r_is_ns["sharpe_ratio"], r_oos_ns["sharpe_ratio"], r_oos_ns["total_trades"])
    results.append({
        "id": "Ex22_Lead_NormalCostStress_SPY", "type": "EXPLOITATION", "family": lead_fam, "context_1d": True, "exit_geometry": lead_exit,
        "concurrency": "FIRST_SIGNAL", "symbol": "SPY", "stress": "NORMAL_STRESS",
        "is_trades": r_is_ns["total_trades"], "is_pf": r_is_ns["profit_factor"], "is_sharpe": r_is_ns["sharpe_ratio"], "is_pnl": r_is_ns["total_net_pnl"],
        "oos_trades": r_oos_ns["total_trades"], "oos_pf": r_oos_ns["profit_factor"], "oos_sharpe": r_oos_ns["sharpe_ratio"], "oos_pnl": r_oos_ns["total_net_pnl"],
        "oos_wr": r_oos_ns["win_rate"], "realized_payoff": r_oos_ns["realized_payoff_ratio"], "breakeven_wr": r_oos_ns["realized_breakeven_win_rate"],
        "ees_score": ees_ns, "ees_class": ees_c_ns.value, "evidence": classify_statistical_evidence(r_oos_ns["total_trades"]).value, "overlap_rate": r_oos_ns["overlap_rate"]
    })
    print(f"  [{budget_stats['executed']:02d}/30] Ex22_Lead_NormalCostStress_SPY -> OOS PF={r_oos_ns['profit_factor']:.2f} | PnL=${r_oos_ns['total_net_pnl']:,.2f}")

    # Ex23: High Cost Stress (20 bps slippage, $0.02 comm) en SPY
    budget_stats["executed"] += 1
    budget_stats["exploitation"] += 1
    sim_high_stress = ExecutionAwareSimulator(evaluator=eval_lead, commission_per_share=0.020, slippage_pct=0.0020)
    r_is_hs = sim_high_stress.run_simulation({"SPY": data_is["SPY"]}, precomputed_features={"SPY": features_is["SPY"]})
    r_oos_hs = sim_high_stress.run_simulation({"SPY": data_oos["SPY"]}, precomputed_features={"SPY": features_oos["SPY"]})
    ees_hs, ees_c_hs = calculate_economic_edge_score(r_oos_hs["profit_factor"], r_oos_hs["expectancy"], r_is_hs["sharpe_ratio"], r_oos_hs["sharpe_ratio"], r_oos_hs["total_trades"])
    results.append({
        "id": "Ex23_Lead_HighCostStress_SPY", "type": "EXPLOITATION", "family": lead_fam, "context_1d": True, "exit_geometry": lead_exit,
        "concurrency": "FIRST_SIGNAL", "symbol": "SPY", "stress": "HIGH_STRESS",
        "is_trades": r_is_hs["total_trades"], "is_pf": r_is_hs["profit_factor"], "is_sharpe": r_is_hs["sharpe_ratio"], "is_pnl": r_is_hs["total_net_pnl"],
        "oos_trades": r_oos_hs["total_trades"], "oos_pf": r_oos_hs["profit_factor"], "oos_sharpe": r_oos_hs["sharpe_ratio"], "oos_pnl": r_oos_hs["total_net_pnl"],
        "oos_wr": r_oos_hs["win_rate"], "realized_payoff": r_oos_hs["realized_payoff_ratio"], "breakeven_wr": r_oos_hs["realized_breakeven_win_rate"],
        "ees_score": ees_hs, "ees_class": ees_c_hs.value, "evidence": classify_statistical_evidence(r_oos_hs["total_trades"]).value, "overlap_rate": r_oos_hs["overlap_rate"]
    })
    print(f"  [{budget_stats['executed']:02d}/30] Ex23_Lead_HighCostStress_SPY -> OOS PF={r_oos_hs['profit_factor']:.2f} | PnL=${r_oos_hs['total_net_pnl']:,.2f}")

    # Ex24: Multi-Symbol Portfolio (ONE_POSITION_GLOBAL)
    budget_stats["executed"] += 1
    budget_stats["exploitation"] += 1
    sim_multi_global = ExecutionAwareSimulator(evaluator=eval_lead, concurrency_policy="ONE_POSITION_GLOBAL", max_concurrent_positions=1)
    r_is_mg = sim_multi_global.run_simulation(data_is, precomputed_features=features_is)
    r_oos_mg = sim_multi_global.run_simulation(data_oos, precomputed_features=features_oos)
    ees_mg, ees_c_mg = calculate_economic_edge_score(r_oos_mg["profit_factor"], r_oos_mg["expectancy"], r_is_mg["sharpe_ratio"], r_oos_mg["sharpe_ratio"], r_oos_mg["total_trades"])
    results.append({
        "id": "Ex24_Lead_MultiSymbol_OneGlobal", "type": "EXPLOITATION", "family": lead_fam, "context_1d": True, "exit_geometry": lead_exit,
        "concurrency": "ONE_POSITION_GLOBAL", "symbol": "PORTFOLIO_4", "stress": "BASELINE",
        "is_trades": r_is_mg["total_trades"], "is_pf": r_is_mg["profit_factor"], "is_sharpe": r_is_mg["sharpe_ratio"], "is_pnl": r_is_mg["total_net_pnl"],
        "oos_trades": r_oos_mg["total_trades"], "oos_pf": r_oos_mg["profit_factor"], "oos_sharpe": r_oos_mg["sharpe_ratio"], "oos_pnl": r_oos_mg["total_net_pnl"],
        "oos_wr": r_oos_mg["win_rate"], "realized_payoff": r_oos_mg["realized_payoff_ratio"], "breakeven_wr": r_oos_mg["realized_breakeven_win_rate"],
        "ees_score": ees_mg, "ees_class": ees_c_mg.value, "evidence": classify_statistical_evidence(r_oos_mg["total_trades"]).value, "overlap_rate": r_oos_mg["overlap_rate"]
    })
    print(f"  [{budget_stats['executed']:02d}/30] Ex24_Lead_MultiSymbol_OneGlobal -> OOS PF={r_oos_mg['profit_factor']:.2f} | PnL=${r_oos_mg['total_net_pnl']:,.2f}")

    # Ex25: Multi-Symbol Portfolio (ONE_POSITION_PER_SYMBOL)
    budget_stats["executed"] += 1
    budget_stats["exploitation"] += 1
    sim_multi_sym = ExecutionAwareSimulator(evaluator=eval_lead, concurrency_policy="ONE_POSITION_PER_SYMBOL", max_concurrent_positions=4)
    r_is_ms = sim_multi_sym.run_simulation(data_is, precomputed_features=features_is)
    r_oos_ms = sim_multi_sym.run_simulation(data_oos, precomputed_features=features_oos)
    ees_ms, ees_c_ms = calculate_economic_edge_score(r_oos_ms["profit_factor"], r_oos_ms["expectancy"], r_is_ms["sharpe_ratio"], r_oos_ms["sharpe_ratio"], r_oos_ms["total_trades"])
    results.append({
        "id": "Ex25_Lead_MultiSymbol_OnePerSymbol", "type": "EXPLOITATION", "family": lead_fam, "context_1d": True, "exit_geometry": lead_exit,
        "concurrency": "ONE_POSITION_PER_SYMBOL", "symbol": "PORTFOLIO_4", "stress": "BASELINE",
        "is_trades": r_is_ms["total_trades"], "is_pf": r_is_ms["profit_factor"], "is_sharpe": r_is_ms["sharpe_ratio"], "is_pnl": r_is_ms["total_net_pnl"],
        "oos_trades": r_oos_ms["total_trades"], "oos_pf": r_oos_ms["profit_factor"], "oos_sharpe": r_oos_ms["sharpe_ratio"], "oos_pnl": r_oos_ms["total_net_pnl"],
        "oos_wr": r_oos_ms["win_rate"], "realized_payoff": r_oos_ms["realized_payoff_ratio"], "breakeven_wr": r_oos_ms["realized_breakeven_win_rate"],
        "ees_score": ees_ms, "ees_class": ees_c_ms.value, "evidence": classify_statistical_evidence(r_oos_ms["total_trades"]).value, "overlap_rate": r_oos_ms["overlap_rate"]
    })
    print(f"  [{budget_stats['executed']:02d}/30] Ex25_Lead_MultiSymbol_OnePerSymbol -> OOS PF={r_oos_ms['profit_factor']:.2f} | PnL=${r_oos_ms['total_net_pnl']:,.2f}")

    # Ex26: Multi-Symbol con REPLACE_IF_STRONGER
    budget_stats["executed"] += 1
    budget_stats["exploitation"] += 1
    sim_multi_rep = ExecutionAwareSimulator(evaluator=eval_lead, concurrency_policy="REPLACE_IF_STRONGER", max_concurrent_positions=2)
    r_is_mr = sim_multi_rep.run_simulation(data_is, precomputed_features=features_is)
    r_oos_mr = sim_multi_rep.run_simulation(data_oos, precomputed_features=features_oos)
    ees_mr, ees_c_mr = calculate_economic_edge_score(r_oos_mr["profit_factor"], r_oos_mr["expectancy"], r_is_mr["sharpe_ratio"], r_oos_mr["sharpe_ratio"], r_oos_mr["total_trades"])
    results.append({
        "id": "Ex26_Lead_MultiSymbol_ReplaceStronger", "type": "EXPLOITATION", "family": lead_fam, "context_1d": True, "exit_geometry": lead_exit,
        "concurrency": "REPLACE_IF_STRONGER", "symbol": "PORTFOLIO_4", "stress": "BASELINE",
        "is_trades": r_is_mr["total_trades"], "is_pf": r_is_mr["profit_factor"], "is_sharpe": r_is_mr["sharpe_ratio"], "is_pnl": r_is_mr["total_net_pnl"],
        "oos_trades": r_oos_mr["total_trades"], "oos_pf": r_oos_mr["profit_factor"], "oos_sharpe": r_oos_mr["sharpe_ratio"], "oos_pnl": r_oos_mr["total_net_pnl"],
        "oos_wr": r_oos_mr["win_rate"], "realized_payoff": r_oos_mr["realized_payoff_ratio"], "breakeven_wr": r_oos_mr["realized_breakeven_win_rate"],
        "ees_score": ees_mr, "ees_class": ees_c_mr.value, "evidence": classify_statistical_evidence(r_oos_mr["total_trades"]).value, "overlap_rate": r_oos_mr["overlap_rate"]
    })
    print(f"  [{budget_stats['executed']:02d}/30] Ex26_Lead_MultiSymbol_ReplaceStronger -> OOS PF={r_oos_mr['profit_factor']:.2f} | PnL=${r_oos_mr['total_net_pnl']:,.2f}")

    # Ex27: Validación en QQQ individual
    budget_stats["executed"] += 1
    budget_stats["exploitation"] += 1
    sim_base = ExecutionAwareSimulator(evaluator=eval_lead)
    r_is_qqq = sim_base.run_simulation({"QQQ": data_is["QQQ"]}, precomputed_features={"QQQ": features_is["QQQ"]})
    r_oos_qqq = sim_base.run_simulation({"QQQ": data_oos["QQQ"]}, precomputed_features={"QQQ": features_oos["QQQ"]})
    ees_qqq, ees_c_qqq = calculate_economic_edge_score(r_oos_qqq["profit_factor"], r_oos_qqq["expectancy"], r_is_qqq["sharpe_ratio"], r_oos_qqq["sharpe_ratio"], r_oos_qqq["total_trades"])
    results.append({
        "id": "Ex27_Lead_Validation_QQQ", "type": "EXPLOITATION", "family": lead_fam, "context_1d": True, "exit_geometry": lead_exit,
        "concurrency": "FIRST_SIGNAL", "symbol": "QQQ", "stress": "BASELINE",
        "is_trades": r_is_qqq["total_trades"], "is_pf": r_is_qqq["profit_factor"], "is_sharpe": r_is_qqq["sharpe_ratio"], "is_pnl": r_is_qqq["total_net_pnl"],
        "oos_trades": r_oos_qqq["total_trades"], "oos_pf": r_oos_qqq["profit_factor"], "oos_sharpe": r_oos_qqq["sharpe_ratio"], "oos_pnl": r_oos_qqq["total_net_pnl"],
        "oos_wr": r_oos_qqq["win_rate"], "realized_payoff": r_oos_qqq["realized_payoff_ratio"], "breakeven_wr": r_oos_qqq["realized_breakeven_win_rate"],
        "ees_score": ees_qqq, "ees_class": ees_c_qqq.value, "evidence": classify_statistical_evidence(r_oos_qqq["total_trades"]).value, "overlap_rate": r_oos_qqq["overlap_rate"]
    })
    print(f"  [{budget_stats['executed']:02d}/30] Ex27_Lead_Validation_QQQ -> OOS PF={r_oos_qqq['profit_factor']:.2f} | PnL=${r_oos_qqq['total_net_pnl']:,.2f}")

    # Ex28: Validación en IWM individual
    budget_stats["executed"] += 1
    budget_stats["exploitation"] += 1
    r_is_iwm = sim_base.run_simulation({"IWM": data_is["IWM"]}, precomputed_features={"IWM": features_is["IWM"]})
    r_oos_iwm = sim_base.run_simulation({"IWM": data_oos["IWM"]}, precomputed_features={"IWM": features_oos["IWM"]})
    ees_iwm, ees_c_iwm = calculate_economic_edge_score(r_oos_iwm["profit_factor"], r_oos_iwm["expectancy"], r_is_iwm["sharpe_ratio"], r_oos_iwm["sharpe_ratio"], r_oos_iwm["total_trades"])
    results.append({
        "id": "Ex28_Lead_Validation_IWM", "type": "EXPLOITATION", "family": lead_fam, "context_1d": True, "exit_geometry": lead_exit,
        "concurrency": "FIRST_SIGNAL", "symbol": "IWM", "stress": "BASELINE",
        "is_trades": r_is_iwm["total_trades"], "is_pf": r_is_iwm["profit_factor"], "is_sharpe": r_is_iwm["sharpe_ratio"], "is_pnl": r_is_iwm["total_net_pnl"],
        "oos_trades": r_oos_iwm["total_trades"], "oos_pf": r_oos_iwm["profit_factor"], "oos_sharpe": r_oos_iwm["sharpe_ratio"], "oos_pnl": r_oos_iwm["total_net_pnl"],
        "oos_wr": r_oos_iwm["win_rate"], "realized_payoff": r_oos_iwm["realized_payoff_ratio"], "breakeven_wr": r_oos_iwm["realized_breakeven_win_rate"],
        "ees_score": ees_iwm, "ees_class": ees_c_iwm.value, "evidence": classify_statistical_evidence(r_oos_iwm["total_trades"]).value, "overlap_rate": r_oos_iwm["overlap_rate"]
    })
    print(f"  [{budget_stats['executed']:02d}/30] Ex28_Lead_Validation_IWM -> OOS PF={r_oos_iwm['profit_factor']:.2f} | PnL=${r_oos_iwm['total_net_pnl']:,.2f}")

    # Ex29: Validación en DIA individual
    budget_stats["executed"] += 1
    budget_stats["exploitation"] += 1
    r_is_dia = sim_base.run_simulation({"DIA": data_is["DIA"]}, precomputed_features={"DIA": features_is["DIA"]})
    r_oos_dia = sim_base.run_simulation({"DIA": data_oos["DIA"]}, precomputed_features={"DIA": features_oos["DIA"]})
    ees_dia, ees_c_dia = calculate_economic_edge_score(r_oos_dia["profit_factor"], r_oos_dia["expectancy"], r_is_dia["sharpe_ratio"], r_oos_dia["sharpe_ratio"], r_oos_dia["total_trades"])
    results.append({
        "id": "Ex29_Lead_Validation_DIA", "type": "EXPLOITATION", "family": lead_fam, "context_1d": True, "exit_geometry": lead_exit,
        "concurrency": "FIRST_SIGNAL", "symbol": "DIA", "stress": "BASELINE",
        "is_trades": r_is_dia["total_trades"], "is_pf": r_is_dia["profit_factor"], "is_sharpe": r_is_dia["sharpe_ratio"], "is_pnl": r_is_dia["total_net_pnl"],
        "oos_trades": r_oos_dia["total_trades"], "oos_pf": r_oos_dia["profit_factor"], "oos_sharpe": r_oos_dia["sharpe_ratio"], "oos_pnl": r_oos_dia["total_net_pnl"],
        "oos_wr": r_oos_dia["win_rate"], "realized_payoff": r_oos_dia["realized_payoff_ratio"], "breakeven_wr": r_oos_dia["realized_breakeven_win_rate"],
        "ees_score": ees_dia, "ees_class": ees_c_dia.value, "evidence": classify_statistical_evidence(r_oos_dia["total_trades"]).value, "overlap_rate": r_oos_dia["overlap_rate"]
    })
    print(f"  [{budget_stats['executed']:02d}/30] Ex29_Lead_Validation_DIA -> OOS PF={r_oos_dia['profit_factor']:.2f} | PnL=${r_oos_dia['total_net_pnl']:,.2f}")

    # Ex30: Walk-Forward Rolling Windows Validation
    budget_stats["executed"] += 1
    budget_stats["exploitation"] += 1
    wf_trades = []
    # Generar ventanas walk-forward sobre SPY
    wf_half = len(data_is["SPY"]["1h"]) // 2
    wf_w1 = data_is["SPY"]["1h"][:wf_half]
    wf_w2 = data_is["SPY"]["1h"][wf_half:]
    wf_f1 = FeaturePrecomputer.precompute(wf_w1, data_is["SPY"]["1d"])
    wf_f2 = FeaturePrecomputer.precompute(wf_w2, data_is["SPY"]["1d"])
    r_wf1 = sim_base.run_simulation({"SPY": {"1h": wf_w1, "1d": data_is["SPY"]["1d"]}}, precomputed_features={"SPY": wf_f1})
    r_wf2 = sim_base.run_simulation({"SPY": {"1h": wf_w2, "1d": data_is["SPY"]["1d"]}}, precomputed_features={"SPY": wf_f2})
    wf_trades_total = r_wf1["total_trades"] + r_wf2["total_trades"]
    wf_net_total = r_wf1["total_net_pnl"] + r_wf2["total_net_pnl"]
    wf_wins = r_wf1["win_rate"] * 0.5 + r_wf2["win_rate"] * 0.5
    wf_pf = round((r_wf1["profit_factor"] + r_wf2["profit_factor"]) / 2.0, 2)
    ees_wf, ees_c_wf = calculate_economic_edge_score(wf_pf, wf_net_total / max(1, wf_trades_total), r_wf1["sharpe_ratio"], r_wf2["sharpe_ratio"], wf_trades_total)
    results.append({
        "id": "Ex30_Lead_WalkForward_Validation", "type": "EXPLOITATION", "family": lead_fam, "context_1d": True, "exit_geometry": lead_exit,
        "concurrency": "FIRST_SIGNAL", "symbol": "SPY", "stress": "BASELINE",
        "is_trades": r_wf1["total_trades"], "is_pf": r_wf1["profit_factor"], "is_sharpe": r_wf1["sharpe_ratio"], "is_pnl": r_wf1["total_net_pnl"],
        "oos_trades": r_wf2["total_trades"], "oos_pf": r_wf2["profit_factor"], "oos_sharpe": r_wf2["sharpe_ratio"], "oos_pnl": r_wf2["total_net_pnl"],
        "oos_wr": wf_wins, "realized_payoff": r_wf2["realized_payoff_ratio"], "breakeven_wr": r_wf2["realized_breakeven_win_rate"],
        "ees_score": ees_wf, "ees_class": ees_c_wf.value, "evidence": classify_statistical_evidence(wf_trades_total).value, "overlap_rate": r_wf2["overlap_rate"]
    })
    print(f"  [{budget_stats['executed']:02d}/30] Ex30_Lead_WalkForward_Validation -> WF PF={wf_pf:.2f} | PnL=${wf_net_total:,.2f}")

    # Guardar resultados en JSON para inspección e informe
    summary_path = root_dir / "ai_trading_agent" / "scratch" / "fase8_results_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "budget": budget_stats,
            "results": results
        }, f, indent=2)

    print("\n[4/5] CONTABILIDAD EXACTA DEL PRESUPUESTO:")
    print(f"  Planificados: {budget_stats['planned']}")
    print(f"  Ejecutados:   {budget_stats['executed']}")
    print(f"  Omitidos:     {budget_stats['skipped']}")
    print(f"  Duplicados:   {budget_stats['duplicates']}")
    print(f"  Exploración:  {budget_stats['exploration']} ({budget_stats['exploration']/budget_stats['executed']*100:.1f}%)")
    print(f"  Explotación:  {budget_stats['exploitation']} ({budget_stats['exploitation']/budget_stats['executed']*100:.1f}%)")

    # [5/5] CANDIDATE GATING & VEREDICTO FINAL
    print("\n[5/5] EVALUACIÓN DE CANDIDATE GATING Y VEREDICTO FINAL:")
    positive_edge_strats = [r for r in results if r["ees_class"] == "POSITIVE_EDGE" and r["oos_pf"] >= 1.25 and r["oos_pnl"] > 0]
    print(f"  Estrategias con POSITIVE_EDGE y PF >= 1.25 en OOS: {len(positive_edge_strats)}")
    if positive_edge_strats:
        print("  [RESULTADO] Estrategia candidata encontrada!")
    else:
        print("  [RESULTADO] CANDIDATE = NONE. Ninguna estrategia supera las fricciones institucionales con POSITIVE_EDGE.")


if __name__ == "__main__":
    run_fase8_campaign()
