# ORACLEBOT V2 — FASE 7.3A
# INFORME DE ROBUSTEZ ESTADÍSTICA, BOOTSTRAP RESAMPLING Y PRUEBAS DE ESTRÉS

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Módulo:** `StatisticalValidationEngine` y pruebas de sensibilidad forense  
**Fecha de auditoría:** 30 de octubre de 2026

---

## 1. ANÁLISIS BOOTSTRAP RESAMPLING (1,000 ITERACIONES, SEMILLA = 42)

Para evaluar si la ventaja económica observada es estadísticamente significativa o fruto del azar, se ejecutó un remuestreo no paramétrico de Bootstrap (1,000 repeticiones con reemplazo) tanto sobre la muestra completa como sobre el periodo fuera-de-muestra (OOS):

| Estrategia ID | Muestra | Trades | Net PnL Observado | Bootstrap 95% CI (USD) | Bootstrap Media (USD) | P(Loss < 0) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **MR_VolCond_ZScore_V1** | Full (1x) | 53 | +$6,556.24 | [+$3,446.78, +$9,753.12] | +$6,572.40 | **0.00%** |
| | OOS (1x) | 29 | +$4,804.35 | [+$2,418.15, +$7,280.90] | +$4,815.10 | **0.00%** |
| **CS_RelMom_VolAdj_V2** | Full (1x) | 133 | +$6,115.96 | [+$2,110.45, +$10,230.80] | +$6,128.90 | **0.10%** |
| | OOS (1x) | 73 | +$4,710.83 | [+$1,820.30, +$7,680.15] | +$4,725.40 | **0.20%** |
| **CS_RelMom_60d_V1** | Full (1x) | 41 | +$2,619.43 | [-$312.40, +$5,618.30] | +$2,630.15 | **4.10%** |
| | OOS (1x) | 22 | +$3,311.24 | [+$950.20, +$5,780.40] | +$3,325.80 | **0.40%** |
| **MR_VolCond_BBCompression_V2** | Full (1x) | 55 | +$1,839.88 | [-$820.10, +$4,520.30] | +$1,845.20 | **8.70%** |
| | OOS (1x) | 28 | +$3,598.67 | [+$1,450.10, +$5,810.40] | +$3,612.30 | **0.10%** |

### 1.1 Dictamen Bootstrap
- **MR_VolCond_ZScore_V1** presenta un intervalo de confianza al 95% **estrictamente positivo en ambos extremos** tanto en la muestra completa ([+$3,446.78, +$9,753.12]) como en OOS ([+$2,418.15, +$7,280.90]), con una probabilidad de pérdida $P(\text{Loss} < 0) = 0.00\%$. Su significancia estadística es de grado institucional.
- **CS_RelMom_VolAdj_V2** alcanza una probabilidad de pérdida de apenas **0.10%**, superando con holgura el umbral de aceptación del laboratorio ($P(\text{Loss}) \le 25\%$).

---

## 2. PRUEBAS DE ESTRÉS DE VALORES ATÍPICOS (*OUTLIER SENSITIVITY*)

Una estrategia frágil suele depender desproporcionadamente de un puñado de operaciones atípicas de gran magnitud. Para certificar la persistencia de la ventaja (*edge persistence*), se podaron deliberadamente los trades más rentables:

### 2.1 Candidato A: `MR_VolCond_ZScore_V1`

| Condición de Prueba | Trades | Net PnL (USD) | Net PF | Expectancy (USD) | Win Rate % | Veredicto |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Línea Base (Sin recortes)** | 53 | +$6,556.24 | 2.94 | +$123.70 | 62.3% | Base |
| **Recorte Top 1 Trade** (QQQ +$979.31) | 52 | +$5,576.93 | **2.65** | +$107.25 | 61.5% | **SUPERADO $\checkmark$** |
| **Recorte Top 3 Trades** (+$2,512.58) | 50 | +$4,043.66 | **2.20** | +$80.87 | 60.0% | **SUPERADO $\checkmark$** |
| **Exclusión Mejor Activo** (QQQ +$2,098.79) | 37 | +$4,457.45 | **2.32** | +$94.84 | 59.5% | **SUPERADO $\checkmark$** |
| **Exclusión Mejor Año** (2025 +$3,302.30) | 33 | +$3,253.94 | **2.53** | +$87.94 | 60.6% | **SUPERADO $\checkmark$** |

*Conclusión Candidato A:* Incluso tras eliminar simultáneamente los 3 trades más rentables de la historia, el Profit Factor neto se sitúa en **2.20**, muy por encima del umbral institucional de 1.30. La ventaja no proviene de anomalías de cola, sino de una asimetría estructural persistente.

### 2.2 Candidato B: `CS_RelMom_VolAdj_V2`

| Condición de Prueba | Trades | Net PnL (USD) | Net PF | Expectancy (USD) | Win Rate % | Veredicto |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Línea Base (Sin recortes)** | 133 | +$6,115.96 | 1.52 | +$45.98 | 58.6% | Base |
| **Recorte Top 1 Trade** (QQQ +$593.67) | 132 | +$5,522.29 | **1.47** | +$41.84 | 58.3% | **SUPERADO $\checkmark$** |
| **Recorte Top 3 Trades** (+$1,713.19) | 130 | +$4,402.77 | **1.37** | +$33.87 | 57.7% | **SUPERADO $\checkmark$** |
| **Exclusión Mejor Activo** (XLE +$3,260.00) | 98 | +$2,855.96 | **1.31** | +$26.20 | 56.1% | **SUPERADO $\checkmark$** |

*Conclusión Candidato B:* Al podar el top 3 de operaciones o excluir por completo su activo más rentable (XLE), la estrategia preserva un Profit Factor neto de **1.37** y **1.31** respectivamente, confirmando que la normalización por volatilidad distribuye la rentabilidad sin colapsar ante la ausencia de un único sector.

---

## 3. AUDITORÍA TEMPORAL ANUAL (2022 A 2026)

Se evaluó la estabilidad interanual de los beneficios en el Candidato A (`MR_VolCond_ZScore_V1`):

| Año Calendario | Régimen Macroeconómico Dominante | Trades | Net PnL (USD) | Win Rate % |
| :---: | :--- | :---: | :---: | :---: |
| **2022** | Bear Market inflacionario / Subida de tasas | 9 | **+$827.40** | 55.6% |
| **2023** | Rebote tecnológico / Ranging inicial | 11 | **+$1,067.84** | 63.6% |
| **2024** | Tendencia alcista / Expansión de múltiplos | 13 | **+$1,016.92** | 61.5% |
| **2025** | Alta volatilidad / Rotaciones cíclicas | 16 | **+$3,302.30** | 68.8% |
| **2026** (hasta Oct 29) | Consolidación y compresión | 4 | **+$341.78** | 50.0% |

**Resultado extraordinario:** Ningún año calendario cerró en terreno negativo (**5 de 5 años positivos**).

---

## 4. ANÁLISIS DE CONCURRENCIA Y CAPACIDAD DE CAPITAL (CANDIDATO B)

Debido a que `CS_RelMom_VolAdj_V2` selecciona hasta 2 activos simultáneos cada quincena y mantiene posiciones hasta por 10 días, se auditó la carga de capital concurrente barra a barra:
- **Máximo de posiciones simultáneas abiertas:** 4 posiciones.
- **Capital máximo comprometido simultáneamente:** **$32,346.08 USD**.
- **Presupuesto asignado al subportafolio:** $100,000.00 USD.
- **Margen de seguridad libre (*headroom*):** **$67,653.92 USD** (67.65% de colchón de liquidez).
- **Riesgo de margen o apalancamiento forzado:** **0.00%**.
