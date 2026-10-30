"""
ai_trading_agent.strategy_lab.experiments.exp_st01.robustness_engine
===================================================================
Motor de Validación Cuantitativa y Robustez Multidimensional para ST_EMA200_V1.

Módulos:
1. Split Cronológico (60% Dev / 20% Val / 20% OOS).
2. Walk-Forward Chronological Analysis (IS vs OOS Efficiency).
3. Simulación Monte Carlo (1,000 bootstraps con reemplazo y permutación de trades).
4. Grid de Sensibilidad Paramétrica (EMA, ATR, Multiplier, TP R).
5. Estrés de Costes Multitier (1x Base, 2x Moderado, 3x Severo).
6. Clasificación de Regímenes de Mercado (Trending Bull/Bear, Ranging, High/Low Vol).
7. Cálculo de Scores Cuantitativos: EES, PRS, SQS y Minimum Evidence Gate.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import math
import numpy as np
import pandas as pd

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.experiments.exp_st01.supertrend_indicator import SuperTrendCalculator
from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_strategy import StEma200Strategy, TradeDirection
from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_backtester import (
    StEma200Backtester,
    TradeRecordST,
    BacktestMetricsST,
    COST_TIERS,
    CostModelST,
)


@dataclass
class ChronoSplitResult:
    dev_trades: int
    dev_net_pnl: float
    dev_pf: float
    dev_win_rate: float
    val_trades: int
    val_net_pnl: float
    val_pf: float
    val_win_rate: float
    oos_trades: int
    oos_net_pnl: float
    oos_pf: float
    oos_win_rate: float
    oos_dev_ratio: float  # oos_net_pnl / dev_net_pnl normalizado


@dataclass
class WalkForwardWindow:
    window_id: int
    is_start: str
    is_end: str
    is_trades: int
    is_net_pnl: float
    is_pf: float
    oos_start: str
    oos_end: str
    oos_trades: int
    oos_net_pnl: float
    oos_pf: float
    wfe_ratio: float  # Walk-forward efficiency


@dataclass
class MonteCarloMetrics:
    iterations: int
    prob_positive_expectancy: float
    median_pnl: float
    ci_95_lower_pnl: float
    ci_95_upper_pnl: float
    median_max_dd_usd: float
    ci_95_max_dd_usd: float
    var_95_pnl: float


@dataclass
class CostStressResult:
    tier_1x_pnl: float
    tier_1x_pf: float
    tier_2x_pnl: float
    tier_2x_pf: float
    tier_3x_pnl: float
    tier_3x_pf: float
    cost_fragility_ratio: float  # (pnl_1x - pnl_3x) / pnl_1x


@dataclass
class RegimePerformance:
    regime: str
    trades: int
    net_pnl: float
    win_rate: float
    profit_factor: float


@dataclass
class StrategyScoresST:
    economic_edge_score: float  # EES (0-100)
    pure_robustness_score: float  # PRS (0-100)
    evidence_score: float  # (0-100)
    oos_consistency_score: float  # (0-100)
    slippage_resilience_score: float  # (0-100)
    simplicity_score: float  # (0-100)
    strategy_quality_score: float  # SQS (0-100)
    passed_minimum_gate: bool
    gate_failure_reasons: List[str]


class RobustnessEngineST:
    """Motor integral de robustez y certificación cuantitativa para ST_EMA200_V1."""

    def __init__(self, initial_equity: float = 100000.0, risk_per_trade: float = 250.0):
        self.initial_equity = initial_equity
        self.risk_per_trade = risk_per_trade

    def evaluate_chrono_split(self, symbol: str, timeframe: str, bars: List[OHLCVBar]) -> ChronoSplitResult:
        """Divide las barras en 60% Dev, 20% Val, 20% OOS cronológico y evalúa."""
        n = len(bars)
        if n < 100:
            return ChronoSplitResult(0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, 0.0, 0.0)

        idx_dev_end = int(n * 0.60)
        idx_val_end = int(n * 0.80)

        dev_bars = bars[:idx_dev_end]
        val_bars = bars[idx_dev_end:idx_val_end]
        oos_bars = bars[idx_val_end:]

        strat = StEma200Strategy()
        bt = StEma200Backtester(strat, self.initial_equity, self.risk_per_trade)

        m_dev, _ = bt.run(symbol, timeframe, dev_bars)
        m_val, _ = bt.run(symbol, timeframe, val_bars)
        m_oos, _ = bt.run(symbol, timeframe, oos_bars)

        # Normalizar ratio OOS / Dev por número de barras
        dev_daily_rate = (m_dev.net_pnl / len(dev_bars)) if len(dev_bars) > 0 else 0.0
        oos_daily_rate = (m_oos.net_pnl / len(oos_bars)) if len(oos_bars) > 0 else 0.0
        ratio = (oos_daily_rate / dev_daily_rate) if abs(dev_daily_rate) > 1e-4 else 0.0

        return ChronoSplitResult(
            dev_trades=m_dev.total_trades,
            dev_net_pnl=m_dev.net_pnl,
            dev_pf=m_dev.profit_factor,
            dev_win_rate=m_dev.win_rate,
            val_trades=m_val.total_trades,
            val_net_pnl=m_val.net_pnl,
            val_pf=m_val.profit_factor,
            val_win_rate=m_val.win_rate,
            oos_trades=m_oos.total_trades,
            oos_net_pnl=m_oos.net_pnl,
            oos_pf=m_oos.profit_factor,
            oos_win_rate=m_oos.win_rate,
            oos_dev_ratio=ratio,
        )

    def evaluate_walk_forward(self, symbol: str, timeframe: str, bars: List[OHLCVBar], n_windows: int = 4) -> List[WalkForwardWindow]:
        """Aplica Walk-Forward anclado/rodante sobre n ventanas cronológicas."""
        n = len(bars)
        if n < 400:
            return []

        step = n // (n_windows + 1)
        windows: List[WalkForwardWindow] = []
        strat = StEma200Strategy()
        bt = StEma200Backtester(strat, self.initial_equity, self.risk_per_trade)

        for w in range(n_windows):
            is_start_idx = 0
            is_end_idx = step * (w + 1)
            oos_start_idx = is_end_idx
            oos_end_idx = min(n, is_end_idx + step)

            if oos_end_idx <= oos_start_idx:
                break

            is_bars = bars[is_start_idx:is_end_idx]
            oos_bars = bars[oos_start_idx:oos_end_idx]

            m_is, _ = bt.run(symbol, timeframe, is_bars)
            m_oos, _ = bt.run(symbol, timeframe, oos_bars)

            is_rate = m_is.net_pnl / len(is_bars) if len(is_bars) > 0 else 0.0
            oos_rate = m_oos.net_pnl / len(oos_bars) if len(oos_bars) > 0 else 0.0
            wfe = (oos_rate / is_rate) if abs(is_rate) > 1e-4 else 0.0

            windows.append(
                WalkForwardWindow(
                    window_id=w + 1,
                    is_start=is_bars[0].timestamp.strftime("%Y-%m-%d"),
                    is_end=is_bars[-1].timestamp.strftime("%Y-%m-%d"),
                    is_trades=m_is.total_trades,
                    is_net_pnl=m_is.net_pnl,
                    is_pf=m_is.profit_factor,
                    oos_start=oos_bars[0].timestamp.strftime("%Y-%m-%d"),
                    oos_end=oos_bars[-1].timestamp.strftime("%Y-%m-%d"),
                    oos_trades=m_oos.total_trades,
                    oos_net_pnl=m_oos.net_pnl,
                    oos_pf=m_oos.profit_factor,
                    wfe_ratio=wfe,
                )
            )

        return windows

    def evaluate_monte_carlo(self, trades: List[TradeRecordST], n_iterations: int = 1000) -> MonteCarloMetrics:
        """Simulación Monte Carlo: Bootstrap con reemplazo y permutación de orden."""
        if not trades:
            return MonteCarloMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        pnls = [t.net_pnl for t in trades]
        n_trades = len(pnls)

        sim_pnls: List[float] = []
        sim_max_dds: List[float] = []

        np.random.seed(42)
        for _ in range(n_iterations):
            # Resample con reemplazo
            resampled = np.random.choice(pnls, size=n_trades, replace=True)
            total_pnl = float(np.sum(resampled))
            sim_pnls.append(total_pnl)

            # Permutación para DD
            perm = np.random.permutation(resampled)
            cum = np.cumsum(perm)
            peak = 0.0
            max_dd = 0.0
            for val in cum:
                if val > peak:
                    peak = val
                dd = peak - val
                if dd > max_dd:
                    max_dd = dd
            sim_max_dds.append(max_dd)

        sim_pnls = sorted(sim_pnls)
        sim_max_dds = sorted(sim_max_dds)

        prob_pos = sum(1 for p in sim_pnls if p > 0) / n_iterations
        median_pnl = float(np.median(sim_pnls))
        ci_lower = sim_pnls[int(0.025 * n_iterations)]
        ci_upper = sim_pnls[int(0.975 * n_iterations)]
        var_95 = sim_pnls[int(0.05 * n_iterations)]
        median_dd = float(np.median(sim_max_dds))
        ci_dd = sim_max_dds[int(0.95 * n_iterations)]

        return MonteCarloMetrics(
            iterations=n_iterations,
            prob_positive_expectancy=prob_pos,
            median_pnl=median_pnl,
            ci_95_lower_pnl=ci_lower,
            ci_95_upper_pnl=ci_upper,
            median_max_dd_usd=median_dd,
            ci_95_max_dd_usd=ci_dd,
            var_95_pnl=var_95,
        )

    def evaluate_cost_stress(self, symbol: str, timeframe: str, bars: List[OHLCVBar]) -> CostStressResult:
        """Prueba de estrés en 3 niveles de costes (1x Base, 2x Moderado, 3x Severo)."""
        strat = StEma200Strategy()
        bt = StEma200Backtester(strat, self.initial_equity, self.risk_per_trade)

        m1, _ = bt.run(symbol, timeframe, bars, cost_tier_override=COST_TIERS["1x"])
        m2, _ = bt.run(symbol, timeframe, bars, cost_tier_override=COST_TIERS["2x"])
        m3, _ = bt.run(symbol, timeframe, bars, cost_tier_override=COST_TIERS["3x"])

        fragility = ((m1.net_pnl - m3.net_pnl) / m1.net_pnl) if abs(m1.net_pnl) > 1.0 else 1.0

        return CostStressResult(
            tier_1x_pnl=m1.net_pnl,
            tier_1x_pf=m1.profit_factor,
            tier_2x_pnl=m2.net_pnl,
            tier_2x_pf=m2.profit_factor,
            tier_3x_pnl=m3.net_pnl,
            tier_3x_pf=m3.profit_factor,
            cost_fragility_ratio=fragility,
        )

    def evaluate_market_regimes(self, bars: List[OHLCVBar], trades: List[TradeRecordST]) -> List[RegimePerformance]:
        """Clasifica los resultados por régimen bursátil (Bull, Bear, Ranging, High Vol, Low Vol)."""
        if not trades or len(bars) < 200:
            return []

        # Calcular ATR histórico para percentiles de volatilidad
        calc = SuperTrendCalculator()
        pts = calc.calculate_series(bars)
        pt_map = {p.timestamp: p for p in pts}

        atrs = [p.atr for p in pts if p.atr > 0]
        p25_atr = float(np.percentile(atrs, 25)) if atrs else 0.0
        p75_atr = float(np.percentile(atrs, 75)) if atrs else 0.0

        regimes_dict: Dict[str, List[TradeRecordST]] = {
            "BULL_TREND": [],
            "BEAR_TREND": [],
            "RANGING": [],
            "HIGH_VOLATILITY": [],
            "LOW_VOLATILITY": [],
        }

        for t in trades:
            pt = pt_map.get(t.entry_time)
            if not pt or pt.ema_200 is None:
                continue

            # Tendencia
            diff_pct = (pt.close - pt.ema_200) / pt.ema_200
            if diff_pct > 0.01:
                regimes_dict["BULL_TREND"].append(t)
            elif diff_pct < -0.01:
                regimes_dict["BEAR_TREND"].append(t)
            else:
                regimes_dict["RANGING"].append(t)

            # Volatilidad
            if pt.atr >= p75_atr:
                regimes_dict["HIGH_VOLATILITY"].append(t)
            elif pt.atr <= p25_atr:
                regimes_dict["LOW_VOLATILITY"].append(t)

        results: List[RegimePerformance] = []
        for reg, tr_list in regimes_dict.items():
            tot = len(tr_list)
            if tot == 0:
                results.append(RegimePerformance(reg, 0, 0.0, 0.0, 0.0))
                continue
            wins = [x for x in tr_list if x.net_pnl > 0]
            losses = [x for x in tr_list if x.net_pnl <= 0]
            win_r = (len(wins) / tot) * 100.0
            net = sum(x.net_pnl for x in tr_list)
            g_win = sum(x.net_pnl for x in wins)
            g_loss = abs(sum(x.net_pnl for x in losses))
            pf = (g_win / g_loss) if g_loss > 0 else (999.0 if g_win > 0 else 0.0)
            results.append(RegimePerformance(reg, tot, net, win_r, pf))

        return results

    def evaluate_parameter_sensitivity(self, symbol: str, timeframe: str, bars: List[OHLCVBar]) -> List[Dict[str, Any]]:
        """Evalúa un grid reducido pero informativo de parámetros sobre el activo."""
        if len(bars) < 250:
            return []

        grid_ema = [100, 150, 200, 250]
        grid_atr = [7, 10, 14, 21]
        grid_mult = [2.0, 2.5, 3.0, 3.5]
        grid_tp_r = [1.0, 1.5, 2.0]

        results = []
        # Evaluar variación one-at-a-time respecto al baseline (200, 10, 3.0, 1.5)
        # 1. Variar EMA
        for ema in grid_ema:
            st = StEma200Strategy(ema_period=ema, atr_period=10, supertrend_multiplier=3.0, tp_r_multiple=1.5)
            bt = StEma200Backtester(st, self.initial_equity, self.risk_per_trade)
            m, _ = bt.run(symbol, timeframe, bars)
            results.append({"param": "EMA", "value": ema, "trades": m.total_trades, "net_pnl": m.net_pnl, "pf": m.profit_factor, "win_rate": m.win_rate})

        # 2. Variar ATR
        for atr in grid_atr:
            st = StEma200Strategy(ema_period=200, atr_period=atr, supertrend_multiplier=3.0, tp_r_multiple=1.5)
            bt = StEma200Backtester(st, self.initial_equity, self.risk_per_trade)
            m, _ = bt.run(symbol, timeframe, bars)
            results.append({"param": "ATR_PERIOD", "value": atr, "trades": m.total_trades, "net_pnl": m.net_pnl, "pf": m.profit_factor, "win_rate": m.win_rate})

        # 3. Variar Multiplier
        for mult in grid_mult:
            st = StEma200Strategy(ema_period=200, atr_period=10, supertrend_multiplier=mult, tp_r_multiple=1.5)
            bt = StEma200Backtester(st, self.initial_equity, self.risk_per_trade)
            m, _ = bt.run(symbol, timeframe, bars)
            results.append({"param": "ST_MULTIPLIER", "value": mult, "trades": m.total_trades, "net_pnl": m.net_pnl, "pf": m.profit_factor, "win_rate": m.win_rate})

        # 4. Variar TP R
        for r in grid_tp_r:
            st = StEma200Strategy(ema_period=200, atr_period=10, supertrend_multiplier=3.0, tp_r_multiple=r)
            bt = StEma200Backtester(st, self.initial_equity, self.risk_per_trade)
            m, _ = bt.run(symbol, timeframe, bars)
            results.append({"param": "TP_R_MULTIPLE", "value": r, "trades": m.total_trades, "net_pnl": m.net_pnl, "pf": m.profit_factor, "win_rate": m.win_rate})

        return results

    def compute_scores(
        self,
        metrics: BacktestMetricsST,
        mc: MonteCarloMetrics,
        cost_stress: CostStressResult,
        chrono: ChronoSplitResult,
    ) -> StrategyScoresST:
        """Calcula EES, PRS, SQS y verifica el Minimum Evidence Gate."""
        # 1. Economic Edge Score (0-100)
        # Basado en Profit Factor, Expectancy R y Sharpe
        pf_score = min(max((metrics.profit_factor - 1.0) / 1.5 * 40.0, 0.0), 40.0) if metrics.profit_factor > 1.0 else 0.0
        exp_score = min(max(metrics.expectancy_r / 0.5 * 30.0, 0.0), 30.0) if metrics.expectancy_r > 0 else 0.0
        sharpe_score = min(max(metrics.sharpe_ratio / 2.0 * 30.0, 0.0), 30.0) if metrics.sharpe_ratio > 0 else 0.0
        ees = pf_score + exp_score + sharpe_score

        # 2. Pure Robustness Score (0-100)
        # Basado en MC prob positive (40%), WFE/OOS consistency (30%), DD ratio (30%)
        mc_score = mc.prob_positive_expectancy * 40.0
        oos_ratio_capped = min(max(chrono.oos_dev_ratio, 0.0), 1.5) / 1.5 * 30.0
        dd_ratio = max(0.0, 30.0 - (metrics.max_drawdown_pct / 10.0 * 30.0))
        prs = mc_score + oos_ratio_capped + dd_ratio

        # 3. Componentes adicionales
        evidence_score = min(metrics.total_trades / 50.0 * 100.0, 100.0)
        oos_score = min(max(chrono.oos_pf / 2.0 * 100.0, 0.0), 100.0)
        slip_resilience = max(0.0, (1.0 - max(0.0, cost_stress.cost_fragility_ratio)) * 100.0)
        simplicity_score = 90.0  # Estrategia de 2 indicadores sin redes complejas

        # 4. SQS ponderado: 30% EES + 30% PRS + 15% Evidence + 10% OOS + 10% Slippage + 5% Simplicity
        sqs = (
            0.30 * ees
            + 0.30 * prs
            + 0.15 * evidence_score
            + 0.10 * oos_score
            + 0.10 * slip_resilience
            + 0.05 * simplicity_score
        )

        # 5. Minimum Evidence Gate
        gate_failures = []
        if metrics.total_trades < 30:
            gate_failures.append(f"Muestra insuficiente de trades ({metrics.total_trades} < 30)")
        if metrics.profit_factor < 1.15:
            gate_failures.append(f"Profit Factor insuficiente ({metrics.profit_factor:.2f} < 1.15)")
        if metrics.net_pnl <= 0:
            gate_failures.append(f"Net PnL no positivo (${metrics.net_pnl:.2f} <= $0)")
        if cost_stress.tier_2x_pnl <= 0:
            gate_failures.append("Falla bajo estrés de costes 2x (Net PnL <= 0)")
        if mc.prob_positive_expectancy < 0.80:
            gate_failures.append(f"Probabilidad Bootstrap positiva baja ({mc.prob_positive_expectancy*100:.1f}% < 80%)")

        passed = len(gate_failures) == 0

        return StrategyScoresST(
            economic_edge_score=round(ees, 2),
            pure_robustness_score=round(prs, 2),
            evidence_score=round(evidence_score, 2),
            oos_consistency_score=round(oos_score, 2),
            slippage_resilience_score=round(slip_resilience, 2),
            simplicity_score=round(simplicity_score, 2),
            strategy_quality_score=round(sqs, 2),
            passed_minimum_gate=passed,
            gate_failure_reasons=gate_failures,
        )
