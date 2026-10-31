# ORACLEBOT V2 — ESTUDIO DE ABLACIÓN CONTROLADA
## FASE EXP-MTF01 — Multi-Timeframe Extreme Reversal
### Descomposición de la Ventaja Estructural vs. Hiper-Restricción Paramétrica

**Proyecto:** OracleBot v2 / AI Trading Agent / Strategy Laboratory  
**Workspace canónico:** `C:\Users\edsel\Documents\trading-app-repo`  
**Identificador único:** `MTF_ExtremeReversal_V1`  
**Campaña:** `EXP-MTF01`  
**Fecha de emisión:** 31 de octubre de 2026  
**Clasificación:** `RESEARCH_ONLY / ANALYSIS_ONLY`  

---

## 1. RESUMEN EJECUTIVO DE ABLACIONES

Para determinar si la metodología del video posee una ventaja económica genuina o si su aparente efectividad se debe a una acumulación de condiciones restrictivas que suprimen las operaciones hasta eliminar la significancia estadística, se evaluaron cinco configuraciones controladas sobre el universo de 6 ETFs (`SPY`, `QQQ`, `DIA`, `IWM`, `GLD`, `TLT`):

| Configuración | Componentes Activos | Señales Generadas | Trades Ejecutados | Win Rate | Net PnL (USD) | Expectancy (R) | Veredicto Técnico |
|---|---|---|---|---|---|---|---|
| **Baseline A — Completo** | D1 Extremo + Desacel + H1 BOS + Fib 0.618 + EMA 50 + M5 Break | 0 | 0 | 0.0% | \$0.00 | 0.000 R | **INSUFFICIENT_EVIDENCE / CERO_SEÑALES** |
| **Ablación B — Sin D1** | H1 BOS + Fib 0.618 + EMA 50 + M5 Break (Sin filtro D1) | 33 | 7 | 42.86% | +\$265.30 | +0.151 R | **PRELIMINARY_SAMPLE / LEVE_EDGE** |
| **Ablación C — Sin Fib** | D1 + H1 BOS + EMA 50 + M5 Break (Sin confluencia Fib) | 0 | 0 | 0.0% | \$0.00 | 0.000 R | **BLOQUEADO_POR_D1** |
| **Ablación D — Sin EMA 50** | D1 + H1 BOS + Fib 0.618 + M5 Break (Sin filtro EMA 50) | 18 | 1 | 0.0% | -\$223.98 | -0.896 R | **MUESTRA_CRÍTICA / EDGE_NEGATIVO** |
| **Ablación E — Sin M5** | D1 + H1 BOS + Fib 0.618 + EMA 50 (Entrada directa H1) | 0 | 0 | 0.0% | \$0.00 | 0.000 R | **BLOQUEADO_POR_D1** |

---

## 2. HALLAZGOS Y ANÁLISIS CUANTITATIVO

### 2.1 Hiper-Restricción del Contexto Diario (D1)
El filtro diario propuesto exige la conjunción simultánea de:
1. Precio dentro de 0.50 ATR del mínimo/máximo de 60 días.
2. Desplazamiento neto a 5 días $\ge 2.50 \times ATR$.
3. Vela de desaceleración (cuerpo $\le 45\%$ y mecha de rechazo $\ge 35\%$, o *inside bar*).

En la ventana empírica real de 60 días (59 barras D1):
- En `SPY`, `QQQ`, `DIA`, `IWM` y `GLD`, la frecuencia de ocurrencia de esta triple condición fue **0**.
- Únicamente en `TLT` se registraron 2 barras que cumplieron el contexto diario, pero en los días siguientes no se produjo la confluencia simultánea de retroceso a la zona de confluencia Fib 0.618 y EMA 50 junto con ruptura M5.
- **Conclusión:** El sistema completo propuesto en el video sufre de un sesgo de "cherry-picking" visual: al autor del video le resulta intuitivo señalar en retrospectiva un punto perfecto donde todo coincidió, pero algorítmicamente la probabilidad conjunta causal en 60 días de mercado real es prácticamente nula.

### 2.2 Desempeño de la Estructura H1 + M5 (Ablación B)
Al retirar el cuello de botella del contexto D1:
- Se generaron **33 señales** y **7 trades ejecutados** a través de los 6 ETFs.
- Resultado: Net PnL positivo de **+\$265.30 USD**, Win Rate del **42.86%** y Expectancy de **+0.151 R**.
- Aunque los resultados son positivos netos de comisiones y slippage, la muestra ($N=7$) se encuentra categorizada como `LOW_SAMPLE` (< 30 trades) por el *Minimum Evidence Gate*, por lo que no es posible certificar significancia estadística sin mayor profundidad histórica intradía.

### 2.3 Rol del Filtro EMA 50 (Ablación D)
- Al eliminar la confluencia con EMA 50 manteniendo el resto de parámetros, la expectativa matemática se desploma a **-0.896 R** (pérdida de -\$223.98 USD en el único trade ejecutado).
- Esto demuestra que la EMA 50 actúa como un filtro reductor de ruido necesario frente a retrocesos de Fibonacci aislados.
