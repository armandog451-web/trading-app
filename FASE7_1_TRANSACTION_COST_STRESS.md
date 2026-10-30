# AUDITORÍA DE ESTRÉS DE COSTES TRANSACCIONALES (FASE 7.1)
## EVALUACIÓN DE RESISTENCIA A COMISIONES Y DESLIZAMIENTO (1×, 2× Y 3×)

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.1 — Auditoría de Fricción Financiera y Deslizamiento  
**Horizonte:** 1,200 barras de mercado (`SPY`)  
**Parámetros Evaluados:** Comisiones por acción y Deslizamiento (Slippage) en bps  

---

## 1. ESCENARIOS DE ESTRÉS TRANSACCIONAL

| Escenario | Comisión por Acción (Entrada + Salida) | Slippage por Operación (Entrada + Salida) | Coste Friccional Estimado por Trade (30 acc @ \$450) |
| :--- | :---: | :---: | :---: |
| **1× Base** | \$0.005 USD / acción (\$0.010 total) | 5.0 bps entrada + 5.0 bps salida (10 bps total) | ~\$13.80 USD |
| **2× Estrés** | \$0.010 USD / acción (\$0.020 total) | 10.0 bps entrada + 10.0 bps salida (20 bps total) | ~\$27.60 USD |
| **3× Severo** | \$0.015 USD / acción (\$0.030 total) | 15.0 bps entrada + 15.0 bps salida (30 bps total) | ~\$41.40 USD |

---

## 2. RESULTADOS COMPARATIVOS BAJO ESTRÉS

### 2.1 `MOM_TrendPullback_V1` (Momentum Filtrada)

| Escenario | Trades | Profit Factor | Expectativa (USD/trade) | Máximo Drawdown | PnL Neto Total | Costes Totales (USD) | Drag de Costes (% PnL Bruto) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1× Base** | 11 | **1.74** | **+\$38.31** | **0.53%** | **+\$421.39** | \$138.16 | 24.7% |
| **2× Estrés** | 11 | **1.44** | **+\$25.75** | **0.59%** | **+\$283.21** | \$276.32 | 49.4% |
| **3× Severo** | 11 | **1.20** | **+\$13.19** | **0.65%** | **+\$145.08** | \$414.48 | 74.1% |

> **Diagnóstico de Momentum:** **SUPERÓ EL ESTRÉS (PASS)**.  
> La estrategia preserva una expectativa positiva y un Profit Factor $> 1.0$ en los tres niveles de estrés. A 3×, retiene un Profit Factor de 1.20, demostrando que su ventaja bruta (\$198 USD promedio en ganancia) es lo suficientemente amplia para absorber fricciones severas del mercado.

---

### 2.2 `MR_RsiBollinger_V1` (Mean Reversion Filtrada)

| Escenario | Trades | Profit Factor | Expectativa (USD/trade) | Máximo Drawdown | PnL Neto Total | Costes Totales (USD) | Drag de Costes (% PnL Bruto) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1× Base** | 18 | **1.04** | **+\$2.15** | **0.43%** | **+\$38.74** | \$226.03 | 85.4% |
| **2× Estrés** | 18 | **0.84** | **-\$10.41** | **0.59%** | **-\$187.32** | \$452.10 | 170.8% |
| **3× Severo** | 18 | **0.67** | **-\$22.97** | **0.76%** | **-\$413.37** | \$678.13 | 256.1% |

> **Diagnóstico de Mean Reversion:** **FALLÓ EL ESTRÉS (HARD FAIL)**.  
> La estrategia colapsa a pérdidas netas inmediatas en el nivel 2× ($PF = 0.84$, PnL -$187.32 USD). Ya en el escenario Base 1×, el drag de costes consumía el **85.4% de la ganancia bruta**. La ganancia media por trade (\$132.58) es prácticamente idéntica a la pérdida media (\$102.19), por lo que un deslizamiento moderado de 10 bps destruye por completo su viabilidad comercial.

---

### 2.3 `MR_RsiBollinger_V1` (Mean Reversion Sin Filtro)

| Escenario | Trades | Profit Factor | Expectativa (USD/trade) | Máximo Drawdown | PnL Neto Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1× Base** | 52 | **0.77** | -\$17.92 | 1.85% | -\$931.72 |
| **2× Estrés** | 52 | **0.65** | -\$30.44 | 2.15% | -\$1,583.02 |
| **3× Severo** | 52 | **0.55** | -\$42.97 | 2.45% | -\$2,234.33 |

---

## 3. ANÁLISIS DE MONOTONÍA Y CAPACIDAD

1. **Monotonía Estricta:** En todas las variantes, el incremento de fricción transaccional exhibió una reducción monótona decreciente del PnL y del Profit Factor, lo que descarta artefactos de sobreajuste por secuencias de salida no controladas.
2. **Capacidad de Mercado:**  
   - Con tamaños de posición de 20 a 30 acciones en `SPY` (notional de ~\$12,000 a \$15,000 USD), el volumen diario de `SPY` (> 50 millones de acciones) garantiza absorción instantánea con impacto de mercado nulo (< 0.5 bps).
   - Sin embargo, para estrategias de alta rotación como Mean Reversion (duración media de 3 días), el volumen acumulado de comisiones y slippage es el factor dominante de desgaste de capital.

---

## 4. DICTAMEN DE RESISTENCIA A COSTES

- **`MOM_TrendPullback_V1`:** **RESISTENTE A COSTES (Aprobada para Fase 7)**.
- **`MR_RsiBollinger_V1`:** **NO RESISTENTE A COSTES (Rechazada para Fase 7)**.
