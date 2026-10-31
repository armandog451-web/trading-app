"""
ai_trading_agent.strategy_lab.experiments.exp_mtf01.run_baseline_and_ablations
==============================================================================
Ejecutor de la Campaña Baseline y Estudios de Ablación para EXP-MTF01.
"""

import os
import sys
import json
import pandas as pd
import numpy as np

sys.path.insert(0, r"C:\Users\edsel\Documents\trading-app-repo")

from ai_trading_agent.strategy_lab.experiments.exp_mtf01.daily_context_engine import DailyContextEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.market_structure_engine import MarketStructureEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.fibonacci_confluence_engine import FibonacciConfluenceEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.m5_entry_engine import M5EntryEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.causal_mtf_synchronizer import CausalMTFSynchronizer
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.mtf_backtester import MTFBacktester

data_dir = r"C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\data"
symbols = ["SPY", "QQQ", "DIA", "IWM", "GLD", "TLT"]

def load_data(sym: str):
    df_d1 = pd.read_csv(os.path.join(data_dir, f"{sym}_1d.csv"), index_col=0, parse_dates=True)
    df_h1 = pd.read_csv(os.path.join(data_dir, f"{sym}_1h.csv"), index_col=0, parse_dates=True)
    df_m5 = pd.read_csv(os.path.join(data_dir, f"{sym}_5m.csv"), index_col=0, parse_dates=True)
    return df_d1, df_h1, df_m5

def run_experiment_suite():
    backtester = MTFBacktester()
    baseline_rows = []
    all_trade_ledgers = {}

    print("=== RUNNING BASELINE A (Full MTF System) ===")
    sync_full = CausalMTFSynchronizer(
        enable_d1_filter=True,
        enable_fib_filter=True,
        enable_ema_filter=True,
        enable_m5_filter=True
    )

    for sym in symbols:
        print(f"Processing Baseline for {sym}...")
        df_d1, df_h1, df_m5 = load_data(sym)
        d1_feat, h1_feat, m5_feat = sync_full.prepare_data(df_d1, df_h1, df_m5)
        signals = sync_full.run_synchronization(d1_feat, h1_feat, m5_feat)
        print(f"  {sym}: Generated {len(signals)} signals.")

        # Variant V1A: Structure Target
        res_v1a = backtester.run_simulation(signals, df_m5, tp_variant="V1A")
        # Variant V1B: Fixed 2.0R Target
        res_v1b = backtester.run_simulation(signals, df_m5, tp_variant="V1B")

        all_trade_ledgers[f"{sym}_V1A"] = res_v1a["trades"]
        all_trade_ledgers[f"{sym}_V1B"] = res_v1b["trades"]

        baseline_rows.append({
            "Symbol": sym,
            "Variant": "MTF_V1A_Structure",
            "Signals": len(signals),
            "Trades": res_v1a["total_trades"],
            "Net_PnL": res_v1a["net_pnl"],
            "Win_Rate": res_v1a["win_rate"],
            "Profit_Factor": res_v1a["profit_factor"],
            "Expectancy_R": res_v1a["expectancy_r"],
            "Max_Drawdown_Pct": res_v1a["max_drawdown_pct"],
            "Final_Equity": res_v1a["final_equity"]
        })

        baseline_rows.append({
            "Symbol": sym,
            "Variant": "MTF_V1B_Fixed_2R",
            "Signals": len(signals),
            "Trades": res_v1b["total_trades"],
            "Net_PnL": res_v1b["net_pnl"],
            "Win_Rate": res_v1b["win_rate"],
            "Profit_Factor": res_v1b["profit_factor"],
            "Expectancy_R": res_v1b["expectancy_r"],
            "Max_Drawdown_Pct": res_v1b["max_drawdown_pct"],
            "Final_Equity": res_v1b["final_equity"]
        })

    df_baseline = pd.DataFrame(baseline_rows)
    baseline_csv_path = r"C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\EXP_MTF01_BASELINE_RESULTS.csv"
    df_baseline.to_csv(baseline_csv_path, index=False)
    print("Baseline results saved to EXP_MTF01_BASELINE_RESULTS.csv")

    # Save detailed ledgers
    with open(r"C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\baseline_trade_ledgers.json", "w", encoding="utf-8") as f:
        json.dump(all_trade_ledgers, f, indent=2)

    # === ABLATION STUDIES ===
    print("\n=== RUNNING CONTROLLED ABLATIONS ===")
    ablations = [
        {"name": "Baseline_A_Full", "d1": True, "fib": True, "ema": True, "m5": True},
        {"name": "Ablation_B_No_D1", "d1": False, "fib": True, "ema": True, "m5": True},
        {"name": "Ablation_C_No_Fib", "d1": True, "fib": False, "ema": True, "m5": True},
        {"name": "Ablation_D_No_EMA50", "d1": True, "fib": True, "ema": False, "m5": True},
        {"name": "Ablation_E_No_M5", "d1": True, "fib": True, "ema": True, "m5": False},
    ]

    ablation_summary = []

    for ab in ablations:
        ab_name = ab["name"]
        print(f"Testing {ab_name}...")
        sync_ab = CausalMTFSynchronizer(
            enable_d1_filter=ab["d1"],
            enable_fib_filter=ab["fib"],
            enable_ema_filter=ab["ema"],
            enable_m5_filter=ab["m5"]
        )

        total_signals = 0
        total_trades = 0
        total_pnl = 0.0
        all_r = []
        wins = 0

        for sym in symbols:
            df_d1, df_h1, df_m5 = load_data(sym)
            d1_feat, h1_feat, m5_feat = sync_ab.prepare_data(df_d1, df_h1, df_m5)
            sigs = sync_ab.run_synchronization(d1_feat, h1_feat, m5_feat)
            res = backtester.run_simulation(sigs, df_m5, tp_variant="V1B")

            total_signals += len(sigs)
            total_trades += res["total_trades"]
            total_pnl += res["net_pnl"]
            for t in res["trades"]:
                all_r.append(t["r_return"])
                if t["net_pnl"] > 0:
                    wins += 1

        win_rate = (wins / total_trades) if total_trades > 0 else 0.0
        exp_r = (sum(all_r) / len(all_r)) if all_r else 0.0

        ablation_summary.append({
            "Configuration": ab_name,
            "Total_Signals": total_signals,
            "Total_Trades": total_trades,
            "Net_PnL": round(total_pnl, 2),
            "Win_Rate": round(win_rate, 4),
            "Expectancy_R": round(exp_r, 4),
            "Description": (
                "Sistema completo multitemporal" if ab_name == "Baseline_A_Full" else
                "Sin filtro de contexto D1 (solo H1+M5)" if ab_name == "Ablation_B_No_D1" else
                "Sin confluencia Fibonacci 0.618" if ab_name == "Ablation_C_No_Fib" else
                "Sin filtro EMA 50" if ab_name == "Ablation_D_No_EMA50" else
                "Entrada directa H1 sin confirmación M5"
            )
        })

    with open(r"C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\ablation_results.json", "w", encoding="utf-8") as f:
        json.dump(ablation_summary, f, indent=2)

    print("Ablation study completed.")

if __name__ == "__main__":
    run_experiment_suite()
