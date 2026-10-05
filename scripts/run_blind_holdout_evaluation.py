"""
scripts/run_blind_holdout_evaluation.py
=======================================
Script institucional para la ejecución One-Shot de la evaluación ciega
del FINAL_HOLDOUT para D21_RangeCompress_5d.
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ai_trading_agent.data.providers.yfinance_provider import YFinanceMarketDataProvider
from ai_trading_agent.strategy_lab.backtesting.daily_execution_simulator import (
    DailyExecutionSimulator,
    DailyStrategyEvaluator,
    DailyFeaturePrecomputer
)

def run_evaluation():
    print("=" * 80)
    print(" EJECUCIÓN ONE-SHOT: BLIND FINAL HOLDOUT EVALUATION (FASE 10.3)")
    print("=" * 80)

    # 1. VERIFICAR FINGERPRINT DE LA ESTRATEGIA
    d21_spec = {
        "strategy_id": "D21_RangeCompress_5d",
        "version": "1.0",
        "family": "daily_range_compression_breakout",
        "timeframe": "1D",
        "holding_horizon_days": 5,
        "donchian_length": 20,
        "rvol_threshold": 1.25,
        "sma_trend_filter": "SMA50",
        "exit_geometry": "time_stop",
        "rr_ratio": 2.0,
        "atr_mult": 1.5,
        "trailing_mult": 2.0,
        "concurrency_policy": "ONE_POSITION_PER_SYMBOL",
        "max_concurrent_positions": 2,
        "risk_per_trade_pct": 0.01,
        "commission_per_share": 0.005,
        "slippage_pct": 0.0005,
        "symbol_universe": ["SPY", "QQQ", "IWM", "DIA"]
    }
    serialized = json.dumps(d21_spec, sort_keys=True)
    current_fp = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
    expected_fp = "f885ec2db2422308"
    if current_fp != expected_fp:
        raise PermissionError(f"SecurityViolationError: Fingerprint mismatch! Got {current_fp}, expected {expected_fp}")
    print(f" [OK] Strategy Fingerprint Verificado: {current_fp}")

    # 2. RUN METADATA & ONE-SHOT RUN ID
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_id = f"HOLDOUT_EVAL_{timestamp_str}_{current_fp}"
    print(f" [OK] One-Shot Run ID: {run_id}")

    # 3. VERIFICAR PROTOCOLO PRE-REGISTRADO
    proto_path = root_dir / "BLIND_HOLDOUT_EVALUATION_PROTOCOL.md"
    if not proto_path.exists():
        raise FileNotFoundError("Protocolo de evaluación no encontrado.")
    proto_hash = hashlib.sha256(proto_path.read_bytes()).hexdigest()
    print(f" [OK] Protocol SHA256: {proto_hash}")

    # 4. CARGAR DATOS Y DELIMITAR FINAL HOLDOUT
    provider = YFinanceMarketDataProvider(fallback_to_synthetic=False)
    symbols = ["SPY", "QQQ", "IWM", "DIA"]
    raw_data = {s: provider.get_historical_bars(symbol=s, count=1500, interval="1d") for s in symbols}
    
    common_start = max(raw_data[s][0].timestamp for s in symbols)
    common_end = min(raw_data[s][-1].timestamp for s in symbols)
    total_days = (common_end - common_start).days
    holdout_days = int(total_days * 0.20)
    pre_start = common_start
    pre_end = common_end - timedelta(days=holdout_days)
    holdout_start = pre_end
    holdout_end = common_end

    print(f" [OK] Fechas Holdout Desbloqueadas: {holdout_start.strftime('%Y-%m-%d')} -> {holdout_end.strftime('%Y-%m-%d')} ({holdout_days} dias)")

    # Warm-up precomputado sobre la serie completa para evitar look-ahead pero permitir continuidad técnica
    full_feat = {s: DailyFeaturePrecomputer.precompute(raw_data[s]) for s in symbols}
    holdout_data = {s: [b for b in raw_data[s] if holdout_start <= b.timestamp <= holdout_end] for s in symbols}

    for s in symbols:
        print(f"    - {s}: {len(holdout_data[s])} barras en Holdout")

    # 5. EJECUTAR EVALUACIÓN FROZEN
    evaluator = DailyStrategyEvaluator(
        family="daily_range_compression_breakout",
        holding_horizon_days=5,
        exit_geometry="time_stop",
        rr_ratio=2.0,
        atr_mult=1.5,
        trailing_mult=2.0
    )
    sim = DailyExecutionSimulator(
        evaluator=evaluator,
        initial_capital=100000.0,
        commission_per_share=0.005,
        slippage_pct=0.0005,
        concurrency_policy="ONE_POSITION_PER_SYMBOL",
        max_concurrent_positions=2
    )

    res = sim.run_simulation(holdout_data, precomputed_features=full_feat)
    trades = res["closed_trades"]

    # 6. MÉTRICAS CORE Y RECONCILIACIÓN DE COSTES
    gross_pnl = res["total_gross_pnl"]
    comm_paid = res["commission_drag"]
    slip_paid = res["slippage_drag"]
    net_pnl = res["total_net_pnl"]
    pf = res["profit_factor"]
    sharpe = res["sharpe_ratio"]
    wr = res["win_rate"]
    max_dd = res["max_drawdown_pct"]
    total_trades = res["total_trades"]
    exp = net_pnl / total_trades if total_trades > 0 else 0.0

    print("\n" + "=" * 80)
    print(" RESULTADOS PRIMARIOS DEL FINAL HOLDOUT (1D)")
    print("=" * 80)
    print(f" Total Trades:          {total_trades}")
    print(f" Gross PnL:             ${gross_pnl:,.2f}")
    print(f" Commission Drag:       -${comm_paid:,.2f}")
    print(f" Slippage Drag:         -${slip_paid:,.2f}")
    print(f" Net Realized PnL:      ${net_pnl:,.2f}")
    reconciled = abs((gross_pnl - comm_paid - slip_paid) - net_pnl)
    print(f" Cost Reconciliation:   Delta = ${reconciled:.4f} (<= $0.01: {reconciled <= 0.01})")
    print(f" Profit Factor:         {pf:.2f}")
    print(f" Expectancy:            ${exp:,.2f} / trade")
    print(f" Win Rate:              {wr:.2f}%")
    print(f" Sharpe Ratio:          {sharpe:.2f}")
    print(f" Max Drawdown:          {max_dd:.2f}%")

    # Holding metrics
    holding_days = [t.get("holding_days", 5) for t in trades]
    if holding_days:
        import numpy as np
        print(f" Mean Holding Days:     {np.mean(holding_days):.2f}")
        print(f" Median Holding Days:   {np.median(holding_days):.2f}")
        wins = [t["net_pnl"] for t in trades if t["net_pnl"] > 0]
        losses = [t["net_pnl"] for t in trades if t["net_pnl"] < 0]
        avg_w = np.mean(wins) if wins else 0.0
        avg_l = abs(np.mean(losses)) if losses else 1e-6
        payoff = avg_w / avg_l
        be_wr = (1.0 / (1.0 + payoff)) * 100.0 if payoff > 0 else 50.0
        print(f" Average Win:           ${avg_w:,.2f}")
        print(f" Average Loss:          ${avg_l:,.2f}")
        print(f" Realized Payoff:       {payoff:.2f}")
        print(f" Breakeven Win Rate:    {be_wr:.2f}%")

    # 7. BREAKDOWN POR SÍMBOLO
    print("\n" + "-" * 80)
    print(" DESGLOSE POR SÍMBOLO (HOLDOUT)")
    print("-" * 80)
    symbol_results = {}
    for s in symbols:
        s_data = {s: holdout_data[s]}
        s_feat = {s: full_feat[s]}
        s_res = sim.run_simulation(s_data, precomputed_features=s_feat)
        s_t = s_res["total_trades"]
        s_pnl = s_res["total_net_pnl"]
        s_pf = s_res["profit_factor"]
        s_sh = s_res["sharpe_ratio"]
        s_dd = s_res["max_drawdown_pct"]
        s_exp = s_pnl / s_t if s_t > 0 else 0.0
        symbol_results[s] = {
            "trades": s_t, "pnl": s_pnl, "pf": s_pf, "sharpe": s_sh, "drawdown": s_dd, "expectancy": s_exp
        }
        print(f" {s:4s} | Trades: {s_t:2d} | Net PnL: ${s_pnl:9,.2f} | PF: {s_pf:4.2f} | Exp: ${s_exp:7.2f} | Sharpe: {s_sh:5.2f} | MaxDD: {s_dd:5.2f}%")

    # 8. BREAKDOWN RETROSPECTIVO POR RÉGIMEN
    print("\n" + "-" * 80)
    print(" DESGLOSE RETROSPECTIVO POR RÉGIMEN (HOLDOUT)")
    print("-" * 80)
    reg_counts = {"BULL_TREND": 0, "BEAR_TREND": 0, "SIDEWAYS": 0, "HIGH_VOL": 0, "LOW_VOL": 0}
    reg_pnl = {"BULL_TREND": 0.0, "BEAR_TREND": 0.0, "SIDEWAYS": 0.0, "HIGH_VOL": 0.0, "LOW_VOL": 0.0}
    for t in trades:
        rg = t.get("regime", "SIDEWAYS")
        reg_counts[rg] = reg_counts.get(rg, 0) + 1
        reg_pnl[rg] = reg_pnl.get(rg, 0.0) + t["net_pnl"]
    for rg, cnt in reg_counts.items():
        print(f" {rg:12s} | Trades: {cnt:2d} | Net PnL: ${reg_pnl[rg]:9,.2f}")

    # 9. GUARDAR RESULTADOS DE AUDITORÍA
    audit_record = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "strategy_id": "D21_RangeCompress_5d",
        "fingerprint": current_fp,
        "protocol_hash": proto_hash,
        "holdout_start": holdout_start.isoformat(),
        "holdout_end": holdout_end.isoformat(),
        "core_metrics": {
            "total_trades": total_trades,
            "gross_pnl": gross_pnl,
            "commission_drag": comm_paid,
            "slippage_drag": slip_paid,
            "net_pnl": net_pnl,
            "profit_factor": pf,
            "sharpe_ratio": sharpe,
            "win_rate": wr,
            "max_drawdown_pct": max_dd,
            "expectancy": exp
        },
        "symbol_results": symbol_results,
        "regime_results": {"counts": reg_counts, "pnl": reg_pnl},
        "dataset_status": "OBSERVED_FINAL_HOLDOUT"
    }

    audit_file = root_dir / "ai_trading_agent" / "scratch" / f"{run_id}_results.json"
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(audit_record, f, indent=2)
    print(f"\n [OK] Registro inmutable de auditoría guardado en: {audit_file}")

if __name__ == "__main__":
    run_evaluation()
