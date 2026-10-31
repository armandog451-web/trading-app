"""
ai_trading_agent.strategy_lab.experiments.exp_mtf01.run_robustness_and_stress
============================================================================
Ejecución de Validación de Robustez, Stress de Costos y Test de Perturbación Futura.
"""

import os
import sys
import json
import pandas as pd
import numpy as np

sys.path.insert(0, r"C:\Users\edsel\Documents\trading-app-repo")

from ai_trading_agent.strategy_lab.experiments.exp_mtf01.causal_mtf_synchronizer import CausalMTFSynchronizer
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.mtf_backtester import MTFBacktester

data_dir = r"C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\data"
symbols = ["SPY", "QQQ", "DIA", "IWM", "GLD", "TLT"]

def load_data(sym: str):
    df_d1 = pd.read_csv(os.path.join(data_dir, f"{sym}_1d.csv"), index_col=0, parse_dates=True)
    df_h1 = pd.read_csv(os.path.join(data_dir, f"{sym}_1h.csv"), index_col=0, parse_dates=True)
    df_m5 = pd.read_csv(os.path.join(data_dir, f"{sym}_5m.csv"), index_col=0, parse_dates=True)

    if df_d1.index.tz is None:
        df_d1.index = df_d1.index.tz_localize('UTC')
    if df_h1.index.tz is None:
        df_h1.index = df_h1.index.tz_localize('UTC')
    if df_m5.index.tz is None:
        df_m5.index = df_m5.index.tz_localize('UTC')

    return df_d1, df_h1, df_m5

def main():
    print("=== 1. COST STRESS TESTING (ABLATION B) ===")
    sync_b = CausalMTFSynchronizer(enable_d1_filter=False, enable_fib_filter=True, enable_ema_filter=True, enable_m5_filter=True)
    all_signals_b = {}
    for sym in symbols:
        d1, h1, m5 = load_data(sym)
        d1_f, h1_f, m5_f = sync_b.prepare_data(d1, h1, m5)
        sigs = sync_b.run_synchronization(d1_f, h1_f, m5_f)
        all_signals_b[sym] = (sigs, m5)

    cost_tiers = [
        {"tier": "1x_Base", "slippage_bps": 2.0, "comm": 0.005},
        {"tier": "2x_Moderate", "slippage_bps": 4.0, "comm": 0.010},
        {"tier": "3x_Severe", "slippage_bps": 6.0, "comm": 0.015},
    ]

    cost_results = []
    trades_by_tier = {}

    for c in cost_tiers:
        bt = MTFBacktester(slippage_bps=c["slippage_bps"], commission_per_share=c["comm"])
        tot_trades = 0
        tot_net_pnl = 0.0
        tot_comm = 0.0
        tot_slip = 0.0
        wins = 0
        all_r = []
        tier_trades = []

        for sym in symbols:
            sigs, m5 = all_signals_b[sym]
            res = bt.run_simulation(sigs, m5, tp_variant="V1B")
            tot_trades += res["total_trades"]
            tot_net_pnl += res["net_pnl"]
            tier_trades.extend(res["trades"])
            for t in res["trades"]:
                tot_comm += t["commissions"]
                tot_slip += t["slippage_cost"]
                all_r.append(t["r_return"])
                if t["net_pnl"] > 0:
                    wins += 1

        wr = (wins / tot_trades) if tot_trades > 0 else 0.0
        exp_r = (sum(all_r) / len(all_r)) if all_r else 0.0
        trades_by_tier[c["tier"]] = tier_trades

        cost_results.append({
            "Cost_Tier": c["tier"],
            "Slippage_Bps": c["slippage_bps"],
            "Commission_Per_Share": c["comm"],
            "Total_Trades": tot_trades,
            "Net_PnL": round(tot_net_pnl, 2),
            "Total_Commissions": round(tot_comm, 2),
            "Total_Slippage": round(tot_slip, 2),
            "Total_Friction": round(tot_comm + tot_slip, 2),
            "Win_Rate": round(wr, 4),
            "Expectancy_R": round(exp_r, 4)
        })

    with open(r"C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\cost_stress_summary.json", "w", encoding="utf-8") as f:
        json.dump(cost_results, f, indent=2)
    print("Cost stress completed.")

    print("\n=== 2. MONTE CARLO BOOTSTRAP (1,000 RESAMPLES) ===")
    base_trades = trades_by_tier["1x_Base"]
    pnls = [t["net_pnl"] for t in base_trades]

    mc_results = {}
    if len(pnls) >= 3:
        np.random.seed(42)
        n_sims = 1000
        sim_pnls = []
        for _ in range(n_sims):
            sample = np.random.choice(pnls, size=len(pnls), replace=True)
            sim_pnls.append(float(np.sum(sample)))

        sim_pnls = np.array(sim_pnls)
        mc_results = {
            "n_resamples": 1000,
            "sample_size": len(pnls),
            "mean_simulated_pnl": round(float(np.mean(sim_pnls)), 2),
            "std_simulated_pnl": round(float(np.std(sim_pnls)), 2),
            "p5_pnl": round(float(np.percentile(sim_pnls, 5)), 2),
            "p50_pnl": round(float(np.percentile(sim_pnls, 50)), 2),
            "p95_pnl": round(float(np.percentile(sim_pnls, 95)), 2),
            "prob_positive_pnl": round(float(np.mean(sim_pnls > 0)), 4)
        }
    else:
        mc_results = {"status": "INSUFFICIENT_TRADES_FOR_BOOTSTRAP", "trades_count": len(pnls)}

    with open(r"C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\monte_carlo_summary.json", "w", encoding="utf-8") as f:
        json.dump(mc_results, f, indent=2)
    print("Monte Carlo bootstrap completed.")

    print("\n=== 3. FUTURE PERTURBATION TEST (ANTI-LEAKAGE) ===")
    # Pick SPY, perturb all prices after cutoff date 2026-10-15
    d1, h1, m5 = load_data("SPY")
    d1_f, h1_f, m5_f = sync_b.prepare_data(d1, h1, m5)
    sigs_original = sync_b.run_synchronization(d1_f, h1_f, m5_f)

    cutoff = pd.Timestamp("2026-10-15 00:00:00", tz="UTC")
    pre_cutoff_original = [s for s in sigs_original if pd.to_datetime(s["signal_time"]) < cutoff]

    # Perturb M5 future prices (multiply high, low, close by 1.15)
    m5_perturbed = m5.copy()
    mask = m5_perturbed.index >= cutoff
    m5_perturbed.loc[mask, 'Close'] = m5_perturbed.loc[mask, 'Close'] * 1.15
    m5_perturbed.loc[mask, 'High'] = m5_perturbed.loc[mask, 'High'] * 1.15
    m5_perturbed.loc[mask, 'Low'] = m5_perturbed.loc[mask, 'Low'] * 1.15

    d1_f_p, h1_f_p, m5_f_p = sync_b.prepare_data(d1, h1, m5_perturbed)
    sigs_perturbed = sync_b.run_synchronization(d1_f_p, h1_f_p, m5_f_p)
    pre_cutoff_perturbed = [s for s in sigs_perturbed if pd.to_datetime(s["signal_time"]) < cutoff]

    identical = (len(pre_cutoff_original) == len(pre_cutoff_perturbed))
    if identical:
        for s1, s2 in zip(pre_cutoff_original, pre_cutoff_perturbed):
            if s1["signal_time"] != s2["signal_time"] or s1["signal_close"] != s2["signal_close"]:
                identical = False
                break

    anti_leakage_res = {
        "asset": "SPY",
        "cutoff_date": "2026-10-15T00:00:00Z",
        "original_signals_pre_cutoff": len(pre_cutoff_original),
        "perturbed_signals_pre_cutoff": len(pre_cutoff_perturbed),
        "pre_cutoff_signals_identical": identical,
        "causal_integrity_certified": identical
    }

    with open(r"C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\anti_leakage_summary.json", "w", encoding="utf-8") as f:
        json.dump(anti_leakage_res, f, indent=2)
    print("Anti-leakage perturbation test completed. Identical:", identical)

if __name__ == "__main__":
    main()
