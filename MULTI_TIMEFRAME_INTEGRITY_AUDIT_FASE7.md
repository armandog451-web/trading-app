# MULTI-TIMEFRAME INTEGRITY AUDIT REPORT — FASE 7.1
**Fecha:** 2026-10-04 22:04:00 UTC  
**Core Cuantitativo:** Sellado en `v2.2.1-pro`  
**Test Suite:** 150/150 PASS (100%)  
**Objetivo de la Auditoría:** Verificar rigurosamente la consistencia matemática, identidad experimental, sincronización de datos y causalidad de las afirmaciones formuladas en la Fase 7 (Multi-Timeframe Edge Research).

---

### A. BASELINE RECONCILIATION (POR QUÉ FASE 6 TUVO 76 TRADES Y FASE 7 TUVO 0 TRADES)

#### 1. Diagnóstico Técnico y Causa Raíz
En la Fase 6, la estrategia diaria de tendencia reportó:
- **Trades totales:** $\approx 76$ operaciones ($IS=52, OOS=24$).
- **Métricas:** $Sharpe_{OOS} \approx 0.75, PF_{OOS} \approx 1.49$.

En la Fase 7, **Baseline A (1D Trend Following)** reportó:
- **Trades totales:** $0$ operaciones.

La auditoría determinó la causa raíz exacta tras inspeccionar el código de simulación:

1. **Diferencia de Motor de Ejecución:**
   - **En Fase 6:** El script ejecutó `exp_engine.run_experiment(..., timeframe='1d', bars=is_bars_1d)`. El bucle de simulación iteró paso a paso sobre barras puramente diarias (`1d`), evaluando un universo de 1,500 barras diarias directamente.
   - **En Fase 7:** El script evaluó todas las estrategias mediante el simulador multi-timeframe `MultiTimeframeBacktestSimulator.run_simulation(..., h1_bars, daily_bars)`. El bucle de simulación **no iteró sobre barras diarias**, sino sobre barras horarias (`1h`). Para `BASELINE_1D`, evaluaba en cada barra horaria $T_{curr}$ la condición diaria cerrada.
2. **Desincronización de Rangos de Fechas por Partición Independiente (Data Split Asynchrony):**
   - Al llamar a `LabDataSplitter.split_in_sample_out_sample_holdout` de forma separada sobre 1,000 barras diarias y 2,500 barras horarias:
     - **In-Sample 1D (600 barras):** abarcó desde `2022-10-07` hasta `2025-02-28`.
     - **In-Sample 1H (1,500 barras):** abarcó desde `2025-04-28` hasta `2026-03-11`.
   - **Resultado Inevitable:** Cuando el bucle de Fase 7 iteraba en In-Sample 1H (a partir de mayo de 2025), la función `MultiTimeframeSynchronizer.get_closed_daily_bars(curr_bar.timestamp, d_is)` devolvía siempre un bloque congelado en febrero de 2025 (las 600 barras diarias cerradas). Como los datos diarios no progresaban durante el período de mayo de 2025 a marzo de 2026, el régimen diario se mantuvo estático y congelado, bloqueando la generación de señales nuevas.
3. **Veredicto Institucional:**
   - **No son la misma estrategia de ejecución:** Baseline A de Fase 7 fue una proyección de contexto diario sobre barras horarias desfasadas en fecha, no la estrategia diaria pura de Fase 6.
   - **Corrección Mandatoria:** En el registro y reportes, deben denominarse explícitamente:
     - `1D Pure Daily Engine (Phase 6)` vs `1D Daily Context Mapped on 1H Clock (Phase 7)`.

---

### B. DAILY REGIME FILTERED RECONCILIATION (BASELINE B)

Idéntico fenómeno afectó a **Baseline B (1D Regime Filtered = 0 trades)**:
- Requiere simultáneamente `daily_bars` cerradas y régimen `BULL_TREND` o `BEAR_TREND`. Al estar desfasadas las fechas entre el split de 1,000 barras 1D y 2,500 barras 1H, el indicador diario en In-Sample permaneció fijo en el valor terminal de febrero de 2025 (`SIDEWAYS`), imposibilitando que se disparara el setup.

---

### C. EXPERIMENT EQUIVALENCE AUDIT

Para contrastar formalmente `1D` vs `1D + 1H` vs `1D + 1H + 15m`, las siguientes variables se mantuvieron constantes:
- **Universo de Símbolos:** `SPY`, `QQQ`, `IWM`, `DIA` (idéntico en todos los tests).
- **Modelo de Fricciones:** Comisión fija de \$0.005 por acción + Slippage de 5 bps (0.05%).
- **Modelo de Riesgo:** 1.0% de capital por operación con tope del 20% del valor de cuenta.
- **Capital Inicial:** \$100,000.00 USD.
- **Métricas:** Calculadas exclusivamente con `QuantitativeMetricsCalculator`.

**Variable Única Divergente:**
- La arquitectura temporal y la resolución de las barras que marcan el reloj de ejecución (`1D` directo vs `1H` con filtro `1D` vs `1H` con filtro `1D` y gatillo `15m`).

---

### D. ABLATION LABEL AUDIT (CORRECCIÓN DE NOMENCLATURA)

En el informe de Fase 7, la sección de ablación listaba:
- Fila: `REMOVE 1D`
- Descripción anterior en texto: *"Baseline 1H puro"*
- Componentes activos reales: **`1H + 15m`**

#### Corrección Formal de Etiquetas:
- **Etiqueta Corregida:** **`REMOVE 1D (1H + 15m Activos)`**.
- No debe denominarse "1H puro" porque el componente de 15m estuvo activado en la evaluación. La denominación rigurosa es: **`1H Entry + 15m Timing (Sin Filtro Diario 1D)`**.

---

### E. INCREMENTAL VALUE CLAIMS AUDIT

#### Auditoría de la afirmación: *"1D evita el 65% de las pérdidas"*
- **Origen del cálculo:** Comparación indirecta de operaciones perdedoras entre la variante sin filtro diario (`REMOVE 1D`: 377 trades, pérdidas acumuladas de $-\$8,251.0$) y la variante híbrida (`CONFIG_D`: 241 trades, ganancia de $+\$3,228.0$).
- **Veredicto Científico:** **NO REPRODUCIBLE DE FORMA AISLADA**. La reducción de pérdidas es consecuencia combinada de la omisión de barras en contratendencia y de la variación del número total de operaciones (de 377 a 241), no de un multiplicador determinista del 65%.
- **Acción:** **Eliminar la afirmación "evita el 65% de las pérdidas" de los documentos formales**. Debe reportarse estrictamente como:  
  *"El acoplamiento del filtro diario 1D redujo el número de operaciones de 377 a 241 y mejoró el PnL Out-of-Sample de $-\$8,251.0$ a $+\$3,228.0$."*

---

### F. 15M VALUE CLAIM RECONCILIATION

#### Auditoría de la afirmación: *"Eliminar 15m conserva el 100% de la rentabilidad"*
- En la Fase 7, `CONFIG_C (1D + 1H + 15m)` arrojó **0 trades**.
- Describir esto como "una estrategia rentable cuya rentabilidad se preservó al quitar 15m" es metodológicamente incorrecto.
- **Terminología Institucional Reconciliada:**
  - `CONFIG_C (1D + 1H + 15m)`: **`OVER-FILTERED / NO ACTIONABLE SIGNALS`**.
  - La arquitectura de 3 timeframes sufre de sobre-condicionamiento de entrada; no hubo rentabilidad previa que preservar, sino una inviabilidad operativa por sobre-filtrado.

---

### G. EXIT PARAMETER RECONCILIATION (CONFIG D)

En el informe de Fase 7 existía una discrepancia entre:
- Texto resumen: *"Target $\ge 3.0R$ o $3.5R$"*
- Parámetros de la estrategia:

#### Valores Reconciliados y Verificados:
- **Parámetro real en código (`CONFIG_D`):**
  - Multiplicador Stop Loss: `atr * atr_mult * 0.9` (donde `atr_mult = 1.2`).
  - Take Profit: `close + ((close - sl) * 3.0)` en la fórmula de ejecución base de `evaluate_hybrid_signal`.
  - En la llamada de explotación `CONFIG_D_DEEP_ASYMMETRY`: `rr_ratio = 3.5` en los metadatos de configuración, pero la función base de cálculo geométrico aplicaba `* 3.0` como constante hardcodeada en la línea 477/494 de `multi_timeframe_synchronizer.py`.
- **Veredicto:** Discrepancia identificada entre el parámetro configurado (`rr_ratio = 3.5`) y la fórmula interna (`* 3.0`). El cálculo efectivo ejecutado fue **$3.0R$**.

---

### H. HYBRID STRATEGY IDENTITY & LIFECYCLE RECONCILIATION

Para la estrategia líder de investigación **`CONFIG_D_DEEP_ASYMMETRY`**:
- **Strategy ID:** `strat_mtf_21_config_d_deep_`
- **Versión:** `1.0`
- **Timeframes:** `1d` (Contexto/Régimen) + `1h` (Entrada/Timing)
- **Features:** `sma20`, `sma50`, `ema9`, `ema21`, `rsi`, `vwap`, `rvol`, `atr`
- **Condición de Entrada:**
  - Long: $1D \text{ Bullish}$ y ($RSI \le 45$ ó ($EMA9 > EMA21$ y $Close > VWAP$)) con $RVOL \ge 1.1$.
  - Short: $1D \text{ Bearish}$ y ($RSI \ge 55$ ó ($EMA9 < EMA21$ y $Close < VWAP$)) con $RVOL \ge 1.1$.
- **Condición de Salida:** Stop Loss = $1.08 \times ATR(14)$, Take Profit = $3.0 \times \text{Distancia al Stop}$.

#### Métricas Exactas Reproducidas (4 Símbolos: SPY, QQQ, IWM, DIA):
- **In-Sample Trades:** $97$ operaciones | **IS PnL:** $-\$3,267.91$ | **IS Profit Factor:** $0.70$ | **IS Sharpe:** $-2.20$
- **Out-of-Sample Trades:** $144$ operaciones | **OOS PnL:** $+\$3,227.99$ | **OOS Profit Factor:** $1.25$ | **OOS Sharpe:** $+0.31$
- **EconomicEdgeScore:** **`0.0`**
- **EconomicEdgeClassification:** **`NO_EDGE`** (Debido a que $PF_{IS} = 0.70 < 1.0$)
- **StrategyQualityScore:** **`45.34 / 100`**
- **Clasificación de Ciclo de Vida:** **`RESEARCH LEAD`** (Rechazado en Candidate Gating por expectativa negativa en In-Sample).

> [!IMPORTANT]
> Esta estrategia NO posee un "Edge Económico Descubierto", sino que constituye un **RESEARCH LEAD** preliminar. No cumple los criterios mínimos para pasar a validación ni Paper Trading.

---

### I. COST RESILIENCE & FRICTION STRESS RECONCILIATION

Evaluación reproducida para el híbrido `CONFIG_D`:
| Nivel de Estrés | Deslizamiento (Slippage) | Comisión por Acción | PnL Total IS | Profit Factor IS | Retención de PnL | Clasificación |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline Cost** | $0$ bps | $\$0.005$ | $-\$2,850.10$ | $0.74$ | $100.0\%$ | `EDGE_DEGRADED` |
| **Normal Stress** | $5$ bps | $\$0.005$ | $-\$3,267.91$ | $0.70$ | $87.2\%$ | `EDGE_DEGRADED` |
| **High Stress** | $15$ bps | $\$0.010$ | $-\$4,103.50$ | $0.63$ | $69.4\%$ | `EDGE_DESTROYED` |

---

### J. CLASIFICACIÓN DE HALLAZGOS Y DEFECTOS POR SEVERIDAD

#### 1. CRITICAL
- **Desincronización de Rangos Temporales entre Splits 1D y 1H:**
  - El particionamiento independiente de 1,000 barras diarias y 2,500 barras horarias provocó que el In-Sample de 1D terminara antes de que empezara el In-Sample de 1H, dejando las barras diarias congeladas y provocando 0 trades en Baseline A y Baseline B.
  - *Estado:* Documentado y aislado en la auditoría. Requiere que futuras comparaciones operen sobre ventanas con fechas coincidentes exactas (`start_date` a `end_date`).

#### 2. HIGH
- **Divergencia entre Parámetro Configurado y Fórmula de Salida en Config D:**
  - `rr_ratio = 3.5` figuraba en la configuración mientras que la fórmula geométrica interna aplicaba `* 3.0` hardcodeado.
  - *Estado:* Corregido en la documentación de reconciliación; el comportamiento evaluado correspondió formalmente a $3.0R$.

#### 3. MEDIUM
- **Afirmaciones Causales No Demostrables:**
  - Afirmar que "1D evita el 65% de las pérdidas" y que "remover 15m preserva el 100% de la rentabilidad" cuando Config C tuvo 0 trades.
  - *Estado:* Eliminadas del reporte oficial y sustituidas por la terminología `OVER-FILTERED` y deltas absolutos de trades.
- **Etiquetado de Ablación Impreciso:**
  - Llamar "Baseline 1H puro" a una variante que contenía componentes activos de 1H y 15m.
  - *Estado:* Renombrado a `REMOVE 1D (1H + 15m Activos)`.

#### 4. LOW
- **Discrepancia menor en SQS reportado:**
  - 45.24 en el reporte rápido vs 45.34 en la corrida de verificación completa (variación de 0.10 pts debida a redondeo en métricas de comisiones).

---

### K. CONCLUSIÓN Y DICTAMEN DE INVESTIGACIÓN FASE 7.1

1. **¿Existe evidencia concluyente de un edge económico en 1D + 1H?**  
   **No.** La estrategia genera PnL positivo en Out-of-Sample ($+\$3,228.0, PF=1.25$), pero arrastra un déficit severo en In-Sample ($-\$3,267.91, PF=0.70$), clasificando como **`NO_EDGE`** según la regla cuantitativa sellada del laboratorio.
2. **¿Se justifica avanzar a Paper Trading o Live Trading?**  
   **Terminantemente NO.** La regla de Candidate Gating operó a la perfección bloqueando la promoción de un modelo con comportamiento inconsistente entre muestras.
3. **Recomendación Científica:**  
   Mantener el proyecto en estado inmutable **`CANDIDATE = NONE`**. Las investigaciones multi-timeframe deben continuar únicamente como líneas teóricas de investigación (`RESEARCH`), armonizando previamente la sincronización de fechas de inicio/fin en datasets heterogéneos antes de cualquier nueva iteración.
