# ORACLEBOT V2 — FASE 7.2: INFORME DE ESTRÉS DE COSTES DE TRANSACCIÓN
## EVALUACIÓN DE FRICCIONES INSTITUCIONALES (1X, 2X, 3X), DESLIZAMIENTO Y COST DRAG

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.2 — Validación Cuantitativa Multiactivo  
**Fecha:** 30 de octubre de 2026  
**Objetivo:** Determinar la resiliencia económica de las estrategias experimentales frente a fricciones de mercado crecientes.

---

## 1. PARÁMETROS DE LOS ESCENARIOS DE ESTRÉS

Para evitar el sesgo de modelado en backtests con costes subestimados, se definieron tres niveles de fricción institucional:

1. **Escenario 1x (Base / Broker Institucional Prime):**
   - Comisión por acción: **$0.005 USD**.
   - Deslizamiento (Slippage): **5.0 puntos básicos (bps)** (0.05% sobre el precio de ejecución).
   - Representa condiciones óptimas de ejecución en ETFs altamente líquidos durante horario regular de mercado.

2. **Escenario 2x (Moderado / Condiciones Normales con Menor Liquidez):**
   - Comisión por acción: **$0.010 USD**.
   - Deslizamiento: **10.0 bps** (0.10%).
   - Simula ensanchamiento de horquillas (*bid-ask spreads*) en aperturas, cierres o volatilidad intradiaria elevada.

3. **Escenario 3x (Extremo / Estrés de Mercado / Peor Caso Operativo):**
   - Comisión por acción: **$0.015 USD**.
   - Deslizamiento: **15.0 bps** (0.15%).
   - Simula condiciones de alta tensión de liquidez o ejecución subóptima.

---

## 2. RESULTADOS DE ESTRÉS PARA MEAN REVERSION (`MR_RsiBollinger_V1`)

### Modo Canónico Filtrado (`RANGING`) — 102 Operaciones

| Escenario | True Gross PnL | Deslizamiento | Comisiones | Total Costes | True Net PnL | Net PF | Cost Drag % | Veredicto Económico |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1x Base** | +$1,867.38 | $706.65 | $594.40 | $1,301.05 | **+$566.33** | **1.06** | **69.67%** | Marginalmente positivo |
| **2x Moderado** | +$1,867.38 | $1,413.30 | $1,188.76 | $2,602.06 | **-$734.68** | **0.93** | **139.34%** | **DEFICITARIO (Quiebra de margen)** |
| **3x Extremo** | +$1,918.76 | $2,120.08 | $1,783.09 | $3,903.17 | **-$1,984.41** | **0.81** | **203.42%** | **COLAPSO SEVERO** |

```
Curva de Degradación Net PnL (Mean Reversion Filtrada):
Net PnL ($)
  +$600 ───● (1x: +$566.33)
    $0 ─────\──────────────────────────────────────
  -$600      \─────● (2x: -$734.68)
-$1,200             \
-$1,800              \─────● (3x: -$1,984.41)
-$2,400 ───────────────────────────────────────────
             1x           2x           3x
```

### Hallazgos de Mean Reversion
- En el escenario 1x, los costes absorben el **69.67%** de las ganancias brutas.
- Con solo un incremento moderado a 2x, la estrategia entra en terreno negativo (-$734.68), demostrando un **margen de seguridad nulo**.
- En 3x, los costes duplican las ganancias brutas (Cost Drag del 203.4%).

---

## 3. RESULTADOS DE ESTRÉS PARA MOMENTUM (`MOM_TrendPullback_V1`)

### Modo Canónico Filtrado (`TRENDING_BULL`) — 9 Operaciones

| Escenario | True Gross PnL | Deslizamiento | Comisiones | Total Costes | True Net PnL | Net PF | Veredicto Económico |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1x Base** | -$20.78 | $60.05 | $49.66 | $109.71 | **-$130.49** | **0.84** | **DEFICITARIO** |
| **2x Moderado** | -$20.78 | $120.10 | $99.32 | $219.42 | **-$240.17** | **0.72** | **DEFICITARIO** |
| **3x Extremo** | -$20.78 | $180.15 | $148.98 | $329.13 | **-$349.89** | **0.61** | **DEFICITARIO** |

### Hallazgos de Momentum
- La estrategia es deficitaria en términos brutos (-$20.78), por lo que cualquier adición de costes amplifica linealmente las pérdidas.
- En 3x, las pérdidas netas alcanzan -$349.89 para solo 9 operaciones realizadas.

---

## 4. ESTRÉS EN LOS MODOS NO FILTRADOS (`UNFILTERED`)

Para completar la auditoría, se examinó la resistencia al estrés de las estrategias en ausencia de filtro de régimen:

### Mean Reversion Sin Filtro (267 Operaciones)
- **1x Base:** Gross +$6,474.68 | Costes $3,366.74 | **Net +$3,107.94** | Net PF 1.12 | Drag 52.00%
- **2x Moderado:** Gross +$6,691.04 | Costes $6,758.63 | **Net -$67.59** | Net PF 1.00 | Drag 101.01%
- **3x Extremo:** Gross +$6,469.08 | Costes $10,138.00 | **Net -$3,668.92** | Net PF 0.88 | Drag 156.71%

### Momentum Sin Filtro (187 Operaciones)
- **1x Base:** Gross +$6,067.89 | Costes $2,394.64 | **Net +$3,673.25** | Net PF 1.20 | Drag 39.46%
- **2x Moderado:** Gross +$6,245.61 | Costes $4,789.45 | **Net +$1,456.16** | Net PF 1.08 | Drag 76.69%
- **3x Extremo:** Gross +$6,330.21 | Costes $7,221.85 | **Net -$891.64** | Net PF 0.96 | Drag 114.09%

---

## 5. CONCLUSIÓN GENERAL DEL TEST DE ESTRÉS

Ambas estrategias presentan una **alta sensibilidad destructiva a las fricciones operativas**. Ninguna de las configuraciones canónicas evaluadas sobrevive a un régimen de costes moderado (2x), lo que confirma que las señales analizadas no poseen suficiente robustez para operar con capital real en el mercado bursátil.
