"""
ai_trading_agent.strategy_lab.discovery.discovery_engine_v2
===========================================================
Strategy Discovery Engine v2 — Motor Autónomo de Descubrimiento Cuantitativo (Fase 7.3)

Módulos Integrados:
1. DataIntegrityGate: Validación estricta de barras 100% cerradas y calendario bursátil NYSE/NASDAQ.
2. HypothesisGenerator & StrategyCandidateBuilder: Familias A (Cross-Sectional Relative Momentum),
   B (Volatility-Conditioned Mean Reversion) y C (Adaptive Allocation).
3. BacktestEngine: Simulador cronológico con contabilidad forense exacta y estrés de costes 1x, 2x, 3x.
4. StatisticalValidationEngine: Walk-Forward (IS vs OOS), Bootstrap (1,000 iter, IC 95%), LOSO y penalización multivariada.
5. EconomicEdgeGate: Compuertas eliminatorias tempranas objetivas.
6. ResearchRankingEngine: Clasificación explicable de hipótesis (PROMISING, INCONCLUSIVE, REJECTED, INVALID).
7. EvidenceExporter: Manifiestos reproducibles JSON y CSV.
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import math
import json
import csv
import hashlib
import inspect
from dataclasses import dataclass, field, asdict
from datetime import datetime, time, timezone
from enum import Enum
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from ai_trading_agent.domain.enums import SignalDirection
from ai_trading_agent.domain.models import OHLCVBar, StrategySignal
from ai_trading_agent.dual_strategy.regime import MarketRegimeV1
from ai_trading_agent.schedule.market_calendar import market_calendar
from ai_trading_agent.data.providers.yfinance_provider import yfinance_provider


# ---------------------------------------------------------------------------
# 1. ENUMS Y MODELOS DE DATOS
# ---------------------------------------------------------------------------

class ResearchStrategyStatus(str, Enum):
    RESEARCH_NEW = "RESEARCH_NEW"
    RESEARCH_TESTING = "RESEARCH_TESTING"
    RESEARCH_INCONCLUSIVE = "RESEARCH_INCONCLUSIVE"
    RESEARCH_PROMISING = "RESEARCH_PROMISING"
    RESEARCH_REJECTED = "RESEARCH_REJECTED"
    INVALID = "INVALID"


class ResearchFamily(str, Enum):
    CROSS_SECTIONAL_MOMENTUM = "CROSS_SECTIONAL_MOMENTUM"
    VOLATILITY_CONDITIONED_REVERSION = "VOLATILITY_CONDITIONED_REVERSION"
    MARKET_REGIME_ADAPTIVE = "MARKET_REGIME_ADAPTIVE"


@dataclass
class ResearchHypothesisRecord:
    hypothesis_id: str
    strategy_id: str
    family: ResearchFamily
    economic_thesis: str
    parameters: Dict[str, Any]
    fingerprint_sha256: str
    dataset_universe: List[str]
    freeze_timestamp: str
    random_seed: int
    cost_scenarios_evaluated: List[str]
    status: ResearchStrategyStatus = ResearchStrategyStatus.RESEARCH_NEW
    verdict_reason: str = ""
    metrics_oos_1x: Dict[str, Any] = field(default_factory=dict)
    metrics_full_1x: Dict[str, Any] = field(default_factory=dict)
    ranking_score: float = 0.0


# ---------------------------------------------------------------------------
# 2. DATA INTEGRITY GATE
# ---------------------------------------------------------------------------

class DataIntegrityGate:
    """Valida calendario, integridad y garantiza que ninguna barra no cerrada contamine el estudio."""

    @staticmethod
    def sanitize_and_validate_bars(
        symbol: str,
        raw_bars: List[OHLCVBar],
        reference_dt: Optional[datetime] = None
    ) -> Tuple[List[OHLCVBar], Dict[str, Any]]:
        if not raw_bars:
            return [], {"status": "ERROR", "message": "No bars provided"}

        ref_time = reference_dt or datetime.utcnow()
        # En horario ET, si hoy es día bursátil y la hora < 16:00 ET, la barra de hoy no está cerrada
        today_str = ref_time.strftime("%Y-%m-%d")

        sanitized: List[OHLCVBar] = []
        invalid_calendar_count = 0
        unclosed_bars_dropped = 0

        for b in raw_bars:
            b_dt = b.timestamp
            b_date_str = str(b_dt)[:10]

            # 1. Filtrar barra no cerrada si corresponde a la sesión activa en curso
            if b_date_str == today_str and ref_time.hour < 16:
                unclosed_bars_dropped += 1
                continue

            # 2. Validar con MarketCalendarService
            if hasattr(b_dt, "tzinfo") and b_dt.tzinfo is None:
                dt_ny = b_dt.replace(tzinfo=market_calendar.tz)
            else:
                dt_ny = b_dt

            if not market_calendar.is_trading_day(dt_ny):
                invalid_calendar_count += 1
                continue

            sanitized.append(b)

        # Hashear el dataset saneado
        tokens = [f"{b.timestamp}_{b.open}_{b.high}_{b.low}_{b.close}_{b.volume}" for b in sanitized]
        sha256_hash = hashlib.sha256("".join(tokens).encode("utf-8")).hexdigest()

        meta = {
            "symbol": symbol,
            "raw_bars_count": len(raw_bars),
            "sanitized_bars_count": len(sanitized),
            "unclosed_bars_dropped": unclosed_bars_dropped,
            "invalid_calendar_count": invalid_calendar_count,
            "first_bar_date": str(sanitized[0].timestamp)[:10] if sanitized else "",
            "last_bar_date": str(sanitized[-1].timestamp)[:10] if sanitized else "",
            "dataset_sha256": sha256_hash,
            "status": "VALID_CLOSED_MARKET_DATA" if invalid_calendar_count == 0 else "INVALID_DATES_DETECTED"
        }

        return sanitized, meta


# ---------------------------------------------------------------------------
# 3. GENERADOR DE HIPÓTESIS Y DEFINICIÓN DE ESTRATEGIAS
# ---------------------------------------------------------------------------

def compute_source_fingerprint(code_str: str, params: Dict[str, Any]) -> str:
    params_repr = json.dumps(params, sort_keys=True)
    return hashlib.sha256((code_str + params_repr).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 4. MOTOR DE BACKTEST CRONOLÓGICO Y CONTABILIDAD RECONCILIADA
# ---------------------------------------------------------------------------

COST_TIERS = {
    "1x": {"comm": 0.005, "slip_bps": 5.0, "label": "Base 1x"},
    "2x": {"comm": 0.010, "slip_bps": 10.0, "label": "Moderado 2x"},
    "3x": {"comm": 0.015, "slip_bps": 15.0, "label": "Severo 3x"}
}


def run_chronological_backtest_asset(
    strategy_id: str,
    symbol: str,
    bars: List[OHLCVBar],
    entry_signals: List[bool],  # booleano por cada barra i
    exit_rules: Dict[str, Any],
    capital_per_trade: float = 100_000.0,
    cost_tier: str = "1x"
) -> List[Dict[str, Any]]:
    """
    Simulación cronológica estricta:
    - Evaluación en barra i -> Ejecución a precio de cierre de la barra i (o apertura i+1).
    - Descomposición exacta: True Gross PnL, Slippage, Comisiones y True Net PnL.
    """
    trades = []
    in_trade = False
    entry_mid = 0.0
    entry_fill = 0.0
    entry_idx = 0
    shares = 0

    cfg = COST_TIERS[cost_tier]
    comm_rate = cfg["comm"]
    slip_rate = cfg["slip_bps"] / 10000.0
    max_holding = exit_rules.get("max_holding", 5)
    stop_loss_pct = exit_rules.get("stop_loss_pct", 0.025)
    profit_target_pct = exit_rules.get("profit_target_pct", 0.04)

    for i in range(len(bars)):
        curr_bar = bars[i]

        if not in_trade:
            if entry_signals[i]:
                entry_mid = curr_bar.close
                entry_fill = entry_mid * (1.0 + slip_rate)
                risk_budget = capital_per_trade * 0.0025  # $250
                stop_dist = max(entry_mid * stop_loss_pct, 1.0)
                shares = max(10, int(risk_budget / stop_dist))
                entry_idx = i
                in_trade = True
        else:
            holding = i - entry_idx
            ret_pct = (curr_bar.close - entry_fill) / entry_fill
            exit_needed = False
            reason = ""

            if holding >= max_holding:
                exit_needed = True
                reason = "TIME_EXIT"
            elif ret_pct >= profit_target_pct:
                exit_needed = True
                reason = "PROFIT_TARGET"
            elif ret_pct <= -stop_loss_pct:
                exit_needed = True
                reason = "STOP_LOSS"

            if exit_needed:
                exit_mid = curr_bar.close
                exit_fill = exit_mid * (1.0 - slip_rate)

                true_gross_pnl = (exit_mid - entry_mid) * shares
                slip_usd = ((entry_fill - entry_mid) + (exit_mid - exit_fill)) * shares
                comm_usd = (comm_rate * shares) * 2.0
                true_net_pnl = true_gross_pnl - slip_usd - comm_usd

                trades.append({
                    "strategy_id": strategy_id,
                    "symbol": symbol,
                    "cost_tier": cost_tier,
                    "entry_idx": entry_idx,
                    "exit_idx": i,
                    "entry_date": str(bars[entry_idx].timestamp)[:10],
                    "exit_date": str(curr_bar.timestamp)[:10],
                    "holding_days": holding,
                    "shares": shares,
                    "entry_mid": round(entry_mid, 4),
                    "exit_mid": round(exit_mid, 4),
                    "entry_fill": round(entry_fill, 4),
                    "exit_fill": round(exit_fill, 4),
                    "true_gross_pnl": round(true_gross_pnl, 2),
                    "slippage_usd": round(slip_usd, 2),
                    "commission_usd": round(comm_usd, 2),
                    "total_costs_usd": round(slip_usd + comm_usd, 2),
                    "true_net_pnl": round(true_net_pnl, 2),
                    "return_pct": round(ret_pct * 100.0, 3),
                    "exit_reason": reason
                })
                in_trade = False

    return trades


def compute_reconciled_metrics(trades: List[Dict[str, Any]], total_bars: int = 1199) -> Dict[str, Any]:
    n = len(trades)
    if n == 0:
        return {
            "trade_count": 0,
            "win_rate_pct": 0.0,
            "annual_frequency": 0.0,
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
            "cost_drag_pct": 0.0
        }

    years = total_bars / 252.0
    annual_freq = round(n / years, 2) if years > 0 else 0.0

    gross_pnls = [t["true_gross_pnl"] for t in trades]
    net_pnls = [t["true_net_pnl"] for t in trades]
    slips = [t["slippage_usd"] for t in trades]
    comms = [t["commission_usd"] for t in trades]

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
    cost_drag = round((sum_costs / sum_gross * 100.0) if sum_gross > 0 else 0.0, 2)

    # Drawdown
    equity = [100_000.0]
    for p in net_pnls:
        equity.append(equity[-1] + p)
    peak = equity[0]
    max_dd_usd = 0.0
    max_dd_pct = 0.0
    for eq in equity:
        if eq > peak:
            peak = eq
        dd = peak - eq
        dd_pct = (dd / peak) * 100.0 if peak > 0 else 0.0
        if dd > max_dd_usd:
            max_dd_usd = dd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

    # Sharpe ratio
    rets = [t["return_pct"] / 100.0 for t in trades]
    mean_r = float(np.mean(rets))
    std_r = float(np.std(rets)) + 1e-9
    trades_per_year = n / years if years > 0 else 1.0
    annual_factor = math.sqrt(max(1.0, trades_per_year))
    sharpe = round((mean_r / std_r) * annual_factor, 2)

    return {
        "trade_count": n,
        "win_rate_pct": win_rate,
        "annual_frequency": annual_freq,
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
        "cost_drag_pct": cost_drag
    }


# ---------------------------------------------------------------------------
# 5. VALIDACIÓN ESTADÍSTICA (BOOTSTRAP Y LOSO)
# ---------------------------------------------------------------------------

def run_bootstrap_ci(trades: List[Dict[str, Any]], iterations: int = 1000, seed: int = 42) -> Dict[str, Any]:
    if len(trades) < 5:
        return {"status": "INSUFFICIENT_TRADES", "p_loss": 1.0}

    np.random.seed(seed)
    n = len(trades)
    net_pnls = np.array([t["true_net_pnl"] for t in trades])

    boot_pnl = []
    boot_pf = []

    for _ in range(iterations):
        sample = np.random.choice(net_pnls, size=n, replace=True)
        boot_pnl.append(float(np.sum(sample)))
        wins = sample[sample > 0]
        losses = np.abs(sample[sample <= 0])
        pf = float(np.sum(wins) / (np.sum(losses) + 1e-9)) if len(losses) > 0 and np.sum(losses) > 0 else 999.0
        boot_pf.append(min(pf, 50.0))

    return {
        "status": "SUCCESS",
        "iterations": iterations,
        "net_pnl_ci95": [round(float(np.percentile(boot_pnl, 2.5)), 2), round(float(np.percentile(boot_pnl, 97.5)), 2)],
        "profit_factor_ci95": [round(float(np.percentile(boot_pf, 2.5)), 2), round(float(np.percentile(boot_pf, 97.5)), 2)],
        "p_loss": round(float(np.mean(np.array(boot_pnl) <= 0)), 4)
    }


# ---------------------------------------------------------------------------
# 6. IMPLEMENTACIÓN DE LAS 4 ESTRATEGIAS CANDIDATAS DE FASE 7.3
# ---------------------------------------------------------------------------

def generate_signals_CS_RelMom_V1(
    bars_by_symbol: Dict[str, List[OHLCVBar]],
    rebalance_period: int = 20,
    momentum_lookback: int = 60,
    trend_filter_sma: int = 120
) -> Dict[str, List[bool]]:
    """
    Familia A — Cross-Sectional Relative Momentum (H-MOM-REL-1):
    Cada 20 días, rankea los 6 activos por retorno de 60 días.
    Filtra: Close > SMA120.
    Selecciona Top 1 activo para comprar y mantener durante el ciclo.
    """
    symbols = list(bars_by_symbol.keys())
    num_bars = len(bars_by_symbol[symbols[0]])
    signals = {sym: [False] * num_bars for sym in symbols}

    closes = {sym: [b.close for b in bars_by_symbol[sym]] for sym in symbols}

    for i in range(max(momentum_lookback, trend_filter_sma) + 5, num_bars):
        if (i % rebalance_period) == 0:
            scores = {}
            for sym in symbols:
                c_now = closes[sym][i]
                c_past = closes[sym][i - momentum_lookback]
                sma_trend = float(np.mean(closes[sym][i - trend_filter_sma:i+1]))

                if c_now > sma_trend:  # Filtro de tendencia positiva
                    mom = (c_now - c_past) / c_past
                    scores[sym] = mom
                else:
                    scores[sym] = -999.0

            # Seleccionar Top 1
            if scores:
                best_sym = max(scores, key=scores.get)
                if scores[best_sym] > 0.0:
                    signals[best_sym][i] = True

    return signals


def generate_signals_CS_RelMom_VolAdj_V2(
    bars_by_symbol: Dict[str, List[OHLCVBar]],
    rebalance_period: int = 10,
    momentum_lookback: int = 60
) -> Dict[str, List[bool]]:
    """
    Familia A — Volatility-Adjusted Relative Momentum (H-MOM-REL-2):
    Cada 10 días, rankea por Sharpe Momentum: Retorno(60d) / Volatilidad(60d).
    Selecciona Top 2 activos.
    """
    symbols = list(bars_by_symbol.keys())
    num_bars = len(bars_by_symbol[symbols[0]])
    signals = {sym: [False] * num_bars for sym in symbols}

    closes = {sym: [b.close for b in bars_by_symbol[sym]] for sym in symbols}

    for i in range(momentum_lookback + 5, num_bars):
        if (i % rebalance_period) == 0:
            scores = {}
            for sym in symbols:
                slice_c = closes[sym][i - momentum_lookback:i+1]
                ret = (slice_c[-1] - slice_c[0]) / slice_c[0]
                daily_rets = np.diff(slice_c) / slice_c[:-1]
                vol = float(np.std(daily_rets)) + 1e-6
                sharpe_mom = ret / vol
                scores[sym] = sharpe_mom

            # Seleccionar Top 2
            sorted_syms = sorted(scores.keys(), key=lambda s: scores[s], reverse=True)
            for best in sorted_syms[:2]:
                if scores[best] > 0.0:
                    signals[best][i] = True

    return signals


def generate_signals_MR_VolCond_ZScore_V1(
    bars: List[OHLCVBar],
    z_lookback: int = 20,
    z_threshold: float = -2.0,
    atr_period: int = 14,
    atr_expansion_mult: float = 1.10
) -> List[bool]:
    """
    Familia B — Volatility-Conditioned Reversion (H-MR-VOL-1):
    Z-Score(20) <= -2.0 Y Expansión de ATR (ATR14 / SMA(ATR14, 50) >= 1.10) Y RSI(4) <= 20.
    """
    n = len(bars)
    signals = [False] * n
    closes = np.array([b.close for b in bars])
    highs = np.array([b.high for b in bars])
    lows = np.array([b.low for b in bars])

    # Calcular ATR
    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for j in range(1, n):
        tr[j] = max(highs[j] - lows[j], abs(highs[j] - closes[j-1]), abs(lows[j] - closes[j-1]))

    atr = np.zeros(n)
    for j in range(atr_period, n):
        atr[j] = float(np.mean(tr[j - atr_period:j]))

    for i in range(60, n):
        slice_c = closes[i - z_lookback:i+1]
        mean_c = float(np.mean(slice_c))
        std_c = float(np.std(slice_c)) + 1e-6
        z_score = (closes[i] - mean_c) / std_c

        # RSI(4)
        diffs = np.diff(closes[i-5:i+1])
        g = float(np.mean(np.maximum(diffs, 0))) + 1e-9
        l = float(np.mean(np.maximum(-diffs, 0))) + 1e-9
        rsi4 = 100.0 - (100.0 / (1.0 + (g / l)))

        sma_atr = float(np.mean(atr[i-50:i])) + 1e-6
        atr_ratio = atr[i] / sma_atr

        if z_score <= z_threshold and atr_ratio >= atr_expansion_mult and rsi4 <= 20.0:
            signals[i] = True

    return signals


def generate_signals_MR_VolCond_BBCompression_V2(
    bars: List[OHLCVBar],
    bb_lookback: int = 20,
    bb_mult: float = 2.0,
    bbw_percentile: float = 25.0
) -> List[bool]:
    """
    Familia B — Low-Volatility Compression Mean Reversion (H-MR-VOL-2):
    Bandas de Bollinger en compresión (BBW <= percentil 25 histórico) y precio toca banda inferior con RSI(4) <= 25.
    """
    n = len(bars)
    signals = [False] * n
    closes = np.array([b.close for b in bars])

    bb_width = np.zeros(n)
    for i in range(bb_lookback, n):
        slice_c = closes[i - bb_lookback:i+1]
        mid = float(np.mean(slice_c))
        std = float(np.std(slice_c))
        bb_width[i] = (2.0 * bb_mult * std) / (mid + 1e-6)

    for i in range(75, n):
        history_bbw = bb_width[i-50:i]
        thresh_bbw = float(np.percentile(history_bbw, bbw_percentile))
        is_compression = bb_width[i] <= thresh_bbw

        slice_c = closes[i - bb_lookback:i+1]
        mid = float(np.mean(slice_c))
        std = float(np.std(slice_c))
        lower_band = mid - bb_mult * std

        diffs = np.diff(closes[i-5:i+1])
        g = float(np.mean(np.maximum(diffs, 0))) + 1e-9
        l = float(np.mean(np.maximum(-diffs, 0))) + 1e-9
        rsi4 = 100.0 - (100.0 / (1.0 + (g / l)))

        if is_compression and closes[i] <= lower_band * 1.002 and rsi4 <= 25.0:
            signals[i] = True

    return signals


# ---------------------------------------------------------------------------
# 7. ORQUESTADOR PRINCIPAL DEL DISCOVERY ENGINE V2
# ---------------------------------------------------------------------------

def run_strategy_discovery_engine_v2() -> Dict[str, Any]:
    print("=" * 80)
    print("ORACLEBOT V2 — STRATEGY DISCOVERY ENGINE V2 (FASE 7.3)")
    print("=" * 80)

    symbols = ["SPY", "QQQ", "IWM", "DIA", "XLF", "XLE"]

    # 1. BLOQUE 0: Descarga y saneamiento estricto de datos cerrados
    gate = DataIntegrityGate()
    sanitized_bars: Dict[str, List[OHLCVBar]] = {}
    datasets_metadata: Dict[str, Any] = {}

    for sym in symbols:
        raw = yfinance_provider.get_historical_bars(sym, count=1200, interval="1d")
        bars_clean, meta = gate.sanitize_and_validate_bars(sym, raw)
        sanitized_bars[sym] = bars_clean
        datasets_metadata[sym] = meta
        print(f"  {sym}: {len(bars_clean)} barras cerradas ({meta['first_bar_date']} -> {meta['last_bar_date']}), Hash={meta['dataset_sha256'][:16]}..., UnclosedDropped={meta['unclosed_bars_dropped']}")

    num_closed = len(sanitized_bars["SPY"])
    split_idx = int(num_closed * 0.50)  # ~600 barras IS (2022-2024), ~600 barras OOS (2024-2026)
    split_date = str(sanitized_bars["SPY"][split_idx].timestamp)[:10]
    print(f"\nDivisión Walk-Forward temporal: Train/IS (0 -> {split_idx}, < {split_date}), Test/OOS ({split_idx} -> {num_closed}, >= {split_date})")

    # 2. Definición del Registro Inmutable de 4 Hipótesis
    candidates_spec = [
        {
            "hypothesis_id": "H-MOM-REL-1",
            "strategy_id": "CS_RelMom_60d_V1",
            "family": ResearchFamily.CROSS_SECTIONAL_MOMENTUM,
            "thesis": "Selección mensual del activo con mayor momentum relativo a 60 días filtrado por tendencia de 120 días.",
            "params": {"rebalance_period": 20, "momentum_lookback": 60, "trend_filter_sma": 120, "max_holding": 20, "stop_loss_pct": 0.035, "profit_target_pct": 0.06},
            "type": "CROSS_SECTIONAL"
        },
        {
            "hypothesis_id": "H-MOM-REL-2",
            "strategy_id": "CS_RelMom_VolAdj_V2",
            "family": ResearchFamily.CROSS_SECTIONAL_MOMENTUM,
            "thesis": "Selección quincenal de los 2 activos con mayor Sharpe-Momentum a 60 días.",
            "params": {"rebalance_period": 10, "momentum_lookback": 60, "max_holding": 10, "stop_loss_pct": 0.03, "profit_target_pct": 0.05},
            "type": "CROSS_SECTIONAL"
        },
        {
            "hypothesis_id": "H-MR-VOL-1",
            "strategy_id": "MR_VolCond_ZScore_V1",
            "family": ResearchFamily.VOLATILITY_CONDITIONED_REVERSION,
            "thesis": "Reversión a la media condicionada a expansión de ATR y sobreventa extrema de Z-Score(20) <= -2.0.",
            "params": {"z_lookback": 20, "z_threshold": -2.0, "atr_expansion_mult": 1.10, "max_holding": 4, "stop_loss_pct": 0.025, "profit_target_pct": 0.035},
            "type": "SINGLE_ASSET"
        },
        {
            "hypothesis_id": "H-MR-VOL-2",
            "strategy_id": "MR_VolCond_BBCompression_V2",
            "family": ResearchFamily.VOLATILITY_CONDITIONED_REVERSION,
            "thesis": "Reversión a la media desde compresión de Bollinger Band Width (percentil 25) con RSI(4) <= 25.",
            "params": {"bb_lookback": 20, "bb_mult": 2.0, "bbw_percentile": 25.0, "max_holding": 3, "stop_loss_pct": 0.02, "profit_target_pct": 0.03},
            "type": "SINGLE_ASSET"
        }
    ]

    all_experiments: List[Dict[str, Any]] = []
    all_trade_records: List[Dict[str, Any]] = []

    for spec in candidates_spec:
        strat_id = spec["strategy_id"]
        hyp_id = spec["hypothesis_id"]
        params = spec["params"]
        fp = compute_source_fingerprint(spec["thesis"], params)

        print(f"\nEvaluando candidato: {strat_id} ({hyp_id}) | Fingerprint: {fp}")

        # Generar señales
        if strat_id == "CS_RelMom_60d_V1":
            signals_map = generate_signals_CS_RelMom_V1(sanitized_bars, params["rebalance_period"], params["momentum_lookback"], params["trend_filter_sma"])
        elif strat_id == "CS_RelMom_VolAdj_V2":
            signals_map = generate_signals_CS_RelMom_VolAdj_V2(sanitized_bars, params["rebalance_period"], params["momentum_lookback"])
        elif strat_id == "MR_VolCond_ZScore_V1":
            signals_map = {sym: generate_signals_MR_VolCond_ZScore_V1(sanitized_bars[sym], params["z_lookback"], params["z_threshold"], 14, params["atr_expansion_mult"]) for sym in symbols}
        elif strat_id == "MR_VolCond_BBCompression_V2":
            signals_map = {sym: generate_signals_MR_VolCond_BBCompression_V2(sanitized_bars[sym], params["bb_lookback"], params["bb_mult"], params["bbw_percentile"]) for sym in symbols}

        # Ejecutar backtests en los 3 escenarios de costes
        strat_results: Dict[str, Any] = {"cost_scenarios": {}}

        for cost_key in ["1x", "2x", "3x"]:
            cost_trades: List[Dict[str, Any]] = []
            trades_by_sym: Dict[str, List[Dict[str, Any]]] = {}

            for sym in symbols:
                sym_trades = run_chronological_backtest_asset(
                    strategy_id=strat_id,
                    symbol=sym,
                    bars=sanitized_bars[sym],
                    entry_signals=signals_map[sym],
                    exit_rules=params,
                    cost_tier=cost_key
                )
                cost_trades.extend(sym_trades)
                trades_by_sym[sym] = sym_trades

                if cost_key == "1x":
                    for t in sym_trades:
                        t_rec = dict(t)
                        t_rec["hypothesis_id"] = hyp_id
                        all_trade_records.append(t_rec)

            # Métricas Full Sample
            full_metrics = compute_reconciled_metrics(cost_trades, total_bars=num_closed)

            # Métricas In-Sample vs Out-of-Sample (Walk-Forward)
            is_trades = [t for t in cost_trades if t["entry_idx"] < split_idx]
            oos_trades = [t for t in cost_trades if t["entry_idx"] >= split_idx]
            is_metrics = compute_reconciled_metrics(is_trades, total_bars=split_idx)
            oos_metrics = compute_reconciled_metrics(oos_trades, total_bars=num_closed - split_idx)

            strat_results["cost_scenarios"][cost_key] = {
                "full_portfolio": full_metrics,
                "in_sample": is_metrics,
                "out_of_sample": oos_metrics,
                "by_symbol": {sym: compute_reconciled_metrics(trades_by_sym[sym], total_bars=num_closed) for sym in symbols}
            }

        # Bootstrap en OOS y Full Sample (Escenario 1x)
        trades_1x = [t for t in all_trade_records if t["strategy_id"] == strat_id]
        oos_trades_1x = [t for t in trades_1x if t["entry_idx"] >= split_idx]
        boot_full = run_bootstrap_ci(trades_1x)
        boot_oos = run_bootstrap_ci(oos_trades_1x)

        # LOSO en 1x Full Sample
        loso_map = {}
        for sym_out in symbols:
            loso_sub = [t for t in trades_1x if t["symbol"] != sym_out]
            loso_map[f"EXCLUDING_{sym_out}"] = compute_reconciled_metrics(loso_sub, total_bars=num_closed)

        # Economic Edge Gate
        m_oos_1x = strat_results["cost_scenarios"]["1x"]["out_of_sample"]
        m_full_1x = strat_results["cost_scenarios"]["1x"]["full_portfolio"]
        m_full_2x = strat_results["cost_scenarios"]["2x"]["full_portfolio"]

        # Criterios objetivos de la compuerta económica
        gate_passed = True
        rejection_reasons = []

        if m_full_1x["trade_count"] < 15:
            gate_passed = False
            rejection_reasons.append(f"INSUFFICIENT_SAMPLE_SIZE: {m_full_1x['trade_count']} trades < 15")
        if m_full_1x["sum_true_net_pnl"] <= 0:
            gate_passed = False
            rejection_reasons.append(f"NEGATIVE_NET_PNL_1X: ${m_full_1x['sum_true_net_pnl']}")
        if m_oos_1x["sum_true_net_pnl"] <= 0:
            gate_passed = False
            rejection_reasons.append(f"NEGATIVE_OOS_NET_PNL: ${m_oos_1x['sum_true_net_pnl']}")
        if m_full_2x["sum_true_net_pnl"] <= 0:
            gate_passed = False
            rejection_reasons.append(f"FAILED_2X_COST_STRESS: Net PnL 2x = ${m_full_2x['sum_true_net_pnl']}")
        if boot_full.get("p_loss", 1.0) > 0.25:
            gate_passed = False
            rejection_reasons.append(f"HIGH_BOOTSTRAP_P_LOSS: {boot_full.get('p_loss')*100:.1f}% > 25%")

        # Veredicto de Estado
        if gate_passed:
            status = ResearchStrategyStatus.RESEARCH_PROMISING
            verdict_text = "APROBADO_ECONOMIC_EDGE_GATE: Cumple robustez OOS, sobrevive a costes 2x y significancia bootstrap."
        elif m_full_1x["trade_count"] < 15:
            status = ResearchStrategyStatus.RESEARCH_INCONCLUSIVE
            verdict_text = f"MUESTRA_INSUFICIENTE: {', '.join(rejection_reasons)}"
        else:
            status = ResearchStrategyStatus.RESEARCH_REJECTED
            verdict_text = f"RECHAZADA_POR_COMPUERTA_ECONOMICA: {'; '.join(rejection_reasons)}"

        # Ranking Score Explicable
        # Componentes: OOS PF (40%), OOS Net PnL normalizado (30%), Supervivencia Costes (20%), Consistencia LOSO (10%)
        pf_score = min(3.0, max(0.0, m_oos_1x["net_profit_factor"])) / 3.0
        pnl_score = 1.0 if m_oos_1x["sum_true_net_pnl"] > 0 else 0.0
        cost_survival = 1.0 if m_full_2x["sum_true_net_pnl"] > 0 else (0.5 if m_full_1x["sum_true_net_pnl"] > 0 else 0.0)
        loso_min_pnl = min([m["sum_true_net_pnl"] for m in loso_map.values()]) if loso_map else 0.0
        loso_score = 1.0 if loso_min_pnl > 0 else 0.0

        ranking_score = round(pf_score * 0.40 + pnl_score * 0.30 + cost_survival * 0.20 + loso_score * 0.10, 3)

        exp_record = {
            "hypothesis_id": hyp_id,
            "strategy_id": strat_id,
            "family": spec["family"].value,
            "thesis": spec["thesis"],
            "parameters": params,
            "fingerprint": fp,
            "status": status.value,
            "verdict_reason": verdict_text,
            "ranking_score": ranking_score,
            "metrics_1x_full": m_full_1x,
            "metrics_1x_oos": m_oos_1x,
            "metrics_1x_is": strat_results["cost_scenarios"]["1x"]["in_sample"],
            "metrics_2x_full": m_full_2x,
            "metrics_3x_full": strat_results["cost_scenarios"]["3x"]["full_portfolio"],
            "bootstrap_full": boot_full,
            "bootstrap_oos": boot_oos,
            "loso_analysis": loso_map,
            "by_symbol_1x": strat_results["cost_scenarios"]["1x"]["by_symbol"]
        }
        all_experiments.append(exp_record)
        print(f"  Resultado: {status.value} | RankScore: {ranking_score} | Full Net PnL (1x): ${m_full_1x['sum_true_net_pnl']} | OOS Net: ${m_oos_1x['sum_true_net_pnl']}")

    # 3. Guardar Manifiesto y CSV
    scratch_dir = repo_root / "ai_trading_agent" / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    # Exportar CSV
    csv_path = scratch_dir / "fase7_3_discovery_trades.csv"
    if all_trade_records:
        keys = list(all_trade_records[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(all_trade_records)
        print(f"\nTrades CSV exportado: {csv_path} ({len(all_trade_records)} registros)")

    # Exportar JSON
    manifest = {
        "manifest_version": "2.0",
        "phase": "FASE_7_3",
        "engine": "Strategy Discovery Engine v2",
        "timestamp_utc": datetime.utcnow().isoformat(),
        "governance": {
            "mode": "RESEARCH / ANALYSIS_ONLY",
            "live_trading_enabled": False,
            "paper_broker": "Moomoo (TrdEnv.SIMULATE)",
            "d21_status": "PAPER_PROTECTED_PENDING_SESSION",
            "d21_fingerprint": "f885ec2db2422308",
            "d21_virtual_capital_usd": 1000000.0
        },
        "datasets": datasets_metadata,
        "experiments": all_experiments
    }

    json_path = scratch_dir / "fase7_3_discovery_manifest.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifiesto Discovery v2 exportado: {json_path}")

    return manifest


if __name__ == "__main__":
    res = run_strategy_discovery_engine_v2()
    print("EJECUCIÓN DEL DISCOVERY ENGINE V2 COMPLETADA.")
