"""
ai_trading_agent.strategy_lab.fase7_2_multiasset_engine
======================================================
Motor de Validación Cuantitativa Multiactivo y Robusteza Estadística (Fase 7.2)
1. Universo de activos reales: SPY, QQQ, IWM, DIA, XLF, XLE (1,200 barras diarias NYSE cada uno).
2. Verificación estricta de calendario NYSE/NASDAQ con MarketCalendarService (cero datos sintéticos).
3. Congelamiento estricto de código y cálculo de fingerprints SHA-256 de MOM y MR.
4. Ejecución cruzada de estrategias:
   - MR_RsiBollinger_V1 (Con filtro RANGING vs Sin filtro)
   - MOM_TrendPullback_V1 (Con filtro TRENDING_BULL vs Sin filtro)
5. Pruebas de estrés de costes de transacción:
   - 1x (Base: $0.005/acción, 5 bps slippage)
   - 2x (Moderado: $0.010/acción, 10 bps slippage)
   - 3x (Extremo: $0.015/acción, 15 bps slippage)
6. Métricas exactas reconciliadas: True Gross PnL, Slippage, Comisiones, True Net PnL, PF, Sharpe, Sortino, MaxDD.
7. Evaluación de portafolio multiactivo agregado.
8. Análisis de robustez estadística: Bootstrap (1,000 resamples, IC 95%) y Leave-One-Symbol-Out (LOSO).
9. Exportación de manifiesto JSON y CSV de trades.
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
import inspect
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from ai_trading_agent.domain.enums import SignalDirection
from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.dual_strategy.regime import MarketRegimeV1
from ai_trading_agent.schedule.market_calendar import market_calendar
from ai_trading_agent.data.providers.yfinance_provider import yfinance_provider
from ai_trading_agent.strategy_lab.fase7_research import (
    MomentumTrendPullbackV1,
    MeanReversionRsiBollingerV1,
    BaseFase7ResearchStrategy
)


TARGET_ASSETS = ["SPY", "QQQ", "IWM", "DIA", "XLF", "XLE"]

COST_SCENARIOS = {
    "1x": {"commission_per_share": 0.005, "slippage_bps": 5.0, "label": "Base (1x)"},
    "2x": {"commission_per_share": 0.010, "slippage_bps": 10.0, "label": "Moderado (2x)"},
    "3x": {"commission_per_share": 0.015, "slippage_bps": 15.0, "label": "Extremo (3x)"}
}


def compute_code_fingerprint(cls_or_obj: Any) -> str:
    """Calcula el hash SHA-256 del código fuente y parámetros de una estrategia."""
    try:
        src = inspect.getsource(cls_or_obj if inspect.isclass(cls_or_obj) else cls_or_obj.__class__)
    except Exception:
        src = str(cls_or_obj)
    params_str = ""
    if hasattr(cls_or_obj, "parameters"):
        params_str = json.dumps(cls_or_obj.parameters, sort_keys=True)
    combined = (src + params_str).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()[:16]


def calculate_regimes_for_bars(bars: List[OHLCVBar]) -> List[MarketRegimeV1]:
    """Clasifica cada barra utilizando el detector determinista MarketRegimeV1."""
    regimes: List[MarketRegimeV1] = []
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

        # Calcular ATR(14)
        tr_list = []
        for j in range(1, len(slice_close)):
            h = slice_high[j]
            l = slice_low[j]
            pc = slice_close[j-1]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            tr_list.append(tr)
        atr_14 = float(np.mean(tr_list[-14:])) if len(tr_list) >= 14 else 1.0

        # Efficiency Ratio (ER20)
        diffs = np.diff(slice_close[-20:]) if len(slice_close) >= 20 else np.array([0.0])
        er_20 = float(abs(slice_close[-1] - slice_close[-20])) / (float(np.sum(np.abs(diffs))) + 1e-9) if len(slice_close) >= 20 else 0.2

        # Proxy ADX(14)
        dx = (abs(slice_close[-1] - sma_50) / (atr_14 + 1e-9)) * 10.0
        adx_14 = min(60.0, max(10.0, dx))

        if adx_14 >= 25.0 and er_20 >= 0.35 and closes[i] > sma_50:
            regimes.append(MarketRegimeV1.TRENDING_BULL)
        elif adx_14 < 20.0 and er_20 < 0.25:
            regimes.append(MarketRegimeV1.RANGING)
        else:
            regimes.append(MarketRegimeV1.INDETERMINATE)

    return regimes


def simulate_strategy_execution(
    strategy: BaseFase7ResearchStrategy,
    symbol: str,
    bars: List[OHLCVBar],
    regimes: List[MarketRegimeV1],
    ignore_regime_filter: bool = False,
    capital_allocated: float = 100_000.0,
    commission_per_share: float = 0.005,
    slippage_bps: float = 5.0
) -> List[Dict[str, Any]]:
    """
    Simula la ejecución de una estrategia barra a barra con contabilidad exacta:
    - Sin solapamiento de posiciones (1 posición abierta a la vez por símbolo).
    - Descomposición matemática: True Gross PnL, Slippage, Comisiones y True Net PnL.
    - Validación de fechas contra calendario oficial NYSE.
    """
    trades = []
    in_trade = False
    entry_price_mid = 0.0
    entry_fill = 0.0
    entry_idx = 0
    shares = 0
    slippage_rate = slippage_bps / 10000.0

    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]

    for i in range(55, len(bars)):
        curr_bar = bars[i]
        actual_regime = regimes[i]
        eval_regime = strategy.target_regime if ignore_regime_filter else actual_regime

        slice_close = closes[max(0, i-50):i+1]
        sma_50 = float(np.mean(slice_close)) if len(slice_close) >= 50 else curr_bar.close
        ema_20 = float(np.mean(closes[max(0, i-20):i+1]))

        # RSI(14)
        diffs = np.diff(slice_close[-15:]) if len(slice_close) >= 15 else np.array([0.0])
        gains = np.maximum(diffs, 0)
        losses = np.maximum(-diffs, 0)
        avg_gain = float(np.mean(gains)) if len(gains) > 0 else 0.001
        avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.001
        rs = avg_gain / (avg_loss + 1e-9)
        rsi = 100.0 - (100.0 / (1.0 + rs))

        # RSI(4) para Mean Reversion
        diffs4 = np.diff(slice_close[-5:]) if len(slice_close) >= 5 else np.array([0.0])
        rs4 = (float(np.mean(np.maximum(diffs4, 0))) + 1e-9) / (float(np.mean(np.maximum(-diffs4, 0))) + 1e-9)
        rsi_4 = 100.0 - (100.0 / (1.0 + rs4))

        # Bollinger Bands(20, 2)
        std_20 = float(np.std(closes[max(0, i-20):i+1])) if len(closes) >= 20 else 1.0
        bb_lower = ema_20 - 2.0 * std_20
        bb_middle = ema_20

        # RVOL(20)
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
                entry_price_mid = curr_bar.close
                entry_fill = entry_price_mid * (1.0 + slippage_rate)
                risk_amount = capital_allocated * 0.0025  # 0.25% ($250)
                stop_dist = max(curr_bar.close * 0.02, 1.0)
                shares = max(10, int(risk_amount / stop_dist))
                entry_idx = i
                in_trade = True
        else:
            holding_days = i - entry_idx
            max_holding = strategy.parameters.get("max_holding_days", 5)
            return_pct = (curr_bar.close - entry_fill) / entry_fill
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
                exit_price_mid = curr_bar.close
                exit_fill = exit_price_mid * (1.0 - slippage_rate)

                # Descomposición exacta
                true_gross_pnl = (exit_price_mid - entry_price_mid) * shares
                slippage_entry_usd = (entry_fill - entry_price_mid) * shares
                slippage_exit_usd = (exit_price_mid - exit_fill) * shares
                total_slippage_usd = slippage_entry_usd + slippage_exit_usd
                total_comm_usd = (commission_per_share * shares) * 2.0
                true_net_pnl = true_gross_pnl - total_slippage_usd - total_comm_usd

                # Verificación de calendario NYSE
                entry_dt = bars[entry_idx].timestamp
                exit_dt = bars[i].timestamp
                if hasattr(entry_dt, "tzinfo") and entry_dt.tzinfo is None:
                    entry_dt_ny = entry_dt.replace(tzinfo=market_calendar.tz)
                    exit_dt_ny = exit_dt.replace(tzinfo=market_calendar.tz)
                else:
                    entry_dt_ny = entry_dt
                    exit_dt_ny = exit_dt

                valid_calendar = market_calendar.is_trading_day(entry_dt_ny) and market_calendar.is_trading_day(exit_dt_ny)

                trades.append({
                    "trade_id": f"{strategy.strategy_id}_{symbol}_{len(trades)+1:03d}",
                    "strategy_id": strategy.strategy_id,
                    "symbol": symbol,
                    "filter_mode": "UNFILTERED" if ignore_regime_filter else "FILTERED",
                    "entry_bar_idx": entry_idx,
                    "exit_bar_idx": i,
                    "entry_date": str(entry_dt)[:10],
                    "exit_date": str(exit_dt)[:10],
                    "entry_day_name": entry_dt.strftime("%A"),
                    "exit_day_name": exit_dt.strftime("%A"),
                    "calendar_valid": valid_calendar,
                    "direction": "BUY",
                    "shares": shares,
                    "entry_mid": round(entry_price_mid, 4),
                    "exit_mid": round(exit_price_mid, 4),
                    "entry_fill": round(entry_fill, 4),
                    "exit_fill": round(exit_fill, 4),
                    "true_gross_pnl": round(true_gross_pnl, 2),
                    "slippage_usd": round(total_slippage_usd, 2),
                    "commission_usd": round(total_comm_usd, 2),
                    "total_costs_usd": round(total_slippage_usd + total_comm_usd, 2),
                    "true_net_pnl": round(true_net_pnl, 2),
                    "return_pct": round(((exit_fill - entry_fill) / entry_fill) * 100.0, 3),
                    "holding_days": holding_days,
                    "exit_reason": exit_reason,
                    "regime_at_entry": regimes[entry_idx].value,
                    "regime_at_exit": regimes[i].value
                })
                in_trade = False

    return trades


def calculate_metrics_from_trades(trades: List[Dict[str, Any]], total_bars: int = 1200) -> Dict[str, Any]:
    """Calcula el conjunto completo de métricas cuantitativas reconciliadas."""
    n = len(trades)
    if n == 0:
        return {
            "trade_count": 0,
            "annual_frequency": 0.0,
            "win_rate_pct": 0.0,
            "sum_true_gross_pnl": 0.0,
            "sum_slippage_usd": 0.0,
            "sum_commission_usd": 0.0,
            "sum_total_costs_usd": 0.0,
            "sum_true_net_pnl": 0.0,
            "gross_profit_factor": 0.0,
            "net_profit_factor": 0.0,
            "expectancy_usd": 0.0,
            "max_drawdown_usd": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "cost_drag_pct": 0.0,
            "calendar_valid_pct": 100.0
        }

    # Frecuencia anualizada (aprox 252 días por año de trading)
    years = total_bars / 252.0
    annual_freq = round(n / years, 2) if years > 0 else 0.0

    gross_pnls = [t["true_gross_pnl"] for t in trades]
    net_pnls = [t["true_net_pnl"] for t in trades]
    slips = [t["slippage_usd"] for t in trades]
    comms = [t["commission_usd"] for t in trades]
    valid_cal = sum(1 for t in trades if t["calendar_valid"])

    wins = [p for p in net_pnls if p > 0]
    losses = [abs(p) for p in net_pnls if p <= 0]
    win_rate = round((len(wins) / n) * 100.0, 2)

    gross_wins = [p for p in gross_pnls if p > 0]
    gross_losses = [abs(p) for p in gross_pnls if p <= 0]
    gross_pf = round(sum(gross_wins) / (sum(gross_losses) + 1e-9), 2) if sum(gross_losses) > 0 else 999.0
    net_pf = round(sum(wins) / (sum(losses) + 1e-9), 2) if sum(losses) > 0 else 999.0

    sum_gross = round(sum(gross_pnls), 2)
    sum_slip = round(sum(slips), 2)
    sum_comm = round(sum(comms), 2)
    sum_costs = round(sum_slip + sum_comm, 2)
    sum_net = round(sum(net_pnls), 2)
    expectancy = round(sum_net / n, 2)

    # Cost drag
    cost_drag = round((sum_costs / sum_gross * 100.0) if sum_gross > 0 else 0.0, 2)

    # Curva de equidad y Drawdown
    equity_curve = [100_000.0]
    for p in net_pnls:
        equity_curve.append(equity_curve[-1] + p)

    peak = equity_curve[0]
    max_dd_usd = 0.0
    max_dd_pct = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = peak - eq
        dd_pct = (dd / peak) * 100.0 if peak > 0 else 0.0
        if dd > max_dd_usd:
            max_dd_usd = dd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

    # Sharpe y Sortino anualizados basados en retornos por trade
    trade_returns = [t["return_pct"] / 100.0 for t in trades]
    mean_ret = float(np.mean(trade_returns))
    std_ret = float(np.std(trade_returns)) + 1e-9
    neg_rets = [r for r in trade_returns if r < 0]
    downside_std = float(np.std(neg_rets)) + 1e-9 if len(neg_rets) > 1 else std_ret

    trades_per_year = n / years if years > 0 else 1.0
    annual_factor = math.sqrt(max(1.0, trades_per_year))
    sharpe = round((mean_ret / std_ret) * annual_factor, 2)
    sortino = round((mean_ret / downside_std) * annual_factor, 2)

    return {
        "trade_count": n,
        "annual_frequency": annual_freq,
        "win_rate_pct": win_rate,
        "sum_true_gross_pnl": sum_gross,
        "sum_slippage_usd": sum_slip,
        "sum_commission_usd": sum_comm,
        "sum_total_costs_usd": sum_costs,
        "sum_true_net_pnl": sum_net,
        "gross_profit_factor": gross_pf,
        "net_profit_factor": net_pf,
        "expectancy_usd": expectancy,
        "max_drawdown_usd": round(max_dd_usd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "cost_drag_pct": cost_drag,
        "calendar_valid_pct": round((valid_cal / n) * 100.0, 2)
    }


def run_bootstrap_analysis(trades: List[Dict[str, Any]], iterations: int = 1000, seed: int = 42) -> Dict[str, Any]:
    """Calcula intervalos de confianza al 95% para Net PnL, Win Rate y Net PF."""
    if len(trades) < 5:
        return {
            "status": "INSUFFICIENT_TRADES_FOR_BOOTSTRAP",
            "iterations": 0
        }

    np.random.seed(seed)
    n = len(trades)
    net_pnls = np.array([t["true_net_pnl"] for t in trades])

    boot_pnl = []
    boot_wr = []
    boot_pf = []

    for _ in range(iterations):
        sample = np.random.choice(net_pnls, size=n, replace=True)
        boot_pnl.append(float(np.sum(sample)))
        boot_wr.append(float(np.sum(sample > 0) / n * 100.0))
        wins = sample[sample > 0]
        losses = np.abs(sample[sample <= 0])
        pf = float(np.sum(wins) / (np.sum(losses) + 1e-9)) if len(losses) > 0 and np.sum(losses) > 0 else 999.0
        boot_pf.append(min(pf, 50.0))

    return {
        "status": "SUCCESS",
        "iterations": iterations,
        "net_pnl_ci95": [round(float(np.percentile(boot_pnl, 2.5)), 2), round(float(np.percentile(boot_pnl, 97.5)), 2)],
        "win_rate_ci95": [round(float(np.percentile(boot_wr, 2.5)), 2), round(float(np.percentile(boot_wr, 97.5)), 2)],
        "profit_factor_ci95": [round(float(np.percentile(boot_pf, 2.5)), 2), round(float(np.percentile(boot_pf, 97.5)), 2)],
        "p_loss": round(float(np.mean(np.array(boot_pnl) <= 0)), 4)
    }


def execute_fase7_2_multiasset_validation() -> Dict[str, Any]:
    """
    Función orquestadora principal de la Fase 7.2.
    """
    print("=" * 80)
    print("INICIANDO FASE 7.2: VALIDACIÓN MULTIACTIVO CON MERCADO REAL")
    print("=" * 80)

    # 1. Congelar estrategias e instanciar
    mom_strat = MomentumTrendPullbackV1()
    mr_strat = MeanReversionRsiBollingerV1()

    mom_fp = compute_code_fingerprint(mom_strat)
    mr_fp = compute_code_fingerprint(mr_strat)

    print(f"Fingerprint MOM_TrendPullback_V1: {mom_fp}")
    print(f"Fingerprint MR_RsiBollinger_V1:   {mr_fp}")

    # 2. Descarga y validación de datos para cada activo
    dataset_metadata: Dict[str, Any] = {}
    bars_by_symbol: Dict[str, List[OHLCVBar]] = {}
    regimes_by_symbol: Dict[str, List[MarketRegimeV1]] = {}

    for sym in TARGET_ASSETS:
        print(f"Descargando datos reales para {sym} (1200 barras)...")
        bars = yfinance_provider.get_historical_bars(sym, count=1200, interval="1d")
        if not bars or len(bars) < 100:
            raise RuntimeError(f"Fallo al descargar barras para {sym}")

        # Hash SHA-256 del dataset
        bar_tokens = [f"{b.timestamp}_{b.open}_{b.high}_{b.low}_{b.close}_{b.volume}" for b in bars]
        ds_hash = hashlib.sha256("".join(bar_tokens).encode("utf-8")).hexdigest()

        # Validación con calendario oficial
        invalid_calendar_count = 0
        for b in bars:
            dt = b.timestamp
            if hasattr(dt, "tzinfo") and dt.tzinfo is None:
                dt_ny = dt.replace(tzinfo=market_calendar.tz)
            else:
                dt_ny = dt
            if not market_calendar.is_trading_day(dt_ny):
                invalid_calendar_count += 1

        regimes = calculate_regimes_for_bars(bars)

        dataset_metadata[sym] = {
            "symbol": sym,
            "bar_count": len(bars),
            "start_date": str(bars[0].timestamp)[:10],
            "end_date": str(bars[-1].timestamp)[:10],
            "sha256": ds_hash,
            "calendar_invalid_bars": invalid_calendar_count,
            "regime_distribution": {
                "TRENDING_BULL": regimes.count(MarketRegimeV1.TRENDING_BULL),
                "RANGING": regimes.count(MarketRegimeV1.RANGING),
                "INDETERMINATE": regimes.count(MarketRegimeV1.INDETERMINATE)
            }
        }
        bars_by_symbol[sym] = bars
        regimes_by_symbol[sym] = regimes
        print(f"  {sym}: {len(bars)} barras ({dataset_metadata[sym]['start_date']} -> {dataset_metadata[sym]['end_date']}), Hash={ds_hash[:12]}..., InvalidDates={invalid_calendar_count}")

    # 3. Ejecución sistemática multiactivo
    # Estructura: strategy -> filter_mode (FILTERED / UNFILTERED) -> cost_scenario (1x, 2x, 3x) -> symbol -> metrics
    all_trades: List[Dict[str, Any]] = []
    matrix_results: Dict[str, Any] = {
        "MOM_TrendPullback_V1": {"FILTERED": {}, "UNFILTERED": {}},
        "MR_RsiBollinger_V1": {"FILTERED": {}, "UNFILTERED": {}}
    }

    strategies = [
        ("MOM_TrendPullback_V1", mom_strat),
        ("MR_RsiBollinger_V1", mr_strat)
    ]

    for strat_id, strat_obj in strategies:
        for filter_mode, ignore_filter in [("FILTERED", False), ("UNFILTERED", True)]:
            matrix_results[strat_id][filter_mode] = {}
            for cost_key, cost_cfg in COST_SCENARIOS.items():
                matrix_results[strat_id][filter_mode][cost_key] = {
                    "by_symbol": {},
                    "aggregate": {}
                }
                cost_trades: List[Dict[str, Any]] = []

                for sym in TARGET_ASSETS:
                    sym_bars = bars_by_symbol[sym]
                    sym_regimes = regimes_by_symbol[sym]
                    sym_trades = simulate_strategy_execution(
                        strategy=strat_obj,
                        symbol=sym,
                        bars=sym_bars,
                        regimes=sym_regimes,
                        ignore_regime_filter=ignore_filter,
                        commission_per_share=cost_cfg["commission_per_share"],
                        slippage_bps=cost_cfg["slippage_bps"]
                    )
                    metrics = calculate_metrics_from_trades(sym_trades, total_bars=len(sym_bars))
                    matrix_results[strat_id][filter_mode][cost_key]["by_symbol"][sym] = metrics
                    cost_trades.extend(sym_trades)

                    # Guardar trades de escenario 1x para el dataset exportable
                    if cost_key == "1x":
                        for t in sym_trades:
                            t_copy = dict(t)
                            t_copy["cost_scenario"] = cost_key
                            all_trades.append(t_copy)

                # Métricas agregadas del portafolio en este escenario
                agg_metrics = calculate_metrics_from_trades(cost_trades, total_bars=1200)
                # Bootstrap sobre el portafolio agregado
                boot = run_bootstrap_analysis(cost_trades)
                agg_metrics["bootstrap"] = boot
                matrix_results[strat_id][filter_mode][cost_key]["aggregate"] = agg_metrics

    # 4. Análisis Leave-One-Symbol-Out (LOSO) en escenario 1x FILTERED
    loso_results: Dict[str, Any] = {"MR_RsiBollinger_V1": {}, "MOM_TrendPullback_V1": {}}
    for strat_id, strat_obj in strategies:
        filtered_1x_trades = [t for t in all_trades if t["strategy_id"] == strat_id and t["filter_mode"] == "FILTERED"]
        for sym_out in TARGET_ASSETS:
            loso_subset = [t for t in filtered_1x_trades if t["symbol"] != sym_out]
            loso_metrics = calculate_metrics_from_trades(loso_subset, total_bars=1200)
            loso_results[strat_id][f"EXCLUDING_{sym_out}"] = loso_metrics

    # 5. Exportar CSV y JSON
    scratch_dir = repo_root / "ai_trading_agent" / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    csv_path = scratch_dir / "fase7_2_multiasset_trades.csv"
    if all_trades:
        fieldnames = list(all_trades[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_trades)
        print(f"Exportado trades CSV: {csv_path} ({len(all_trades)} registros)")

    manifest = {
        "manifest_version": "1.0",
        "timestamp_utc": datetime.utcnow().isoformat(),
        "phase": "FASE_7_2",
        "governance": {
            "mode": "RESEARCH / ANALYSIS_ONLY",
            "trading_mode": "ANALYSIS_ONLY",
            "live_trading_enabled": False,
            "paper_broker": "Moomoo (TrdEnv.SIMULATE)",
            "d21_status": "PAPER_PROTECTED_PENDING_SESSION",
            "d21_fingerprint": "f885ec2db2422308",
            "d21_virtual_capital_usd": 1000000.0
        },
        "strategy_fingerprints": {
            "MOM_TrendPullback_V1": mom_fp,
            "MR_RsiBollinger_V1": mr_fp
        },
        "target_universe": TARGET_ASSETS,
        "datasets": dataset_metadata,
        "matrix_results": matrix_results,
        "loso_analysis": loso_results
    }

    manifest_path = scratch_dir / "fase7_2_multiasset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Exportado manifest JSON: {manifest_path}")

    return manifest


if __name__ == "__main__":
    res = execute_fase7_2_multiasset_validation()
    print("FASE 7.2 MULTIASSET VALIDATION COMPLETADA.")
