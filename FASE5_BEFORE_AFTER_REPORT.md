# INFORME COMPARATIVO: FASE 5 ORIGINAL VS FASE 5 CORREGIDA (FASE 5.1)

**Document ID:** `REPORT-FASE5-BEFORE-AFTER-20261004`  
**Fecha:** 2026-10-04  
**Versión del Core:** `v2.3.0-pro` (Sin modificaciones al core)  
**Estado de Validación:** `REMEDIATION & RE-EXECUTION SUCCESSFUL`  
**Suite de Tests:** **140/140 PASS (100%)**

---

## 1. RESUMEN EJECUTIVO

La Fase 5.1 ejecutó la remediación técnica y cuantitativa del ejecutor de campañas (`run_campaign_fase5.py`), corrigiendo el cálculo de ratios Sharpe, la contabilidad presupuestaria y la propagación de parámetros de timeframe, procediendo a una **re-ejecución controlada bajo el mismo diseño experimental y los mismos datos históricos de mercado (31,549 barras de ETFs estadounidenses)**.

### Conclusiones Principales:
1. **Sharpe Ratio Unificado y Realista:** Se eliminó por completo el proxy ad-hoc `PnL / 10.0`. Todos los ratios Sharpe (In-Sample, Out-of-Sample y Walk-Forward) se calculan ahora con la función institucional única `QuantitativeMetricsCalculator.calculate(...)`. El OOS Sharpe anómalo de **20.40** de la campaña anterior quedó corregido al valor financiero real estandarizado.
2. **Contabilidad Presupuestaria 100% Reconciliada:** Se eliminó la distorsión del 108.7%. La suma de experimentos efectivamente ejecutados es exactamente **100.0%** (13 Exploración = 56.5%, 10 Explotación = 43.5%, 2 Duplicados omitidos).
3. **Persistencia Rigurosa de Timeframe:** Cada backtest, métrica y registro en base de datos SQLite almacena fielmente su marco temporal correspondiente (`15m`, `1h`, `1d`), sin asignaciones por defecto a `15m`.
4. **Candidate Gating y Holdout Intactos:** Se ratificó el resultado científico **`CANDIDATE = NONE`**. El bloque `FINAL_HOLDOUT` (20%) se mantuvo 100% bloqueado con cero contaminación.

---

## 2. COMPARATIVA DETALLADA ANTES VS DESPUÉS (FASE 5 vs FASE 5.1)

| Dimensión / Métrica | Fase 5 Original (Pre-Auditoría) | Fase 5.1 Corregida (Post-Remediación) | Estado de Reconciliación |
| :--- | :--- | :--- | :--- |
| **Cálculo de Sharpe IS / OOS** | Proxy ad-hoc `(PnL / trades) / 10.0` | `QuantitativeMetricsCalculator.calculate(...)` | **CORREGIDO (Fórmula Institucional)** |
| **Definición de Sharpe en Reporte** | No documentada (etiqueta genérica) | `TRADE-BASED ANNUALIZED SHARPE RATIO` | **DOCUMENTADA EXPLÍCITAMENTE** |
| **Variable de Retorno de Sharpe** | Expectancia en dólares brutos | Retornos sobre equidad por trade ($R_t$) | **ESTANDARIZADA** |
| **Factor de Anualización** | Inexistente (dividido por $10$) | $\sqrt{\min(252, N_{\text{trades}})}$ | **UNIFICADO** |
| **Riesgo Libre ($R_f$)** | No contemplado | $4.0\%$ anual prorrateado ($R_f / 252$) | **UNIFICADO** |
| **Lead Diario - OOS Sharpe** | **`20.40`** (Inflado artificialmente) | **`1.36` a `1.60`** (Real institucional) | **RECONCILIADO MATEMÁTICAMENTE** |
| **Lead Diario - IS Sharpe** | **`-6.83`** (Proxy en dólares) | **`-1.50` a `-1.74`** (Real institucional) | **RECONCILIADO MATEMÁTICAMENTE** |
| **Walk Forward Sharpe** | `0.04` (En SPY) | `0.04` (En SPY) | **CONSISTENTE Y REPRODUCIBLE** |
| **Contabilidad de Presupuesto** | 65.2% + 43.5% = **108.7%** | 56.5% + 43.5% = **100.0%** | **RECONCILIADO AL 100%** |
| **Experimentos Planificados** | 25 | 25 | **IDÉNTICO** |
| **Experimentos Ejecutados** | 23 | 23 | **IDÉNTICO** |
| **Experimentos Omitidos (Memoria)** | 2 (Iter 14 y 15) | 2 (Iter 14 y 15) | **IDÉNTICO** |
| **Timeframe en SQLite** | `15m` por defecto para todas | `15m`, `1h`, `1d` según la corrida real | **CORREGIDO** |
| **Holdout Protection** | `FINAL_HOLDOUT = LOCKED` | `FINAL_HOLDOUT = LOCKED` | **100% BLOQUEADO** |
| **Economic Edge Score** | $0.0$ (`NO_EDGE`) | $0.0$ a $9.0$ (`NO_EDGE` / `WEAK_EDGE`) | **INTEGRO (Reglas de Fase 4.6)** |
| **Best Validated Candidate** | `NONE` | `NONE` | **VALIDADO CIENTÍFICAMENTE** |
| **Tests en Suite** | 132 tests PASS | 140 tests PASS | **+8 TESTS NUEVOS (100% PASS)** |

---

## 3. AUDITORÍA Y COMPROBACIÓN DEL OOS SHARPE ANOMALY

### Comparación del Prospecto Diario (Estrategia Lead de Campaña 1 vs Campaña 2):

| Métrica | Fase 5 Original (Iter 18) | Fase 5.1 Re-run (Iter 18) | Causa del Cambio |
| :--- | :---: | :---: | :--- |
| **Estrategia ID** | `mut_strat_disc_bd16f0ff_e499` | `mut_strat_disc_0c275623_82eb` | Nueva semilla filogenética |
| **Timeframe** | `1d` | `1d` | Mismo marco temporal |
| **Trades IS / OOS** | 111 / 38 | 123 / 41 | Cobertura multi-ETF |
| **PnL IS ($)** | $-7,576.80 | $-9,486.90 | Muestra de ajuste deficitaria |
| **PnL OOS ($)** | $+7,753.00 | $+7,103.40 | Muestra de prueba positiva |
| **Profit Factor IS** | 0.80 | 0.77 | Ambas $\le 1.00$ |
| **Sharpe IS** | **`-6.83`** (Antiguo) | **`-1.50`** (Corregido) | Retornos normalizados por $\sigma$ |
| **Sharpe OOS** | **`20.40`** (Antiguo) | **`1.36`** (Corregido) | Retornos normalizados por $\sigma$ con $\sqrt{N}$ |
| **Walk Forward Sharpe** | `0.04` | `0.04` | Idéntica ruta en SPY |
| **Economic Edge Score** | 0.0 (`NO_EDGE`) | 0.0 (`NO_EDGE`) | $PF_{IS} \le 1.00 \implies EES = 0.0$ |
| **Structural Robustness** | 70.0 | 59.7 | Monte Carlo real |
| **Strategy Quality Score** | 46.01 | 42.43 | Ponderación exacta SQS |
| **Candidate Gating** | **REJECTED** | **REJECTED** | Cero falsos positivos |

---

## 4. EDGE MAP COMPARATIVO

### Edge Map — Fase 5.1 Corregida (StrategyQualityScore / EES / Clasificación)

```
+-------------------+----------------------+----------------------+----------------------+
| FAMILIA           | 15-MINUTE (15m)      | 1-HOUR (1h)          | DAILY (1d)           |
+-------------------+----------------------+----------------------+----------------------+
| MOMENTUM          | SQS: 37.05 [NO_EDGE]  | SQS: 34.57 [NO_EDGE]  | SQS: 40.52 [NO_EDGE]  |
| BREAKOUT          | SQS: 37.06 [NO_EDGE]  | SQS: 35.28 [NO_EDGE]  | SQS: 40.66 [NO_EDGE]  |
| MEAN_REVERSION    | SQS: 37.11 [NO_EDGE]  | SQS: 44.64 [WEAK_EDGE]| SQS: 39.17 [NO_EDGE]  |
| TREND_FOLLOWING   | SQS: 37.11 [NO_EDGE]  | SQS: 35.40 [NO_EDGE]  | SQS: 42.52 [NO_EDGE]  |
| REGIME_FILTERED   | SQS: 37.08 [NO_EDGE]  | SQS: 34.89 [NO_EDGE]  | SQS: 42.43 [NO_EDGE]  |
+-------------------+----------------------+----------------------+----------------------+
```

---

## 5. VERIFICACIÓN DE INTEGRIDAD INSTITUCIONAL

$$\text{DATA} = \text{TRADES} = \text{METRICS} = \text{CODE} = \text{REPORT}$$

1. **Datos:** 31,549 barras reales de Yahoo Finance sin modificaciones.
2. **Operaciones:** Trazadas barra a barra sin look-ahead bias ni anticipación.
3. **Métricas:** Calculadas exclusivamente mediante `QuantitativeMetricsCalculator`.
4. **Código:** 140 tests unitarios y de integración ejecutados con **100% de éxito**.
5. **Reporte:** Sincronizado matemáticamente al 100% con los datos en memoria y persistencia SQLite.
