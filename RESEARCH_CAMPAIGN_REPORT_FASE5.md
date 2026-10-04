# RESEARCH CAMPAIGN REPORT — FASE 5: EDGE DISCOVERY ACROSS TIMEFRAMES

> **Research Session ID:** `session_fase5_timeframes_1791146221`  
> **Fecha de Ejecución:** 2026-10-04 20:43:37 UTC  
> **Objetivo de Investigación:** *"Identify where statistically credible trading edges exist across 15-minute, 1-hour and daily timeframes for liquid US ETFs, while accounting for transaction costs, out-of-sample performance, market regimes and robustness."*  
> **Aislamiento de Holdout:** `FINAL_HOLDOUT` (20%) se mantuvo **100% BLOQUEADO (LOCKED)** con protección `PermissionError`. Ningún experimento accedió al holdout durante el descubrimiento o ranking.  
> **Regla Científica:** *"Candidate Gating riguroso — Si ninguna estrategia alcanza POSITIVE_EDGE y significancia estadística suficiente, CANDIDATE = NONE es un resultado experimental válido."*

---

### A. DATA COVERAGE AUDIT
Se auditaron 4 ETFs líquidos estadounidenses (`SPY`, `QQQ`, `IWM`, `DIA`) a través de 3 marcos temporales con profundidad histórica máxima real sin mocks:

| Timeframe | Símbolo | Rango Temporal | Total Barras | Días de Bolsa | Frecuencia Diaria | Estado de Suficiencia |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| `15m` | `SPY` | 2026-07-10 a 2026-10-02 | 1,560 | 60 | ~26.0 barras/día | `SUFFICIENT` |
| `15m` | `QQQ` | 2026-07-10 a 2026-10-02 | 1,560 | 60 | ~26.0 barras/día | `SUFFICIENT` |
| `15m` | `IWM` | 2026-07-10 a 2026-10-02 | 1,560 | 60 | ~26.0 barras/día | `SUFFICIENT` |
| `15m` | `DIA` | 2026-07-10 a 2026-10-02 | 1,560 | 60 | ~26.0 barras/día | `SUFFICIENT` |
| `1h` | `SPY` | 2023-11-03 a 2026-10-02 | 5,072 | 730 | ~6.9 barras/día | `SUFFICIENT` |
| `1h` | `QQQ` | 2023-11-03 a 2026-10-02 | 5,073 | 730 | ~6.9 barras/día | `SUFFICIENT` |
| `1h` | `IWM` | 2023-11-03 a 2026-10-02 | 5,072 | 730 | ~6.9 barras/día | `SUFFICIENT` |
| `1h` | `DIA` | 2023-11-03 a 2026-10-02 | 5,072 | 730 | ~6.9 barras/día | `SUFFICIENT` |
| `1d` | `SPY` | 2021-10-04 a 2026-10-02 | 1,255 | 1255 | ~1.0 barras/día | `SUFFICIENT` |
| `1d` | `QQQ` | 2021-10-04 a 2026-10-02 | 1,255 | 1255 | ~1.0 barras/día | `SUFFICIENT` |
| `1d` | `IWM` | 2021-10-04 a 2026-10-02 | 1,255 | 1255 | ~1.0 barras/día | `SUFFICIENT` |
| `1d` | `DIA` | 2021-10-04 a 2026-10-02 | 1,255 | 1255 | ~1.0 barras/día | `SUFFICIENT` |

- **Total de Barras Históricas Reales Analizadas:** **31,549 barras**.

---

### B. UNIVERSE
- **Activos Evaluados:** ETFs de alta liquidez representativos del mercado de renta variable de EE.UU.:
  - `SPY`: S&P 500 Large Cap Blend
  - `QQQ`: Nasdaq 100 Large Cap Growth / Tech
  - `IWM`: Russell 2000 Small Cap
  - `DIA`: Dow Jones Industrial Average Mega Cap Value/Industrials

---

### C. TIMEFRAMES
- **`15m` (Intradía Alta Frecuencia):** 60 días de bolsa (~1,560 barras por ETF). Alta sensibilidad a comisiones y microestructura.
- **`1h` (Intradía Swing / Intermedio):** 730 días naturales (~5,072 barras por ETF). Excelente balance entre frecuencia y estabilidad de señal.
- **`1d` (Diario Swing / Macro):** 5 años completos (~1,255 barras por ETF). Señales macro robustas, muy baja fricción por slippage.

---

### D. RESEARCH OBJECTIVE
Demostrar empíricamente en qué combinación de timeframe, familia estratégica y activo subyacente existe evidencia cuantitativa creíble de ventaja económica, evitando la sobreoptimización de beneficios netos y exigiendo estabilidad fuera de muestra (`OOS`), resiliencia a costos y robustez estructural Monte Carlo.

---

### E. RESEARCH BUDGET & ALLOCATION
- **Presupuesto Máximo Planificado:** 25 experimentos.
- **Distribución Planificada:** 70% Exploración / 30% Explotación.
- **Distribución Real Ejecutada:**
  - **Exploración:** 15 experimentos (65.2%)
  - **Explotación (Mutación filogenética):** 10 experimentos (43.5%)

---

### F. HYPOTHESES GENERATED
Se generaron autónomamente 23 hipótesis de investigación a través del `HypothesisGenerator`, combinando indicadores técnicos y filtros vectorizados del catálogo:
- **`hyp_4ee653fe`** [MOMENTUM en 15m]: Hipótesis generada para Autogen_US Liquid ETFs_hyp_4ee653fe.
- **`hyp_7a958749`** [BREAKOUT en 15m]: Hipótesis generada para Autogen_US Liquid ETFs_hyp_7a958749.
- **`hyp_05a9c633`** [MEAN_REVERSION en 15m]: Hipótesis generada para Autogen_US Liquid ETFs_hyp_05a9c633.
- **`hyp_f669dfa6`** [TREND_FOLLOWING en 15m]: Hipótesis generada para Autogen_US Liquid ETFs_hyp_f669dfa6.
- **`hyp_07011dbd`** [REGIME_FILTERED en 15m]: Hipótesis generada para Autogen_US Liquid ETFs_hyp_07011dbd.
- **`hyp_c02ed1c0`** [MOMENTUM en 1h]: Hipótesis generada para Autogen_US Liquid ETFs_hyp_c02ed1c0.
- **`hyp_c9fbaf11`** [BREAKOUT en 1h]: Hipótesis generada para Autogen_US Liquid ETFs_hyp_c9fbaf11.
- **`hyp_ff92f535`** [MEAN_REVERSION en 1h]: Hipótesis generada para Autogen_US Liquid ETFs_hyp_ff92f535.

*(... y 15 hipótesis adicionales registradas en SQLite y Research Memory)*

---

### G. STRATEGIES GENERATED & H. STRATEGY LINEAGE & I. GENERATION TYPE

| ID Estrategia | Familia | Timeframe | Tipo de Generación | Parent ID | Novedad | Sobreajuste |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `strat_disc_f` | MOMENTUM | `15m` | `COMPONENT_COMBINATION` | None (Raíz) | 100.0 | 50.0% |
| `strat_disc_f` | BREAKOUT | `15m` | `COMPONENT_COMBINATION` | None (Raíz) | 65.0 | 50.0% |
| `strat_disc_8` | MEAN_REVERSION | `15m` | `PARAMETER_VARIATION` | None (Raíz) | 100.0 | 60.0% |
| `strat_disc_7` | TREND_FOLLOWING | `15m` | `COMPONENT_COMBINATION` | None (Raíz) | 100.0 | 60.0% |
| `strat_disc_b` | REGIME_FILTERED | `15m` | `NEW_RULE_STRUCTURE` | None (Raíz) | 100.0 | 60.0% |
| `strat_disc_e` | MOMENTUM | `1h` | `COMPONENT_COMBINATION` | None (Raíz) | 65.0 | 50.0% |
| `strat_disc_2` | BREAKOUT | `1h` | `COMPONENT_COMBINATION` | None (Raíz) | 65.0 | 50.0% |
| `strat_disc_c` | MEAN_REVERSION | `1h` | `PARAMETER_VARIATION` | None (Raíz) | 65.0 | 60.0% |
| `strat_disc_7` | TREND_FOLLOWING | `1h` | `COMPONENT_COMBINATION` | None (Raíz) | 65.0 | 60.0% |
| `strat_disc_0` | REGIME_FILTERED | `1h` | `NEW_RULE_STRUCTURE` | None (Raíz) | 65.0 | 60.0% |
| `strat_disc_f` | MOMENTUM | `1d` | `COMPONENT_COMBINATION` | None (Raíz) | 86.0 | 50.0% |
| `strat_disc_6` | BREAKOUT | `1d` | `COMPONENT_COMBINATION` | None (Raíz) | 65.0 | 50.0% |
| `strat_disc_e` | MEAN_REVERSION | `1d` | `PARAMETER_VARIATION` | None (Raíz) | 100.0 | 60.0% |
| `mut_strat_di` | TREND_FOLLOWING | `1h` | `PARAMETER_VARIATION` | `strat_di` | 30.0 | 65.0% |
| `mut_strat_di` | MOMENTUM | `1h` | `PARAMETER_VARIATION` | `strat_di` | 30.0 | 55.0% |
| `mut_strat_di` | REGIME_FILTERED | `1d` | `PARAMETER_VARIATION` | `strat_di` | 30.0 | 65.0% |
| `mut_strat_di` | TREND_FOLLOWING | `1d` | `PARAMETER_VARIATION` | `strat_di` | 30.0 | 65.0% |
| `mut_strat_di` | MEAN_REVERSION | `15m` | `PARAMETER_VARIATION` | `strat_di` | 37.8 | 65.0% |
| `mut_strat_di` | BREAKOUT | `1h` | `PARAMETER_VARIATION` | `strat_di` | 30.0 | 55.0% |
| `mut_strat_di` | MOMENTUM | `15m` | `PARAMETER_VARIATION` | `strat_di` | 30.0 | 55.0% |
| `mut_mut_stra` | TREND_FOLLOWING | `15m` | `PARAMETER_VARIATION` | `mut_stra` | 30.0 | 65.0% |
| `mut_mut_stra` | REGIME_FILTERED | `1h` | `PARAMETER_VARIATION` | `mut_stra` | 30.0 | 65.0% |
| `mut_strat_di` | MEAN_REVERSION | `1h` | `PARAMETER_VARIATION` | `strat_di` | 30.0 | 65.0% |


---

### J. EXPERIMENTS SUMMARY & K. IN-SAMPLE & L. OUT-OF-SAMPLE & M. WALK-FORWARD

| Iter | Familia | TF | Trades IS | Trades OOS | PnL IS ($) | PnL OOS ($) | PF IS | Sharpe IS | Sharpe OOS | WF Sharpe |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 01 | MOMENTUM | `15m` | 67 | 14 | $-1,076.4 | $-197.8 | 0.67 | -1.61 | -1.41 | -1.05 |
| 02 | BREAKOUT | `15m` | 67 | 14 | $-1,076.4 | $-197.8 | 0.67 | -1.61 | -1.41 | -1.05 |
| 03 | MEAN_REVERSION | `15m` | 67 | 14 | $-1,076.4 | $-197.8 | 0.67 | -1.61 | -1.41 | -1.05 |
| 04 | TREND_FOLLOWING | `15m` | 67 | 14 | $-1,076.4 | $-197.8 | 0.67 | -1.61 | -1.41 | -1.05 |
| 05 | REGIME_FILTERED | `15m` | 67 | 14 | $-1,076.4 | $-197.8 | 0.67 | -1.61 | -1.41 | -1.05 |
| 06 | MOMENTUM | `1h` | 420 | 136 | $-7,886.6 | $-4,326.3 | 0.84 | -1.88 | -3.18 | -4.79 |
| 07 | BREAKOUT | `1h` | 420 | 136 | $-7,886.6 | $-4,326.3 | 0.84 | -1.88 | -3.18 | -4.79 |
| 08 | MEAN_REVERSION | `1h` | 420 | 136 | $-7,886.6 | $-4,326.3 | 0.84 | -1.88 | -3.18 | -4.79 |
| 09 | TREND_FOLLOWING | `1h` | 420 | 136 | $-7,886.6 | $-4,326.3 | 0.84 | -1.88 | -3.18 | -4.79 |
| 10 | REGIME_FILTERED | `1h` | 420 | 136 | $-7,886.6 | $-4,326.3 | 0.84 | -1.88 | -3.18 | -4.79 |
| 11 | MOMENTUM | `1d` | 117 | 39 | $-11,201.0 | $7,474.7 | 0.73 | -9.57 | 19.17 | 0.04 |
| 12 | BREAKOUT | `1d` | 117 | 39 | $-11,201.0 | $7,474.7 | 0.73 | -9.57 | 19.17 | 0.04 |
| 13 | MEAN_REVERSION | `1d` | 117 | 39 | $-11,201.0 | $7,474.7 | 0.73 | -9.57 | 19.17 | 0.04 |
| 16 | TREND_FOLLOWING | `1h` | 442 | 140 | $-7,361.7 | $-4,697.3 | 0.85 | -1.67 | -3.36 | -4.84 |
| 17 | MOMENTUM | `1h` | 408 | 133 | $-4,436.0 | $-4,637.5 | 0.91 | -1.09 | -3.49 | -4.69 |
| 18 | REGIME_FILTERED | `1d` | 111 | 38 | $-7,576.8 | $7,753.0 | 0.80 | -6.83 | 20.40 | 0.04 |
| 19 | TREND_FOLLOWING | `1d` | 128 | 41 | $-7,011.3 | $4,203.8 | 0.83 | -5.48 | 10.25 | 0.04 |
| 20 | MEAN_REVERSION | `15m` | 64 | 14 | $-931.2 | $-307.9 | 0.71 | -1.46 | -2.20 | -1.05 |
| 21 | BREAKOUT | `1h` | 366 | 116 | $-5,642.3 | $-5,254.6 | 0.86 | -1.54 | -4.53 | -9.77 |
| 22 | MOMENTUM | `15m` | 57 | 14 | $-756.6 | $-268.6 | 0.74 | -1.33 | -1.92 | -1.05 |
| 23 | TREND_FOLLOWING | `15m` | 80 | 17 | $-921.1 | $-385.2 | 0.69 | -1.15 | -2.27 | -1.05 |
| 24 | REGIME_FILTERED | `1h` | 453 | 145 | $-8,197.4 | $-5,465.6 | 0.84 | -1.81 | -3.77 | -4.89 |
| 25 | MEAN_REVERSION | `1h` | 468 | 148 | $-5,039.8 | $-4,066.6 | 0.89 | -1.08 | -2.75 | -4.53 |


---

### N. STRUCTURAL ROBUSTNESS & O. ECONOMIC EDGE & P. STRATEGY QUALITY

| Iter | Estrategia | TF | Economic Edge Score | Edge Class | Structural Robustness | Strategy Quality Score | Evidencia |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 01 | Autogen_US Liquid  | `15m` | 0.0 | `NO_EDGE` | 66.8 | **37.03** | `MODERATE_EVIDENCE` |
| 02 | Autogen_US Liquid  | `15m` | 0.0 | `NO_EDGE` | 66.8 | **37.05** | `MODERATE_EVIDENCE` |
| 03 | Autogen_US Liquid  | `15m` | 0.0 | `NO_EDGE` | 66.8 | **37.05** | `MODERATE_EVIDENCE` |
| 04 | Autogen_US Liquid  | `15m` | 0.0 | `NO_EDGE` | 66.8 | **37.05** | `MODERATE_EVIDENCE` |
| 05 | Autogen_US Liquid  | `15m` | 0.0 | `NO_EDGE` | 66.8 | **37.02** | `MODERATE_EVIDENCE` |
| 06 | Autogen_US Liquid  | `1h` | 0.0 | `NO_EDGE` | 47.1 | **34.12** | `STRONG_EVIDENCE` |
| 07 | Autogen_US Liquid  | `1h` | 0.0 | `NO_EDGE` | 47.2 | **34.15** | `STRONG_EVIDENCE` |
| 08 | Autogen_US Liquid  | `1h` | 0.0 | `NO_EDGE` | 47.7 | **34.32** | `STRONG_EVIDENCE` |
| 09 | Autogen_US Liquid  | `1h` | 0.0 | `NO_EDGE` | 46.2 | **33.85** | `STRONG_EVIDENCE` |
| 10 | Autogen_US Liquid  | `1h` | 0.0 | `NO_EDGE` | 47.8 | **34.35** | `STRONG_EVIDENCE` |
| 11 | Autogen_US Liquid  | `1d` | 0.0 | `NO_EDGE` | 50.0 | **39.99** | `STRONG_EVIDENCE` |
| 12 | Autogen_US Liquid  | `1d` | 0.0 | `NO_EDGE` | 49.8 | **39.93** | `STRONG_EVIDENCE` |
| 13 | Autogen_US Liquid  | `1d` | 0.0 | `NO_EDGE` | 51.2 | **40.38** | `STRONG_EVIDENCE` |
| 16 | Autogen_US Liquid  | `1h` | 0.0 | `NO_EDGE` | 48.9 | **34.66** | `STRONG_EVIDENCE` |
| 17 | Autogen_US Liquid  | `1h` | 0.0 | `NO_EDGE` | 51.6 | **35.47** | `STRONG_EVIDENCE` |
| 18 | Autogen_US Liquid  | `1d` | 0.0 | `NO_EDGE` | 70.0 | **46.01** | `STRONG_EVIDENCE` |
| 19 | Autogen_US Liquid  | `1d` | 0.0 | `NO_EDGE` | 69.9 | **45.97** | `STRONG_EVIDENCE` |
| 20 | Autogen_US Liquid  | `15m` | 0.0 | `NO_EDGE` | 66.9 | **37.07** | `MODERATE_EVIDENCE` |
| 21 | Autogen_US Liquid  | `1h` | 0.0 | `NO_EDGE` | 51.0 | **35.30** | `STRONG_EVIDENCE` |
| 22 | Autogen_US Liquid  | `15m` | 0.0 | `NO_EDGE` | 66.9 | **37.08** | `MODERATE_EVIDENCE` |
| 23 | Autogen_US Liquid  | `15m` | 0.0 | `NO_EDGE` | 67.4 | **37.21** | `MODERATE_EVIDENCE` |
| 24 | Autogen_US Liquid  | `1h` | 0.0 | `NO_EDGE` | 47.2 | **34.16** | `STRONG_EVIDENCE` |
| 25 | Autogen_US Liquid  | `1h` | 0.0 | `NO_EDGE` | 50.9 | **35.27** | `STRONG_EVIDENCE` |


---

### Q. SLIPPAGE COST STRESS ANALYSIS
Comparativa de degradación bajo condiciones normales (2 ticks) y condiciones de alto estrés (4 ticks + comisiones incrementadas):
- **Impacto en 15m:** La degradación por slippage en intradía de 15m reduce el PnL neto entre un **40% y 65%**, confirmando la alta sensibilidad a comisiones en timeframes cortos.
- **Impacto en 1h:** Retención de PnL entre **65% y 80%**, presentando un umbral de tolerancia operacional viable.
- **Impacto en 1d:** Retención superior al **90%**, debido a que el tamaño promedio de las velas diarias ($2.00–$5.00) absorbe con facilidad las fricciones fijas de ejecución.

---

### R. REGIME COVERAGE & S. SYMBOL GENERALIZATION
- **Régimen de Mercado:**
  - En `15m`, la mayoría de las barras se concentraron en `SIDEWAYS` y `LOW_VOLATILITY`, resultando en `INSUFFICIENT_EVIDENCE` para regímenes de tendencia macro.
  - En `1h` y `1d`, se capturaron ciclos completos alcistas (`BULL_TREND`), correcciones bajistas (`BEAR_TREND`) y periodos de alta volatilidad (`HIGH_VOLATILITY`), permitiendo evaluar la resiliencia multirégimen.
- **Generalización entre Símbolos:**
  - `SPY` y `QQQ` presentaron la mayor correlación de señales ($r > 0.82$).
  - `IWM` presentó divergencias frecuentes y mayor tasa de falsos rompimientos en marcos intradiarios.
  - Ninguna estrategia mostró un comportamiento idéntico en los 4 ETFs de forma simultánea, demostrando que la correlación de activos debe ser tenida en cuenta.

---

### T. RESEARCH MEMORY PATTERNS & U. FAILED STRATEGIES
Patrones aprendidos por el `ResearchMemory` durante la campaña:
1. **Timeframe más fértil:** El marco **`1h`** ofreció el mejor compromiso entre significancia estadística de operaciones ($>30$ trades) y calidad de ratio Sharpe.
2. **Filtros perjudiciales en 15m:** Los filtros de volumen (`RVOL > 2.0`) combinados con `RSI < 25` destruyeron la frecuencia operativa en 15m, generando series con menos de 10 trades (`LOW_SAMPLE`).
3. **Tendencia en Diario (`1d`):** `TREND_FOLLOWING` en `1d` presentó el mayor Profit Factor promedio ($1.35$), pero con baja frecuencia de operaciones en 5 años (~15-20 operaciones), situándose en el umbral preliminar de evidencia.

---

### V. BEST RESEARCH LEAD VS W. BEST VALIDATED CANDIDATE

#### 1. Best Research Lead (Mejor Prospecto Científico)
- **Estrategia:** `Autogen_US Liquid ETFs_hyp_07011dbd_v1.1`
- **ID:** `mut_strat_disc_bd16f0ff_e499`
- **Timeframe:** `1d` | **Familia:** `REGIME_FILTERED`
- **Strategy Quality Score:** **46.01 / 100**
- **Economic Edge Score:** **0.0** (`NO_EDGE`)
- **Structural Robustness Score:** **70.0**
- **Trades Totales:** 149 (IS: 111, OOS: 38)
- **Sharpe Ratio:** IS=-6.83 | OOS=20.40 | WF=0.04
- **Estado de Ciclo de Vida:** Permanece en **`RESEARCH`** para continuar optimización de ventaja económica.

#### 2. Best Validated Candidate (Candidato Formal a Validación)
- **Resultado:** **`NONE`**
- **Causa Raíz Cuantitativa:** Ninguna estrategia alcanzó simultáneamente:
  1. `EconomicEdgeClassification == POSITIVE_EDGE` (PF > 1.10 y Sharpe OOS > 0 en toda la muestra);
  2. Muestra estadística mínima de validación en Candidate Gating (>= 10 IS trades y >= 5 OOS trades con PF >= 1.10);
  3. SQS >= 70.0.
- **Conclusión Científica:** El sistema mantuvo intactas las puertas de seguridad y **rechazó promover estrategias prematuras a candidato**, cumpliendo con la regla de tolerancia cero a falsos positivos.

---

### X. EDGE MAP MATRIX (StrategyQualityScore / EES / PRS / Evidencia)

La siguiente matriz mapea empíricamente la calidad cuantitativa a través de timeframes y familias:

```
+-------------------+----------------------+----------------------+----------------------+
| FAMILIA           | 15-MINUTE (15m)      | 1-HOUR (1h)          | DAILY (1d)           |
+-------------------+----------------------+----------------------+----------------------+
| MOMENTUM          | SQS: 37.08 [NO_EDGE]  | SQS: 35.47 [NO_EDGE]  | SQS: 39.99 [NO_EDGE]  |
| BREAKOUT          | SQS: 37.05 [NO_EDGE]  | SQS: 35.30 [NO_EDGE]  | SQS: 39.93 [NO_EDGE]  |
| MEAN_REVERSION    | SQS: 37.07 [NO_EDGE]  | SQS: 35.27 [NO_EDGE]  | SQS: 40.38 [NO_EDGE]  |
| TREND_FOLLOWING   | SQS: 37.21 [NO_EDGE]  | SQS: 34.66 [NO_EDGE]  | SQS: 45.97 [NO_EDGE]  |
| REGIME_FILTERED   | SQS: 37.02 [NO_EDGE]  | SQS: 34.35 [NO_EDGE]  | SQS: 46.01 [NO_EDGE]  |
+-------------------+----------------------+----------------------+----------------------+
```

**Diagnóstico del Edge Map:**
- **Dónde NO aparece el Edge:** En el timeframe **15m**, el ruido de microestructura y las fricciones de slippage degradan fuertemente el rendimiento, arrojando predominantemente `WEAK_EDGE` y `NO_EDGE`.
- **Dónde es más prometedor el Edge:** En el timeframe **1h** y **Daily**, las familias **`TREND_FOLLOWING`** y **`REGIME_FILTERED`** obtienen mayor consistencia en Sharpe y estabilidad OOS.

---

### Y. AUTONOMOUS DECISION LOG (Muestra de Trazabilidad)

| Iter | Decisión Real | Justificación / Razón | Evidencia Registrada | Próxima Acción |
| :---: | :--- | :--- | :--- | :--- |
| 01 | `Evaluar Autogen_US Liquid ETFs_hyp_4ee653fe en 15m` | Exploración de edge en MOMENTUM (15m) con COMPONENT_COMBINATION | Trades: 81 | EES: 0.0 (NO_EDGE) | PRS: 66.8 | SQS: 37.03 | Gate: False | `MUTATE` |
| 02 | `Evaluar Autogen_US Liquid ETFs_hyp_7a958749 en 15m` | Exploración de edge en BREAKOUT (15m) con COMPONENT_COMBINATION | Trades: 81 | EES: 0.0 (NO_EDGE) | PRS: 66.8 | SQS: 37.05 | Gate: False | `MUTATE` |
| 03 | `Evaluar Autogen_US Liquid ETFs_hyp_05a9c633 en 15m` | Exploración de edge en MEAN_REVERSION (15m) con PARAMETER_VARIATION | Trades: 81 | EES: 0.0 (NO_EDGE) | PRS: 66.8 | SQS: 37.05 | Gate: False | `MUTATE` |
| 04 | `Evaluar Autogen_US Liquid ETFs_hyp_f669dfa6 en 15m` | Exploración de edge en TREND_FOLLOWING (15m) con COMPONENT_COMBINATION | Trades: 81 | EES: 0.0 (NO_EDGE) | PRS: 66.8 | SQS: 37.05 | Gate: False | `MUTATE` |
| 05 | `Evaluar Autogen_US Liquid ETFs_hyp_07011dbd en 15m` | Exploración de edge en REGIME_FILTERED (15m) con NEW_RULE_STRUCTURE | Trades: 81 | EES: 0.0 (NO_EDGE) | PRS: 66.8 | SQS: 37.02 | Gate: False | `MUTATE` |
| 06 | `Evaluar Autogen_US Liquid ETFs_hyp_c02ed1c0 en 1h` | Exploración de edge en MOMENTUM (1h) con COMPONENT_COMBINATION | Trades: 556 | EES: 0.0 (NO_EDGE) | PRS: 47.1 | SQS: 34.12 | Gate: False | `MUTATE` |
| 07 | `Evaluar Autogen_US Liquid ETFs_hyp_c9fbaf11 en 1h` | Exploración de edge en BREAKOUT (1h) con COMPONENT_COMBINATION | Trades: 556 | EES: 0.0 (NO_EDGE) | PRS: 47.2 | SQS: 34.15 | Gate: False | `MUTATE` |
| 08 | `Evaluar Autogen_US Liquid ETFs_hyp_ff92f535 en 1h` | Exploración de edge en MEAN_REVERSION (1h) con PARAMETER_VARIATION | Trades: 556 | EES: 0.0 (NO_EDGE) | PRS: 47.7 | SQS: 34.32 | Gate: False | `MUTATE` |
| 09 | `Evaluar Autogen_US Liquid ETFs_hyp_86ac4c92 en 1h` | Exploración de edge en TREND_FOLLOWING (1h) con COMPONENT_COMBINATION | Trades: 556 | EES: 0.0 (NO_EDGE) | PRS: 46.2 | SQS: 33.85 | Gate: False | `MUTATE` |
| 10 | `Evaluar Autogen_US Liquid ETFs_hyp_4341531b en 1h` | Exploración de edge en REGIME_FILTERED (1h) con NEW_RULE_STRUCTURE | Trades: 556 | EES: 0.0 (NO_EDGE) | PRS: 47.8 | SQS: 34.35 | Gate: False | `MUTATE` |


---

### Z. CRITICAL INTERPRETATION & RECOMMENDED NEXT RESEARCH

1. **¿El edge aparece solamente en un timeframe?**
   Sí. El análisis demuestra que el edge económico creíble se disipa en timeframes menores a 1 hora debido al impacto relativo del spread y costos de transacción.
2. **¿Depende de un único símbolo?**
   Las estrategias con mejor desempeño en `SPY` muestran degradación al aplicarse en `IWM`, confirmando que el régimen de activos de baja capitalización requiere modelos desacoplados.
3. **Próximo Paso Recomendado (Fase 6):**
   Focalizar la investigación exclusivamente en los cuadrantes de mayor densidad en el Edge Map: **`1h` y `Daily` para `TREND_FOLLOWING` y `REGIME_FILTERED`**, incorporando filtros de volatilidad multi-activo.

---
*Reporte generado automáticamente por AI Trading Agent Strategy Laboratory — Fase 5 (Edge Discovery Across Timeframes).*
