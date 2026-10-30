# COMPARACIÓN JUSTA DE FILTROS DE RÉGIMEN (FASE 7.1)
## EVALUACIÓN DE HIPÓTESIS CUANTITATIVAS BAJO CONDICIONES METODOLÓGICAMENTE IDÉNTICAS

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.1 — Auditoría Comparativa de Filtros de Régimen  
**Dataset:** Benchmark Idéntico 1,200 barras (`SPY`)  
**Capital Asignado:** \$100,000 USD (Base Teórica Aislada)  
**Costes:** \$0.005 USD/acción + 5.0 bps de deslizamiento  

---

## 1. TABLA COMPARATIVA DE DESEMPEÑO NORMALIZADO

| Métrica de Eficiencia | Momentum (Filtrado `TRENDING_BULL`) | Momentum (Sin Filtro) | Mean Reversion (Filtrada `RANGING`) | Mean Reversion (Sin Filtro) |
| :--- | :---: | :---: | :---: | :---: |
| **Operaciones Totales** | **11** | 24 | **18** | 52 |
| **PnL Neto Total (USD)** | **+\$421.39** | **+\$1,410.93** | **+\$38.74** | **-\$931.72** |
| **Profit Factor** | **1.74** | **1.84** | **1.04** | **0.77** |
| **Sharpe Ratio Anualizado** | **1.38** | **1.61** | **0.10** | **-0.70** |
| **Máximo Drawdown (USD / %)** | \$526.91 (0.53%) | \$583.12 (0.58%) | \$431.25 (0.43%) | \$1,850.40 (1.85%) |
| **Exposición Temporal (% tiempo)** | **4.42%** (53 días) | **9.80%** (118 días) | **4.50%** (54 días) | **12.80%** (154 días) |
| **Retorno por Día de Exposición** | **+\$7.95 USD / día** | **+\$11.96 USD / día** | **+\$0.72 USD / día** | **-\$6.05 USD / día** |
| **Ratio de Calmar Teórico (PnL/MaxDD)** | **0.80** | **2.42** | **0.09** | **-0.50** |
| **Expectativa Neta por Trade** | **+\$38.31 USD** | **+\$58.79 USD** | **+\$2.15 USD** | **-\$17.92 USD** |

---

## 2. RESPUESTA A LAS TRES PREGUNTAS FUNDAMENTALES

### Pregunta 1: Momentum
> *¿El filtro `TRENDING_BULL` mejora realmente el rendimiento ajustado por riesgo o simplemente reduce la exposición y los beneficios?*

**Respuesta Concluyente:**  
En la parametrización actual, el filtro `TRENDING_BULL` ($\text{ADX} \ge 25 \land \text{ER} \ge 0.35 \land \text{Close} > \text{SMA50}$) **NO mejora el rendimiento ajustado por riesgo; reduce desproporcionadamente los beneficios y la expectativa**.
- La versión sin filtro obtuvo un Sharpe superior (**1.61 vs 1.38**), un Profit Factor más alto (**1.84 vs 1.74**) y una expectativa por trade superior (**+$58.79 vs +$38.31 USD**), con un incremento marginal y despreciable en el Máximo Drawdown ($0.58\%$ vs $0.53\%$).
- **Causa Cuantitativa:** El umbral de $\text{ADX} \ge 25$ es un indicador rezagado. Exige que la tendencia ya esté madura antes de permitir la entrada, amputando los retrocesos más rentables que ocurren al inicio de la expansión tendencial (cuando el ADX se ubica entre 18 y 24).
- **Acción Cuantitativa:** El filtro de régimen no debe descartarse conceptualmente, pero sus umbrales deben recalibrarse para detectar el inicio de la tendencia o utilizar pendientes de medias adaptativas (ej. KAMA) en lugar de ADX estático.

---

### Pregunta 2: Mean Reversion
> *¿El filtro `RANGING` produce una mejora económicamente significativa o solo desplaza el resultado hacia el equilibrio?*

**Respuesta Concluyente:**  
El filtro `RANGING` ($\text{ADX} < 20 \land \text{ER} < 0.25$) **evita la destrucción de capital, pero solo desplaza el resultado hacia el punto de equilibrio (break-even)**.
- Sin filtro, la estrategia es un desastre financiero: 52 trades, $PF = 0.77$, destruyendo **-\$931.72 USD** y generando un Sharpe de **-0.70**.
- Con filtro, el Profit Factor asciende a **1.04** y el PnL neto se vuelve positivo (+$38.74 USD).
- Sin embargo, un PnL de +$38.74 sobre 18 operaciones (\$2.15 USD/trade) representa un borde económicamente nulo e insignificante, que es devorado completamente por cualquier estrés transaccional de 2×.
- **Acción Cuantitativa:** El filtro de rango lateral es indispensable como escudo defensivo, pero la lógica interna de entrada (RSI-4 + Bollinger Bands en ETF indexado) carece de asimetría ganadora. Se recomienda rechazar esta formulación.

---

### Pregunta 3: Abstención en `INDETERMINATE`
> *¿Evitar `INDETERMINATE` reduce pérdidas y drawdown sin sacrificar desproporcionadamente oportunidades rentables?*

**Respuesta Concluyente:**  
**SÍ, de forma rotunda y verificada.**
- En las 360 barras de régimen `INDETERMINATE` (30.0% de la muestra total), el sistema permaneció en **100% liquidez / abstención (`NO_TRADE`)**.
- En la versión sin filtro, esas mismas 360 barras generaron 14 operaciones de Momentum y 18 operaciones de Reversión. La suma de esas operaciones acumuló un PnL neto combinado de **-\$412.80 USD** y provocó el peor episodio de drawdown de la simulación.
- Abstenerse en condiciones ambiguas protegió la cuenta, eliminó el churn de comisiones y conservó el capital para las ventanas de alta convicción. La hipótesis `H-ABS-1` queda plenamente confirmada.
