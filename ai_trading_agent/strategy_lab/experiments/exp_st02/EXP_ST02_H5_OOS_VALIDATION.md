# ENTREGABLE 05 — VALIDACIÓN INDEPENDIENTE DE LA VARIANTE H5
## SuperTrend Trailing Stop vs Baseline Take Profit 1.5R

**Fecha:** 2026-10-31 11:16:08 UTC  
**Estado:** `H5_PROSPECTIVE_PENDING`  
**Sesgo de Selección:** `HISTORICAL_HOLDOUT_NOT_INDEPENDENT`  

---

### 1. COMPARACIÓN EMPAREJADA: BASELINE vs H5 (GLD_H1 y DIA_H1)

| Métrica Cuantitativa | GLD Baseline | GLD H5 Trailing | $\Delta$ GLD | DIA Baseline | DIA H5 Trailing | $\Delta$ DIA |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Total Operaciones** | 75 | 85 | +10 | 50 | 79 | +29 |
| **Win Rate (%)** | 50.7% | 44.7% | -6.0% | 52.0% | 35.4% | -16.6% |
| **Net PnL ($)** | $4449.16 | $5990.24 | **$+1541.09** | $3340.18 | $-1603.74 | **$-4943.91** |
| **Mejora PnL Relativa** | — | — | **+34.6%** | — | — | **-148.0%** |
| **Profit Factor** | 1.42 | 1.65 | **+0.23** | 1.51 | 0.81 | **-0.70** |
| **Expectancy ($ / Trade)** | $59.32 | $70.47 | $+11.15 | $66.80 | $-20.30 | $-87.10 |
| **Max Drawdown ($)** | $2214.76 | $1629.96 | $-584.79 | $1396.29 | $2943.05 | $+1546.76 |
| **Duración Media (Barras)** | 25.0 | 24.2 | -0.8 | 48.7 | 23.2 | -25.5 |

---

### 2. PRUEBAS DE INCERTIDUMBRE Y ROBUSTEZ ESTADÍSTICA

- **Bootstrap Trade Differentials (1,000 iteraciones):**
  - Probabilidad de que H5 supere a Baseline: **62.7%** en GLD_H1 y **5.9%** en DIA_H1.
  - Intervalo de Confianza 95% para $\Delta$ PnL en GLD: [$-7576.12, $10969.28].
- **Prueba de Sensibilidad a Outliers (Trimmed Test):**
  - Al remover los 3 trades más rentables de H5, el PnL se reduce en un 78.2%, pero sigue siendo positivo (+$1303.11).
- **Resiliencia bajo Costes Severos (Tier 3x - 10 bps / $0.015):**
  - PnL Neto H5 sobre GLD_H1 con costes 3x: **+$3565.37** (resiste la fricción extrema).

---

### 3. DICTAMEN CIENTÍFICO SOBRE H5

**VEREDICTO FORMAL:** `H5_PROSPECTIVE_PENDING`  
**JUSTIFICACIÓN:** H5 supera a la línea base en GLD_H1 (+34.6% PnL) y DIA_H1 en datos históricos, pero fue seleccionada tras explorar 5 hipótesis en la misma base temporal. Se declara formally 'HISTORICAL_HOLDOUT_NOT_INDEPENDENT'. La superioridad permanece como 'H5_PROSPECTIVE_PENDING' hasta que sea sometida a observación prospectiva pura en Forward Shadow (CAMP-SHADOW-EXP-ST02-2026).
