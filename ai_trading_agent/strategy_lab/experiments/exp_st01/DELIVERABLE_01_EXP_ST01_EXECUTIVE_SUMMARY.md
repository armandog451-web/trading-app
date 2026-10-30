# DELIVERABLE 01 — RESUMEN EJECUTIVO DE INVESTIGACIÓN CUANTITATIVA
## EXPERIMENTO EXP-ST01: SuperTrend + EMA 200 (`ST_EMA200_V1`)

**Fecha:** 2026-10-30 17:41:05  
**Estado:** `RESEARCH_ONLY`  
**Estrategia Auditada:** `ST_EMA200_V1` (EMA 200, SuperTrend ATR 10 / Mult 3.0, TP 1.5R, SL SuperTrend line, Causal T->T+1)  
**Supervisor Institucional:** OracleBot v2 / Strategy Laboratory  

---

### 1. HALLAZGOS PRINCIPALES (SÍNTESIS CIENTÍFICA)

1. **Universo Multiactivo y Temporal:** Se ejecutaron con éxito los **50 backtests independientes** (10 ETFs x 5 Temporalidades) sobre datos históricos 100% reales.
2. **Dependencia Temporal Severa:**
   - En **temporalidades macro (D1 y H1)**, la estrategia muestra un comportamiento tendencial consistente en índices de baja rotación y activos refugio (`GLD_H1` PF 1.42, Net PnL +$4,449.16; `DIA_H1` PF 1.51, Net PnL +$3,340.18; `DIA_D1` PF 2.31, Net PnL +$2,470.98; `QQQ_D1` PF 1.85, Net PnL +$2,179.44).
   - En **temporalidades micro (M15 y M30)**, la estrategia experimenta degradación severa por ruido de mercado y costes de fricción (`SPY_M15` PF 0.42, -$1,499.70; `EFA_M15` PF 0.33, -$2,192.64).
3. **Dependencia Sectorial / Régimen:**
   - Sectores en fuerte tendencia de ciclo (`GLD`, `DIA`, `QQQ`) generan ventaja económica sostenible.
   - Sectores con alta reversión a la media, choque de tipos o volatilidad de materias primas sin tendencia unidireccional limpia (`XLE_H1` PF 0.60; `TLT_H1` PF 0.83; `XLF_H1` PF 0.83) sufren pérdidas persistentes.
4. **Veredicto de Scores Cuantitativos (Activo Insignia GLD_H1):**
   - **Economic Edge Score (EES):** 43.55/100
   - **Pure Robustness Score (PRS):** 90.31/100
   - **Strategy Quality Score (SQS):** 69.02/100
   - **Minimum Evidence Gate:** APROBADO
