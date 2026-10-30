# ORACLEBOT V2 — FASE 7.3A
# AUDITORÍA DE FUGA TEMPORAL, ANÁLISIS WALK-FORWARD (IS VS OOS) Y CONDICIÓN EPISTEMOLÓGICA

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Módulo auditado:** Protocolo de partición temporal y motores de señal  
**Fecha de auditoría:** 30 de octubre de 2026

---

## 1. PROTOCOLO TEMPORAL WALK-FORWARD (TRAIN / TEST)

El Strategy Discovery Engine v2 aplica una división cronológica estricta al 50% de las 1,199 barras cerradas:

- **Conjunto In-Sample (Train / IS):** Barras 0 a 599 (2022-01-20 a 2024-06-10). Cubre el ciclo bajista de 2022 y la fase inicial de recuperación de 2023–2024.
- **Conjunto Out-of-Sample (Test / OOS):** Barras 600 a 1,199 (2024-06-11 a 2026-10-29). Cubre la expansión alcista madura, el régimen de compresión y la volatilidad de 2025–2026.

---

## 2. RESULTADOS WALK-FORWARD: IN-SAMPLE VS OUT-OF-SAMPLE (1X BASE)

| Estrategia ID | Muestra IS (Trades) | Net PnL IS | Net PF IS | Muestra OOS (Trades) | Net PnL OOS | Net PF OOS | OOS Expectancy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **MR_VolCond_ZScore_V1** | 24 | +$1,751.89 | 2.12 | 29 | **+$4,804.35** | **3.88** | +$165.67 |
| **CS_RelMom_VolAdj_V2** | 60 | +$1,405.13 | 1.25 | 73 | **+$4,710.83** | **1.74** | +$64.53 |
| **CS_RelMom_60d_V1** | 19 | -$691.81 | 0.77 | 22 | **+$3,311.24** | **2.21** | +$150.51 |
| **MR_VolCond_BBCompression_V2** | 27 | -$1,758.79 | 0.44 | 28 | **+$3,598.67** | **3.26** | +$128.52 |

### 2.1 Análisis de Generalización OOS
- **MR_VolCond_ZScore_V1** exhibe una robustez superior: es consistentemente rentable tanto In-Sample (+$1,751.89, PF 2.12) como Out-of-Sample (+$4,804.35, PF 3.88). No muestra indicios de sobreajuste local a un único ciclo de mercado.
- **CS_RelMom_VolAdj_V2** es igualmente rentable en ambos subperiodos (IS +$1,405.13 vs OOS +$4,710.83), demostrando que la normalización por volatilidad mitiga los drawdowns provocados por rotaciones bruscas de sectores.
- Las dos estrategias secundarias (`CS_RelMom_60d_V1` y `MR_VolCond_BBCompression_V2`) experimentaron dificultades en el mercado bajista de 2022 (IS negativo), compensándolo ampliamente en el periodo OOS.

---

## 3. AUDITORÍA FORENSE DE FUGA TEMPORAL (*NO-LOOKAHEAD BIAS*)

Se auditó línea por línea la computación de cada indicador técnico en [`discovery_engine_v2.py`](file:///C:/Users/edsel/Documents/trading-app-repo/ai_trading_agent/strategy_lab/discovery/discovery_engine_v2.py):
1. **Z-Score(20):** Calculado estrictamente con las 20 barras precedentes `closes[i-20:i]`. Ningún valor posterior a la barra $i$ interviene en la media ni en la desviación estándar.
2. **Ratio de Expansión de ATR:** Utiliza `tr[j] = max(highs[j] - lows[j], abs(highs[j] - closes[j-1]), abs(lows[j] - closes[j-1]))`, donde el cierre previo $j-1$ es estrictamente causal.
3. **Filtros de Tendencia (SMA 120) y Momentum (60d):** Calculados exclusivamente sobre ventanas retrospectivas $i - 120$ e $i - 60$.
4. **Ejecución y Desfase Causal:** La decisión se toma tras el cierre de la barra $i$ y la entrada se simula al precio de cierre $i$ (o apertura $i+1$) incorporando el spread y slippage correspondientes.

---

## 4. DECLARACIÓN EPISTEMOLÓGICA OBLIGATORIA

> [!CAUTION]
> **CLASIFICACIÓN DE DATOS Y LÍMITES DE INFERENCIA:**  
> A pesar de que la partición temporal separa cronológicamente el Train del Test, todo el corpus histórico (2022–2026) ha sido objeto de estudio previo en iteraciones de investigación pasadas (`PREVIOUSLY_EXAMINED_HISTORICAL_DATA`).  
> 
> En términos epistemológicos formales:  
> - El desempeño Out-of-Sample aquí verificado constituye una **validación estadística cruzada retrospectiva**, pero **NO sustituye a una prueba prospectiva real** (*Forward Walk-Forward*).  
> - Por tanto, se declara formalmente **`INSUFFICIENT_INDEPENDENT_EVIDENCE`** para autorizar trading con capital operativo o activar las estrategias en el broker.  
> - Las hipótesis se autorizan únicamente para avanzar en la taxonomía del laboratorio cuantitativo.
