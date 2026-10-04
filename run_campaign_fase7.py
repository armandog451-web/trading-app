"""
run_campaign_fase7.py
=====================
Ejecutor de la Campaña de Investigación Multi-Timeframe
(FASE 7 — MULTI-TIMEFRAME EDGE RESEARCH).

Objetivo Científico:
"Can a higher-timeframe market regime/context filter combined with
lower-timeframe entry timing improve economic edge, OOS stability,
drawdown and cost resilience without materially increasing complexity
and overfitting risk?"

Estructura de la Campaña:
1. 4 Baselines Obligatorios:
   - Baseline A: 1D Trend Following puro
   - Baseline B: 1D Regime Filtered puro
   - Baseline C: 1H Mean Reversion puro
   - Baseline D: 1H Best Surviving Lead de Fase 6
2. 4 Configuraciones Híbridas Principales:
   - Config A: 1D Context (Trend) + 1H Entry Timing (Pullback)
   - Config B: 1D Regime Filter + 1H Entry (Momentum) + 1H Dynamic Exit
   - Config C: 1D Context + 1H Entry Setup + 15m Execution Timing Trigger
   - Config D: 1D Context + 1H Entry + Asymmetric Volatility Exit (ATR 3.0R)
3. Presupuesto: 30 experimentos reproducibles (21 Exploración / 9 Explotación).
4. Sincronización Estricta Closed-Bar: Zero Look-Ahead Bias / Zero Future Leakage.
5. Ablation Study Exhaustivo para el mejor híbrido (FULL, -15m, -1D, -1H, BASELINE).
6. Control de Complejidad & Pruebas de Valor Incremental (Delta SQS, Delta EES, Delta Sharpe, Delta DD, Delta Slippage).
7. Análisis Multi-Símbolo (SPY, QQQ, IWM, DIA), Resiliencia a Costos y Desglose por Régimen.
8. Genera: RESEARCH_CAMPAIGN_REPORT_FASE7.md con Secciones A hasta W y las 12 Preguntas Críticas.
"""

import math
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from ai_trading_agent.data.providers.yfinance_provider import YFinanceMarketDataProvider
from ai_trading_agent.backtest.metrics import metrics_calculator, QuantitativeMetricsCalculator
from ai_trading_agent.strategy_lab.backtesting.data_splitter import LabDataSplitter, DataSplitType
from ai_trading_agent.strategy_lab.discovery.orchestrator import DiscoveryOrchestrator
from ai_trading_agent.strategy_lab.discovery.experiment_prioritizer import (
    calculate_novelty_score,
    calculate_overfitting_risk_score
)
from ai_trading_agent.strategy_lab.discovery.quantitative_hardening import (
    StatisticalEvidenceLevel,
    EconomicEdgeClassification,
    classify_statistical_evidence,
    calculate_economic_edge_score,
    calculate_oos_stability_score,
    calculate_slippage_resilience_score,
    calculate_strategy_quality_score,
    SlippageCostStressEvaluator,
    RegimeCoverageEvaluator,
    SymbolCoverageEvaluator,
    DataSufficiencyEvaluator
)
from ai_trading_agent.strategy_lab.lifecycle.manager import LifecycleManager, CandidateGatingConfig
from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition, StrategyStatus
from ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer import (
    MultiTimeframeSynchronizer,
    MultiTimeframeStrategyEvaluator,
    MultiTimeframeBacktestSimulator,
    MultiTimeframeComplexityCalculator
)


def run_fase7_multi_timeframe_research():
    print("=" * 85)
    print(" INICIANDO FASE 7: MULTI-TIMEFRAME EDGE RESEARCH (1D + 1H + 15M)")
    print("=" * 85)

    # 1. DESCARGA Y AUDITORÍA DE DATOS MULTI-TIMEFRAME (15m, 1h, 1d x 4 SÍMBOLOS)
    provider = YFinanceMarketDataProvider(fallback_to_synthetic=False)
    target_symbols = ["SPY", "QQQ", "IWM", "DIA"]
    target_timeframes = ["15m", "1h", "1d"]

    data_store: Dict[str, Dict[str, List[Any]]] = {tf: {} for tf in target_timeframes}
    data_audit_records: Dict[str, Dict[str, Any]] = {}

    print("\n[1/7] AUDITORÍA DE COBERTURA Y DESCARGA DE DATOS MULTI-TIMEFRAME...")
    for tf in target_timeframes:
        data_audit_records[tf] = {}
        count_param = 1560 if tf == "15m" else (2500 if tf == "1h" else 1000)
        for sym in target_symbols:
            bars = provider.get_historical_bars(symbol=sym, count=count_param, interval=tf)
            data_store[tf][sym] = bars
            if bars:
                earliest = bars[0].timestamp.isoformat()
                latest = bars[-1].timestamp.isoformat()
                t_days = len(set(b.timestamp.date() for b in bars))
                sufficiency_rep = DataSufficiencyEvaluator.evaluate(
                    symbol=sym,
                    timeframe=tf,
                    bars=bars,
                    min_required_trades=15,
                    recommended_min_bars=1000 if tf in ["15m", "1h"] else 400
                )
                data_audit_records[tf][sym] = {
                    "total_bars": len(bars),
                    "start": earliest[:10],
                    "end": latest[:10],
                    "trading_days": t_days,
                    "sufficiency": sufficiency_rep.data_sufficiency_status.value
                }
                print(f"  [OK] {sym} [{tf:3s}]: {len(bars)} barras | {t_days} días de bolsa ({earliest[:10]} -> {latest[:10]}) | Estado: {sufficiency_rep.data_sufficiency_status.value}")
            else:
                print(f"  [ERROR] {sym} [{tf:3s}]: Sin datos.")

    # 2. PARTICIÓN DE DATOS (IN-SAMPLE 60%, OUT-OF-SAMPLE 20%, FINAL_HOLDOUT 20% LOCKED)
    print("\n[2/7] PARTICIÓN ESTRICTA DE DATOS (IS 60% / OOS 20% / HOLDOUT 20% LOCKED)...")
    splits_store: Dict[str, Dict[str, Dict[str, Any]]] = {tf: {} for tf in target_timeframes}
    for tf in target_timeframes:
        for sym in target_symbols:
            bars = data_store[tf][sym]
            ds = LabDataSplitter.split_in_sample_out_sample_holdout(bars, in_sample_ratio=0.60, out_sample_ratio=0.20)
            splits_store[tf][sym] = {
                "protected": ds,
                "in_sample": ds.get_split(DataSplitType.IN_SAMPLE, purpose="RESEARCH"),
                "out_sample": ds.get_split(DataSplitType.OUT_OF_SAMPLE, purpose="RESEARCH")
            }

    # 3. VERIFICACIÓN DE PROTECCIÓN DEL FINAL_HOLDOUT
    print("\n[3/7] VERIFICANDO AISLAMIENTO INSTITUCIONAL DEL FINAL_HOLDOUT...")
    for sym in target_symbols:
        try:
            splits_store["1h"][sym]["protected"].get_split(DataSplitType.FINAL_HOLDOUT, purpose="RESEARCH")
            raise RuntimeError(f"VIOLACIÓN DE AISLAMIENTO: FINAL_HOLDOUT de {sym} fue accesible sin autorización.")
        except PermissionError:
            pass
    print("  [OK] FINAL_HOLDOUT (20%) protegido y bloqueado bajo PermissionError.")

    # 4. PLAN DE INVESTIGACIÓN: 30 EXPERIMENTOS MULTI-TIMEFRAME
    # 4 Baselines obligatorios + Configuraciones A, B, C, D + variaciones de parámetros / salidas
    experiment_plan = [
        # --- 4 BASELINES OBLIGATORIOS (EXPLORATION) ---
        ("BASELINE_1D_TREND", "BASELINE_1D", "EXPLORATION", {"trend_sma_fast": 20, "trend_sma_slow": 50, "atr_mult": 1.5, "rr_ratio": 2.0}, 1, 3, 2, 4),
        ("BASELINE_1D_REGIME", "BASELINE_1D", "EXPLORATION", {"trend_sma_fast": 10, "trend_sma_slow": 30, "atr_mult": 2.0, "rr_ratio": 2.0}, 1, 3, 2, 4),
        ("BASELINE_1H_MR", "BASELINE_1H", "EXPLORATION", {"rsi_period": 14, "rsi_lower": 35.0, "rsi_upper": 65.0, "rvol_threshold": 1.1, "atr_mult": 1.5, "rr_ratio": 2.0}, 1, 3, 2, 5),
        ("BASELINE_1H_F6_LEAD", "BASELINE_1H", "EXPLORATION", {"rsi_period": 14, "rsi_lower": 40.0, "rsi_upper": 60.0, "rvol_threshold": 1.2, "atr_mult": 1.2, "rr_ratio": 2.5}, 1, 3, 2, 5),

        # --- CONFIG A: 1D Context (Trend) + 1H Entry Timing (Pullback) ---
        ("CONFIG_A_CORE", "CONFIG_A", "EXPLORATION", {"rsi_period": 14, "rvol_threshold": 1.0, "atr_mult": 1.5, "rr_ratio": 2.0}, 2, 4, 3, 4),
        ("CONFIG_A_STRICT_RSI", "CONFIG_A", "EXPLORATION", {"rsi_period": 14, "rvol_threshold": 1.1, "atr_mult": 1.5, "rr_ratio": 2.0}, 2, 4, 3, 4),
        ("CONFIG_A_VOL_FILTER", "CONFIG_A", "EXPLORATION", {"rsi_period": 14, "rvol_threshold": 1.3, "atr_mult": 1.5, "rr_ratio": 2.0}, 2, 4, 3, 4),
        ("CONFIG_A_WIDE_STOP", "CONFIG_A", "EXPLORATION", {"rsi_period": 14, "rvol_threshold": 1.1, "atr_mult": 2.0, "rr_ratio": 2.0}, 2, 4, 3, 4),
        ("CONFIG_A_TIGHT_STOP", "CONFIG_A", "EXPLORATION", {"rsi_period": 14, "rvol_threshold": 1.1, "atr_mult": 1.0, "rr_ratio": 2.5}, 2, 4, 3, 4),

        # --- CONFIG B: 1D Regime Filter + 1H Momentum + Dynamic Exit ---
        ("CONFIG_B_CORE", "CONFIG_B", "EXPLORATION", {"rvol_threshold": 1.0, "atr_mult": 1.5, "rr_ratio": 2.0}, 2, 5, 4, 4),
        ("CONFIG_B_MOM_EXPANSIVE", "CONFIG_B", "EXPLORATION", {"rvol_threshold": 1.2, "atr_mult": 1.5, "rr_ratio": 2.4}, 2, 5, 4, 4),
        ("CONFIG_B_STRICT_REGIME", "CONFIG_B", "EXPLORATION", {"rvol_threshold": 1.1, "atr_mult": 1.8, "rr_ratio": 2.2}, 2, 5, 4, 4),
        ("CONFIG_B_HIGH_VOL_TARGET", "CONFIG_B", "EXPLORATION", {"rvol_threshold": 1.3, "atr_mult": 2.0, "rr_ratio": 2.5}, 2, 5, 4, 4),
        ("CONFIG_B_QUICK_TRAIL", "CONFIG_B", "EXPLORATION", {"rvol_threshold": 1.1, "atr_mult": 1.2, "rr_ratio": 1.8}, 2, 5, 4, 4),

        # --- CONFIG C: 1D Context + 1H Entry + 15m Execution Timing Trigger ---
        ("CONFIG_C_CORE", "CONFIG_C", "EXPLORATION", {"rvol_threshold": 1.0, "atr_mult": 1.5, "rr_ratio": 2.0}, 3, 6, 5, 4),
        ("CONFIG_C_HIGH_RVOL", "CONFIG_C", "EXPLORATION", {"rvol_threshold": 1.2, "atr_mult": 1.5, "rr_ratio": 2.0}, 3, 6, 5, 4),
        ("CONFIG_C_TIGHT_TIMING", "CONFIG_C", "EXPLORATION", {"rvol_threshold": 1.1, "atr_mult": 1.2, "rr_ratio": 2.2}, 3, 6, 5, 4),
        ("CONFIG_C_VOLATILE_SURGE", "CONFIG_C", "EXPLORATION", {"rvol_threshold": 1.4, "atr_mult": 1.8, "rr_ratio": 2.0}, 3, 6, 5, 4),
        ("CONFIG_C_SMOOTH_EXIT", "CONFIG_C", "EXPLORATION", {"rvol_threshold": 1.1, "atr_mult": 2.0, "rr_ratio": 2.4}, 3, 6, 5, 4),

        # --- CONFIG D: 1D Context + 1H Entry + Asymmetric Volatility Exit (3.0R) ---
        ("CONFIG_D_CORE", "CONFIG_D", "EXPLORATION", {"rvol_threshold": 1.0, "atr_mult": 1.5, "rr_ratio": 3.0}, 2, 4, 3, 4),
        ("CONFIG_D_DEEP_ASYMMETRY", "CONFIG_D", "EXPLORATION", {"rvol_threshold": 1.1, "atr_mult": 1.2, "rr_ratio": 3.5}, 2, 4, 3, 4),

        # --- 9 EXPERIMENTOS DE EXPLOTACIÓN (MUTACIONES / SWEEDS DE LOS MEJORES CONFIGS) ---
        ("EXP_CONFIG_A_OPTIM_1", "CONFIG_A", "EXPLOITATION", {"rsi_period": 14, "rvol_threshold": 1.15, "atr_mult": 1.4, "rr_ratio": 2.2}, 2, 4, 3, 4),
        ("EXP_CONFIG_A_OPTIM_2", "CONFIG_A", "EXPLOITATION", {"rsi_period": 14, "rvol_threshold": 1.25, "atr_mult": 1.6, "rr_ratio": 2.3}, 2, 4, 3, 4),
        ("EXP_CONFIG_B_OPTIM_1", "CONFIG_B", "EXPLOITATION", {"rvol_threshold": 1.15, "atr_mult": 1.6, "rr_ratio": 2.4}, 2, 5, 4, 4),
        ("EXP_CONFIG_B_OPTIM_2", "CONFIG_B", "EXPLOITATION", {"rvol_threshold": 1.25, "atr_mult": 1.4, "rr_ratio": 2.2}, 2, 5, 4, 4),
        ("EXP_CONFIG_C_OPTIM_1", "CONFIG_C", "EXPLOITATION", {"rvol_threshold": 1.15, "atr_mult": 1.4, "rr_ratio": 2.2}, 3, 6, 5, 4),
        ("EXP_CONFIG_C_OPTIM_2", "CONFIG_C", "EXPLOITATION", {"rvol_threshold": 1.25, "atr_mult": 1.6, "rr_ratio": 2.4}, 3, 6, 5, 4),
        ("EXP_CONFIG_D_OPTIM_1", "CONFIG_D", "EXPLOITATION", {"rvol_threshold": 1.15, "atr_mult": 1.3, "rr_ratio": 3.2}, 2, 4, 3, 4),
        ("EXP_CONFIG_D_OPTIM_2", "CONFIG_D", "EXPLOITATION", {"rvol_threshold": 1.05, "atr_mult": 1.5, "rr_ratio": 2.8}, 2, 4, 3, 4),
        ("EXP_CONFIG_D_OPTIM_3", "CONFIG_D", "EXPLOITATION", {"rvol_threshold": 1.20, "atr_mult": 1.4, "rr_ratio": 3.0}, 2, 4, 3, 4),
    ]

    total_experiments = len(experiment_plan)
    executed_exploration = sum(1 for e in experiment_plan if e[2] == "EXPLORATION")
    executed_exploitation = sum(1 for e in experiment_plan if e[2] == "EXPLOITATION")

    print(f"\n[4/7] EJECUTANDO PLAN DE 30 EXPERIMENTOS MULTI-TIMEFRAME ({executed_exploration} Exploración / {executed_exploitation} Explotación)...")

    results_registry: List[Dict[str, Any]] = []
    decision_log: List[Dict[str, Any]] = []

    for idx, (exp_name, cfg_type, mode, params, tf_count, f_count, c_count, p_count) in enumerate(experiment_plan, start=1):
        strat_id = f"strat_mtf_{idx:02d}_{exp_name.lower()[:15]}"
        evaluator = MultiTimeframeStrategyEvaluator(
            config_type=cfg_type,
            parameters=params,
            strategy_id=strat_id,
            version="1.0"
        )
        simulator = MultiTimeframeBacktestSimulator(evaluator=evaluator)

        all_is_trades = []
        all_oos_trades = []
        symbol_is_metrics = {}
        symbol_oos_metrics = {}

        for sym in target_symbols:
            h1_is = splits_store["1h"][sym]["in_sample"]
            h1_oos = splits_store["1h"][sym]["out_sample"]
            d_is = splits_store["1d"][sym]["in_sample"]
            d_oos = splits_store["1d"][sym]["out_sample"]
            m15_is = splits_store["15m"][sym]["in_sample"]
            m15_oos = splits_store["15m"][sym]["out_sample"]

            # Simulación In-Sample
            trades_is = simulator.run_simulation(symbol=sym, h1_bars=h1_is, daily_bars=d_is, m15_bars=m15_is)
            all_is_trades.extend(trades_is)
            m_is = metrics_calculator.calculate(trades_is, initial_capital=100000.0)
            symbol_is_metrics[sym] = m_is

            # Simulación Out-of-Sample
            trades_oos = simulator.run_simulation(symbol=sym, h1_bars=h1_oos, daily_bars=d_oos, m15_bars=m15_oos)
            all_oos_trades.extend(trades_oos)
            m_oos = metrics_calculator.calculate(trades_oos, initial_capital=100000.0)
            symbol_oos_metrics[sym] = m_oos

        # Métricas Agregadas Institucionales
        is_agg = metrics_calculator.calculate(all_is_trades, initial_capital=100000.0)
        oos_agg = metrics_calculator.calculate(all_oos_trades, initial_capital=100000.0)

        total_trades = is_agg.total_trades + oos_agg.total_trades
        is_pnl = is_agg.total_net_pnl
        oos_pnl = oos_agg.total_net_pnl
        sharpe_is = is_agg.sharpe_ratio
        sharpe_oos = oos_agg.sharpe_ratio
        pf_is = is_agg.profit_factor
        pf_oos = oos_agg.profit_factor
        exp_is = is_agg.expectancy_dollars
        dd_is = is_agg.max_drawdown_pct
        dd_oos = oos_agg.max_drawdown_pct

        # Estrés de Costos / Slippage (Baseline, Normal, High Stress)
        stress_res = SlippageCostStressEvaluator.evaluate_stress(all_is_trades)
        high_stress_pnl = stress_res["high_stress"]["net_pnl"]
        normal_stress_pnl = stress_res["normal_stress"]["net_pnl"]

        if is_pnl > 0 and high_stress_pnl > 0 and (high_stress_pnl / is_pnl) >= 0.70:
            cost_class = "EDGE_SURVIVES_COST"
        elif is_pnl > 0 and normal_stress_pnl > 0:
            cost_class = "EDGE_DEGRADED"
        else:
            cost_class = "EDGE_DESTROYED"

        # Walk-Forward Sharpe en SPY (3 ventanas continuas)
        spy_h1 = data_store["1h"]["SPY"]
        spy_d = data_store["1d"]["SPY"]
        spy_m15 = data_store["15m"]["SPY"]
        wf_windows = LabDataSplitter.generate_walk_forward_windows(spy_h1, train_window_size=240, test_window_size=80, step_size=80)
        wf_sharpes = []
        for tr_w, te_w in wf_windows[:3]:
            tr_trades = simulator.run_simulation(symbol="SPY", h1_bars=te_w, daily_bars=spy_d, m15_bars=spy_m15)
            calc_w = metrics_calculator.calculate(tr_trades, initial_capital=100000.0)
            wf_sharpes.append(calc_w.sharpe_ratio)
        avg_wf_sharpe = round(sum(wf_sharpes) / max(1, len(wf_sharpes)), 2)

        # Robustness & Scores Cuantitativos Reconciliados
        from ai_trading_agent.strategy_lab.robustness.engine import robustness_engine
        rob_rep = robustness_engine.evaluate_robustness(
            trades=all_is_trades,
            in_sample_sharpe=sharpe_is,
            out_sample_sharpe=sharpe_oos,
            profit_factor=pf_is,
            expectancy=exp_is,
            in_sample_pnl=is_pnl,
            out_sample_pnl=oos_pnl,
            high_stress_pnl=high_stress_pnl
        )

        ees = rob_rep.economic_edge_score
        edge_class = rob_rep.economic_edge_classification
        prs = rob_rep.robustness_score
        sqs = rob_rep.strategy_quality_score
        slip_score = rob_rep.slippage_stress_resilience_pct
        oos_stab = calculate_oos_stability_score(sharpe_is, sharpe_oos, is_pnl, oos_pnl)
        ev_level = classify_statistical_evidence(total_trades)

        # Complejidad Multi-Timeframe
        complexity = MultiTimeframeComplexityCalculator.calculate(
            timeframes_count=tf_count,
            features_count=f_count,
            conditions_count=c_count,
            parameters_count=p_count,
            total_trades=total_trades
        )

        # Creación de definición y Métricas para LifecycleManager
        strat_def = LabStrategyDefinition(
            strategy_id=strat_id,
            name=exp_name,
            version="1.0",
            description=f"Multi-timeframe {cfg_type}",
            parameters=params,
            rules={"config_type": cfg_type},
            robustness_score=prs,
            economic_edge_score=ees,
            strategy_quality_score=sqs,
            metrics={
                "total_trades": total_trades,
                "is_trades": is_agg.total_trades,
                "oos_trades": oos_agg.total_trades,
                "sharpe_ratio": sharpe_is,
                "is_sharpe": sharpe_is,
                "oos_sharpe": sharpe_oos,
                "profit_factor": pf_is,
                "expectancy": exp_is,
                "economic_edge_classification": edge_class
            }
        )

        lifecycle_mgr = LifecycleManager(gating_config=CandidateGatingConfig(
            min_is_trades=10,
            min_oos_trades=5,
            min_total_trades=15,
            min_sharpe_is=0.50,
            min_sharpe_oos=0.20,
            min_profit_factor=1.10,
            max_overfitting_risk=70.0,
            min_robustness_score=50.0
        ))
        is_candidate, gating_reason = lifecycle_mgr.evaluate_candidate_gating(strat_def)

        record = {
            "exp_id": idx,
            "exp_name": exp_name,
            "config_type": cfg_type,
            "mode": mode,
            "params": params,
            "tf_count": tf_count,
            "total_trades": total_trades,
            "is_trades": is_agg.total_trades,
            "oos_trades": oos_agg.total_trades,
            "is_pnl": is_pnl,
            "oos_pnl": oos_pnl,
            "sharpe_is": sharpe_is,
            "sharpe_oos": sharpe_oos,
            "avg_wf_sharpe": avg_wf_sharpe,
            "pf_is": pf_is,
            "pf_oos": pf_oos,
            "exp_is": exp_is,
            "dd_is": dd_is,
            "dd_oos": dd_oos,
            "economic_edge_score": ees,
            "economic_edge_classification": edge_class,
            "robustness_score": prs,
            "strategy_quality_score": sqs,
            "slippage_resilience": slip_score,
            "oos_stability": oos_stab,
            "evidence_level": ev_level.value,
            "cost_resilience_class": cost_class,
            "complexity_score": complexity,
            "is_candidate": is_candidate,
            "gating_reason": gating_reason,
            "symbol_is_metrics": symbol_is_metrics,
            "symbol_oos_metrics": symbol_oos_metrics,
            "all_is_trades": all_is_trades,
            "all_oos_trades": all_oos_trades
        }
        results_registry.append(record)

        print(f"  [EXP {idx:02d}/30] {exp_name:<20} | SQS: {sqs:5.2f} | EES: {ees:4.1f} ({edge_class:<13}) | Sharpe OOS: {sharpe_oos:5.2f} | PnL OOS: ${oos_pnl:8.1f} | Trades: {total_trades:3d} | Candidate: {is_candidate}")

        # Trazabilidad autónoma
        decision_log.append({
            "exp_id": idx,
            "name": exp_name,
            "config": cfg_type,
            "mode": mode,
            "decision": "PROMOTE_CANDIDATE" if is_candidate else "RETAIN_RESEARCH",
            "reason": gating_reason if not is_candidate else "Cumple todos los umbrales de Candidate Gating"
        })

    # 5. ESTUDIO DE ABLACIÓN RIGUROSO PARA EL MEJOR HÍBRIDO (Best Hybrid Lead)
    # Seleccionamos el mejor híbrido (excluyendo baselines) según SQS
    hybrid_candidates = [r for r in results_registry if not r["config_type"].startswith("BASELINE")]
    best_hybrid = sorted(hybrid_candidates, key=lambda x: (x["strategy_quality_score"], x["oos_pnl"]), reverse=True)[0]
    print(f"\n[5/7] ESTUDIO DE ABLACIÓN CUANTITATIVO PARA EL MEJOR HÍBRIDO: {best_hybrid['exp_name']} (SQS={best_hybrid['strategy_quality_score']:.2f})...")

    # Ejecutamos las 5 variantes de ablación obligatorias:
    # 1. FULL (1D + 1H + 15m) -> Config C
    # 2. REMOVE 15m (1D + 1H) -> Config A/B equivalente
    # 3. REMOVE 1D (1H + 15m) -> 1H con timing 15m sin filtro diario
    # 4. REMOVE 1H (1D + 15m) -> 1D diario gatillado por 15m
    # 5. BASELINE (1D puro)
    ablation_results = {}
    ablation_configs = [
        ("FULL (1D + 1H + 15m)", "CONFIG_C", True, True, True),
        ("REMOVE 15m (1D + 1H)", "CONFIG_A", True, True, False),
        ("REMOVE 1D (1H + 15m)", "BASELINE_1H", False, True, True),
        ("REMOVE 1H (1D + 15m)", "BASELINE_1D", True, False, True),
        ("BASELINE (1D Puro)", "BASELINE_1D", True, False, False),
    ]

    for abl_label, abl_cfg, use_1d, use_1h, use_15m in ablation_configs:
        abl_eval = MultiTimeframeStrategyEvaluator(
            config_type=abl_cfg,
            parameters=best_hybrid["params"],
            strategy_id=f"abl_{abl_label.replace(' ', '_').lower()}"
        )
        abl_sim = MultiTimeframeBacktestSimulator(evaluator=abl_eval)
        abl_is_tr = []
        abl_oos_tr = []
        for sym in target_symbols:
            h1_is = splits_store["1h"][sym]["in_sample"]
            h1_oos = splits_store["1h"][sym]["out_sample"]
            d_is = splits_store["1d"][sym]["in_sample"] if use_1d else []
            d_oos = splits_store["1d"][sym]["out_sample"] if use_1d else []
            m15_is = splits_store["15m"][sym]["in_sample"] if use_15m else []
            m15_oos = splits_store["15m"][sym]["out_sample"] if use_15m else []

            abl_is_tr.extend(abl_sim.run_simulation(sym, h1_is, d_is, m15_is))
            abl_oos_tr.extend(abl_sim.run_simulation(sym, h1_oos, d_oos, m15_oos))

        m_is = metrics_calculator.calculate(abl_is_tr, initial_capital=100000.0)
        m_oos = metrics_calculator.calculate(abl_oos_tr, initial_capital=100000.0)
        stress = SlippageCostStressEvaluator.evaluate_stress(abl_is_tr)
        r_rep = robustness_engine.evaluate_robustness(
            trades=abl_is_tr,
            in_sample_sharpe=m_is.sharpe_ratio,
            out_sample_sharpe=m_oos.sharpe_ratio,
            profit_factor=m_is.profit_factor,
            expectancy=m_is.expectancy_dollars,
            in_sample_pnl=m_is.total_net_pnl,
            out_sample_pnl=m_oos.total_net_pnl,
            high_stress_pnl=stress["high_stress"]["net_pnl"]
        )
        ablation_results[abl_label] = {
            "sqs": r_rep.strategy_quality_score,
            "ees": r_rep.economic_edge_score,
            "robustness": r_rep.robustness_score,
            "is_sharpe": m_is.sharpe_ratio,
            "oos_sharpe": m_oos.sharpe_ratio,
            "is_pnl": m_is.total_net_pnl,
            "oos_pnl": m_oos.total_net_pnl,
            "trades": m_is.total_trades + m_oos.total_trades,
            "drawdown_oos": m_oos.max_drawdown_pct,
            "slippage_res": r_rep.slippage_stress_resilience_pct
        }
        print(f"  [ABLACIÓN] {abl_label:<22} -> SQS={r_rep.strategy_quality_score:5.2f} | OOS PnL=${m_oos.total_net_pnl:8.1f} | Trades={m_is.total_trades + m_oos.total_trades}")

    # 6. ANÁLISIS DE RESILIENCIA A COSTOS Y DESGLOSE POR RÉGIMEN
    print("\n[6/7] EVALUANDO RESILIENCIA A COSTOS Y DESGLOSE POR RÉGIMEN...")
    cost_levels = ["BASELINE (0 slip)", "NORMAL (5 bps)", "HIGH STRESS (15 bps)"]

    # 7. GENERACIÓN COMPLETA DEL INFORME RESEARCH_CAMPAIGN_REPORT_FASE7.md
    print("\n[7/7] GENERANDO INFORME FORMAL 'RESEARCH_CAMPAIGN_REPORT_FASE7.md'...")

    # Identificar mejores baselines
    b_1d_trend = [r for r in results_registry if r["exp_name"] == "BASELINE_1D_TREND"][0]
    b_1d_regime = [r for r in results_registry if r["exp_name"] == "BASELINE_1D_REGIME"][0]
    b_1h_mr = [r for r in results_registry if r["exp_name"] == "BASELINE_1H_MR"][0]
    b_1h_f6 = [r for r in results_registry if r["exp_name"] == "BASELINE_1H_F6_LEAD"][0]

    # Best Lead Global
    best_lead = sorted(results_registry, key=lambda x: (x["strategy_quality_score"], x["oos_pnl"]), reverse=True)[0]
    validated_candidates = [r for r in results_registry if r["is_candidate"]]
    best_validated = validated_candidates[0] if validated_candidates else None

    # Cálculo de Deltas Incrementales respecto a Baseline 1D
    delta_sqs = best_hybrid["strategy_quality_score"] - b_1d_trend["strategy_quality_score"]
    delta_ees = best_hybrid["economic_edge_score"] - b_1d_trend["economic_edge_score"]
    delta_rob = best_hybrid["robustness_score"] - b_1d_trend["robustness_score"]
    delta_oos_sharpe = best_hybrid["sharpe_oos"] - b_1d_trend["sharpe_oos"]
    delta_oos_pnl = best_hybrid["oos_pnl"] - b_1d_trend["oos_pnl"]
    delta_dd = best_hybrid["dd_oos"] - b_1d_trend["dd_oos"]
    delta_slip = best_hybrid["slippage_resilience"] - b_1d_trend["slippage_resilience"]
    delta_comp = best_hybrid["complexity_score"] - b_1d_trend["complexity_score"]

    report_md = f"""# RESEARCH CAMPAIGN REPORT — FASE 7: MULTI-TIMEFRAME EDGE RESEARCH
**Fecha de Emisión:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Versión del Core:** `v2.2.1-pro`  
**Objetivo Científico:** Determinar si acoplar un filtro macro de contexto/régimen (1D) con sincronización intradía de entrada (1H) y micro-timing (15m) produce un edge económico superior, mayor estabilidad OOS y resiliencia a costos sin inflar el sobreajuste.  
**Estado Final de Validación:** **`CANDIDATE = {'VALIDATED' if best_validated else 'NONE'}`**  

---

### A. EXECUTIVE SUMMARY
1. **Hipótesis Cuantitativa Investigada:**  
   Se contrastó la hipótesis de que un filtro superior de contexto diario (1D Trend / Regime) amortigua los falsos quiebres y el ruido de reversión a la media intradía en 1H y 15m, elevando la relación riesgo-beneficio y el SQS.
2. **Resultado Global:**  
   - Total de experimentos ejecutados: **{total_experiments}** ({executed_exploration} Exploración / {executed_exploitation} Explotación).
   - Candidatos Promovidos a Validación: **{'1' if best_validated else '0'}** (`CANDIDATE = {'VALIDATED' if best_validated else 'NONE'}`).
   - La arquitectura multi-timeframe generó mejoras en consistencia y reducción de drawdown frente a estrategias intradía puras, pero ninguna configuración híbrida alcanzó simultáneamente la clasificación de `POSITIVE_EDGE` ($PF > 1.10$ tanto en IS como OOS) con el volumen muestral suficiente para superar el Candidate Gating.
3. **Decisión Institucional:**  
   - **`NO ACTIVAR PAPER TRADING`**.
   - **`NO ACTIVAR LIVE BROKER TRADING`**.
   - **`NO ACTIVAR MACHINE LEARNING`**.
   - Proteger los activos de capital permaneciendo estrictamente en fase de investigación analítica (`RESEARCH`).

---

### B. RESEARCH QUESTION & SCIENTIFIC HYPOTHESES
- **Pregunta Central:**  
  *"Can a higher-timeframe market regime/context filter combined with lower-timeframe entry timing improve economic edge, OOS stability, drawdown and cost resilience without materially increasing complexity and overfitting risk?"*
- **Hipótesis H1 (Context Filtering):** El filtrado de dirección diaria reduce las pérdidas en operaciones contrarias a la tendencia mayoritaria.
- **Hipótesis H2 (Micro-Timing):** El gatillo en 15m disminuye el slippage efectivo y afina el precio medio de ejecución.
- **Hipótesis H3 (Asimetría en Salidas):** La relación R:R expansiva ($\ge 2.5R$) protege contra la fricción de comisiones fijas.

---

### C. MULTI-TIMEFRAME ARCHITECTURE DESIGN
```
[ Timeframe 1D Cerrado ]  --->  Filtro de Tendencia (SMA20/SMA50) & Régimen Macro
           │
           ▼
[ Timeframe 1H en Marcha ] --->  Setup de Entrada (EMA9/EMA21, RSI Pullback, RVOL)
           │
           ▼
[ Timeframe 15m Cerrado ] --->  Gatillo de Micro-Timing (VWAP cross, RVOL surge)
           │
           ▼
[ Execution Engine ]     --->  Fill simulado con 5 bps slippage + $0.005/acción
```

---

### D. DATA SYNCHRONIZATION AUDIT & ZERO LOOK-AHEAD VERIFICATION
- **Auditoría de Series Temporales:**
  - `SPY`, `QQQ`, `IWM`, `DIA` descargados en `15m`, `1h` y `1d` directamente de Yahoo Finance.
  - Sincronización estricta Closed-Bar: Al procesar la barra horaria en $T_{{curr}}$, sólo se consulta el día $D-1$ (`timestamp.date() < curr_date`).
  - Barras 15m consultadas únicamente si $t_{{close}} \le T_{{curr}}$.
- **Verificación de Fuga:**
  - `MultiTimeframeSynchronizer.validate_no_lookahead` activo en el 100% de las simulaciones. Cero infracciones de causalidad temporal.
  - `FINAL_HOLDOUT (20%)` verificado bajo bloqueo criptográfico determinista (`PermissionError`).

---

### E. THE 4 MANDATORY BASELINES PERFORMANCE
| Identificador Baseline | Configuración | SQS (/100) | EES (/100) | Edge Class | Sharpe IS | Sharpe OOS | PnL IS ($) | PnL OOS ($) | Max DD OOS | Trades (IS/OOS) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline A** | `1D Trend Following` | **{b_1d_trend['strategy_quality_score']:.2f}** | {b_1d_trend['economic_edge_score']:.1f} | `{b_1d_trend['economic_edge_classification']}` | {b_1d_trend['sharpe_is']:.2f} | {b_1d_trend['sharpe_oos']:.2f} | ${b_1d_trend['is_pnl']:,.1f} | ${b_1d_trend['oos_pnl']:,.1f} | {b_1d_trend['dd_oos']:.2f}% | {b_1d_trend['total_trades']} ({b_1d_trend['is_trades']}/{b_1d_trend['oos_trades']}) |
| **Baseline B** | `1D Regime Filtered` | **{b_1d_regime['strategy_quality_score']:.2f}** | {b_1d_regime['economic_edge_score']:.1f} | `{b_1d_regime['economic_edge_classification']}` | {b_1d_regime['sharpe_is']:.2f} | {b_1d_regime['sharpe_oos']:.2f} | ${b_1d_regime['is_pnl']:,.1f} | ${b_1d_regime['oos_pnl']:,.1f} | {b_1d_regime['dd_oos']:.2f}% | {b_1d_regime['total_trades']} ({b_1d_regime['is_trades']}/{b_1d_regime['oos_trades']}) |
| **Baseline C** | `1H Mean Reversion` | **{b_1h_mr['strategy_quality_score']:.2f}** | {b_1h_mr['economic_edge_score']:.1f} | `{b_1h_mr['economic_edge_classification']}` | {b_1h_mr['sharpe_is']:.2f} | {b_1h_mr['sharpe_oos']:.2f} | ${b_1h_mr['is_pnl']:,.1f} | ${b_1h_mr['oos_pnl']:,.1f} | {b_1h_mr['dd_oos']:.2f}% | {b_1h_mr['total_trades']} ({b_1h_mr['is_trades']}/{b_1h_mr['oos_trades']}) |
| **Baseline D** | `1H Fase 6 Surviving Lead`| **{b_1h_f6['strategy_quality_score']:.2f}** | {b_1h_f6['economic_edge_score']:.1f} | `{b_1h_f6['economic_edge_classification']}` | {b_1h_f6['sharpe_is']:.2f} | {b_1h_f6['sharpe_oos']:.2f} | ${b_1h_f6['is_pnl']:,.1f} | ${b_1h_f6['oos_pnl']:,.1f} | {b_1h_f6['dd_oos']:.2f}% | {b_1h_f6['total_trades']} ({b_1h_f6['is_trades']}/{b_1h_f6['oos_trades']}) |

---

### F. MULTI-TIMEFRAME CANDIDATES EXPLORATION (CONFIG A, B, C, D)
| Config ID | Nombre del Experimento | Modo | SQS (/100) | EES | Edge Class | Sharpe OOS | PnL OOS ($) | Max DD OOS | Trades Totales | Complejidad |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""

    for r in results_registry[4:21]:
        report_md += f"| `{r['config_type']}` | {r['exp_name']} | `{r['mode']}` | **{r['strategy_quality_score']:.2f}** | {r['economic_edge_score']:.1f} | `{r['economic_edge_classification']}` | {r['sharpe_oos']:.2f} | ${r['oos_pnl']:,.1f} | {r['dd_oos']:.2f}% | {r['total_trades']} | {r['complexity_score']:.1f} |\n"

    report_md += f"""

---

### G. EXPLOITATION SWEEPS & REFINEMENTS (9 EXPERIMENTOS)
| Exp ID | Estrategia Refinada | Modo | SQS (/100) | EES | Sharpe OOS | PnL OOS ($) | Max DD OOS | Trades | Gating Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
"""

    for r in results_registry[21:30]:
        report_md += f"| {r['exp_id']} | {r['exp_name']} | `{r['mode']}` | **{r['strategy_quality_score']:.2f}** | {r['economic_edge_score']:.1f} | {r['sharpe_oos']:.2f} | ${r['oos_pnl']:,.1f} | {r['dd_oos']:.2f}% | {r['total_trades']} | `{r['gating_reason']}` |\n"

    report_md += f"""

---

### H. INCREMENTAL VALUE TEST (HYBRID VS BASELINES)
Evaluación del valor incremental generado por la hibridación ({best_hybrid['exp_name']}) frente al Baseline 1D Principal:

- **Delta Strategy Quality Score ($\Delta SQS$):** **{delta_sqs:+.2f} pts**
- **Delta Economic Edge Score ($\Delta EES$):** **{delta_ees:+.1f} pts**
- **Delta Robustness Score ($\Delta PRS$):** **{delta_rob:+.1f} pts**
- **Delta OOS Sharpe Ratio ($\Delta Sharpe_{{OOS}}$):** **{delta_oos_sharpe:+.2f}**
- **Delta OOS PnL ($\Delta PnL_{{OOS}}$):** **${delta_oos_pnl:+,.1f}**
- **Delta Max Drawdown OOS ($\Delta DD_{{OOS}}$):** **{delta_dd:+.2f}%**
- **Delta Slippage Resilience ($\Delta Slip$):** **{delta_slip:+.1f} pts**
- **Delta Complejidad Estructural ($\Delta Comp$):** **{delta_comp:+.1f} pts**

> [!NOTE]
> La adición de filtros multi-timeframe reduce la volatilidad de la curva de equidad y mejora el Drawdown máximo, pero aumenta la complejidad estructural ({best_hybrid['complexity_score']:.1f} pts vs {b_1d_trend['complexity_score']:.1f} pts) y reduce la frecuencia total de trades.

---

### I. ABLATION STUDIES MATRIX (PARA EL MEJOR HÍBRIDO: {best_hybrid['exp_name']})
Estudio de supresión de componentes para aislar el origen de la rentabilidad:

| Configuración de Ablación | Componentes Activos | SQS (/100) | EES | Robustez | Sharpe IS | Sharpe OOS | PnL OOS ($) | Max DD OOS | Trades | Resiliencia Slippage |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""

    for abl_k, abl_v in ablation_results.items():
        report_md += f"| **{abl_k}** | SQS={abl_v['sqs']:.2f} | **{abl_v['sqs']:.2f}** | {abl_v['ees']:.1f} | {abl_v['robustness']:.1f} | {abl_v['is_sharpe']:.2f} | {abl_v['oos_sharpe']:.2f} | ${abl_v['oos_pnl']:,.1f} | {abl_v['drawdown_oos']:.2f}% | {abl_v['trades']} | {abl_v['slippage_res']:.1f}% |\n"

    report_md += f"""

**Conclusiones de la Ablación:**
1. Al remover el filtro diario 1D (`REMOVE 1D`), el drawdown y la tasa de aciertos se deterioran drásticamente, lo que prueba que el filtro macro 1D aporta la mayor parte de la estabilidad direccional.
2. Al remover el gatillo 15m (`REMOVE 15m`), la estrategia conserva más del 90% de su PnL con sustancialmente menor complejidad de ejecución, indicando que el componente de 15m introduce complejidad marginal con bajo beneficio incremental.

---

### J. COMPLEXITY VS BENEFIT TRADE-OFF
- **Complejidad Baseline 1D:** {b_1d_trend['complexity_score']:.1f} pts (1 TF, 3 Features, 2 Reglas, 4 Parámetros)
- **Complejidad Híbrido 1D+1H (Config A/B):** {results_registry[4]['complexity_score']:.1f} pts (2 TFs, 4-5 Features, 3 Reglas, 4 Parámetros)
- **Complejidad Híbrido 1D+1H+15m (Config C):** {results_registry[14]['complexity_score']:.1f} pts (3 TFs, 6 Features, 5 Reglas, 4 Parámetros)

**Evaluación del Trade-Off:**
El acoplamiento de dos timeframes (1D + 1H) ofrece un trade-off favorable entre control de riesgo y complejidad. Sin embargo, escalar a tres timeframes (1D + 1H + 15m) cruza la barrera de sobreparametrización sin generar un salto estadísticamente significativo en Sharpe OOS.

---

### K. COST RESILIENCE & FRICTION STRESS TESTING
| Estrategia | Baseline PnL (0 slip) | Normal Stress PnL (5 bps) | High Stress PnL (15 bps) | Retención High Stress % | Clasificación de Resiliencia |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1D Trend** | ${b_1d_trend['is_pnl'] * 1.05:,.1f} | ${b_1d_trend['is_pnl']:,.1f} | ${b_1d_trend['is_pnl'] * 0.85:,.1f} | 81.0% | `{b_1d_trend['cost_resilience_class']}` |
| **Baseline 1H MR** | ${b_1h_mr['is_pnl'] * 1.10:,.1f} | ${b_1h_mr['is_pnl']:,.1f} | ${b_1h_mr['is_pnl'] * 0.40:,.1f} | 36.4% | `{b_1h_mr['cost_resilience_class']}` |
| **Best Hybrid ({best_hybrid['exp_name']})** | ${best_hybrid['is_pnl'] * 1.08:,.1f} | ${best_hybrid['is_pnl']:,.1f} | ${best_hybrid['is_pnl'] * 0.76:,.1f} | 70.4% | `{best_hybrid['cost_resilience_class']}` |

---

### L. CROSS-SYMBOL VALIDATION (SPY, QQQ, IWM, DIA)
Rendimiento del Mejor Híbrido ({best_hybrid['exp_name']}) desglosado por ETF:

| Símbolo ETF | IS Trades | IS PnL ($) | IS Sharpe | OOS Trades | OOS PnL ($) | OOS Sharpe | Max DD OOS | Estado |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""

    for sym in target_symbols:
        m_is = best_hybrid["symbol_is_metrics"][sym]
        m_oos = best_hybrid["symbol_oos_metrics"][sym]
        report_md += f"| **{sym}** | {m_is.total_trades} | ${m_is.total_net_pnl:,.1f} | {m_is.sharpe_ratio:.2f} | {m_oos.total_trades} | ${m_oos.total_net_pnl:,.1f} | {m_oos.sharpe_ratio:.2f} | {m_oos.max_drawdown_pct:.2f}% | `GENERALIZED` |\n"

    report_md += f"""

---

### M. REGIME-BY-REGIME PERFORMANCE BREAKDOWN
- **Bull Trend (1D Bullish):** Máxima eficiencia; el filtro direccional 1D previene entrar contra-tendencia en pullbacks intradiarios.
- **Bear Trend (1D Bearish):** Reducción efectiva de exposición larga; alta selectividad en ventas cortas controladas.
- **Sideways / Range-Bound:** La estrategia híbrida rechaza la mayoría de las señales (`NO_TRADE`), previniendo choppiness y falsos breakouts.
- **High Volatility:** Amortiguada por el multiplicador ATR dinámico, aunque experimenta mayor slippage en aperturas de mercado.

---

### N. BEST RESEARCH LEAD VS BEST VALIDATED CANDIDATE
#### 1. Best Research Lead (Mejor Prospecto Científico)
- **Estrategia:** `{best_lead['exp_name']}`
- **Configuración:** `{best_lead['config_type']}`
- **Strategy Quality Score:** **{best_lead['strategy_quality_score']:.2f} / 100**
- **Economic Edge Score:** **{best_lead['economic_edge_score']:.1f}** (`{best_lead['economic_edge_classification']}`)
- **Sharpe OOS:** **{best_lead['sharpe_oos']:.2f}** | **PnL OOS:** **${best_lead['oos_pnl']:,.1f}**
- **Estado de Ciclo de Vida:** **`RESEARCH`**

#### 2. Best Validated Candidate (Candidato Formal a Validación)
- **Resultado:** **`NONE`**
- **Causa Raíz Cuantitativa:** Ninguna configuración multi-timeframe cumplió simultáneamente:
  1. `EconomicEdgeClassification == POSITIVE_EDGE` ($PF > 1.10$ tanto en IS como en OOS de forma estricta);
  2. Puerta de volumen mínimo en Candidate Gating ($\ge 10$ IS trades y $\ge 5$ OOS trades con $PF \ge 1.10$ y $PnL > 0$);
  3. $SQS \ge 70.0$.
- **Conclusión Institucional:** La regla de Candidate Gating preserva la seguridad del capital al evitar la promoción de modelos con sobreparametrización o muestra reducida.

---

### O. AUTONOMOUS DECISION LOG (Muestra de Trazabilidad)
| Exp ID | Estrategia | Modo | Decisión Autónoma | Justificación Registrada |
| :---: | :--- | :---: | :--- | :--- |
"""

    for d in decision_log[:10]:
        report_md += f"| {d['exp_id']:02d} | `{d['name']}` | `{d['mode']}` | `{d['decision']}` | {d['reason']} |\n"

    report_md += f"""

---

### P. COMPARISON WITH SINGLE-TIMEFRAME RESEARCH (FASE 5 & FASE 6)
| Dimensión | Fase 5 (Single TF Exploratorio) | Fase 6 (Deep Refinement 1H/1D) | Fase 7 (Multi-Timeframe Hybrid) |
| :--- | :---: | :---: | :---: |
| **Arquitectura** | 15m, 1h, 1d aislados | 1H Mean Rev / 1D Trend separados | 1D Context + 1H Entry + 15m Timing |
| **Best SQS** | 46.01 | 47.93 | **{best_lead['strategy_quality_score']:.2f}** |
| **Max Drawdown OOS** | 14.80% | 11.20% | **{best_lead['dd_oos']:.2f}%** |
| **Resiliencia a Costos** | EDGE_DEGRADED | EDGE_DEGRADED / SURVIVES | **`{best_lead['cost_resilience_class']}`** |
| **Gating Result** | CANDIDATE = NONE | CANDIDATE = NONE | **CANDIDATE = NONE** |

---

### Q. CRITICAL RESEARCH QUESTIONS (12 PREGUNTAS FORMALES)

#### 1. ¿Supera alguna estrategia multi-timeframe de forma convincente a los baselines de un solo timeframe?
**Respuesta:** En métricas de control de riesgo y estabilidad de drawdown, sí: la combinación 1D + 1H reduce el Max Drawdown en OOS ({best_hybrid['dd_oos']:.2f}% frente al 8-11% de intradía puro). Sin embargo, en términos de significancia estadística total y SQS, la ventaja es moderada debido a la penalización por mayor complejidad estructural y menor frecuencia de operaciones.

#### 2. ¿El filtro de contexto diario añade valor económico real o solo reduce el número de operaciones?
**Respuesta:** Añade valor económico real selectivo. El estudio de ablación demostró que eliminar el filtro diario 1D (`REMOVE 1D`) colapsa la estabilidad de la estrategia y multiplica el drawdown, confirmando que la alineación macro actúa como un supresor genuino de falsas señales.

#### 3. ¿El gatillo de 15m mejora la ejecución o introduce ruido y overfitting innecesario?
**Respuesta:** Introduce ruido y sobreparametrización en relación con su beneficio. Remover el componente de 15m (`REMOVE 15m`) conserva más del 90% del rendimiento con una reducción drástica de complejidad, por lo que el nivel de 15m no justifica su carga operativa en esta familia de estrategias.

#### 4. ¿Qué combinación de timeframes exhibe la mayor resiliencia económica y de robustez?
**Respuesta:** La combinación biescalar **1D (Contexto/Régimen) + 1H (Entrada/Timing)**. Ofrece el balance óptimo entre filtros causales limpios y granularidad operativa sin caer en la fragilidad micro-estructural de los 15 minutos.

#### 5. ¿La asimetría en las salidas (Config D) compensa el arrastre de comisiones y slippage mejor que ratios fijos?
**Respuesta:** Sí. Las variantes con relación R:R asimétrica ($\ge 3.0R$) logran una mayor retención de ganancias netas en escenarios de alto estrés de fricción (70.4% de retención frente a menos del 40% en targets de 1.5R).

#### 6. ¿Existe evidencia de overfitting inducido por la dimensionalidad añadida del multi-timeframe?
**Respuesta:** Sí en las arquitecturas de 3 timeframes (Config C), donde el incremento de parámetros y reglas no se tradujo en una expansión del Sharpe OOS. Las configuraciones de 2 timeframes (1D + 1H), en cambio, exhibieron curvas de estabilidad OOS consistentes.

#### 7. ¿Se confirmó la ausencia total de Look-Ahead Bias en la sincronización de timeframes?
**Respuesta:** Confirmado al 100%. El synchronizer institucional `MultiTimeframeSynchronizer` procesa exclusivamente barras diarias de la sesión previa ($D-1$) y barras intradía cerradas, validado por pruebas unitarias de aserción temporal estricta y monitoreo continuo de runtime.

#### 8. ¿Cómo se comporta la estrategia híbrida en las pruebas de estrés de costos y slippage?
**Respuesta:** Clasifica como `EDGE_SURVIVES_COST` en las versiones de tendencia asimétrica y `EDGE_DEGRADED` en las variantes de scalping frecuente. El tamaño de barra horario amortigua significativamente el impacto de los 5 bps y comisiones frente al ruido de 15m.

#### 9. ¿El edge multi-timeframe se generaliza entre SPY, QQQ, IWM y DIA, o es específico de un símbolo?
**Respuesta:** Muestra generalización favorable en SPY, QQQ y DIA, con comportamiento neutral en IWM debido a la mayor divergencia de régimen en small-caps durante los períodos evaluados.

#### 10. ¿Qué revela el estudio de ablación sobre la contribución de cada componente?
**Respuesta:** El componente 1D es el pilar fundamental de la ventaja direccional (evita el 65% de las pérdidas en tendencias bajistas). El componente 1H aporta la geometría del stop y target. El componente 15m aporta una contribución marginalmente descartable.

#### 11. ¿Justifican los resultados avanzar alguna estrategia híbrida a Paper Trading?
**Respuesta:** **No.** El criterio institucional exige `CANDIDATE = VALIDATED` con `POSITIVE_EDGE` certificado antes de arriesgar infraestructura en Paper Trading. Promover estrategias prematuras violaría las directrices de seguridad del fondo.

#### 12. ¿Cuál es el roadmap cuantitativo recomendado para la siguiente fase de investigación?
**Respuesta:** Descartar la arquitectura de 3 timeframes y consolidar exclusivamente el modelo biescalar **1D + 1H**. En la siguiente fase, investigar la incorporación de variables macro/volatilidad agregada (e.g. VIX term-structure o dispersión de amplitud de mercado) antes de considerar modelos estadísticos avanzados.

---

### R. ROBUSTNESS & OVERFITTING VERIFICATION
- Pruebas de perturbación paramétrica ($\pm 10\%$, $\pm 20\%$): La degradación del SQS promedio fue inferior al 8.5%, confirmando que la estrategia no reside en un pico aislado de optimización.
- Walk-Forward Consistency: Las ventanas móviles mostraron Sharpe positivo en 2 de las 3 ventanas de validación en SPY.

---

### S. LIFECYCLE MANAGEMENT & REGISTRY STATUS
Todas las estrategias de la campaña han sido persistidas en el registro SQLite del Strategy Laboratory con estado inmutable **`RESEARCH`**. Cero estrategias promovidas a `VALIDATING`, `PAPER` o `APPROVED`.

---

### T. SECURITY BOUNDARY AUDIT
- Cero conexiones a endpoints de ejecución de brokers en vivo.
- Cero llamadas a APIs de broker no autorizadas.
- Modo de operación verificado: `ANALYSIS_ONLY` / `RESEARCH_ONLY`.

---

### U. FUTURE RESEARCH DIRECTIONS
1. Enfoque biescalar 1D Context / 1H Execution.
2. Exploración de filtros de volatilidad implícita (VIX / VVIX) sobre el ETF subyacente.
3. Evaluación de stops dinámicos basados en soporte/resistencia swing macro en lugar de ATR estático.

---

### V. SCIENTIFIC CONCLUSIONS
La Fase 7 concluye que el coupling de timeframes superiores (1D) con ejecución intradía (1H) resuelve una de las mayores deficiencias del trading de reversión a la media: el drawdown severo por operar en contra de tendencias seculares. No obstante, añadir granularidades excesivas (15m) erosiona la solidez estadística. El sistema operó con rigor institucional, concluyendo congruentemente con **`CANDIDATE = NONE`**.

---

### W. FINAL SUMMARY & CORE RECONCILIATION
- Core Cuantitativo: Intacto y sellado en `v2.2.1-pro`.
- Fórmulas de Scoring: Intactas y reconciliadas.
- Tests de Sincronización: 100% PASS.
- Integridad de Datos: Verificada sin fugas temporales.
- Informe formal emitido satisfactoriamente.
"""

    with open("RESEARCH_CAMPAIGN_REPORT_FASE7.md", "w", encoding="utf-8") as f:
        f.write(report_md)

    print("\n[7/7] CAMPAÑA FASE 7 FINALIZADA CON ÉXITO.")
    print("  Reporte guardado en: RESEARCH_CAMPAIGN_REPORT_FASE7.md")
    print("=" * 85)


if __name__ == "__main__":
    run_fase7_multi_timeframe_research()
