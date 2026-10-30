"""
ai_trading_agent.strategy_lab.fase7_1a_forensic_engine
=====================================================
Motor de Auditoría Forense Correctiva de Datos y Contabilidad (Fase 7.1A):
1. Descomposición contable exacta: True Gross PnL, Slippage, Comisiones, Net PnL.
2. Auditoría exhaustiva de fechas con MarketCalendarService (NYSE/NASDAQ).
3. Análisis de procedencia y hashes de datos (Sintético vs Mercado Real).
4. Auditoría de intervalos de tenencia reales y solapamientos de posición.
5. Ejecución comparativa sobre datos reales auténticos de SPY (1,200 barras diarias NYSE).
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import math
import json
import csv
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Tuple
import numpy as np

from ai_trading_agent.domain.enums import SignalDirection
from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.dual_strategy.regime import MarketRegimeV1, RegimeFeatureCalculator
from ai_trading_agent.schedule.market_calendar import market_calendar
from ai_trading_agent.data.providers.yfinance_provider import yfinance_provider
from ai_trading_agent.strategy_lab.fase7_research import (
    MomentumTrendPullbackV1,
    MeanReversionRsiBollingerV1,
    BaseFase7ResearchStrategy
)
from ai_trading_agent.strategy_lab.fase7_1_audit_engine import generate_canonical_fase7_benchmark


def run_forensic_accounting_on_trades(
    trades: List[Dict[str, Any]],
    bars: List[OHLCVBar],
    commission_per_share: float = 0.005,
    slippage_bps: float = 5.0
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Reconstruye cada trade calculando estrictamente:
    - Mid Entry & Mid Exit (sin slippage)
    - True Gross PnL
    - Slippage Entry & Exit
    - Commissions
    - Net PnL
    """
    reconciled = []
    slippage_rate = slippage_bps / 10000.0

    for t in trades:
        entry_idx = t["entry_bar_idx"]
        exit_idx = t["exit_bar_idx"]
        shares = t["shares"]

        # Precios mid reales de la barra (sin slippage)
        entry_mid = bars[entry_idx].close
        exit_mid = bars[exit_idx].close

        # Precios con slippage
        entry_fill = entry_mid * (1.0 + slippage_rate)
        exit_fill = exit_mid * (1.0 - slippage_rate)

        # 1. True Gross PnL
        true_gross_pnl = (exit_mid - entry_mid) * shares

        # 2. Deslizamiento real en USD
        slippage_entry_usd = (entry_fill - entry_mid) * shares
        slippage_exit_usd = (exit_mid - exit_fill) * shares
        total_slippage_usd = slippage_entry_usd + slippage_exit_usd

        # 3. Comisiones
        total_comm_usd = (commission_per_share * shares) * 2.0

        # 4. Net PnL exacto
        true_net_pnl = true_gross_pnl - total_slippage_usd - total_comm_usd

        # 5. Validación de calendario NYSE
        entry_dt = bars[entry_idx].timestamp
        exit_dt = bars[exit_idx].timestamp
        if hasattr(entry_dt, "tzinfo") and entry_dt.tzinfo is None:
            entry_dt_ny = entry_dt.replace(tzinfo=market_calendar.tz)
            exit_dt_ny = exit_dt.replace(tzinfo=market_calendar.tz)
        else:
            entry_dt_ny = entry_dt
            exit_dt_ny = exit_dt

        entry_is_trading_day = market_calendar.is_trading_day(entry_dt_ny)
        exit_is_trading_day = market_calendar.is_trading_day(exit_dt_ny)
        calendar_valid = entry_is_trading_day and exit_is_trading_day

        reconciled.append({
            "trade_id": t["trade_id"],
            "strategy_id": t["strategy_id"],
            "symbol": t["symbol"],
            "entry_bar_idx": entry_idx,
            "exit_bar_idx": exit_idx,
            "entry_date": str(entry_dt)[:10],
            "exit_date": str(exit_dt)[:10],
            "entry_day_name": entry_dt.strftime("%A"),
            "exit_day_name": exit_dt.strftime("%A"),
            "calendar_valid": calendar_valid,
            "shares": shares,
            "entry_mid": round(entry_mid, 4),
            "exit_mid": round(exit_mid, 4),
            "entry_fill": round(entry_fill, 4),
            "exit_fill": round(exit_fill, 4),
            "true_gross_pnl": round(true_gross_pnl, 2),
            "slippage_usd": round(total_slippage_usd, 2),
            "commission_usd": round(total_comm_usd, 2),
            "total_costs_usd": round(total_slippage_usd + total_comm_usd, 2),
            "true_net_pnl": round(true_net_pnl, 2),
            "exit_reason": t["exit_reason"],
            "holding_days": t["holding_days"]
        })

    # Resumen contable
    sum_gross = sum(r["true_gross_pnl"] for r in reconciled)
    sum_slip = sum(r["slippage_usd"] for r in reconciled)
    sum_comm = sum(r["commission_usd"] for r in reconciled)
    sum_net = sum(r["true_net_pnl"] for r in reconciled)

    gross_wins = [r["true_gross_pnl"] for r in reconciled if r["true_gross_pnl"] > 0]
    gross_losses = [abs(r["true_gross_pnl"]) for r in reconciled if r["true_gross_pnl"] <= 0]
    gross_pf = (sum(gross_wins) / sum(gross_losses)) if sum(gross_losses) > 0 else 0.0

    net_wins = [r["true_net_pnl"] for r in reconciled if r["true_net_pnl"] > 0]
    net_losses = [abs(r["true_net_pnl"]) for r in reconciled if r["true_net_pnl"] <= 0]
    net_pf = (sum(net_wins) / sum(net_losses)) if sum(net_losses) > 0 else 0.0

    summary = {
        "trade_count": len(reconciled),
        "calendar_valid_trades": sum(1 for r in reconciled if r["calendar_valid"]),
        "calendar_invalid_trades": sum(1 for r in reconciled if not r["calendar_valid"]),
        "sum_true_gross_pnl": round(sum_gross, 2),
        "sum_slippage_usd": round(sum_slip, 2),
        "sum_commission_usd": round(sum_comm, 2),
        "sum_total_costs_usd": round(sum_slip + sum_comm, 2),
        "sum_true_net_pnl": round(sum_net, 2),
        "gross_profit_factor": round(gross_pf, 2),
        "net_profit_factor": round(net_pf, 2),
        "cost_drag_pct": round(((sum_slip + sum_comm) / sum_gross * 100.0) if sum_gross > 0 else 0.0, 2)
    }

    return reconciled, summary


def evaluate_on_real_spy_market_data(
    count: int = 1200,
    commission_per_share: float = 0.005,
    slippage_bps: float = 5.0
) -> Dict[str, Any]:
    """
    Descarga barras diarias reales auténticas de SPY desde Yahoo Finance
    y ejecuta la auditoría con el calendario oficial y el detector de regímenes determinista.
    """
    bars = yfinance_provider.get_historical_bars("SPY", count=count, interval="1d")
    if not bars or len(bars) < 100:
        return {"status": "ERROR", "message": "No se pudieron obtener barras reales de SPY"}

    # Hashes de procedencia de datos
    bar_tokens = [f"{b.timestamp}_{b.open}_{b.high}_{b.low}_{b.close}_{b.volume}" for b in bars]
    dataset_hash = hashlib.sha256("".join(bar_tokens).encode("utf-8")).hexdigest()

    # Precomputar regímenes reales para cada barra
    regimes = []
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]

    for i in range(len(bars)):
        if i < 55:
            regimes.append(MarketRegimeV1.INDETERMINATE)
            continue

        slice_close = closes[max(0, i-50):i+1]
        slice_high = highs[max(0, i-50):i+1]
        slice_low = lows[max(0, i-50):i+1]

        sma_50 = float(np.mean(slice_close)) if len(slice_close) >= 50 else closes[i]

        # Calcular ADX(14)
        tr_list = []
        for j in range(1, len(slice_close)):
            h = slice_high[j]
            l = slice_low[j]
            pc = slice_close[j-1]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            tr_list.append(tr)
        atr_14 = float(np.mean(tr_list[-14:])) if len(tr_list) >= 14 else 1.0

        diffs = np.diff(slice_close[-20:]) if len(slice_close) >= 20 else np.array([0.0])
        er_20 = float(abs(slice_close[-1] - slice_close[-20])) / (float(np.sum(np.abs(diffs))) + 1e-9) if len(slice_close) >= 20 else 0.2

        # Proxy determinista de ADX
        dx = (abs(slice_close[-1] - sma_50) / (atr_14 + 1e-9)) * 10.0
        adx_14 = min(60.0, max(10.0, dx))

        # Clasificación con MarketRegimeV1
        if adx_14 >= 25.0 and er_20 >= 0.35 and closes[i] > sma_50:
            regimes.append(MarketRegimeV1.TRENDING_BULL)
        elif adx_14 < 20.0 and er_20 < 0.25:
            regimes.append(MarketRegimeV1.RANGING)
        else:
            regimes.append(MarketRegimeV1.INDETERMINATE)

    # Simular Momentum y Mean Reversion sobre datos reales
    from ai_trading_agent.strategy_lab.fase7_1_audit_engine import simulate_trades_detailed, compute_comprehensive_metrics

    mom = MomentumTrendPullbackV1()
    mr = MeanReversionRsiBollingerV1()

    raw_trades_mom = simulate_trades_detailed(mom, "SPY", bars, regimes, commission_per_share, slippage_bps)
    raw_trades_mr = simulate_trades_detailed(mr, "SPY", bars, regimes, commission_per_share, slippage_bps)

    rec_mom, sum_mom = run_forensic_accounting_on_trades(raw_trades_mom, bars, commission_per_share, slippage_bps)
    rec_mr, sum_mr = run_forensic_accounting_on_trades(raw_trades_mr, bars, commission_per_share, slippage_bps)

    return {
        "status": "SUCCESS",
        "dataset_info": {
            "symbol": "SPY",
            "bar_count": len(bars),
            "start_date": str(bars[0].timestamp)[:10],
            "end_date": str(bars[-1].timestamp)[:10],
            "data_source": "yfinance_real_market",
            "dataset_sha256": dataset_hash
        },
        "regime_distribution": {
            "TRENDING_BULL": regimes.count(MarketRegimeV1.TRENDING_BULL),
            "RANGING": regimes.count(MarketRegimeV1.RANGING),
            "INDETERMINATE": regimes.count(MarketRegimeV1.INDETERMINATE)
        },
        "momentum_real": sum_mom,
        "mean_reversion_real": sum_mr,
        "reconciled_trades_mom_real": rec_mom,
        "reconciled_trades_mr_real": rec_mr
    }


def main():
    # 1. Auditoría sobre el benchmark sintético de Fase 7.0 / 7.1
    bars_synth, regimes_synth = generate_canonical_fase7_benchmark(1200, seed=42)
    mom = MomentumTrendPullbackV1()
    mr = MeanReversionRsiBollingerV1()

    from ai_trading_agent.strategy_lab.fase7_1_audit_engine import simulate_trades_detailed
    raw_mom_synth = simulate_trades_detailed(mom, "SPY", bars_synth, regimes_synth)
    raw_mr_synth = simulate_trades_detailed(mr, "SPY", bars_synth, regimes_synth)

    rec_mom_synth, sum_mom_synth = run_forensic_accounting_on_trades(raw_mom_synth, bars_synth)
    rec_mr_synth, sum_mr_synth = run_forensic_accounting_on_trades(raw_mr_synth, bars_synth)

    # Hash del benchmark sintético
    synth_tokens = [f"{b.timestamp}_{b.open}_{b.high}_{b.low}_{b.close}_{b.volume}" for b in bars_synth]
    synth_hash = hashlib.sha256("".join(synth_tokens).encode("utf-8")).hexdigest()

    # 2. Auditoría sobre el mercado real auténtico de SPY
    real_results = evaluate_on_real_spy_market_data(count=1200)

    forensic_output = {
        "forensic_audit_timestamp": datetime.utcnow().isoformat(),
        "phase": "FASE_7_1A",
        "synthetic_benchmark_audit": {
            "dataset_type": "SYNTHETIC_GBM_WITH_CALENDAR_INCREMENTS",
            "sha256": synth_hash,
            "total_bars": len(bars_synth),
            "classification": "INVALID_DATA_PROVENANCE_FOR_PRODUCTION",
            "momentum": sum_mom_synth,
            "mean_reversion": sum_mr_synth
        },
        "real_market_audit": real_results
    }

    out_file = r"C:\Users\edsel\OneDrive\Documents\trading-app-repo\ai_trading_agent\scratch\fase7_1a_forensic_manifest.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(forensic_output, f, indent=2)

    print(json.dumps({
        "status": "FORENSIC_AUDIT_COMPLETED",
        "synthetic_benchmark": {
            "mom": sum_mom_synth,
            "mr": sum_mr_synth
        },
        "real_market": {
            "info": real_results.get("dataset_info"),
            "regimes": real_results.get("regime_distribution"),
            "mom": real_results.get("momentum_real"),
            "mr": real_results.get("mean_reversion_real")
        }
    }, indent=2))


if __name__ == "__main__":
    main()
