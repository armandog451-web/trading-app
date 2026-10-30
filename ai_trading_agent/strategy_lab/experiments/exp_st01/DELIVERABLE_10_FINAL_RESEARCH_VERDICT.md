# INFORME DE INVESTIGACIÓN CUANTITATIVA
## EXPERIMENTO EXP-ST01 — SUPERTREND + EMA 200 (`ST_EMA200_V1`)

**Fecha:** 2026-10-30 17:41:05  
**Entorno:** Strategy Laboratory (`RESEARCH_ONLY`)  
**Estrategia:** `ST_EMA200_V1`  
**Supervisión 24/7:** OracleBot  

---

### 1. DATOS GENERALES DEL EXPERIMENTO

- **ID de Estrategia:** `ST_EMA200_V1`
- **Familia:** Trend Following (Filtro Macro EMA 200 + Disparador de Volatilidad SuperTrend)
- **Activos Analizados:** 10 ETFs (`SPY`, `QQQ`, `IWM`, `DIA`, `XLK`, `XLF`, `XLE`, `GLD`, `TLT`, `EFA`)
- **Temporalidades:** 5 (`M15`, `M30`, `H1`, `H4`, `D1`)
- **Total de Backtests:** 50
- **Total de Trades Evaluados:** 1072

---

### 2. RESULTADOS DE LA CAMPAÑA DE 50 BACKTESTS

- **Combinaciones Válidas con Muestra Suficiente:** 25 / 50
- **Combinaciones con PnL Neto Positivo:** 15 (60.0%)
- **Combinaciones con PnL Neto Negativo:** 10 (40.0%)

#### Top 5 Configuraciones Líderes
1. **GLD_H1:** 75 trades | WinRate 50.7% | Net PnL +$4,449.16 | PF 1.42 | Sharpe 1.20 | DD 1.83%
2. **DIA_H1:** 50 trades | WinRate 52.0% | Net PnL +$3,340.18 | PF 1.51 | Sharpe 1.44 | DD 1.28%
3. **DIA_D1:** 20 trades | WinRate 60.0% | Net PnL +$2,470.98 | PF 2.31 | Sharpe 1.87 | DD 0.81%
4. **QQQ_D1:** 24 trades | WinRate 54.2% | Net PnL +$2,179.44 | PF 1.85 | Sharpe 1.49 | DD 1.09%
5. **XLK_H1:** 43 trades | WinRate 48.8% | Net PnL +$1,986.54 | PF 1.34 | Sharpe 0.92 | DD 1.62%

#### Peores Configuraciones (Rechazo por Fricción / Whipsaws)
1. **XLE_H1:** 46 trades | WinRate 30.4% | Net PnL -$3,502.53 | PF 0.60 | Sharpe -1.69
2. **EFA_M15:** 15 trades | WinRate 20.0% | Net PnL -$2,192.64 | PF 0.33 | Sharpe -2.19
3. **TLT_H1:** 61 trades | WinRate 41.0% | Net PnL -$1,874.14 | PF 0.83 | Sharpe -0.64
4. **SPY_M15:** 12 trades | WinRate 25.0% | Net PnL -$1,499.70 | PF 0.42 | Sharpe -1.52
5. **XLF_H1:** 50 trades | WinRate 36.0% | Net PnL -$1,376.62 | PF 0.83 | Sharpe -0.63

---

### 3. ROBUSTEZ Y ESTADÍSTICA DEL ACTIVO LÍDER (`GLD_H1`)

- **Economic Edge Score (EES):** 43.55 / 100
- **Pure Robustness Score (PRS):** 90.31 / 100
- **Strategy Quality Score (SQS):** 69.02 / 100
- **Monte Carlo Bootstrap P(E > 0):** 92.0%
- **Resiliencia a Costes (1x a 3x):** PnL 1x = $4449.16 | PnL 2x = $3182.05 | PnL 3x = $830.25
- **Minimum Evidence Gate:** SUPERADO

---

### 4. EVALUACIÓN DE HIPÓTESIS DE DESCUBRIMIENTO (H1 A H5)

- **H1 (Regime ADX > 25):** RECHAZADA — $\Delta$PF: -0.06, $\Delta$PnL: $-2655.4
- **H2 (RVOL > 1.2x SMA20):** RECHAZADA — $\Delta$PF: -0.02, $\Delta$PnL: $-902.4
- **H3 (ATR Volatility Expansion):** RECHAZADA — $\Delta$PF: +0.06, $\Delta$PnL: $-962.0
- **H4 (Session Timing Core):** RECHAZADA — $\Delta$PF: -0.19, $\Delta$PnL: $-3374.9
- **H5 (Adaptive Trailing Stop):** CONFIRMADA — $\Delta$PF: +0.23, $\Delta$PnL: $+1541.1

---

### 5. CONCLUSIÓN Y RECOMENDACIÓN FINAL

**Veredicto Oficial:** `CONDITIONAL_APPROVAL`

1. **No desplegar de forma indiscriminada:** La estrategia SuperTrend + EMA 200 **no es un 'santo grial' universal** aplicable a cualquier activo o temporalidad. Falla estrepitosamente en temporalidades cortas (M15) y en sectores cíclicos/reversivos (XLE, TLT).
2. **Ventaja Confirmada en Clases de Activos Tendenciales:** En oro (`GLD_H1`) e índices de empresas maduras (`DIA_H1`, `DIA_D1`, `QQQ_D1`), la estrategia demuestra una ventaja económica estadística clara (PF 1.42 a 2.31) que sobrevive a costes 2x y 3x.
3. **Paso Siguiente Recomendado:** Preservar `ST_EMA200_V1` en el catálogo de investigación como candidata especializada para portafolios multiactivo condicionados por régimen macro, **sin alterar la operación Paper activa de D21**.
