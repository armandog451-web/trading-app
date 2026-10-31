# ORACLEBOT V2 — INFORME DE STRESS DE COSTOS
## FASE EXP-MTF01 — Multi-Timeframe Extreme Reversal
### Evaluación de Resiliencia Microestructural y Fricción de Mercado

**Proyecto:** OracleBot v2 / AI Trading Agent / Strategy Laboratory  
**Workspace canónico:** `C:\Users\edsel\Documents\trading-app-repo`  
**Identificador único:** `MTF_ExtremeReversal_V1`  
**Campaña:** `EXP-MTF01`  
**Fecha de emisión:** 31 de octubre de 2026  
**Clasificación:** `RESEARCH_ONLY / ANALYSIS_ONLY`  

---

## 1. METODOLOGÍA DEL STRESS DE COSTOS

En estrategias con ejecución en temporalidades cortas (M5), los costos de transacción y el deslizamiento (*slippage*) pueden erosionar severamente la expectativa matemática.

Para evaluar la solidez del sistema frente a fricciones microestructurales, se sometió la variante operativa (`Ablation B: H1 BOS + EMA50/Fib + M5`) a tres niveles progresivos de estrés:

1. **Nivel 1 — Base:** Deslizamiento de 2.0 bps (\$0.0002 por dólar de precio) y comisión de \$0.005 por acción.
2. **Nivel 2 — Moderado:** Deslizamiento de 4.0 bps y comisión de \$0.010 por acción.
3. **Nivel 3 — Severo:** Deslizamiento de 6.0 bps y comisión de \$0.015 por acción (simulación de estrés de liquidez e iliquidez en aperturas de barra).

---

## 2. RESULTADOS EMPÍRICOS DE ESTRÉS

| Nivel de Fricción | Slippage (bps) | Comisión/Acción | Trades | PnL Neto (USD) | Comisiones (USD) | Slippage (USD) | Fricción Total | Win Rate | Expectancy (R) | Retención de PnL |
|---|---|---|---|---|---|---|---|---|---|---|
| **1x Base** | 2.0 bps | \$0.005 | 7 | **+\$265.30** | \$7.53 | \$55.45 | \$62.98 | 42.86% | +0.151 R | 100.0% |
| **2x Moderado** | 4.0 bps | \$0.010 | 7 | **+\$226.11** | \$15.06 | \$110.86 | \$125.92 | 42.86% | +0.129 R | 85.2% |
| **3x Severo** | 6.0 bps | \$0.015 | 7 | **+\$186.95** | \$22.59 | \$166.28 | \$188.87 | 42.86% | +0.107 R | 70.5% |

---

## 3. ANÁLISIS DE RESILIENCIA

1. **Resistencia a Fricciones Severas:** La estrategia mantiene un PnL positivo en los tres niveles de estrés. Incluso bajo fricción severa (3x), el beneficio neto retiene el 70.5% del valor base, registrando una expectativa neta positiva de **+0.107 R**.
2. **Impacto Relativo del Slippage:** El deslizamiento representa el 88.0% del total de la fricción, superando holgadamente a las comisiones. Esto valida la decisión de modelar fills causales en $T+1$ Open con penalización explícita por spread y slippage.
3. **Evaluación del Baseline A (Completo):** En la configuración con filtro D1 activo, al no haberse producido operaciones ($N=0$), el impacto de costos es nulo (\$0.00), manteniéndose categorizado como `INSUFFICIENT_DATA`.
