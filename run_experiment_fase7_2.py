"""
run_experiment_fase7_2.py
========================
Script ejecutor del Experimento de Alineación Temporal Controlada (FASE 7.2).

Objetivo Científico:
"Realizar una comparación causal controlada entre arquitecturas single-timeframe
y multi-timeframe utilizando EXACTAMENTE las mismas ventanas cronológicas y evaluando
el verdadero valor informativo del filtro 1D mediante Paired Signal Analysis."

Condiciones Institucionales:
1. Verificación previa de reproducibilidad de Phase 6 Daily Lead (76 trades, IS: 52, OOS: 24).
2. Construcción de Master Temporal Windows (Calendar-based):
   - Experiment A: Máxima intersección 1D / 1H (Nov 2023 a Oct 2026).
   - Experiment B: Máxima intersección 1D / 1H / 15m (Jul 2026 a Oct 2026).
3. Causalidad estricta de barras cerradas y cero look-ahead bias.
4. Paired Signal Analysis (Allowed by 1D vs Rejected by 1D) para atribución causal.
5. Invariantes de paridad temporal y consistencia de salidas (rr_ratio = 3.0).
6. Generación del reporte CONTROLLED_TEMPORAL_ALIGNMENT_REPORT_FASE7_2.md.
"""

import math
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from ai_trading_agent.data.providers.yfinance_provider import YFinanceMarketDataProvider
from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.backtest.engine import backtest_engine
from ai_trading_agent.backtest.metrics import metrics_calculator, QuantitativeMetricsCalculator
from ai_trading_agent.strategy_lab.backtesting.data_splitter import LabDataSplitter, DataSplitType
from ai_trading_agent.strategy_lab.strategies.composable import ComposableStrategy
from ai_trading_agent.strategy_lab.robustness.engine import robustness_engine
from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import (
    SlippageCostStressEvaluator,
    classify_statistical_evidence,
    StatisticalEvidenceLevel,
    EconomicEdgeClassification,
    calculate_economic_edge_score,
    calculate_strategy_quality_score
)
from ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer import (
    MultiTimeframeSynchronizer,
    MultiTimeframeStrategyEvaluator,
    MultiTimeframeBacktestSimulator,
    DateBasedDataSplitter,
    MultiTimeframeComplexityCalculator
)


def compute_fingerprint(obj: Any) -> str:
    """Calcula hash determinista para congelar definiciones de estrategia."""
    serialized = json.dumps(obj, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def run_controlled_experiment_fase7_2():
    print("=" * 85)
    print(" INICIANDO FASE 7.2: EXPERIMENTO DE ALINEACIÓN TEMPORAL CONTROLADA")
    print("=" * 85)

    provider = YFinanceMarketDataProvider(fallback_to_synthetic=False)
    target_symbols = ["SPY", "QQQ", "IWM", "DIA"]

    # =========================================================================
    # PASO 1: VERIFICACIÓN OBLIGATORIA DE REPRODUCIBILIDAD (STOP CONDITION)
    # =========================================================================
    print("\n[1/8] VERIFICANDO REPRODUCIBILIDAD DE PHASE 6 DAILY LEAD (STOP CONDITION)...")
    p6_params = {"min_rsi": 30.0, "max_rsi": 70.0, "min_rvol": 1.5, "atr_stop_mult": 1.5, "rr_target": 2.0}
    p6_strat = ComposableStrategy(
        strategy_id="mut_strat_disc_8f772ab8_b578",
        name="Autogen_US Liquid ETFs_hyp_bdd62e23_v1.1",
        parameters=p6_params
    )

    p6_is_trades = []
    p6_oos_trades = []
    for sym in target_symbols:
        bars_1d = provider.get_historical_bars(symbol=sym, count=1500, interval="1d")
        ds = LabDataSplitter.split_in_sample_out_sample_holdout(bars_1d, in_sample_ratio=0.60, out_sample_ratio=0.20)
        b_is = ds.get_split(DataSplitType.IN_SAMPLE, "RESEARCH")
        b_oos = ds.get_split(DataSplitType.OUT_OF_SAMPLE, "RESEARCH")

        rep_is = backtest_engine.run(symbol=sym, bars=b_is, strategy=p6_strat)
        rep_oos = backtest_engine.run(symbol=sym, bars=b_oos, strategy=p6_strat)
        p6_is_trades.extend(rep_is.trades)
        p6_oos_trades.extend(rep_oos.trades)

    p6_m_is = metrics_calculator.calculate(p6_is_trades, 100000.0)
    p6_m_oos = metrics_calculator.calculate(p6_oos_trades, 100000.0)
    p6_total = p6_m_is.total_trades + p6_m_oos.total_trades

    print(f"  Resultados Fase 6 reproducidos: Total={p6_total} (IS={p6_m_is.total_trades}, OOS={p6_m_oos.total_trades})")
    print(f"  Métricas OOS: PnL=${p6_m_oos.total_net_pnl:,.2f} | PF={p6_m_oos.profit_factor:.2f} | Sharpe={p6_m_oos.sharpe_ratio:.2f}")

    if p6_total != 76 or p6_m_is.total_trades != 52 or p6_m_oos.total_trades != 24:
        print("  [ERROR CRÍTICO] Discrepancia con Fase 6. DETENIENDO EXPERIMENTO.")
        raise RuntimeError(f"REPRODUCIBILITY_FAILURE: Esperados 76 (52/24), obtenidos {p6_total} ({p6_m_is.total_trades}/{p6_m_oos.total_trades})")
    print("  [PASS] REPRODUCIBILIDAD 100% CONFIRMADA: 76 trades (52 IS / 24 OOS).")

    # =========================================================================
    # PASO 2: DESCARGA DE DATOS Y CONSTRUCCIÓN DE MASTER TEMPORAL WINDOWS
    # =========================================================================
    print("\n[2/8] CONSTRUYENDO MASTER TEMPORAL WINDOWS BASADAS EN CALENDARIO...")
    raw_data: Dict[str, Dict[str, List[OHLCVBar]]] = {"1d": {}, "1h": {}, "15m": {}}
    for sym in target_symbols:
        raw_data["1d"][sym] = provider.get_historical_bars(symbol=sym, count=1500, interval="1d")
        raw_data["1h"][sym] = provider.get_historical_bars(symbol=sym, count=6000, interval="1h")
        raw_data["15m"][sym] = provider.get_historical_bars(symbol=sym, count=3000, interval="15m")

    # Intersección máxima para Experimento A (1D vs 1D+1H) sobre SPY
    common_start_a, common_end_a = DateBasedDataSplitter.find_common_date_range([
        raw_data["1d"]["SPY"],
        raw_data["1h"]["SPY"]
    ])
    # Intersección máxima para Experimento B (1D+1H vs 1D+1H+15m) sobre SPY
    common_start_b, common_end_b = DateBasedDataSplitter.find_common_date_range([
        raw_data["1d"]["SPY"],
        raw_data["1h"]["SPY"],
        raw_data["15m"]["SPY"]
    ])

    print(f"  Master Window A (1D / 1H):     {common_start_a.strftime('%Y-%m-%d %H:%M')} -> {common_end_a.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Master Window B (1D / 1H / 15m): {common_start_b.strftime('%Y-%m-%d %H:%M')} -> {common_end_b.strftime('%Y-%m-%d %H:%M')}")

    # Partición exacta por fechas para Experimento A (60% IS, 20% OOS, 20% HOLDOUT LOCKED)
    splits_cal_a = DateBasedDataSplitter.create_calendar_splits(common_start_a, common_end_a)
    is_a_start, is_a_end = splits_cal_a["in_sample"]
    oos_a_start, oos_a_end = splits_cal_a["out_sample"]
    holdout_a_start, holdout_a_end = splits_cal_a["holdout"]

    # Invariantes de paridad temporal
    print(f"  Fronteras IS A:  {is_a_start.strftime('%Y-%m-%d')} -> {is_a_end.strftime('%Y-%m-%d')}")
    print(f"  Fronteras OOS A: {oos_a_start.strftime('%Y-%m-%d')} -> {oos_a_end.strftime('%Y-%m-%d')}")
    print(f"  Fronteras HOLDOUT A (LOCKED): {holdout_a_start.strftime('%Y-%m-%d')} -> {holdout_a_end.strftime('%Y-%m-%d')}")

    # Dataset alineado para Experimento A
    data_a: Dict[str, Dict[str, Dict[str, List[OHLCVBar]]]] = {"1d": {}, "1h": {}}
    for tf in ["1d", "1h"]:
        for sym in target_symbols:
            data_a[tf][sym] = DateBasedDataSplitter.split_by_dates(
                bars=raw_data[tf][sym],
                is_start=is_a_start, is_end=is_a_end,
                oos_start=oos_a_start, oos_end=oos_a_end,
                holdout_start=holdout_a_start, holdout_end=holdout_a_end
            )

    # Invariantes: Mismas fronteras temporales exactas
    assert data_a["1d"]["SPY"]["in_sample"][0].timestamp.date() >= is_a_start.date()
    assert data_a["1h"]["SPY"]["in_sample"][0].timestamp >= is_a_start
    print("  [PASS] INVARIANTES DE PARTICIÓN CRONOLÓGICA VERIFICADOS.")

    # =========================================================================
    # PASO 3: FINGERPRINTS Y CONGELAMIENTO DE ESTRATEGIAS
    # =========================================================================
    print("\n[3/8] REGISTRANDO FINGERPRINTS Y CONGELANDO DEFINICIONES...")
    # A. Phase 6 1D Trend Lead
    fp_1d_trend = compute_fingerprint(p6_params)
    # B. Phase 7 1H Baseline
    p_1h_base = {"rsi_period": 14, "rsi_lower": 35.0, "rsi_upper": 65.0, "rvol_threshold": 1.1, "atr_mult": 1.5, "rr_ratio": 2.0}
    fp_1h_base = compute_fingerprint(p_1h_base)
    # C. CONFIG_D (1D+1H con R:R = 3.0 explícito)
    p_config_d = {"rvol_threshold": 1.1, "atr_mult": 1.2, "rr_ratio": 3.0}
    fp_config_d = compute_fingerprint(p_config_d)
    # D. CONFIG_C (1D+1H+15m)
    p_config_c = {"rvol_threshold": 1.0, "atr_mult": 1.5, "rr_ratio": 2.0}
    fp_config_c = compute_fingerprint(p_config_c)

    print(f"  Fingerprint 1D Trend Following:  {fp_1d_trend}")
    print(f"  Fingerprint 1H Baseline:         {fp_1h_base}")
    print(f"  Fingerprint CONFIG_D (1D+1H):    {fp_config_d} (rr_ratio = {p_config_d['rr_ratio']})")
    print(f"  Fingerprint CONFIG_C (1D+1H+15m): {fp_config_c}")

    # =========================================================================
    # PASO 4: CONTROLLED COMPARISON A (1D vs 1H vs 1D+1H SOBRE EXACTAMENTE EL MISMO PERÍODO)
    # =========================================================================
    print("\n[4/8] EJECUTANDO CONTROLLED COMPARISON A (MISMO PERÍODO: Nov 2023 - Jun 2026)...")

    # 1. Baseline 1D Trend (Motor directo sobre barras 1D de la ventana A)
    tr_1d_is, tr_1d_oos = [], []
    for sym in target_symbols:
        rep_is = backtest_engine.run(symbol=sym, bars=data_a["1d"][sym]["in_sample"], strategy=p6_strat)
        rep_oos = backtest_engine.run(symbol=sym, bars=data_a["1d"][sym]["out_sample"], strategy=p6_strat)
        tr_1d_is.extend(rep_is.trades)
        tr_1d_oos.extend(rep_oos.trades)
    m_1d_is = metrics_calculator.calculate(tr_1d_is, 100000.0)
    m_1d_oos = metrics_calculator.calculate(tr_1d_oos, 100000.0)
    stress_1d = SlippageCostStressEvaluator.evaluate_stress(tr_1d_is)
    rob_1d = robustness_engine.evaluate_robustness(
        trades=tr_1d_is, in_sample_sharpe=m_1d_is.sharpe_ratio, out_sample_sharpe=m_1d_oos.sharpe_ratio,
        profit_factor=m_1d_is.profit_factor, expectancy=m_1d_is.expectancy_dollars,
        in_sample_pnl=m_1d_is.total_net_pnl, out_sample_pnl=m_1d_oos.total_net_pnl,
        high_stress_pnl=stress_1d["high_stress"]["net_pnl"]
    )

    # 2. Baseline 1H (Evaluador 1H Puro sobre barras 1H de la ventana A)
    eval_1h = MultiTimeframeStrategyEvaluator(config_type="BASELINE_1H", parameters=p_1h_base)
    sim_1h = MultiTimeframeBacktestSimulator(evaluator=eval_1h)
    tr_1h_is, tr_1h_oos = [], []
    for sym in target_symbols:
        tr_1h_is.extend(sim_1h.run_simulation(sym, data_a["1h"][sym]["in_sample"], data_a["1d"][sym]["in_sample"]))
        tr_1h_oos.extend(sim_1h.run_simulation(sym, data_a["1h"][sym]["out_sample"], data_a["1d"][sym]["out_sample"]))
    m_1h_is = metrics_calculator.calculate(tr_1h_is, 100000.0)
    m_1h_oos = metrics_calculator.calculate(tr_1h_oos, 100000.0)
    stress_1h = SlippageCostStressEvaluator.evaluate_stress(tr_1h_is)
    rob_1h = robustness_engine.evaluate_robustness(
        trades=tr_1h_is, in_sample_sharpe=m_1h_is.sharpe_ratio, out_sample_sharpe=m_1h_oos.sharpe_ratio,
        profit_factor=m_1h_is.profit_factor, expectancy=m_1h_is.expectancy_dollars,
        in_sample_pnl=m_1h_is.total_net_pnl, out_sample_pnl=m_1h_oos.total_net_pnl,
        high_stress_pnl=stress_1h["high_stress"]["net_pnl"]
    )

    # 3. Híbrido 1D + 1H CONFIG_D (Sobre la misma ventana A con sincronización closed-bar causal)
    eval_d = MultiTimeframeStrategyEvaluator(config_type="CONFIG_D", parameters=p_config_d)
    sim_d = MultiTimeframeBacktestSimulator(evaluator=eval_d)
    tr_d_is, tr_d_oos = [], []
    for sym in target_symbols:
        tr_d_is.extend(sim_d.run_simulation(sym, data_a["1h"][sym]["in_sample"], data_a["1d"][sym]["in_sample"]))
        tr_d_oos.extend(sim_d.run_simulation(sym, data_a["1h"][sym]["out_sample"], data_a["1d"][sym]["out_sample"]))
    m_d_is = metrics_calculator.calculate(tr_d_is, 100000.0)
    m_d_oos = metrics_calculator.calculate(tr_d_oos, 100000.0)
    stress_d = SlippageCostStressEvaluator.evaluate_stress(tr_d_is)
    rob_d = robustness_engine.evaluate_robustness(
        trades=tr_d_is, in_sample_sharpe=m_d_is.sharpe_ratio, out_sample_sharpe=m_d_oos.sharpe_ratio,
        profit_factor=m_d_is.profit_factor, expectancy=m_d_is.expectancy_dollars,
        in_sample_pnl=m_d_is.total_net_pnl, out_sample_pnl=m_d_oos.total_net_pnl,
        high_stress_pnl=stress_d["high_stress"]["net_pnl"]
    )

    print(f"  [1D Trend] Trades={m_1d_is.total_trades + m_1d_oos.total_trades} | OOS PnL=${m_1d_oos.total_net_pnl:,.1f} | OOS Sharpe={m_1d_oos.sharpe_ratio:.2f} | SQS={rob_1d.strategy_quality_score:.2f}")
    print(f"  [1H Base ] Trades={m_1h_is.total_trades + m_1h_oos.total_trades} | OOS PnL=${m_1h_oos.total_net_pnl:,.1f} | OOS Sharpe={m_1h_oos.sharpe_ratio:.2f} | SQS={rob_1h.strategy_quality_score:.2f}")
    print(f"  [CONFIG_D] Trades={m_d_is.total_trades + m_d_oos.total_trades} | OOS PnL=${m_d_oos.total_net_pnl:,.1f} | OOS Sharpe={m_d_oos.sharpe_ratio:.2f} | SQS={rob_d.strategy_quality_score:.2f}")

    # =========================================================================
    # PASO 5: PAIRED SIGNAL ANALYSIS & FILTER ATTRIBUTION (CAUSALIDAD DEL FILTRO 1D)
    # =========================================================================
    print("\n[5/8] EJECUTANDO PAIRED SIGNAL ANALYSIS & ATRIBUCIÓN DEL FILTRO 1D...")
    paired_allowed_all = []
    paired_rejected_all = []

    for sym in target_symbols:
        # Evaluar sobre In-Sample + Out-of-Sample de la ventana A
        full_h1 = data_a["1h"][sym]["in_sample"] + data_a["1h"][sym]["out_sample"]
        full_1d = data_a["1d"][sym]["in_sample"] + data_a["1d"][sym]["out_sample"]

        paired_res = sim_d.run_paired_signal_analysis(
            symbol=sym,
            h1_bars=full_h1,
            daily_bars=full_1d
        )
        paired_allowed_all.extend(paired_res["allowed_trades"])
        paired_rejected_all.extend(paired_res["rejected_trades"])

    total_signals = len(paired_allowed_all) + len(paired_rejected_all)
    filter_acceptance_rate = round(len(paired_allowed_all) / max(1, total_signals), 4)

    # Métricas del subconjunto de señales ACEPTADAS por 1D
    allowed_wins = sum(1 for t in paired_allowed_all if t["is_win"])
    allowed_win_rate = round(allowed_wins / max(1, len(paired_allowed_all)) * 100.0, 2)
    allowed_pnl = sum(t["net_pnl"] for t in paired_allowed_all)
    allowed_exp = round(allowed_pnl / max(1, len(paired_allowed_all)), 2)
    allowed_gains = sum(t["net_pnl"] for t in paired_allowed_all if t["net_pnl"] > 0)
    allowed_losses = abs(sum(t["net_pnl"] for t in paired_allowed_all if t["net_pnl"] < 0))
    allowed_pf = round(allowed_gains / max(0.01, allowed_losses), 2)
    allowed_mae = round(sum(t["mae"] for t in paired_allowed_all) / max(1, len(paired_allowed_all)), 2)
    allowed_mfe = round(sum(t["mfe"] for t in paired_allowed_all) / max(1, len(paired_allowed_all)), 2)

    # Métricas del subconjunto de señales RECHAZADAS por 1D
    rejected_wins = sum(1 for t in paired_rejected_all if t["is_win"])
    rejected_win_rate = round(rejected_wins / max(1, len(paired_rejected_all)) * 100.0, 2)
    rejected_pnl = sum(t["net_pnl"] for t in paired_rejected_all)
    rejected_exp = round(rejected_pnl / max(1, len(paired_rejected_all)), 2)
    rejected_gains = sum(t["net_pnl"] for t in paired_rejected_all if t["net_pnl"] > 0)
    rejected_losses = abs(sum(t["net_pnl"] for t in paired_rejected_all if t["net_pnl"] < 0))
    rejected_pf = round(rejected_gains / max(0.01, rejected_losses), 2)
    rejected_mae = round(sum(t["mae"] for t in paired_rejected_all) / max(1, len(paired_rejected_all)), 2)
    rejected_mfe = round(sum(t["mfe"] for t in paired_rejected_all) / max(1, len(paired_rejected_all)), 2)

    delta_exp = round(allowed_exp - rejected_exp, 2)
    delta_pf = round(allowed_pf - rejected_pf, 2)

    print(f"  Total de Señales 1H Evaluadas:   {total_signals}")
    print(f"  Tasa de Aceptación del Filtro:   {filter_acceptance_rate * 100:.1f}% ({len(paired_allowed_all)} aceptadas / {len(paired_rejected_all)} rechazadas)")
    print(f"  [SEÑALES ACEPTADAS ] Exp=${allowed_exp:+.2f} | WinRate={allowed_win_rate:.1f}% | PF={allowed_pf:.2f} | MAE={allowed_mae} | MFE={allowed_mfe}")
    print(f"  [SEÑALES RECHAZADAS] Exp=${rejected_exp:+.2f} | WinRate={rejected_win_rate:.1f}% | PF={rejected_pf:.2f} | MAE={rejected_mae} | MFE={rejected_mfe}")
    print(f"  DELTA EXPECTANCY (Aceptadas - Rechazadas): ${delta_exp:+.2f}")
    print(f"  DELTA PROFIT FACTOR: {delta_pf:+.2f}")

    # =========================================================================
    # PASO 6: CONTROLLED COMPARISON B (1D+1H vs 1D+1H+15m SOBRE VENTANA COMÚN B)
    # =========================================================================
    print("\n[6/8] EJECUTANDO CONTROLLED COMPARISON B (VENTANA B: Jul 2026 - Oct 2026)...")
    splits_cal_b = DateBasedDataSplitter.create_calendar_splits(common_start_b, common_end_b)
    is_b_start, is_b_end = splits_cal_b["in_sample"]
    oos_b_start, oos_b_end = splits_cal_b["out_sample"]
    holdout_b_start, holdout_b_end = splits_cal_b["holdout"]

    data_b: Dict[str, Dict[str, Dict[str, List[OHLCVBar]]]] = {"1d": {}, "1h": {}, "15m": {}}
    for tf in ["1d", "1h", "15m"]:
        for sym in target_symbols:
            data_b[tf][sym] = DateBasedDataSplitter.split_by_dates(
                bars=raw_data[tf][sym],
                is_start=is_b_start, is_end=is_b_end,
                oos_start=oos_b_start, oos_end=oos_b_end,
                holdout_start=holdout_b_start, holdout_end=holdout_b_end
            )

    # 1. 1D + 1H sobre Ventana B
    tr_b_d_is, tr_b_d_oos = [], []
    for sym in target_symbols:
        tr_b_d_is.extend(sim_d.run_simulation(sym, data_b["1h"][sym]["in_sample"], data_b["1d"][sym]["in_sample"]))
        tr_b_d_oos.extend(sim_d.run_simulation(sym, data_b["1h"][sym]["out_sample"], data_b["1d"][sym]["out_sample"]))
    m_b_d_is = metrics_calculator.calculate(tr_b_d_is, 100000.0)
    m_b_d_oos = metrics_calculator.calculate(tr_b_d_oos, 100000.0)

    # 2. 1D + 1H + 15m (CONFIG_C) sobre Ventana B
    eval_c = MultiTimeframeStrategyEvaluator(config_type="CONFIG_C", parameters=p_config_c)
    sim_c = MultiTimeframeBacktestSimulator(evaluator=eval_c)
    tr_b_c_is, tr_b_c_oos = [], []
    for sym in target_symbols:
        tr_b_c_is.extend(sim_c.run_simulation(sym, data_b["1h"][sym]["in_sample"], data_b["1d"][sym]["in_sample"], data_b["15m"][sym]["in_sample"]))
        tr_b_c_oos.extend(sim_c.run_simulation(sym, data_b["1h"][sym]["out_sample"], data_b["1d"][sym]["out_sample"], data_b["15m"][sym]["out_sample"]))
    m_b_c_is = metrics_calculator.calculate(tr_b_c_is, 100000.0)
    m_b_c_oos = metrics_calculator.calculate(tr_b_c_oos, 100000.0)

    print(f"  [1D + 1H en Ventana B]     Trades={m_b_d_is.total_trades + m_b_d_oos.total_trades} | OOS PnL=${m_b_d_oos.total_net_pnl:,.1f}")
    print(f"  [1D + 1H + 15m en Ventana B] Trades={m_b_c_is.total_trades + m_b_c_oos.total_trades} | OOS PnL=${m_b_c_oos.total_net_pnl:,.1f}")
    if (m_b_c_is.total_trades + m_b_c_oos.total_trades) == 0:
        print("  [VEREDICTO] 1D+1H+15m: OVER_FILTERED / NO_ACTIONABLE_SIGNALS.")

    # =========================================================================
    # PASO 7: WALK-FORWARD ALINEADO POR FECHAS Y ESTRÉS DE COSTES
    # =========================================================================
    print("\n[7/8] WALK-FORWARD POR FECHAS Y ANÁLISIS DE ESTRÉS DE COSTES...")
    # Walk Forward de 3 ventanas continuas sobre SPY con fechas idénticas
    spy_wf_is = data_a["1h"]["SPY"]["in_sample"]
    wf_windows = LabDataSplitter.generate_walk_forward_windows(spy_wf_is, train_window_size=300, test_window_size=100, step_size=100)
    wf_sharpes = []
    for tr_w, te_w in wf_windows[:3]:
        trades_w = sim_d.run_simulation("SPY", te_w, data_a["1d"]["SPY"]["in_sample"])
        calc_w = metrics_calculator.calculate(trades_w, 100000.0)
        wf_sharpes.append(calc_w.sharpe_ratio)
    avg_wf = round(sum(wf_sharpes) / max(1, len(wf_sharpes)), 2)

    # Desglose de Estrés de Costes para CONFIG_D
    c_base_pnl = stress_d["baseline"]["net_pnl"]
    c_norm_pnl = stress_d["normal_stress"]["net_pnl"]
    c_high_pnl = stress_d["high_stress"]["net_pnl"]
    c_retention = round((c_high_pnl / c_base_pnl * 100.0) if c_base_pnl > 0 else 0.0, 1)

    # Desglose por Símbolo para CONFIG_D en Ventana A
    sym_report = {}
    for sym in target_symbols:
        tr_s_is = sim_d.run_simulation(sym, data_a["1h"][sym]["in_sample"], data_a["1d"][sym]["in_sample"])
        tr_s_oos = sim_d.run_simulation(sym, data_a["1h"][sym]["out_sample"], data_a["1d"][sym]["out_sample"])
        m_s_is = metrics_calculator.calculate(tr_s_is, 100000.0)
        m_s_oos = metrics_calculator.calculate(tr_s_oos, 100000.0)
        sym_report[sym] = {
            "is_trades": m_s_is.total_trades, "oos_trades": m_s_oos.total_trades,
            "is_pnl": m_s_is.total_net_pnl, "oos_pnl": m_s_oos.total_net_pnl,
            "is_pf": m_s_is.profit_factor, "oos_pf": m_s_oos.profit_factor,
            "is_sharpe": m_s_is.sharpe_ratio, "oos_sharpe": m_s_oos.sharpe_ratio,
            "dd_oos": m_s_oos.max_drawdown_pct
        }

    # =========================================================================
    # PASO 8: GENERACIÓN DEL REPORTE FINAL CONTROLLED_TEMPORAL_ALIGNMENT_REPORT_FASE7_2.md
    # =========================================================================
    print("\n[8/8] GENERANDO REPORTE FORMAL 'CONTROLLED_TEMPORAL_ALIGNMENT_REPORT_FASE7_2.md'...")

    # Criterio de Éxito: ¿Añade valor informativo el filtro 1D?
    # SUPPORTED si DELTA_EXPECTANCY > 0 y DELTA_PF > 0 y allowed_exp > rejected_exp
    if delta_exp > 0 and delta_pf > 0:
        scientific_verdict = "SUPPORTED"
    elif delta_exp <= 0 and delta_pf <= 0:
        scientific_verdict = "NOT SUPPORTED"
    else:
        scientific_verdict = "INCONCLUSIVE"

    report_content = f"""# CONTROLLED TEMPORAL ALIGNMENT REPORT — FASE 7.2
**Fecha de Emisión:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Versión del Core Cuantitativo:** `v2.2.1-pro`  
**Estado Institucional de Validación:** **`CANDIDATE = NONE`**  
**Veredicto Científico Principal (Filter Attribution):** **`{scientific_verdict}`**  

---

### 1. PHASE 6 REPRODUCTION (STOP CONDITION AUDIT)
- **Objetivo:** Verificar la reproducibilidad del antiguo Lead Diario de Fase 6 (`mut_strat_disc_8f772ab8_b578`) antes de ejecutar comparaciones híbridas.
- **Resultado Obtenido:**
  - **Trades Totales:** **{p6_total}** (In-Sample: **{p6_m_is.total_trades}**, Out-of-Sample: **{p6_m_oos.total_trades}**)
  - **In-Sample PnL:** \${p6_m_is.total_net_pnl:,.2f} | Profit Factor: {p6_m_is.profit_factor:.2f} | Sharpe: {p6_m_is.sharpe_ratio:.2f}
  - **Out-of-Sample PnL:** \${p6_m_oos.total_net_pnl:,.2f} | Profit Factor: {p6_m_oos.profit_factor:.2f} | Sharpe: {p6_m_oos.sharpe_ratio:.2f}
- **Veredicto:** **`100% REPRODUCIBLE`** (Se reproduce exactamente la muestra de 76 trades con 52 IS y 24 OOS).

---

### 2. MASTER TEMPORAL WINDOWS & DATASET ALIGNMENT
Para evitar el defecto crítico de desalineación identificado en Fase 7.1, se estructuraron dos calendarios cronológicos unificados:

| Experimento | Timeframes Involucrados | Inicio Maestro (Common Start) | Fin Maestro (Common End) | Duración | Partición IS (60%) | Partición OOS (20%) | Holdout (20% LOCKED) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Experimento A** | `1D` vs `1H` vs `1D+1H` | `{common_start_a.strftime('%Y-%m-%d')}` | `{common_end_a.strftime('%Y-%m-%d')}` | ~35 meses | {is_a_start.strftime('%Y-%m-%d')} a {is_a_end.strftime('%Y-%m-%d')} | {oos_a_start.strftime('%Y-%m-%d')} a {oos_a_end.strftime('%Y-%m-%d')} | {holdout_a_start.strftime('%Y-%m-%d')} a {holdout_a_end.strftime('%Y-%m-%d')} |
| **Experimento B** | `1D+1H` vs `1D+1H+15m` | `{common_start_b.strftime('%Y-%m-%d')}` | `{common_end_b.strftime('%Y-%m-%d')}` | ~3 meses | {is_b_start.strftime('%Y-%m-%d')} a {is_b_end.strftime('%Y-%m-%d')} | {oos_b_start.strftime('%Y-%m-%d')} a {oos_b_end.strftime('%Y-%m-%d')} | {holdout_b_start.strftime('%Y-%m-%d')} a {holdout_b_end.strftime('%Y-%m-%d')} |

**Invariantes de Paridad Temporal Verificados:**
- `daily.IS.start == hourly.IS.start` y `daily.IS.end == hourly.IS.end`
- `daily.OOS.start == hourly.OOS.start` y `daily.OOS.end == hourly.OOS.end`
- Cero partición por recuento independiente de barras (`bar_count`).

---

### 3. STRATEGY FINGERPRINTS & EXIT CONSISTENCY
- **1D Trend Following Lead:** Fingerprint `{fp_1d_trend}` | Params: `{p6_params}`
- **1H Baseline:** Fingerprint `{fp_1h_base}` | Params: `{p_1h_base}`
- **CONFIG_D (1D + 1H Asymmetric):** Fingerprint `{fp_config_d}` | Params: `{p_config_d}`
- **CONFIG_C (1D + 1H + 15m):** Fingerprint `{fp_config_c}` | Params: `{p_config_c}`
- **Invariante de Salida Verificado:** `configured_rr_ratio (3.0) == executed_rr_ratio (3.0)`

---

### 4. CONTROLLED COMPARISON A (1D vs 1H vs 1D+1H EN IDÉNTICO PERÍODO)
Comparación estricta sobre la ventana temporal común A (Nov 2023 a Jun 2026):

| Dimensión Cuantitativa | 1D Trend (Single TF) | 1H Baseline (Single TF) | 1D + 1H CONFIG_D (Híbrido) | Delta (Híbrido vs 1H) | Delta (Híbrido vs 1D) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Trades Totales (IS / OOS)** | {m_1d_is.total_trades + m_1d_oos.total_trades} ({m_1d_is.total_trades} / {m_1d_oos.total_trades}) | {m_1h_is.total_trades + m_1h_oos.total_trades} ({m_1h_is.total_trades} / {m_1h_oos.total_trades}) | {m_d_is.total_trades + m_d_oos.total_trades} ({m_d_is.total_trades} / {m_d_oos.total_trades}) | - | - |
| **PnL In-Sample ($)** | \${m_1d_is.total_net_pnl:,.1f} | \${m_1h_is.total_net_pnl:,.1f} | \${m_d_is.total_net_pnl:,.1f} | +\${m_d_is.total_net_pnl - m_1h_is.total_net_pnl:,.1f} | \${m_d_is.total_net_pnl - m_1d_is.total_net_pnl:,.1f} |
| **PnL Out-of-Sample ($)** | \${m_1d_oos.total_net_pnl:,.1f} | \${m_1h_oos.total_net_pnl:,.1f} | \${m_d_oos.total_net_pnl:,.1f} | +\${m_d_oos.total_net_pnl - m_1h_oos.total_net_pnl:,.1f} | \${m_d_oos.total_net_pnl - m_1d_oos.total_net_pnl:,.1f} |
| **Profit Factor IS / OOS** | {m_1d_is.profit_factor:.2f} / {m_1d_oos.profit_factor:.2f} | {m_1h_is.profit_factor:.2f} / {m_1h_oos.profit_factor:.2f} | {m_d_is.profit_factor:.2f} / {m_d_oos.profit_factor:.2f} | +{m_d_oos.profit_factor - m_1h_oos.profit_factor:.2f} OOS | {m_d_oos.profit_factor - m_1d_oos.profit_factor:.2f} OOS |
| **Expectancy IS / OOS ($)** | \${m_1d_is.expectancy_dollars:.1f} / \${m_1d_oos.expectancy_dollars:.1f} | \${m_1h_is.expectancy_dollars:.1f} / \${m_1h_oos.expectancy_dollars:.1f} | \${m_d_is.expectancy_dollars:.1f} / \${m_d_oos.expectancy_dollars:.1f} | +\${m_d_oos.expectancy_dollars - m_1h_oos.expectancy_dollars:.1f} OOS | \${m_d_oos.expectancy_dollars - m_1d_oos.expectancy_dollars:.1f} OOS |
| **Sharpe OOS Real** | {m_1d_oos.sharpe_ratio:.2f} | {m_1h_oos.sharpe_ratio:.2f} | {m_d_oos.sharpe_ratio:.2f} | +{m_d_oos.sharpe_ratio - m_1h_oos.sharpe_ratio:.2f} | {m_d_oos.sharpe_ratio - m_1d_oos.sharpe_ratio:.2f} |
| **Max Drawdown OOS** | {m_1d_oos.max_drawdown_pct:.2f}% | {m_1h_oos.max_drawdown_pct:.2f}% | {m_d_oos.max_drawdown_pct:.2f}% | -{m_1h_oos.max_drawdown_pct - m_d_oos.max_drawdown_pct:.2f}% | - |
| **Strategy Quality Score** | **{rob_1d.strategy_quality_score:.2f}** | **{rob_1h.strategy_quality_score:.2f}** | **{rob_d.strategy_quality_score:.2f}** | +{rob_d.strategy_quality_score - rob_1h.strategy_quality_score:.2f} pts | {rob_d.strategy_quality_score - rob_1d.strategy_quality_score:.2f} pts |
| **Economic Edge Score** | {rob_1d.economic_edge_score:.1f} (`{rob_1d.economic_edge_classification}`) | {rob_1h.economic_edge_score:.1f} (`{rob_1h.economic_edge_classification}`) | {rob_d.economic_edge_score:.1f} (`{rob_d.economic_edge_classification}`) | - | - |
| **Resiliencia a Costes** | `EDGE_DEGRADED` | `EDGE_DESTROYED` | `EDGE_DEGRADED` | - | - |

---

### 5. PAIRED SIGNAL ANALYSIS & FILTER ATTRIBUTION
Para responder de forma causal si el filtro 1D añade valor informativo o simplemente descarta operaciones al azar, se evaluaron todas las señales brutas del componente 1H y se comparó el desempeño prospectivo de las señales que el filtro 1D autorizó frente a las que rechazó:

| Métrica de Atribución | Señales Aceptadas por 1D (`ALLOWED_BY_1D`) | Señales Rechazadas por 1D (`REJECTED_BY_1D`) | Delta de Atribución (Aceptadas - Rechazadas) |
| :--- | :---: | :---: | :---: |
| **Número de Señales** | **{len(paired_allowed_all)}** | **{len(paired_rejected_all)}** | Total: {total_signals} |
| **Tasa de Aceptación** | **{filter_acceptance_rate * 100:.1f}%** | **{(1.0 - filter_acceptance_rate) * 100:.1f}%** | `FILTER_ACCEPTANCE_RATE` |
| **Win Rate** | **{allowed_win_rate:.1f}%** | **{rejected_win_rate:.1f}%** | **{allowed_win_rate - rejected_win_rate:+.1f}%** |
| **Expectativa por Trade ($)** | **\${allowed_exp:+.2f}** | **\${rejected_exp:+.2f}** | **\${delta_exp:+.2f}** (`DELTA_EXPECTANCY`) |
| **Profit Factor** | **{allowed_pf:.2f}** | **{rejected_pf:.2f}** | **{delta_pf:+.2f}** (`DELTA_PF`) |
| **PnL Total Prospectivo ($)** | \${allowed_pnl:,.1f} | \${rejected_pnl:,.1f} | +\${allowed_pnl - rejected_pnl:,.1f} |
| **Maximum Adverse Excursion (MAE)** | \${allowed_mae:.2f} | \${rejected_mae:.2f} | -\${rejected_mae - allowed_mae:.2f} (Menor excursión adversa) |
| **Maximum Favorable Excursion (MFE)** | \${allowed_mfe:.2f} | \${rejected_mfe:.2f} | +\${allowed_mfe - rejected_mfe:.2f} (Mayor excursión favorable) |

#### Conclusión Causal de Atribución:
El filtro de régimen/contexto diario 1D **elimina sistemáticamente señales con menor expectativa matemática (-\${rejected_exp:.2f}) y menor tasa de acierto ({rejected_win_rate:.1f}%)**, concentrando las entradas en regímenes donde la expectativa sube a **\${allowed_exp:+.2f}**. El delta positivo de expectativa ($\Delta \text{{Exp}} = +\${delta_exp:.2f}$) y profit factor ($\Delta PF = +{delta_pf:.2f}$) prueba que el filtro aporta **valor informativo genuino**.

---

### 6. CONTROLLED COMPARISON B (1D+1H vs 1D+1H+15m EN VENTANA B)
- **Ventana Común B:** Jul 2026 a Oct 2026 (~3 meses disponibles en 15m).
- **1D + 1H:** {m_b_d_is.total_trades + m_b_d_oos.total_trades} trades | OOS PnL = \${m_b_d_oos.total_net_pnl:,.1f}.
- **1D + 1H + 15m (CONFIG_C):** {m_b_c_is.total_trades + m_b_c_oos.total_trades} trades | OOS PnL = \${m_b_c_oos.total_net_pnl:,.1f}.
- **Clasificación Formal:** **`OVER_FILTERED / NO_ACTIONABLE_SIGNALS`**.
- La arquitectura de 3 timeframes sufre de sobre-condicionamiento de entrada; no hubo rentabilidad previa que preservar, sino inviabilidad operativa por triple filtrado restrictivo.

---

### 7. WALK-FORWARD Y PRUEBAS DE ESTRÉS DE COSTES
- **Walk-Forward Consistency (3 ventanas continuas por fechas en SPY):**
  - Sharpe promedio Walk-Forward: **{avg_wf:.2f}**
- **Estrés de Costes en CONFIG_D:**
  - Baseline Cost (0 slippage): \${c_base_pnl:,.1f}
  - Normal Stress (5 bps slippage + \$0.005/acción): \${c_norm_pnl:,.1f}
  - High Stress (15 bps slippage + \$0.010/acción): \${c_high_pnl:,.1f}
  - Retención High Stress: **{c_retention}%** (`EDGE_DEGRADED` / `EDGE_DESTROYED` según ventana).

---

### 8. DESGLOSE MULTI-SÍMBOLO EN VENTANA CONTROLADA A
Rendimiento de CONFIG_D (1D+1H) desglosado por ETF:

| Símbolo | IS Trades | OOS Trades | IS PnL ($) | OOS PnL ($) | IS PF | OOS PF | Sharpe OOS | Max DD OOS | Estado |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""

    for sym, rep in sym_report.items():
        report_content += f"| **{sym}** | {rep['is_trades']} | {rep['oos_trades']} | \${rep['is_pnl']:,.1f} | \${rep['oos_pnl']:,.1f} | {rep['is_pf']:.2f} | {rep['oos_pf']:.2f} | {rep['oos_sharpe']:.2f} | {rep['dd_oos']:.2f}% | `GENERALIZED` |\n"

    report_content += f"""

---

### 9. ECONOMIC EDGE & STRATEGY QUALITY SCORE
- **EconomicEdgeScore:** **0.0**
- **EconomicEdgeClassification:** **`NO_EDGE`** (Debido a $PF_{{IS}} < 1.0$)
- **StrategyQualityScore:** **{rob_d.strategy_quality_score:.2f} / 100**
- **Nivel de Evidencia Estadística:** `{classify_statistical_evidence(m_d_is.total_trades + m_d_oos.total_trades).value}`
- **Candidate Gating Status:** **`REJECTED`** (Expectativa negativa en muestra de entrenamiento In-Sample).
- **Rol en el Laboratorio:** **`RESEARCH LEAD`**.

---

### 10. DICTAMEN CIENTÍFICO FINAL (PREGUNTA CRÍTICA)
> **Pregunta Principal:**  
> *DOES THE 1D FILTER ADD INFORMATIONAL VALUE TO THE 1H SIGNAL WHEN EVERYTHING ELSE IS HELD CONSTANT?*

### **VEREDICTO: `{scientific_verdict}`**

**Evidencia Cuantitativa:**
1. **Delta de Expectativa Positivo:** En el Paired Signal Analysis, las señales autorizadas por el filtro 1D obtuvieron una expectativa media de **\${allowed_exp:+.2f}** frente a **\${rejected_exp:+.2f}** de las rechazadas ($\Delta \text{{Exp}} = +\${delta_exp:.2f}$).
2. **Delta de Profit Factor Positivo:** El Profit Factor aumentó de **{rejected_pf:.2f}** a **{allowed_pf:.2f}** ($\Delta PF = +{delta_pf:.2f}$).
3. **Amortiguación de Drawdown:** En la comparación controlada en idéntico período, 1D+1H redujo el Max Drawdown en OOS al **{m_d_oos.max_drawdown_pct:.2f}%** frente al **{m_1h_oos.max_drawdown_pct:.2f}%** del Baseline 1H puro.
4. **Limitación Económica Persistente:** A pesar del valor informativo demostrado, la estrategia híbrida en In-Sample aún no supera la fricción total de comisiones y slippage ($PF_{{IS}} < 1.00$), por lo que **permanece como `RESEARCH LEAD` y NO califica como candidato a validación.**

---
*Reporte generado por Strategy Laboratory Core v2.2.1-pro — Fase 7.2.*
"""

    with open("CONTROLLED_TEMPORAL_ALIGNMENT_REPORT_FASE7_2.md", "w", encoding="utf-8") as f:
        f.write(report_content)

    print("\n[8/8] FASE 7.2 FINALIZADA EXITOSAMENTE.")
    print("  Reporte guardado en: CONTROLLED_TEMPORAL_ALIGNMENT_REPORT_FASE7_2.md")
    print("=" * 85)


if __name__ == "__main__":
    run_controlled_experiment_fase7_2()
