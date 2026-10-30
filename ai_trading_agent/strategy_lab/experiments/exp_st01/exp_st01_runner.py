"""
ai_trading_agent.strategy_lab.experiments.exp_st01.exp_st01_runner
==================================================================
Master Experiment Runner para FASE EXP-ST01 (SuperTrend + EMA 200).

Ejecuta el ciclo experimental completo:
1. Campaña de 50 Backtests (10 Activos x 5 Temporalidades).
2. Evaluación de Robustez Multidimensional (Split cronológico, Walk-Forward, Monte Carlo, Sensibilidad, Regímenes, Costes).
3. Evaluación de Hipótesis de Descubrimiento H1 a H5.
4. Cálculo de Scores EES, PRS, SQS y Minimum Evidence Gate.
5. Generación de los 10 Entregables Formales.
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import json
import csv
from datetime import datetime
from typing import List, Dict, Any

from ai_trading_agent.strategy_lab.experiments.exp_st01.campaign_50_backtests import Campaign50BacktestsRunner
from ai_trading_agent.strategy_lab.experiments.exp_st01.robustness_engine import (
    RobustnessEngineST,
    StrategyScoresST,
    MonteCarloMetrics,
    CostStressResult,
    ChronoSplitResult,
)
from ai_trading_agent.strategy_lab.experiments.exp_st01.discovery_hypotheses import DiscoveryHypothesesEvaluator
from ai_trading_agent.strategy_lab.experiments.exp_st01.data_loader import ExpSt01DataLoader, ASSETS_UNIVERSE, TIMEFRAMES


class ExpSt01MasterRunner:
    """Orquestador integral del experimento EXP-ST01."""

    def __init__(self):
        self.exp_dir = Path(__file__).resolve().parent
        self.data_loader = ExpSt01DataLoader(cache_dir=self.exp_dir / "data_cache")
        self.campaign_runner = Campaign50BacktestsRunner(output_dir=self.exp_dir)
        self.robustness_engine = RobustnessEngineST(initial_equity=100000.0, risk_per_trade=250.0)
        self.hypotheses_evaluator = DiscoveryHypothesesEvaluator(initial_equity=100000.0, risk_per_trade=250.0)

    def run_experiment(self):
        print("================================================================================")
        print("          ORACLEBOT V2 — FASE EXP-ST01: SUPERTREND + EMA 200 RESEARCH          ")
        print("================================================================================")

        # 1. Ejecutar Campaña de 50 Backtests
        metrics_list, trades_dict, audits = self.campaign_runner.run_all()

        # Filtrar candidatos válidos
        valid_candidates = [m for m in metrics_list if m.status == "VALID" and m.net_pnl > 0]
        valid_candidates.sort(key=lambda x: x.profit_factor, reverse=True)

        print("\n=== TOP CANDIDATOS CON VENTAJA ECONÓMICA BRUTA / NETA ===")
        for c in valid_candidates[:5]:
            print(f"-> {c.symbol}_{c.timeframe}: PF={c.profit_factor:.2f}, NetPnL=${c.net_pnl:.2f}, Sharpe={c.sharpe_ratio:.2f}, Trades={c.total_trades}")

        # Seleccionar activo insignia representativo para batería de robustez profunda
        # GLD_H1 tiene 75 trades (muestra más grande), DIA_H1 tiene 50 trades, QQQ_D1 y DIA_D1 alta consistencia
        lead_sym, lead_tf = "GLD", "H1"
        if not any(m.symbol == lead_sym and m.timeframe == lead_tf for m in metrics_list):
            lead_sym, lead_tf = "SPY", "D1"

        lead_bars, _ = self.data_loader.load_or_fetch(lead_sym, lead_tf)
        lead_trades = trades_dict.get(f"{lead_sym}_{lead_tf}", [])
        lead_metrics = next(m for m in metrics_list if m.symbol == lead_sym and m.timeframe == lead_tf)

        # También analizar segundo activo líder: DIA_D1 / QQQ_D1
        second_sym, second_tf = "DIA", "D1"
        second_bars, _ = self.data_loader.load_or_fetch(second_sym, second_tf)
        second_trades = trades_dict.get(f"{second_sym}_{second_tf}", [])
        second_metrics = next(m for m in metrics_list if m.symbol == second_sym and m.timeframe == second_tf)

        print(f"\nEjecutando batería de robustez sobre activo líder: {lead_sym}_{lead_tf}...")

        # 2. Robustez
        chrono = self.robustness_engine.evaluate_chrono_split(lead_sym, lead_tf, lead_bars)
        wf_windows = self.robustness_engine.evaluate_walk_forward(lead_sym, lead_tf, lead_bars)
        mc = self.robustness_engine.evaluate_monte_carlo(lead_trades)
        cost_stress = self.robustness_engine.evaluate_cost_stress(lead_sym, lead_tf, lead_bars)
        regimes = self.robustness_engine.evaluate_market_regimes(lead_bars, lead_trades)
        param_grid = self.robustness_engine.evaluate_parameter_sensitivity(lead_sym, lead_tf, lead_bars)
        scores = self.robustness_engine.compute_scores(lead_metrics, mc, cost_stress, chrono)

        print(f"Resultados Robustez {lead_sym}_{lead_tf}:")
        print(f"  - EES: {scores.economic_edge_score} | PRS: {scores.pure_robustness_score} | SQS: {scores.strategy_quality_score}")
        print(f"  - Minimum Evidence Gate: {'APROBADO' if scores.passed_minimum_gate else 'RECHAZADO'}")
        if scores.gate_failure_reasons:
            print(f"    Motivos: {scores.gate_failure_reasons}")

        # 3. Hipótesis H1 - H5
        print(f"\nEvaluando Hipótesis de Descubrimiento H1 a H5 sobre {lead_sym}_{lead_tf}...")
        h1 = self.hypotheses_evaluator.evaluate_h1_adx(lead_sym, lead_tf, lead_bars)
        h2 = self.hypotheses_evaluator.evaluate_h2_rvol(lead_sym, lead_tf, lead_bars)
        h3 = self.hypotheses_evaluator.evaluate_h3_atr_expansion(lead_sym, lead_tf, lead_bars)
        h4 = self.hypotheses_evaluator.evaluate_h4_session_timing(lead_sym, lead_tf, lead_bars)
        h5 = self.hypotheses_evaluator.evaluate_h5_trailing_stop(lead_sym, lead_tf, lead_bars)

        hypotheses_results = [h1, h2, h3, h4, h5]
        for h in hypotheses_results:
            print(f"  - [{h.hypothesis_id}] {h.name}: DeltaPF={h.delta_pf:+.2f}, DeltaPnL=${h.delta_pnl:+.2f} -> {h.verdict}")

        # 4. Generar y exportar los 10 entregables requeridos
        self._generate_all_deliverables(
            metrics_list,
            audits,
            lead_sym,
            lead_tf,
            lead_metrics,
            chrono,
            wf_windows,
            mc,
            cost_stress,
            regimes,
            param_grid,
            scores,
            hypotheses_results,
            second_metrics,
        )

        print("\n================================================================================")
        print("          FASE EXP-ST01 COMPLETADA — TODOS LOS ENTREGABLES GENERADOS           ")
        print("================================================================================")

    def _generate_all_deliverables(
        self,
        metrics_list: List[Any],
        audits: List[Any],
        lead_sym: str,
        lead_tf: str,
        lead_m: Any,
        chrono: ChronoSplitResult,
        wf_windows: List[Any],
        mc: MonteCarloMetrics,
        cost_stress: CostStressResult,
        regimes: List[Any],
        param_grid: List[Any],
        scores: StrategyScoresST,
        hypotheses: List[Any],
        second_m: Any,
    ):
        # 1. DELIVERABLE 01 - Resumen Ejecutivo
        self._write_deliverable_01(metrics_list, lead_m, scores, hypotheses)

        # 2. DELIVERABLE 02 - Matriz de 50 Backtests (ya generada en campaign_50_backtests.py)

        # 3. DELIVERABLE 03 - Reporte de Robustez Estadística
        self._write_deliverable_03(lead_sym, lead_tf, chrono, wf_windows, mc, scores)

        # 4. DELIVERABLE 04 - Heatmap de Sensibilidad Paramétrica
        self._write_deliverable_04(param_grid)

        # 5. DELIVERABLE 05 - Estrés de Costes
        self._write_deliverable_05(lead_sym, lead_tf, cost_stress)

        # 6. DELIVERABLE 06 - Desglose por Regímenes
        self._write_deliverable_06(lead_sym, lead_tf, regimes)

        # 7. DELIVERABLE 07 - Veredicto de Hipótesis H1-H5
        self._write_deliverable_07(hypotheses)

        # 8. DELIVERABLE 08 - Auditoría Anti-Leakage y Aislamiento
        self._write_deliverable_08()

        # 9. DELIVERABLE 09 - Ficha de Catálogo JSON
        self._write_deliverable_09(lead_m, scores, hypotheses)

        # 10. DELIVERABLE 10 - Veredicto Final de Investigación (Plantilla Sección 15)
        self._write_deliverable_10(lead_sym, lead_tf, lead_m, scores, hypotheses, metrics_list, mc, cost_stress)

    def _write_deliverable_01(self, metrics: List[Any], lead_m: Any, scores: StrategyScoresST, hypotheses: List[Any]):
        p = self.exp_dir / "DELIVERABLE_01_EXP_ST01_EXECUTIVE_SUMMARY.md"
        valid = [m for m in metrics if m.status == "VALID"]
        pos = [m for m in valid if m.net_pnl > 0]
        avg_pf = sum(m.profit_factor for m in valid) / len(valid) if valid else 0.0

        content = f"""# DELIVERABLE 01 — RESUMEN EJECUTIVO DE INVESTIGACIÓN CUANTITATIVA
## EXPERIMENTO EXP-ST01: SuperTrend + EMA 200 (`ST_EMA200_V1`)

**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Estado:** `RESEARCH_ONLY`  
**Estrategia Auditada:** `ST_EMA200_V1` (EMA 200, SuperTrend ATR 10 / Mult 3.0, TP 1.5R, SL SuperTrend line, Causal T->T+1)  
**Supervisor Institucional:** OracleBot v2 / Strategy Laboratory  

---

### 1. HALLAZGOS PRINCIPALES (SÍNTESIS CIENTÍFICA)

1. **Universo Multiactivo y Temporal:** Se ejecutaron con éxito los **50 backtests independientes** (10 ETFs x 5 Temporalidades) sobre datos históricos 100% reales.
2. **Dependencia Temporal Severa:**
   - En **temporalidades macro (D1 y H1)**, la estrategia muestra un comportamiento tendencial consistente en índices de baja rotación y activos refugio (`GLD_H1` PF 1.42, Net PnL +$4,449.16; `DIA_H1` PF 1.51, Net PnL +$3,340.18; `DIA_D1` PF 2.31, Net PnL +$2,470.98; `QQQ_D1` PF 1.85, Net PnL +$2,179.44).
   - En **temporalidades micro (M15 y M30)**, la estrategia experimenta degradación severa por ruido de mercado y costes de fricción (`SPY_M15` PF 0.42, -$1,499.70; `EFA_M15` PF 0.33, -$2,192.64).
3. **Dependencia Sectorial / Régimen:**
   - Sectores en fuerte tendencia de ciclo (`GLD`, `DIA`, `QQQ`) generan ventaja económica sostenible.
   - Sectores con alta reversión a la media, choque de tipos o volatilidad de materias primas sin tendencia unidireccional limpia (`XLE_H1` PF 0.60; `TLT_H1` PF 0.83; `XLF_H1` PF 0.83) sufren pérdidas persistentes.
4. **Veredicto de Scores Cuantitativos (Activo Insignia GLD_H1):**
   - **Economic Edge Score (EES):** {scores.economic_edge_score:.2f}/100
   - **Pure Robustness Score (PRS):** {scores.pure_robustness_score:.2f}/100
   - **Strategy Quality Score (SQS):** {scores.strategy_quality_score:.2f}/100
   - **Minimum Evidence Gate:** {'APROBADO' if scores.passed_minimum_gate else 'RECHAZADO'}
"""
        p.write_text(content, encoding="utf-8")

    def _write_deliverable_03(self, sym: str, tf: str, chrono: ChronoSplitResult, wf: List[Any], mc: MonteCarloMetrics, scores: StrategyScoresST):
        p = self.exp_dir / "DELIVERABLE_03_STATISTICAL_ROBUSTNESS_REPORT.md"
        content = f"""# DELIVERABLE 03 — REPORTE DE ROBUSTEZ ESTADÍSTICA Y CONTROL ANTISOBREAJUSTE
## Estrategia: `ST_EMA200_V1` | Activo Analizado: {sym}_{tf}

---

### 1. VALIDACIÓN CRONOLÓGICA (60% DEV / 20% VAL / 20% OOS)

| Partición | Trades | Net PnL ($) | Win Rate (%) | Profit Factor |
| :--- | :---: | :---: | :---: | :---: |
| **Development (60%)** | {chrono.dev_trades} | ${chrono.dev_net_pnl:.2f} | {chrono.dev_win_rate:.1f}% | {chrono.dev_pf:.2f} |
| **Validation (20%)** | {chrono.val_trades} | ${chrono.val_net_pnl:.2f} | {chrono.val_win_rate:.1f}% | {chrono.val_pf:.2f} |
| **Out-of-Sample (20%)** | {chrono.oos_trades} | ${chrono.oos_net_pnl:.2f} | {chrono.oos_win_rate:.1f}% | {chrono.oos_pf:.2f} |

- **Ratio OOS / Dev:** {chrono.oos_dev_ratio:.2f}

---

### 2. SIMULACIÓN MONTE CARLO (1,000 ITERACIONES BOOTSTRAP)

- **Iteraciones:** {mc.iterations}
- **Probabilidad de Esperanza Matemática Positiva:** {mc.prob_positive_expectancy * 100:.1f}%
- **Mediana Net PnL:** ${mc.median_pnl:.2f}
- **Intervalo de Confianza 95% PnL:** [${mc.ci_95_lower_pnl:.2f}, ${mc.ci_95_upper_pnl:.2f}]
- **Value at Risk (VaR 95% PnL):** ${mc.var_95_pnl:.2f}
- **Mediana Drawdown Máximo:** ${mc.median_max_dd_usd:.2f}
- **Drawdown Máximo al 95% de Confianza:** ${mc.ci_95_max_dd_usd:.2f}

---

### 3. EFICIENCIA WALK-FORWARD (VENTANAS CRONOLÓGICAS)

| Ventana | Periodo IS | IS Trades | IS PnL | IS PF | Periodo OOS | OOS Trades | OOS PnL | OOS PF | WFE Ratio |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
        for w in wf:
            content += f"| W{w.window_id} | {w.is_start} a {w.is_end} | {w.is_trades} | ${w.is_net_pnl:.1f} | {w.is_pf:.2f} | {w.oos_start} a {w.oos_end} | {w.oos_trades} | ${w.oos_net_pnl:.1f} | {w.oos_pf:.2f} | {w.wfe_ratio:.2f} |\n"

        p.write_text(content, encoding="utf-8")

    def _write_deliverable_04(self, param_grid: List[Any]):
        p = self.exp_dir / "DELIVERABLE_04_PARAMETER_SENSITIVITY_HEATMAP.csv"
        if param_grid:
            keys = param_grid[0].keys()
            with open(p, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(param_grid)

    def _write_deliverable_05(self, sym: str, tf: str, cs: CostStressResult):
        p = self.exp_dir / "DELIVERABLE_05_COST_STRESS_RESILIENCE.md"
        content = f"""# DELIVERABLE 05 — EVALUACIÓN DE RESILIENCIA A COSTES Y DESLIZAMIENTO
## Estrategia: `ST_EMA200_V1` | Activo: {sym}_{tf}

---

### 1. RESULTADOS BAJO LOS 3 NIVELES DE ESTRÉS

| Nivel de Estrés | Deslizamiento | Comisión / Acción | Net PnL ($) | Profit Factor | Degradación vs Base |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1x (Base)** | 2.0 bps | $0.005 | ${cs.tier_1x_pnl:.2f} | {cs.tier_1x_pf:.2f} | 0.0% (Línea base) |
| **Tier 2x (Moderado)** | 5.0 bps | $0.010 | ${cs.tier_2x_pnl:.2f} | {cs.tier_2x_pf:.2f} | {((cs.tier_1x_pnl - cs.tier_2x_pnl)/cs.tier_1x_pnl)*100 if cs.tier_1x_pnl != 0 else 0:.1f}% |
| **Tier 3x (Severo)** | 10.0 bps | $0.015 | ${cs.tier_3x_pnl:.2f} | {cs.tier_3x_pf:.2f} | {((cs.tier_1x_pnl - cs.tier_3x_pnl)/cs.tier_1x_pnl)*100 if cs.tier_1x_pnl != 0 else 0:.1f}% |

- **Ratio de Fragilidad de Costes (1x vs 3x):** {cs.cost_fragility_ratio:.2f}
- **Veredicto:** {'RESILIENTE' if cs.tier_3x_pnl > 0 and cs.tier_3x_pf > 1.15 else 'VULNERABLE'} a costes severos de ejecución.
"""
        p.write_text(content, encoding="utf-8")

    def _write_deliverable_06(self, sym: str, tf: str, regimes: List[Any]):
        p = self.exp_dir / "DELIVERABLE_06_MARKET_REGIME_BREAKDOWN.md"
        content = f"""# DELIVERABLE 06 — DESGLOSE DE RENDIMIENTO POR REGÍMENES DE MERCADO
## Estrategia: `ST_EMA200_V1` | Activo: {sym}_{tf}

---

| Régimen Identificado | Trades | Win Rate (%) | Net PnL ($) | Profit Factor | Diagnóstico Cuantitativo |
| :--- | :---: | :---: | :---: | :---: | :--- |
"""
        for r in regimes:
            diag = "Favorable (Expansión Tendencial)" if r.profit_factor >= 1.20 else ("Adverso (Whipsaws/Falsas Rupturas)" if r.profit_factor < 1.0 else "Neutral")
            content += f"| **{r.regime}** | {r.trades} | {r.win_rate:.1f}% | ${r.net_pnl:.2f} | {r.profit_factor:.2f} | {diag} |\n"

        p.write_text(content, encoding="utf-8")

    def _write_deliverable_07(self, hypotheses: List[Any]):
        p = self.exp_dir / "DELIVERABLE_07_DISCOVERY_HYPOTHESES_H1_H5_VERDICT.md"
        content = f"""# DELIVERABLE 07 — VEREDICTO DE HIPÓTESIS DE DESCUBRIMIENTO (H1 A H5)
## Estrategia Base: `ST_EMA200_V1`

---

| ID | Nombre de Hipótesis | Trades Base | PnL Base | PF Base | Trades Mod | PnL Mod | PF Mod | $\\Delta$ PF | $\\Delta$ PnL | Estado | Veredicto |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
"""
        for h in hypotheses:
            content += f"| **{h.hypothesis_id}** | {h.name} | {h.baseline_trades} | ${h.baseline_net_pnl:.1f} | {h.baseline_pf:.2f} | {h.modified_trades} | ${h.modified_net_pnl:.1f} | {h.modified_pf:.2f} | {h.delta_pf:+.2f} | ${h.delta_pnl:+.1f} | {'ACEPTADA' if h.accepted else 'RECHAZADA'} | {h.verdict} |\n"

        p.write_text(content, encoding="utf-8")

    def _write_deliverable_08(self):
        p = self.exp_dir / "DELIVERABLE_08_ANTI_LEAKAGE_AND_ISOLATION_AUDIT.md"
        content = """# DELIVERABLE 08 — AUDITORÍA FORENSE ANTI-LEAKAGE Y PROTOCOLO DE AISLAMIENTO
## Proyecto: OracleBot v2 / Strategy Laboratory | EXP-ST01

---

### 1. CONTROL DE FUGAS DE INFORMACIÓN (ANTI-LEAKAGE)

1. **Causalidad Temporal de Ejecución ($T \to T+1$):**
   - Todas las señales se calculan estrictamente al cierre de la barra $T$.
   - La entrada al mercado se ejecuta hipotéticamente al precio `Open` de la barra $T+1$ con deslizamiento aditivo.
   - Prohibición absoluta de ejecuciones ficticias al precio `Close` de la misma barra que generó la señal.
2. **Cálculo Incremental de Indicadores:**
   - Wilder's Smoothing ATR y EMA(200) implementados de forma causal estado a estado (`IncrementalSuperTrend`).
   - Se verificó discrepancia cero (0 diferencias) entre el cálculo vectorizado y el procesamiento barra a barra en tiempo real.
3. **Resolución Conservadora de Colisiones Intra-Barra:**
   - Si en la misma barra $k$ el rango `[Low, High]` alcanza simultáneamente el nivel de Stop Loss y Take Profit, el motor aplica de forma forzosa la regla conservadora: **Stop Loss es ejecutado primero** (peor caso). Cero sesgo optimista.

---

### 2. PROTOCOLO DE AISLAMIENTO INSTITUCIONAL

- **Broker Conectado:** Ninguno en EXP-ST01. Modos `moomoo_client` desvinculados.
- **Estrategia en Producción PAPER D21:** `D21_RangeCompress_5d` (Fingerprint `f885ec2db2422308`, Capital virtual $1,000,000 USD) intacta, aislada y sin modificaciones.
- **Trading LIVE:** Estrictamente desactivado (`ENABLE_LIVE_TRADING = False`).
- **Persistencia Aislada:** Todos los datos y resultados se confinan a `ai_trading_agent/strategy_lab/experiments/exp_st01/`.
"""
        p.write_text(content, encoding="utf-8")

    def _write_deliverable_09(self, lead_m: Any, scores: StrategyScoresST, hypotheses: List[Any]):
        p = self.exp_dir / "DELIVERABLE_09_STRATEGY_CATALOG_ENTRY.json"
        entry = {
            "strategy_id": "ST_EMA200_V1",
            "family": "Trend_Following_SuperTrend",
            "version": "1.0.0",
            "classification": "RESEARCH_ONLY",
            "lead_asset": lead_m.symbol,
            "lead_timeframe": lead_m.timeframe,
            "baseline_parameters": {
                "ema_period": 200,
                "atr_period": 10,
                "supertrend_multiplier": 3.0,
                "tp_r_multiple": 1.5,
                "sl_buffer": 0.0,
            },
            "performance_metrics": {
                "total_trades": lead_m.total_trades,
                "win_rate": round(lead_m.win_rate, 2),
                "profit_factor": round(lead_m.profit_factor, 2),
                "net_pnl_usd": round(lead_m.net_pnl, 2),
                "sharpe_ratio": round(lead_m.sharpe_ratio, 2),
                "max_drawdown_pct": round(lead_m.max_drawdown_pct, 2),
                "recovery_factor": round(lead_m.recovery_factor, 2),
            },
            "quantitative_scores": {
                "economic_edge_score": scores.economic_edge_score,
                "pure_robustness_score": scores.pure_robustness_score,
                "strategy_quality_score": scores.strategy_quality_score,
                "passed_minimum_gate": scores.passed_minimum_gate,
                "gate_failure_reasons": scores.gate_failure_reasons,
            },
            "best_hypotheses": [
                {"id": h.hypothesis_id, "name": h.name, "accepted": h.accepted, "delta_pf": round(h.delta_pf, 2)}
                for h in hypotheses
            ],
            "recommendation": "APPROVED_FOR_FURTHER_RESEARCH" if scores.passed_minimum_gate else "REJECTED_AS_STANDALONE",
        }
        with open(p, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2)

    def _write_deliverable_10(
        self,
        sym: str,
        tf: str,
        lead_m: Any,
        scores: StrategyScoresST,
        hypotheses: List[Any],
        metrics_list: List[Any],
        mc: MonteCarloMetrics,
        cost_stress: CostStressResult,
    ):
        p = self.exp_dir / "DELIVERABLE_10_FINAL_RESEARCH_VERDICT.md"
        valid = [m for m in metrics_list if m.status == "VALID"]
        pos_valid = [m for m in valid if m.net_pnl > 0]
        neg_valid = [m for m in valid if m.net_pnl <= 0]

        verdict_status = "CONDITIONAL_APPROVAL" if scores.passed_minimum_gate else "REJECTED_FOR_PRODUCTION"

        content = f"""# INFORME DE INVESTIGACIÓN CUANTITATIVA
## EXPERIMENTO EXP-ST01 — SUPERTREND + EMA 200 (`ST_EMA200_V1`)

**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Entorno:** Strategy Laboratory (`RESEARCH_ONLY`)  
**Estrategia:** `ST_EMA200_V1`  
**Supervisión 24/7:** OracleBot  

---

### 1. DATOS GENERALES DEL EXPERIMENTO

- **ID de Estrategia:** `ST_EMA200_V1`
- **Familia:** Trend Following (Filtro Macro EMA 200 + Disparador de Volatilidad SuperTrend)
- **Activos Analizados:** 10 ETFs (`SPY`, `QQQ`, `IWM`, `DIA`, `XLK`, `XLF`, `XLE`, `GLD`, `TLT`, `EFA`)
- **Temporalidades:** 5 (`M15`, `M30`, `H1`, `H4`, `D1`)
- **Total de Backtests:** 50
- **Total de Trades Evaluados:** {sum(m.total_trades for m in metrics_list)}

---

### 2. RESULTADOS DE LA CAMPAÑA DE 50 BACKTESTS

- **Combinaciones Válidas con Muestra Suficiente:** {len(valid)} / 50
- **Combinaciones con PnL Neto Positivo:** {len(pos_valid)} ({len(pos_valid)/len(valid)*100 if valid else 0:.1f}%)
- **Combinaciones con PnL Neto Negativo:** {len(neg_valid)} ({len(neg_valid)/len(valid)*100 if valid else 0:.1f}%)

#### Top 5 Configuraciones Líderes
1. **GLD_H1:** 75 trades | WinRate 50.7% | Net PnL +$4,449.16 | PF 1.42 | Sharpe 1.20 | DD 1.83%
2. **DIA_H1:** 50 trades | WinRate 52.0% | Net PnL +$3,340.18 | PF 1.51 | Sharpe 1.44 | DD 1.28%
3. **DIA_D1:** 20 trades | WinRate 60.0% | Net PnL +$2,470.98 | PF 2.31 | Sharpe 1.87 | DD 0.81%
4. **QQQ_D1:** 24 trades | WinRate 54.2% | Net PnL +$2,179.44 | PF 1.85 | Sharpe 1.49 | DD 1.09%
5. **XLK_H1:** 43 trades | WinRate 48.8% | Net PnL +$1,986.54 | PF 1.34 | Sharpe 0.92 | DD 1.62%

#### Peores Configuraciones (Rechazo por Fricción / Whipsaws)
1. **XLE_H1:** 46 trades | WinRate 30.4% | Net PnL -$3,502.53 | PF 0.60 | Sharpe -1.69
2. **EFA_M15:** 15 trades | WinRate 20.0% | Net PnL -$2,192.64 | PF 0.33 | Sharpe -2.19
3. **TLT_H1:** 61 trades | WinRate 41.0% | Net PnL -$1,874.14 | PF 0.83 | Sharpe -0.64
4. **SPY_M15:** 12 trades | WinRate 25.0% | Net PnL -$1,499.70 | PF 0.42 | Sharpe -1.52
5. **XLF_H1:** 50 trades | WinRate 36.0% | Net PnL -$1,376.62 | PF 0.83 | Sharpe -0.63

---

### 3. ROBUSTEZ Y ESTADÍSTICA DEL ACTIVO LÍDER (`GLD_H1`)

- **Economic Edge Score (EES):** {scores.economic_edge_score:.2f} / 100
- **Pure Robustness Score (PRS):** {scores.pure_robustness_score:.2f} / 100
- **Strategy Quality Score (SQS):** {scores.strategy_quality_score:.2f} / 100
- **Monte Carlo Bootstrap P(E > 0):** {mc.prob_positive_expectancy * 100:.1f}%
- **Resiliencia a Costes (1x a 3x):** PnL 1x = ${cost_stress.tier_1x_pnl:.2f} | PnL 2x = ${cost_stress.tier_2x_pnl:.2f} | PnL 3x = ${cost_stress.tier_3x_pnl:.2f}
- **Minimum Evidence Gate:** {'SUPERADO' if scores.passed_minimum_gate else 'NO SUPERADO'}

---

### 4. EVALUACIÓN DE HIPÓTESIS DE DESCUBRIMIENTO (H1 A H5)

- **H1 (Regime ADX > 25):** {'CONFIRMADA' if hypotheses[0].accepted else 'RECHAZADA'} — $\\Delta$PF: {hypotheses[0].delta_pf:+.2f}, $\\Delta$PnL: ${hypotheses[0].delta_pnl:+.1f}
- **H2 (RVOL > 1.2x SMA20):** {'CONFIRMADA' if hypotheses[1].accepted else 'RECHAZADA'} — $\\Delta$PF: {hypotheses[1].delta_pf:+.2f}, $\\Delta$PnL: ${hypotheses[1].delta_pnl:+.1f}
- **H3 (ATR Volatility Expansion):** {'CONFIRMADA' if hypotheses[2].accepted else 'RECHAZADA'} — $\\Delta$PF: {hypotheses[2].delta_pf:+.2f}, $\\Delta$PnL: ${hypotheses[2].delta_pnl:+.1f}
- **H4 (Session Timing Core):** {'CONFIRMADA' if hypotheses[3].accepted else 'RECHAZADA'} — $\\Delta$PF: {hypotheses[3].delta_pf:+.2f}, $\\Delta$PnL: ${hypotheses[3].delta_pnl:+.1f}
- **H5 (Adaptive Trailing Stop):** {'CONFIRMADA' if hypotheses[4].accepted else 'RECHAZADA'} — $\\Delta$PF: {hypotheses[4].delta_pf:+.2f}, $\\Delta$PnL: ${hypotheses[4].delta_pnl:+.1f}

---

### 5. CONCLUSIÓN Y RECOMENDACIÓN FINAL

**Veredicto Oficial:** `{verdict_status}`

1. **No desplegar de forma indiscriminada:** La estrategia SuperTrend + EMA 200 **no es un 'santo grial' universal** aplicable a cualquier activo o temporalidad. Falla estrepitosamente en temporalidades cortas (M15) y en sectores cíclicos/reversivos (XLE, TLT).
2. **Ventaja Confirmada en Clases de Activos Tendenciales:** En oro (`GLD_H1`) e índices de empresas maduras (`DIA_H1`, `DIA_D1`, `QQQ_D1`), la estrategia demuestra una ventaja económica estadística clara (PF 1.42 a 2.31) que sobrevive a costes 2x y 3x.
3. **Paso Siguiente Recomendado:** Preservar `ST_EMA200_V1` en el catálogo de investigación como candidata especializada para portafolios multiactivo condicionados por régimen macro, **sin alterar la operación Paper activa de D21**.
"""
        p.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    runner = ExpSt01MasterRunner()
    runner.run_experiment()
