# ORACLEBOT V2 — VEREDICTO FINAL DE INVESTIGACIÓN CIENTÍFICA
## FASE EXP-MTF01 — Multi-Timeframe Extreme Reversal
### Dictamen Cuantitativo Institucional, Scoring y Recomendaciones

**Proyecto:** OracleBot v2 / AI Trading Agent / Strategy Laboratory  
**Workspace canónico:** `C:\Users\edsel\Documents\trading-app-repo`  
**Identificador único:** `MTF_ExtremeReversal_V1`  
**Campaña:** `EXP-MTF01`  
**Fecha de emisión:** 31 de octubre de 2026  
**Clasificación:** `RESEARCH_ONLY / ANALYSIS_ONLY`  

---

## 1. EVALUACIÓN DE LA HIPÓTESIS PRINCIPAL

> **Hipótesis del Brief:** Una estrategia que combina extremos diarios (D1), desaceleración, cambio de estructura horaria (H1 BOS), confluencia con EMA 50 / Fibonacci 0.618 y confirmación intradía (M5) presenta una expectativa económica neta positiva frente a referencias más sencillas.

### Veredicto Empírico sobre la Hipótesis:
1. **Baseline A (Método Completo del Video):** **RECHAZADO POR HIPER-RESTRICCIÓN.**  
   En la ventana histórica real de mercado con las 3 temporalidades disponibles simultáneamente (60 días, 4,680 barras M5 por activo a través de 6 ETFs representativos), el sistema completo generó **0 operaciones**. La acumulación de 6 filtros secuenciales independientes reduce la probabilidad de ocurrencia conjunta a un evento estadísticamente irrelevante, invalidando la pretensión de ser un sistema de trading repetible en el corto/medio plazo.
2. **Ablación B (Estructura H1 + Confluencia EMA/Fib + Gatillo M5):** **INCONCLUSIVE (MUESTRA PRELIMINAR).**  
   Al remover la hiper-restricción del filtro diario D1, el núcleo del método (H1 BOS + confluencia de retroceso 0.618 con EMA 50 + ruptura fractal local M5) generó **7 operaciones**, obteniendo un Net PnL positivo de **+\$265.30 USD**, Win Rate del **42.86%** y Expectancy de **+0.151 R**, resistiendo el estrés de costos hasta 3x deslizamiento severo (6 bps). No obstante, al contar únicamente con 7 operaciones ($N < 30$), el resultado no supera el *Minimum Evidence Gate*.

---

## 2. SCORING INSTITUCIONAL

| Métrica / Scoring | Baseline A (Completo) | Ablación B (Sin D1) | Umbral Requerido | Evaluación Institucional |
|---|---|---|---|---|
| **Total Trades ($N$)** | 0 | 7 | $\ge 30$ | **INSUFFICIENT_EVIDENCE** |
| **Profit Factor** | 0.00 | 1.34 | $> 1.15$ | **FAVORABLE_PERO_PRELIMINAR (Abl. B)** |
| **Win Rate** | 0.0% | 42.86% | $> 40.0\%$ | **CUMPLE EN ABLACIÓN B** |
| **Expectancy en R** | 0.000 R | +0.151 R | $> +0.100 \text{ R}$ | **CUMPLE EN ABLACIÓN B** |
| **Economic Edge Score (EES)** | 0.0 / 100 | 24.5 / 100 | $\ge 60.0$ | **NO_EDGE (Penalizado por muestra $N < 30$)** |
| **Pure Robustness Score (PRS)** | 0.0 / 100 | 32.0 / 100 | $\ge 50.0$ | **NO_SUPERADO (Falta retención OOS plurianual)** |
| **Strategy Quality Score (SQS)**| 0.0 / 100 | 27.5 / 100 | $\ge 55.0$ | **NO_SUPERADO** |
| **Minimum Evidence Gate** | **FALLIDO (N=0)** | **FALLIDO (N=7)** | Mínimo 30 trades | **RECHAZADO POR PUERTA DE EVIDENCIA** |

---

## 3. LIMITACIONES METODOLÓGICAS FORMALES

1. **Profundidad Histórica Intradía M5:** Las fuentes públicas y gratuitas de Yahoo Finance limitan estrictamente las consultas de barras de 5 minutos a 60 días naturales retrospectivos. Conforme a las normas del proyecto, no se crearon barras sintéticas ni interpoladas para no distorsionar la realidad empírica.
2. **Discrecionalidad vs. Algoritmo:** El autor del video se apoya en líneas diagonales trazadas a mano y en la selección subjetiva de operaciones pasadas. Cuando sus conceptos se traducen a reglas deterministas e invariantes en el tiempo, la confluencia exacta resulta excepcionalmente infrecuente.

---

## 4. VEREDICTO FINAL Y RECOMENDACIÓN

- **Veredicto Definitivo:** `INCONCLUSIVE` (con dictamen de `REJECTED` para la variante Baseline A por hiper-restricción).
- **Recomendación Operativa:**
  - **PROHIBIDO** avanzar esta estrategia a PAPER Trading con brokers o a Forward Shadow.
  - **MANTENER** la estrategia exclusivamente como código de laboratorio en `experiments/exp_mtf01/`.
  - Si en el futuro se adquiere una base de datos histórica de tick/M5 de 5 o más años, se autoriza re-evaluar la variante `Ablation B` para determinar si su ligera ventaja positiva (+0.151 R) se sostiene sobre una muestra de 100+ operaciones.
- **Acción Siguiente Requerida:** Archivar la investigación EXP-MTF01 y preservar intactos los procesos operativos de D21 y las campañas Forward Shadow de Phase 7.4 y EXP-ST02.
