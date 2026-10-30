"""
ai_trading_agent.strategy_lab.fase7_1_audit_engine
=================================================
Motor de Auditoría Cuantitativa Profunda para Fase 7.1:
1. Reconstrucción y Reconciliación Trade a Trade (Bloque A).
2. Auditoría Estadística Avanzada y Bootstrap Resampling (Bloque B).
3. Prueba de Estrés de Costes Transaccionales (1x, 2x, 3x) (Bloque C).
4. Comparativa Justa de Filtros de Régimen (Bloque D).
5. Evaluación de Cartera Teórica Aislada (Bloque F).

Totalmente desacoplado de brokers y bases de datos de producción.
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import math
import json
import csv
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import numpy as np

from ai_trading_agent.domain.enums import SignalDirection
from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.dual_strategy.regime import MarketRegimeV1
from ai_trading_agent.strategy_lab.fase7_research import (
    MomentumTrendPullbackV1,
    MeanReversionRsiBollingerV1,
    BaseFase7ResearchStrategy,
    ResearchTrade
)


def generate_canonical_fase7_benchmark(num_days=1200, seed=42) -> Tuple[List[OHLCVBar], List[MarketRegimeV1]]:
    """Genera exactamente el mismo benchmark determinista de 1200 barras de Fase 7.0."""
    np.random.seed(seed)
    bars = []
    regimes = []
    base_date = datetime(2020, 1, 1)
    price = 320.0

    for i in range(num_days):
        dt = base_date + timedelta(days=i)
        cycle = (i // 120) % 3
        if cycle == 0:
            regime = MarketRegimeV1.TRENDING_BULL
            daily_ret = np.random.normal(0.0008, 0.009)
            vol = np.random.uniform(1.2e6, 2.5e6)
        elif cycle == 1:
            regime = MarketRegimeV1.RANGING
            daily_ret = np.random.normal(0.0, 0.006)
            vol = np.random.uniform(8.0e5, 1.4e6)
        else:
            regime = MarketRegimeV1.INDETERMINATE
            daily_ret = np.random.normal(-0.0005, 0.015)
            vol = np.random.uniform(1.5e6, 3.5e6)

        price *= (1.0 + daily_ret)
        high = price * (1.0 + abs(np.random.normal(0.005, 0.003)))
        low = price * (1.0 - abs(np.random.normal(0.005, 0.003)))
        open_p = (high + low) / 2.0

        bars.append(OHLCVBar(
            symbol="SPY",
            timestamp=dt,
            open=open_p,
            high=high,
            low=low,
            close=price,
            volume=vol
        ))
        regimes.append(regime)

    return bars, regimes


def simulate_trades_detailed(
    strategy: BaseFase7ResearchStrategy,
    symbol: str,
    bars: List[OHLCVBar],
    regime_series: List[MarketRegimeV1],
    commission_per_share: float = 0.005,
    slippage_bps: float = 5.0,
    capital_allocated: float = 100000.0,
    ignore_regime_filter: bool = False
) -> List[Dict[str, Any]]:
    """Ejecuta simulación y retorna lista detallada de trades para reconciliación."""
    trades = []
    in_trade = False
    entry_price = 0.0
    entry_idx = 0
    shares = 0
    entry_bar_ts = ""
    slippage_rate = slippage_bps / 10000.0

    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]

    for i in range(55, len(bars)):
        curr_bar = bars[i]
        actual_regime = regime_series[i] if i < len(regime_series) else MarketRegimeV1.INDETERMINATE
        eval_regime = strategy.target_regime if ignore_regime_filter else actual_regime

        slice_close = closes[max(0, i-50):i+1]
        sma_50 = float(np.mean(slice_close)) if len(slice_close) >= 50 else curr_bar.close
        ema_20 = float(np.mean(closes[max(0, i-20):i+1]))
        diffs = np.diff(slice_close[-15:]) if len(slice_close) >= 15 else np.array([0.0])
        gains = np.maximum(diffs, 0)
        losses = np.maximum(-diffs, 0)
        avg_gain = float(np.mean(gains)) if len(gains) > 0 else 0.001
        avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.001
        rs = avg_gain / (avg_loss + 1e-9)
        rsi = 100.0 - (100.0 / (1.0 + rs))

        diffs4 = np.diff(slice_close[-5:]) if len(slice_close) >= 5 else np.array([0.0])
        rs4 = (float(np.mean(np.maximum(diffs4, 0))) + 1e-9) / (float(np.mean(np.maximum(-diffs4, 0))) + 1e-9)
        rsi_4 = 100.0 - (100.0 / (1.0 + rs4))

        std_20 = float(np.std(closes[max(0, i-20):i+1])) if len(closes) >= 20 else 1.0
        bb_lower = ema_20 - 2.0 * std_20
        bb_middle = ema_20

        avg_vol_20 = float(np.mean(volumes[max(0, i-20):i])) if i >= 20 else curr_bar.volume
        rvol = curr_bar.volume / (avg_vol_20 + 1e-9)

        indicators = {
            "rsi": rsi,
            "rsi_4": rsi_4,
            "rvol": rvol,
            "ema_20": ema_20,
            "sma_50": sma_50,
            "bb_lower": bb_lower,
            "bb_middle": bb_middle
        }

        if not in_trade:
            signal = strategy.evaluate_signal(symbol, bars[:i+1], eval_regime, indicators)
            if signal.direction == SignalDirection.BUY:
                fill_price = curr_bar.close * (1.0 + slippage_rate)
                risk_amount = capital_allocated * 0.0025  # 0.25% ($250)
                stop_dist = max(curr_bar.close * 0.02, 1.0)
                shares = max(10, int(risk_amount / stop_dist))
                entry_price = fill_price
                entry_idx = i
                entry_bar_ts = str(curr_bar.timestamp)
                in_trade = True
        else:
            holding_days = i - entry_idx
            max_holding = strategy.parameters.get("max_holding_days", 5)
            return_pct = (curr_bar.close - entry_price) / entry_price
            exit_signal = False
            exit_reason = ""

            if holding_days >= max_holding:
                exit_signal = True
                exit_reason = "TIME_EXIT"
            elif return_pct >= 0.035:
                exit_signal = True
                exit_reason = "PROFIT_TARGET"
            elif return_pct <= -0.02:
                exit_signal = True
                exit_reason = "STOP_LOSS"

            if exit_signal:
                exit_fill = curr_bar.close * (1.0 - slippage_rate)
                gross = (exit_fill - entry_price) * shares
                comm = (commission_per_share * shares) * 2.0
                slip = (entry_price * slippage_rate + exit_fill * slippage_rate) * shares
                net = gross - comm
                r_multiple = net / (capital_allocated * 0.0025)

                trades.append({
                    "trade_id": f"{strategy.strategy_id}_{len(trades)+1:03d}",
                    "strategy_id": strategy.strategy_id,
                    "symbol": symbol,
                    "entry_bar_idx": entry_idx,
                    "exit_bar_idx": i,
                    "entry_date": entry_bar_ts[:10],
                    "exit_date": str(curr_bar.timestamp)[:10],
                    "direction": "BUY",
                    "shares": shares,
                    "entry_price": round(entry_price, 4),
                    "exit_price": round(exit_fill, 4),
                    "gross_pnl": round(gross, 2),
                    "commission": round(comm, 2),
                    "slippage": round(slip, 2),
                    "total_cost": round(comm + slip, 2),
                    "net_pnl": round(net, 2),
                    "r_multiple": round(r_multiple, 3),
                    "return_pct": round(((exit_fill - entry_price) / entry_price) * 100.0, 3),
                    "holding_days": holding_days,
                    "exit_reason": exit_reason,
                    "actual_regime": actual_regime.value
                })
                in_trade = False

    return trades


def compute_comprehensive_metrics(trades: List[Dict[str, Any]], capital: float = 100000.0, total_bars: int = 1200) -> Dict[str, Any]:
    """Calcula todas las métricas cuantitativas solicitadas en el Bloque B."""
    if not trades:
        return {
            "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
            "win_rate_pct": 0.0, "avg_win_usd": 0.0, "avg_loss_usd": 0.0,
            "expectancy_usd": 0.0, "expectancy_r": 0.0, "profit_factor": 0.0,
            "sharpe_ratio": 0.0, "sortino_ratio": 0.0, "max_drawdown_usd": 0.0,
            "max_drawdown_pct": 0.0, "recovery_factor": 0.0, "time_exposure_pct": 0.0,
            "mean_holding_days": 0.0, "max_losing_streak": 0, "total_net_pnl": 0.0
        }

    pnls = [t["net_pnl"] for t in trades]
    r_mults = [t["r_multiple"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    n = len(pnls)
    w_count = len(wins)
    l_count = len(losses)
    wr = (w_count / n) if n > 0 else 0.0

    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = abs(float(np.mean(losses))) if losses else 0.0
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)

    # Expectancy: (WR * AvgWin) - ((1-WR) * AvgLoss)
    expectancy_usd = (wr * avg_win) - ((1.0 - wr) * avg_loss)
    expectancy_r = float(np.mean(r_mults)) if r_mults else 0.0

    # Drawdown
    cum_pnl = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum_pnl)
    dd = peak - cum_pnl
    max_dd_usd = float(np.max(dd)) if len(dd) > 0 else 0.0
    max_dd_pct = (max_dd_usd / capital) * 100.0

    total_net = sum(pnls)
    recovery_factor = (total_net / max_dd_usd) if max_dd_usd > 0 else (99.0 if total_net > 0 else 0.0)

    # Sharpe y Sortino (trade-based normalizado a 252 días de trading)
    mean_pnl = float(np.mean(pnls))
    std_pnl = float(np.std(pnls, ddof=1)) if len(pnls) > 1 else 1.0
    sharpe = (mean_pnl / (std_pnl + 1e-9)) * math.sqrt(252.0 / 5.0)

    downside_losses = [min(0.0, p) for p in pnls]
    downside_std = float(np.std(downside_losses, ddof=1)) if len(downside_losses) > 1 else 1.0
    sortino = (mean_pnl / (downside_std + 1e-9)) * math.sqrt(252.0 / 5.0)

    # Exposición temporal
    total_days_in_trade = sum(t["holding_days"] for t in trades)
    time_exposure_pct = (total_days_in_trade / total_bars) * 100.0
    mean_holding = float(np.mean([t["holding_days"] for t in trades]))

    # Rachas de pérdidas
    max_lose_streak = 0
    curr_streak = 0
    for p in pnls:
        if p <= 0:
            curr_streak += 1
            max_lose_streak = max(max_lose_streak, curr_streak)
        else:
            curr_streak = 0

    return {
        "total_trades": n,
        "winning_trades": w_count,
        "losing_trades": l_count,
        "win_rate_pct": round(wr * 100.0, 2),
        "avg_win_usd": round(avg_win, 2),
        "avg_loss_usd": round(avg_loss, 2),
        "expectancy_usd": round(expectancy_usd, 2),
        "expectancy_r": round(expectancy_r, 3),
        "profit_factor": round(pf, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "max_drawdown_usd": round(max_dd_usd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "recovery_factor": round(recovery_factor, 2),
        "time_exposure_pct": round(time_exposure_pct, 2),
        "mean_holding_days": round(mean_holding, 1),
        "max_losing_streak": max_lose_streak,
        "total_net_pnl": round(total_net, 2)
    }


def run_bootstrap_resampling(trades: List[Dict[str, Any]], n_iterations: int = 1000, seed: int = 42) -> Dict[str, Any]:
    """Ejecuta bootstrap de 1,000 iteraciones con intervalos de confianza del 95%."""
    if len(trades) < 5:
        return {"error": "INSUFFICIENT_DATA_FOR_BOOTSTRAP"}

    np.random.seed(seed)
    pnls = np.array([t["net_pnl"] for t in trades])
    n = len(pnls)

    boot_expectancy = []
    boot_pf = []
    boot_win_rate = []

    for _ in range(n_iterations):
        sample = np.random.choice(pnls, size=n, replace=True)
        wins = sample[sample > 0]
        losses = sample[sample <= 0]
        gw = np.sum(wins) if len(wins) > 0 else 0.0
        gl = abs(np.sum(losses)) if len(losses) > 0 else 0.0
        pf = (gw / gl) if gl > 0 else (10.0 if gw > 0 else 0.0)
        wr = (len(wins) / n) * 100.0
        exp = np.mean(sample)

        boot_expectancy.append(exp)
        boot_pf.append(pf)
        boot_win_rate.append(wr)

    return {
        "bootstrap_iterations": n_iterations,
        "sample_size": n,
        "expectancy": {
            "mean": round(float(np.mean(boot_expectancy)), 2),
            "ci_95_lower": round(float(np.percentile(boot_expectancy, 2.5)), 2),
            "ci_95_upper": round(float(np.percentile(boot_expectancy, 97.5)), 2),
            "prob_positive": round(float(np.mean(np.array(boot_expectancy) > 0) * 100.0), 1)
        },
        "profit_factor": {
            "mean": round(float(np.mean(boot_pf)), 2),
            "ci_95_lower": round(float(np.percentile(boot_pf, 2.5)), 2),
            "ci_95_upper": round(float(np.percentile(boot_pf, 97.5)), 2),
            "prob_gt_1": round(float(np.mean(np.array(boot_pf) > 1.0) * 100.0), 1)
        },
        "win_rate_pct": {
            "mean": round(float(np.mean(boot_win_rate)), 2),
            "ci_95_lower": round(float(np.percentile(boot_win_rate, 2.5)), 2),
            "ci_95_upper": round(float(np.percentile(boot_win_rate, 97.5)), 2)
        }
    }


def run_full_fase7_1_audit():
    """Ejecuta el protocolo integral de auditoría de la Fase 7.1."""
    bars, regimes = generate_canonical_fase7_benchmark(1200, seed=42)
    mom = MomentumTrendPullbackV1()
    mr = MeanReversionRsiBollingerV1()

    # 1. Reproducibilidad y Reconciliación Base 1x
    trades_mom_filtered = simulate_trades_detailed(mom, "SPY", bars, regimes, commission_per_share=0.005, slippage_bps=5.0, ignore_regime_filter=False)
    trades_mom_unfiltered = simulate_trades_detailed(mom, "SPY", bars, regimes, commission_per_share=0.005, slippage_bps=5.0, ignore_regime_filter=True)
    trades_mr_filtered = simulate_trades_detailed(mr, "SPY", bars, regimes, commission_per_share=0.005, slippage_bps=5.0, ignore_regime_filter=False)
    trades_mr_unfiltered = simulate_trades_detailed(mr, "SPY", bars, regimes, commission_per_share=0.005, slippage_bps=5.0, ignore_regime_filter=True)

    metrics_mom_filtered = compute_comprehensive_metrics(trades_mom_filtered)
    metrics_mom_unfiltered = compute_comprehensive_metrics(trades_mom_unfiltered)
    metrics_mr_filtered = compute_comprehensive_metrics(trades_mr_filtered)
    metrics_mr_unfiltered = compute_comprehensive_metrics(trades_mr_unfiltered)

    # 2. Bootstrap Resampling (1,000 iteraciones)
    boot_mom_filtered = run_bootstrap_resampling(trades_mom_filtered)
    boot_mom_unfiltered = run_bootstrap_resampling(trades_mom_unfiltered)
    boot_mr_filtered = run_bootstrap_resampling(trades_mr_filtered)
    boot_mr_unfiltered = run_bootstrap_resampling(trades_mr_unfiltered)

    # 3. Estrés de Costes Transaccionales (1x, 2x, 3x)
    stress_scenarios = {
        "1x_Base": {"comm": 0.005, "slip": 5.0},
        "2x_Stress": {"comm": 0.010, "slip": 10.0},
        "3x_Severe": {"comm": 0.015, "slip": 15.0}
    }

    cost_stress_results = {}
    for sc_name, sc_params in stress_scenarios.items():
        tr_mom_f = simulate_trades_detailed(mom, "SPY", bars, regimes, commission_per_share=sc_params["comm"], slippage_bps=sc_params["slip"], ignore_regime_filter=False)
        tr_mr_f = simulate_trades_detailed(mr, "SPY", bars, regimes, commission_per_share=sc_params["comm"], slippage_bps=sc_params["slip"], ignore_regime_filter=False)
        tr_mr_unf = simulate_trades_detailed(mr, "SPY", bars, regimes, commission_per_share=sc_params["comm"], slippage_bps=sc_params["slip"], ignore_regime_filter=True)

        m_mom_f = compute_comprehensive_metrics(tr_mom_f)
        m_mr_f = compute_comprehensive_metrics(tr_mr_f)
        m_mr_unf = compute_comprehensive_metrics(tr_mr_unf)

        total_costs_mom = sum(t["total_cost"] for t in tr_mom_f)
        total_costs_mr = sum(t["total_cost"] for t in tr_mr_f)

        cost_stress_results[sc_name] = {
            "parameters": sc_params,
            "mom_filtered": {
                "trades": m_mom_f["total_trades"],
                "profit_factor": m_mom_f["profit_factor"],
                "expectancy_usd": m_mom_f["expectancy_usd"],
                "max_drawdown_pct": m_mom_f["max_drawdown_pct"],
                "net_pnl": m_mom_f["total_net_pnl"],
                "total_costs": round(total_costs_mom, 2)
            },
            "mr_filtered": {
                "trades": m_mr_f["total_trades"],
                "profit_factor": m_mr_f["profit_factor"],
                "expectancy_usd": m_mr_f["expectancy_usd"],
                "max_drawdown_pct": m_mr_f["max_drawdown_pct"],
                "net_pnl": m_mr_f["total_net_pnl"],
                "total_costs": round(total_costs_mr, 2)
            },
            "mr_unfiltered": {
                "trades": m_mr_unf["total_trades"],
                "profit_factor": m_mr_unf["profit_factor"],
                "expectancy_usd": m_mr_unf["expectancy_usd"],
                "max_drawdown_pct": m_mr_unf["max_drawdown_pct"],
                "net_pnl": m_mr_unf["total_net_pnl"]
            }
        }

    # 4. Evaluación de Cartera Teórica Aislada (Momentum + Mean Reversion combinadas)
    all_trades_portfolio = sorted(trades_mom_filtered + trades_mr_filtered, key=lambda x: x["entry_bar_idx"])
    portfolio_metrics = compute_comprehensive_metrics(all_trades_portfolio, capital=100000.0)

    # 5. Estructurar Resultados Consolidados
    audit_manifest = {
        "audit_metadata": {
            "timestamp_utc": datetime.utcnow().isoformat(),
            "fase": "FASE_7_1",
            "environment": "RESEARCH_ONLY / AIR_GAPPED",
            "d21_status": "UNTOUCHED_PAPER",
            "seed": 42,
            "total_bars": 1200
        },
        "reproducibility_check": {
            "mom_filtered_reproduced": (metrics_mom_filtered["total_trades"] == 11 and metrics_mom_filtered["profit_factor"] == 1.74 and metrics_mom_filtered["total_net_pnl"] == 421.39),
            "mom_unfiltered_reproduced": (metrics_mom_unfiltered["total_trades"] == 24 and metrics_mom_unfiltered["profit_factor"] == 1.84 and metrics_mom_unfiltered["total_net_pnl"] == 1410.93),
            "mr_filtered_reproduced": (metrics_mr_filtered["total_trades"] == 18 and metrics_mr_filtered["profit_factor"] == 1.04 and metrics_mr_filtered["total_net_pnl"] == 38.72),
            "mr_unfiltered_reproduced": (metrics_mr_unfiltered["total_trades"] == 52 and metrics_mr_unfiltered["profit_factor"] == 0.77 and metrics_mr_unfiltered["total_net_pnl"] == -931.72)
        },
        "baseline_metrics": {
            "mom_filtered": metrics_mom_filtered,
            "mom_unfiltered": metrics_mom_unfiltered,
            "mr_filtered": metrics_mr_filtered,
            "mr_unfiltered": metrics_mr_unfiltered,
            "portfolio_combined": portfolio_metrics
        },
        "bootstrap_audit": {
            "mom_filtered": boot_mom_filtered,
            "mom_unfiltered": boot_mom_unfiltered,
            "mr_filtered": boot_mr_filtered,
            "mr_unfiltered": boot_mr_unfiltered
        },
        "transaction_cost_stress": cost_stress_results,
        "reconciled_trades": {
            "mom_filtered": trades_mom_filtered,
            "mr_filtered": trades_mr_filtered
        }
    }

    # Guardar en archivo JSON para reproducibilidad
    output_path = r"C:\Users\edsel\OneDrive\Documents\trading-app-repo\ai_trading_agent\scratch\fase7_1_audit_manifest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(audit_manifest, f, indent=2)

    # Exportar CSV reconciliado trade-a-trade
    csv_path = r"C:\Users\edsel\OneDrive\Documents\trading-app-repo\ai_trading_agent\scratch\fase7_1_reconciled_trades.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(trades_mom_filtered[0].keys()))
        writer.writeheader()
        for t in trades_mom_filtered:
            writer.writerow(t)
        for t in trades_mr_filtered:
            writer.writerow(t)

    print(json.dumps({
        "status": "AUDIT_COMPLETED",
        "reproducibility": audit_manifest["reproducibility_check"],
        "metrics_mom_filtered": metrics_mom_filtered,
        "metrics_mr_filtered": metrics_mr_filtered,
        "portfolio_combined": portfolio_metrics
    }, indent=2))

    return audit_manifest


if __name__ == "__main__":
    run_full_fase7_1_audit()
