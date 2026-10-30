# INFORME DE DESEMPEÑO CORREGIDO Y AUDITORÍA FORENSE (FASE 7.1A)
## RECALCULACIÓN CONTABLE, CALENDARIO BURSÁTIL Y CLASIFICACIÓN DE EVIDENCIA

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.1A — Auditoría Forense Correctiva de Datos y Contabilidad  
**Workspace:** `trading-app-repo`  
**Modo:** `RESEARCH / ANALYSIS_ONLY` (Totalmente Aislado / Air-Gapped)  
**Fecha de Emisión:** 30 de Octubre de 2026  
**Estado:** **DICTAMEN REVISADO EMITIDO — CERTIFICACIÓN ECONÓMICA RECTIFICADA**  

---

## 1. DICTAMEN GLOBAL Y RECTIFICACIÓN DE CLASIFICACIÓN

Con base en la auditoría forense de datos, calendario bursátil y contabilidad de costes, se emite la rectificación formal de los resultados de la Fase 7.0 y 7.1:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        MATRIZ DE CLASIFICACIÓN FORENSE RECTIFICADA                     │
├────────────────────────────────┬───────────────────────────────┬───────────────────────┤
│ Estrategia y Dataset           │ Clasificación Anterior (7.1) │ Clasificación Forense │
├────────────────────────────────┼───────────────────────────────┼───────────────────────┤
│ MOMENTUM (Benchmark Sintético) │ `RESEARCH_INCONCLUSIVE`       │ ❌ INVALID            │
│ MEAN REVERSION (Sintético)     │ `RESEARCH_REJECTED`           │ ❌ INVALID            │
│ CARTERA COMBINADA (Sintética)  │ `RESEARCH_INCONCLUSIVE`       │ ❌ INVALID            │
├────────────────────────────────┼───────────────────────────────┼───────────────────────┤
│ MOMENTUM (Mercado Real SPY)    │ No evaluada anteriormente     │ ⚠️ NOT_VERIFIED (N=2) │
│ MEAN REVERSION (Mercado Real)  │ No evaluada anteriormente     │ ⚠️ NOT_VERIFIED (N=22)│
└────────────────────────────────┴───────────────────────────────┴───────────────────────┘
```

### Razones de la Clasificación `INVALID` para el Benchmark Original:
1. **Procedencia de Datos:** Los datos eran 100% sintéticos (GBM estocástico), no cotizaciones reales de NYSE/NASDAQ.
2. **Violación de Calendario:** El **72.4% de las operaciones** (21 de 29) entraron o salieron en sábados, domingos o festivos bursátiles.
3. **Defecto Contable:** Ambigüedad en la presentación de costes brutos y netos, aunque el Net PnL final dedujo costes de forma única.

---

## 2. RECALCULACIÓN CONTABLE SOBRE EL BENCHMARK SINTÉTICO (RECONCILIADA)

A continuación se presenta la tabla con la descomposición contable exacta y matemáticamente cuadrable al céntimo:

| Métrica Contable | `MOM_TrendPullback` (Filtrada) | `MR_RsiBollinger` (Filtrada) | Cartera Sintética Combinada |
| :--- | :---: | :---: | :---: |
| **Operaciones Totales** | 11 trades | 18 trades | 29 trades |
| **Operaciones en Días No Hábiles** | **7 trades (63.6%)** | **14 trades (77.8%)** | **21 trades (72.4%)** |
| **True Gross PnL (Pre-costes)** | **+\$559.55 USD** | **+\$264.77 USD** | **+\$824.32 USD** |
| **(-) Deslizamiento (Slippage)** | **-\$135.14 USD** | **-\$221.21 USD** | **-\$356.35 USD** |
| **(-) Comisiones** | **-\$3.02 USD** | **-\$4.82 USD** | **-\$7.84 USD** |
| **Costes Totales Absorbidos** | **\$138.16 USD** | **\$226.03 USD** | **\$364.19 USD** |
| **(=) True Net PnL Reconciliado** | **+\$421.39 USD** | **+\$38.74 USD** | **+\$460.13 USD** |
| **Gross Profit Factor** | **2.11** | **1.29** | **1.64** |
| **Net Profit Factor** | **1.74** | **1.04** | **1.29** |
| **Cost Drag (% del Bruto)** | **24.69%** | **85.37%** | **44.18%** |
| **Veredicto Institucional** | **`INVALID`** | **`INVALID`** | **`INVALID`** |

---

## 3. EVALUACIÓN PARALELA SOBRE MERCADO REAL AUTÉNTICO (`SPY` 2022-2026)

Para ofrecer evidencia rigurosa sobre datos auténticos de mercado, se ejecutó la evaluación sobre las **1,200 barras diarias reales de `SPY`** (SHA-256: `a2fe260316936f613b655a9ceea06716ca841b7632dd5555d46fbe0f0cc39418`):

| Métrica Cuantitativa | `MOM_TrendPullback_V1` (SPY Real) | `MR_RsiBollinger_V1` (SPY Real) |
| :--- | :---: | :---: |
| **Período Temporal** | 2022-01-20 a 2026-10-30 (1,200 barras) | 2022-01-20 a 2026-10-30 (1,200 barras) |
| **Calendario NYSE** | **100% Válido (0 fines de semana)** | **100% Válido (0 fines de semana)** |
| **Operaciones Totales ($N$)** | **2 trades** | **22 trades** |
| **Win Rate** | 100.0% (2 de 2) | 50.0% (11 de 22) |
| **True Gross PnL** | +\$299.91 USD | +\$1,729.89 USD |
| **(-) Deslizamiento** | -\$24.84 USD | -\$269.29 USD |
| **(-) Comisiones** | -\$0.47 USD | -\$4.89 USD |
| **(=) True Net PnL** | **+\$274.60 USD** | **+\$1,455.71 USD** |
| **Gross Profit Factor** | Undefined (sin pérdidas) | **2.55** |
| **Net Profit Factor** | Undefined (sin pérdidas) | **2.21** |
| **Cost Drag** | 8.44% | 15.85% |
| **Clasificación Institucional** | **`NOT_VERIFIED (INSUFFICIENT_N)`** | **`NOT_VERIFIED (REQUIRES_OOS)`** |

### Análisis de la Serie Real:
1. **Momentum en Mercado Real ($N=2$):** En 4.5 años de datos diarios de `SPY`, la combinación de $\text{ADX} \ge 25 \land \text{ER} \ge 0.35$ con retesteo de EMA(20) solo ocurrió **2 veces**. Aunque ambas fueron rentables, una muestra de 2 operaciones es estadísticamente nula. Demuestra de forma concluyente que las condiciones de entrada son excesivamente restrictivas para un ETF indexado en velas diarias.
2. **Mean Reversion en Mercado Real ($N=22$):** En la serie real de `SPY`, la estrategia generó 22 operaciones, obteniendo un Net PnL de **+\$1,455.71 USD** y un Net Profit Factor de **2.21** con un drag de costes de solo el 15.85%.  
   - **Por qué funcionó en datos reales vs sintéticos:** El mercado real de `SPY` exhibe una reversión a la media estructuralmente más potente en correcciones laterales que la simulación sintética de caminata aleatoria.
   - **Restricción Obligatoria:** A pesar de este resultado positivo, **se clasifica como `NOT_VERIFIED`**. No se puede promover a `PAPER` sin antes validar su estabilidad fuera de muestra (out-of-sample) en otros activos (`QQQ`, `IWM`) y sin optimizar umbrales.

---

## 4. AUDITORÍA DE CONCURRENCIA DE INTERVALOS REALES DE TENENCIA

Se auditaron los intervalos de tenencia cronológicos $[t_{\text{in}}, t_{\text{out}}]$ entre las operaciones de ambas estrategias:
- **En Serie Sintética:** Cero solapamientos (las estrategias operaban en ciclos fijos de 120 días).
- **En Serie Real de `SPY`:** Cero colisiones de posiciones simultáneas. Las 2 operaciones de Momentum ocurrieron en periodos donde el régimen permaneció en `TRENDING_BULL` y Mean Reversion no estuvo activa.
- **Riesgo Agregado:** Se mantuvo en todo momento por debajo del límite de riesgo de 0.25% por posición y cero colisión de margen.

---

## 5. ESTADO INMUTABLE DE D21 Y CIERRE DE MERCADO

- **D21 en PAPER:** `D21_RangeCompress_5d` (fingerprint `f885ec2db2422308`) no ha sufrido ninguna modificación ni interferencia.
- **Capital PAPER:** $1,000,000 USD intacto en Moomoo (`TrdEnv.SIMULATE`).
- **Trading LIVE:** `ENABLE_LIVE_TRADING = False` (físicamente bloqueado).
- **Próxima Evaluación Prospectiva:** Hoy 30 de octubre a las **16:15 ET** (en espera pasiva del cierre de mercado).
- **Estado de Git:** Cero commits, pushes o despliegues remotos ejecutados sin autorización expresa.
