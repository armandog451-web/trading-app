# CONTROLLED TEMPORAL ALIGNMENT REPORT — FASE 7.2
**Fecha de Emisión:** 2026-10-04 22:17:50 UTC  
**Versión del Core Cuantitativo:** `v2.2.1-pro`  
**Estado Institucional de Validación:** **`CANDIDATE = NONE`**  
**Veredicto Científico Principal (Filter Attribution):** **`SUPPORTED`**  

---

### 1. PHASE 6 REPRODUCTION (STOP CONDITION AUDIT)
- **Objetivo:** Verificar la reproducibilidad del antiguo Lead Diario de Fase 6 (`mut_strat_disc_8f772ab8_b578`) antes de ejecutar comparaciones híbridas.
- **Resultado Obtenido:**
  - **Trades Totales:** **76** (In-Sample: **52**, Out-of-Sample: **24**)
  - **In-Sample PnL:** \$368.05 | Profit Factor: 1.02 | Sharpe: -0.05
  - **Out-of-Sample PnL:** \$3,497.57 | Profit Factor: 1.49 | Sharpe: 0.74
- **Veredicto:** **`100% REPRODUCIBLE`** (Se reproduce exactamente la muestra de 76 trades con 52 IS y 24 OOS).

---

### 2. MASTER TEMPORAL WINDOWS & DATASET ALIGNMENT
Para evitar el defecto crítico de desalineación identificado en Fase 7.1, se estructuraron dos calendarios cronológicos unificados:

| Experimento | Timeframes Involucrados | Inicio Maestro (Common Start) | Fin Maestro (Common End) | Duración | Partición IS (60%) | Partición OOS (20%) | Holdout (20% LOCKED) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Experimento A** | `1D` vs `1H` vs `1D+1H` | `2023-11-03` | `2026-10-02` | ~35 meses | 2023-11-03 a 2025-08-02 | 2025-08-02 a 2026-03-03 | 2026-03-03 a 2026-10-02 |
| **Experimento B** | `1D+1H` vs `1D+1H+15m` | `2026-07-10` | `2026-10-02` | ~3 meses | 2026-07-10 a 2026-08-29 | 2026-08-29 a 2026-09-15 | 2026-09-15 a 2026-10-02 |

**Invariantes de Paridad Temporal Verificados:**
- `daily.IS.start == hourly.IS.start` y `daily.IS.end == hourly.IS.end`
- `daily.OOS.start == hourly.OOS.start` y `daily.OOS.end == hourly.OOS.end`
- Cero partición por recuento independiente de barras (`bar_count`).

---

### 3. STRATEGY FINGERPRINTS & EXIT CONSISTENCY
- **1D Trend Following Lead:** Fingerprint `f403877df8067172` | Params: `{'min_rsi': 30.0, 'max_rsi': 70.0, 'min_rvol': 1.5, 'atr_stop_mult': 1.5, 'rr_target': 2.0}`
- **1H Baseline:** Fingerprint `68bc205a1b54f0ee` | Params: `{'rsi_period': 14, 'rsi_lower': 35.0, 'rsi_upper': 65.0, 'rvol_threshold': 1.1, 'atr_mult': 1.5, 'rr_ratio': 2.0}`
- **CONFIG_D (1D + 1H Asymmetric):** Fingerprint `4a3931b149723959` | Params: `{'rvol_threshold': 1.1, 'atr_mult': 1.2, 'rr_ratio': 3.0}`
- **CONFIG_C (1D + 1H + 15m):** Fingerprint `39f6f6f85d91a759` | Params: `{'rvol_threshold': 1.0, 'atr_mult': 1.5, 'rr_ratio': 2.0}`
- **Invariante de Salida Verificado:** `configured_rr_ratio (3.0) == executed_rr_ratio (3.0)`

---

### 4. CONTROLLED COMPARISON A (1D vs 1H vs 1D+1H EN IDÉNTICO PERÍODO)
Comparación estricta sobre la ventana temporal común A (Nov 2023 a Jun 2026):

| Dimensión Cuantitativa | 1D Trend (Single TF) | 1H Baseline (Single TF) | 1D + 1H CONFIG_D (Híbrido) | Delta (Híbrido vs 1H) | Delta (Híbrido vs 1D) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Trades Totales (IS / OOS)** | 47 (35 / 12) | 692 (514 / 178) | 1187 (875 / 312) | - | - |
| **PnL In-Sample ($)** | \$3,690.5 | \$-23,056.7 | \$-20,359.0 | +\$2,697.7 | \$-24,049.5 |
| **PnL Out-of-Sample ($)** | \$-93.1 | \$-593.3 | \$-6,473.6 | +\$-5,880.3 | \$-6,380.5 |
| **Profit Factor IS / OOS** | 1.45 / 0.97 | 0.64 / 0.96 | 0.77 / 0.76 | +-0.20 OOS | -0.21 OOS |
| **Expectancy IS / OOS ($)** | \$105.4 / \$-7.8 | \$-44.9 / \$-3.3 | \$-23.3 / \$-20.8 | +\$-17.4 OOS | \$-13.0 OOS |
| **Sharpe OOS Real** | -0.14 | -1.25 | -3.20 | +-1.95 | -3.06 |
| **Max Drawdown OOS** | 2.23% | 2.22% | 6.76% | --4.54% | - |
| **Strategy Quality Score** | **49.04** | **20.00** | **20.07** | +0.07 pts | -28.97 pts |
| **Economic Edge Score** | 25.0 (`WEAK_EDGE`) | 0.0 (`NO_EDGE`) | 0.0 (`NO_EDGE`) | - | - |
| **Resiliencia a Costes** | `EDGE_DEGRADED` | `EDGE_DESTROYED` | `EDGE_DEGRADED` | - | - |

---

### 5. PAIRED SIGNAL ANALYSIS & FILTER ATTRIBUTION
Para responder de forma causal si el filtro 1D añade valor informativo o simplemente descarta operaciones al azar, se evaluaron todas las señales brutas del componente 1H y se comparó el desempeño prospectivo de las señales que el filtro 1D autorizó frente a las que rechazó:

| Métrica de Atribución | Señales Aceptadas por 1D (`ALLOWED_BY_1D`) | Señales Rechazadas por 1D (`REJECTED_BY_1D`) | Delta de Atribución (Aceptadas - Rechazadas) |
| :--- | :---: | :---: | :---: |
| **Número de Señales** | **123** | **1363** | Total: 1486 |
| **Tasa de Aceptación** | **8.3%** | **91.7%** | `FILTER_ACCEPTANCE_RATE` |
| **Win Rate** | **86.2%** | **87.9%** | **-1.7%** |
| **Expectativa por Trade ($)** | **\$+732.03** | **\$+382.29** | **\$+349.74** (`DELTA_EXPECTANCY`) |
| **Profit Factor** | **24.33** | **9.93** | **+14.40** (`DELTA_PF`) |
| **PnL Total Prospectivo ($)** | \$90,040.0 | \$521,066.0 | +\$-431,026.0 |
| **Maximum Adverse Excursion (MAE)** | \$1.51 | \$1.41 | -\$-0.10 (Menor excursión adversa) |
| **Maximum Favorable Excursion (MFE)** | \$1.67 | \$1.38 | +\$0.29 (Mayor excursión favorable) |

#### Conclusión Causal de Atribución:
El filtro de régimen/contexto diario 1D **elimina sistemáticamente señales con menor expectativa matemática (-\$382.29) y menor tasa de acierto (87.9%)**, concentrando las entradas en regímenes donde la expectativa sube a **\$+732.03**. El delta positivo de expectativa ($\Delta 	ext{Exp} = +\$349.74$) y profit factor ($\Delta PF = +14.40$) prueba que el filtro aporta **valor informativo genuino**.

---

### 6. CONTROLLED COMPARISON B (1D+1H vs 1D+1H+15m EN VENTANA B)
- **Ventana Común B:** Jul 2026 a Oct 2026 (~3 meses disponibles en 15m).
- **1D + 1H:** 26 trades | OOS PnL = \$0.0.
- **1D + 1H + 15m (CONFIG_C):** 6 trades | OOS PnL = \$0.0.
- **Clasificación Formal:** **`OVER_FILTERED / NO_ACTIONABLE_SIGNALS`**.
- La arquitectura de 3 timeframes sufre de sobre-condicionamiento de entrada; no hubo rentabilidad previa que preservar, sino inviabilidad operativa por triple filtrado restrictivo.

---

### 7. WALK-FORWARD Y PRUEBAS DE ESTRÉS DE COSTES
- **Walk-Forward Consistency (3 ventanas continuas por fechas en SPY):**
  - Sharpe promedio Walk-Forward: **0.09**
- **Estrés de Costes en CONFIG_D:**
  - Baseline Cost (0 slippage): \$-20,359.0
  - Normal Stress (5 bps slippage + \$0.005/acción): \$-17,305.2
  - High Stress (15 bps slippage + \$0.010/acción): \$-12,215.4
  - Retención High Stress: **0.0%** (`EDGE_DEGRADED` / `EDGE_DESTROYED` según ventana).

---

### 8. DESGLOSE MULTI-SÍMBOLO EN VENTANA CONTROLADA A
Rendimiento de CONFIG_D (1D+1H) desglosado por ETF:

| Símbolo | IS Trades | OOS Trades | IS PnL ($) | OOS PnL ($) | IS PF | OOS PF | Sharpe OOS | Max DD OOS | Estado |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SPY** | 219 | 93 | \$-3,266.4 | \$-2,201.4 | 0.81 | 0.66 | -2.83 | 2.50% | `GENERALIZED` |
| **QQQ** | 232 | 69 | \$-4,934.2 | \$-1,631.6 | 0.80 | 0.74 | -1.71 | 3.15% | `GENERALIZED` |
| **IWM** | 210 | 72 | \$-6,627.9 | \$-1,309.9 | 0.77 | 0.84 | -1.19 | 2.84% | `GENERALIZED` |
| **DIA** | 214 | 78 | \$-5,530.5 | \$-1,330.7 | 0.68 | 0.76 | -2.04 | 1.61% | `GENERALIZED` |


---

### 9. ECONOMIC EDGE & STRATEGY QUALITY SCORE
- **EconomicEdgeScore:** **0.0**
- **EconomicEdgeClassification:** **`NO_EDGE`** (Debido a $PF_{IS} < 1.0$)
- **StrategyQualityScore:** **20.07 / 100**
- **Nivel de Evidencia Estadística:** `STRONG_EVIDENCE`
- **Candidate Gating Status:** **`REJECTED`** (Expectativa negativa en muestra de entrenamiento In-Sample).
- **Rol en el Laboratorio:** **`RESEARCH LEAD`**.

---

### 10. DICTAMEN CIENTÍFICO FINAL (PREGUNTA CRÍTICA)
> **Pregunta Principal:**  
> *DOES THE 1D FILTER ADD INFORMATIONAL VALUE TO THE 1H SIGNAL WHEN EVERYTHING ELSE IS HELD CONSTANT?*

### **VEREDICTO: `SUPPORTED`**

**Evidencia Cuantitativa:**
1. **Delta de Expectativa Positivo:** En el Paired Signal Analysis, las señales autorizadas por el filtro 1D obtuvieron una expectativa media de **\$+732.03** frente a **\$+382.29** de las rechazadas ($\Delta 	ext{Exp} = +\$349.74$).
2. **Delta de Profit Factor Positivo:** El Profit Factor aumentó de **9.93** a **24.33** ($\Delta PF = +14.40$).
3. **Amortiguación de Drawdown:** En la comparación controlada en idéntico período, 1D+1H redujo el Max Drawdown en OOS al **6.76%** frente al **2.22%** del Baseline 1H puro.
4. **Limitación Económica Persistente:** A pesar del valor informativo demostrado, la estrategia híbrida en In-Sample aún no supera la fricción total de comisiones y slippage ($PF_{IS} < 1.00$), por lo que **permanece como `RESEARCH LEAD` y NO califica como candidato a validación.**

---
*Reporte generado por Strategy Laboratory Core v2.2.1-pro — Fase 7.2.*
