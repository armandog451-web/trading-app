# RESEARCH CAMPAIGN REPORT — FASE 4 (REAL DATA EXPANSION v2)

> **Research Session ID:** `session_fase4_1791143998`  
> **Fecha de Ejecución:** 2026-10-04  
> **Objetivo de Investigación:** *"Find robust intraday momentum and breakout strategies for liquid US ETFs that maintain positive expectancy, controlled drawdown and reasonable stability across symbols and market regimes."*  
> **Aislamiento de Holdout:** `FINAL_HOLDOUT` (20%) se mantuvo **100% BLOQUEADO (LOCKED)**. Ningún experimento accedió a este dataset durante optimización o selección.  
> **Nota de Evidencia Estadística:** *"Evidence level is an internal research classification, not a formal statistical significance test."*

---

## 1. DATA COVERAGE AUDIT & UNIVERSO DE DATOS REALES

Se auditaron 4 ETFs líquidos de EE.UU. utilizando barras intradiarias reales de 15 minutos (60 días de bolsa transcurridos):

| Símbolo | Timeframe | Rango Temporal | Total Barras | Días de Bolsa | Gaps / Faltantes | Estado de Suficiencia |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| `SPY` | 15m | 2026-07-10 a 2026-10-02 | 1560 | 60 | 0 | `SUFFICIENT` (>1,000 barras) |
| `QQQ` | 15m | 2026-07-10 a 2026-10-02 | 1560 | 60 | 0 | `SUFFICIENT` (>1,000 barras) |
| `IWM` | 15m | 2026-07-10 a 2026-10-02 | 1560 | 60 | 0 | `SUFFICIENT` (>1,000 barras) |
| `DIA` | 15m | 2026-07-10 a 2026-10-02 | 1560 | 60 | 0 | `SUFFICIENT` (>1,000 barras) |

- **Total de Barras Reales Procesadas en la Campaña:** 6240 barras intradiarias.

---

## 2. RESUMEN EJECUTIVO Y ASIGNACIÓN EXPLORACIÓN VS EXPLOTACIÓN

- **Experimentos Ejecutados:** 11
- **Hipótesis Generadas:** 11
- **Estrategias Diseñadas:** 11
- **Asignación Exploración vs Explotación:**
  - **Planificado:** 70% Exploración / 30% Explotación
  - **Real Ejecutado:** 8 Exploración (72.7%) / 4 Explotación (27.3%)
  - *Diferencia:* Ajuste por discrepancia de redondeo entero al ejecutar 11 iteraciones.
- **Memoria de Investigación:** 11 observaciones guardadas | 11 patrones de fallo registrados.

---

## 3. DETALLE DE ESTRATEGIAS GENERADAS Y TIPO DE GENERACIÓN

| Strategy ID | Nombre | Tipo de Generación | Template Base | Features Utilizados | Overfitting Risk | Novelty Score |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| `strat_disc_910dc7ba` | Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_80e75100 | `PARAMETER_VARIATION` | DYNAMIC | `ema_cross_9_21, relative_volume_rvol, atr_14` | 60.0 | 100.0 |
| `strat_disc_d8d363a6` | Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_d6992344 | `PARAMETER_VARIATION` | DYNAMIC | `rsi_14, bollinger_band_width, returns_1d` | 60.0 | 100.0 |
| `strat_disc_468202f9` | Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_7e099dd9 | `COMPONENT_COMBINATION` | DYNAMIC | `opening_range_breakout, volume_surge, atr_14` | 60.0 | 86.0 |
| `strat_disc_b7e1bdac` | Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_89500a56 | `COMPONENT_COMBINATION` | DYNAMIC | `market_regime_type, price_vs_vwap` | 60.0 | 100.0 |
| `mut_strat_disc_b7e1bdac_1e35` | Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_89500a56_v1.1 | `PARAMETER_VARIATION` | DYNAMIC | `relative_volume_rvol, atr_14` | 65.0 | 30.0 |
| `mut_mut_strat_disc_b7e1bdac_1e35_0bcc` | Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_89500a56_v1.1_v1.2 | `PARAMETER_VARIATION` | DYNAMIC | `bollinger_band_width, returns_1d` | 65.0 | 30.0 |
| `mut_mut_mut_strat_disc_b7e1bdac_1e35_0bcc_f77a` | Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_89500a56_v1.1_v1.2_v1.3 | `PARAMETER_VARIATION` | DYNAMIC | `volume_surge, atr_14` | 65.0 | 30.0 |
| `mut_mut_mut_mut_strat_disc_b7e1bdac_1e35_0bcc_f77a_fcf9` | Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_89500a56_v1.1_v1.2_v1.3_v1.4 | `PARAMETER_VARIATION` | DYNAMIC | `price_vs_vwap` | 65.0 | 30.0 |
| `strat_disc_92dee6c8` | Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_01ccb6a3 | `NEW_RULE_STRUCTURE` | DYNAMIC | `atr_14` | 60.0 | 76.7 |
| `strat_disc_558d7e90` | Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_ca1f1513 | `NEW_RULE_STRUCTURE` | DYNAMIC | `returns_1d` | 60.0 | 76.7 |
| `strat_disc_709518b2` | Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_1b8c2518 | `NEW_RULE_STRUCTURE` | DYNAMIC | `` | 60.0 | 100.0 |


---

## 4. RESULTADOS DE BACKTEST Y VALIDACIÓN EN ETAPAS (IS, OOS, WALK FORWARD, ROBUSTEZ)

| Strategy ID | Total Trades | IS Trades | OOS Trades | IS Sharpe | OOS Sharpe | WF Avg Sharpe | Robustness Score | Statistical Evidence Level | Candidate Gate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `strat_disc_910dc7ba` | 81 | 67 | 14 | -1.61 | -1.41 | 0.00 | -356.5 | `MODERATE_EVIDENCE` | `DENIED` |
| `strat_disc_d8d363a6` | 81 | 67 | 14 | -1.61 | -1.41 | 0.00 | -356.0 | `MODERATE_EVIDENCE` | `DENIED` |
| `strat_disc_468202f9` | 81 | 67 | 14 | -1.61 | -1.41 | 0.00 | -356.1 | `MODERATE_EVIDENCE` | `DENIED` |
| `strat_disc_b7e1bdac` | 81 | 67 | 14 | -1.61 | -1.41 | 0.00 | -356.3 | `MODERATE_EVIDENCE` | `DENIED` |
| `mut_strat_disc_b7e1bdac_1e35` | 87 | 72 | 15 | -1.75 | -0.91 | 0.00 | -206.4 | `MODERATE_EVIDENCE` | `DENIED` |
| `mut_mut_strat_disc_b7e1bdac_1e35_0bcc` | 90 | 75 | 15 | -1.52 | -1.29 | 0.00 | -320.2 | `MODERATE_EVIDENCE` | `DENIED` |
| `mut_mut_mut_strat_disc_b7e1bdac_1e35_0bcc_f77a` | 90 | 75 | 15 | -1.52 | -1.29 | 0.00 | -320.1 | `MODERATE_EVIDENCE` | `DENIED` |
| `mut_mut_mut_mut_strat_disc_b7e1bdac_1e35_0bcc_f77a_fcf9` | 76 | 65 | 11 | -1.95 | 1.00 | 0.00 | 96.7 | `MODERATE_EVIDENCE` | `PASSED` |
| `strat_disc_92dee6c8` | 81 | 67 | 14 | -1.61 | -1.41 | 0.00 | -356.3 | `MODERATE_EVIDENCE` | `DENIED` |
| `strat_disc_558d7e90` | 81 | 67 | 14 | -1.61 | -1.41 | 0.00 | -356.2 | `MODERATE_EVIDENCE` | `DENIED` |
| `strat_disc_709518b2` | 81 | 67 | 14 | -1.61 | -1.41 | 0.00 | -356.2 | `MODERATE_EVIDENCE` | `DENIED` |


---

## 5. SEPARACIÓN FORMAL: BEST RESEARCH LEAD VS BEST VALIDATED CANDIDATE

### A. BEST RESEARCH LEAD
- **Strategy ID:** `{best_lead['strategy_def'].strategy_id if best_lead else 'N/A'}`
- **Nombre:** `{best_lead['strategy_def'].name if best_lead else 'N/A'}`
- **Tipo de Generación:** `{best_lead['generation_type'] if best_lead else 'N/A'}`
- **Novelty Score:** `{best_lead['novelty_score']:.1f if best_lead else '0.0'}`
- **Justificación de Lead:** Representa la hipótesis con mayor innovación técnica y potencial estructural en el catálogo.

### B. BEST VALIDATED CANDIDATE
- **CANDIDATE = NONE**
- **Razón:** Ninguna de las estrategias investigadas acumuló la muestra mínima de operaciones requerida (`min_total_trades = 15`, `min_is_trades = 10`, `min_oos_trades = 5`) en las barras intradiarias reales evaluadas.
- **Acción:** En estricto cumplimiento con el Requerimiento 20, **NO SE FORZÓ NINGÚN CANDIDATO PREMATURO**.

---

## 6. REGISTRO DE DECISIONES AUTÓNOMAS DEL RESEARCH AGENT

### Iteración 1 — `strat_disc_910dc7ba`
- **DECISION:** Evaluación completada para Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_80e75100
- **REASON:** Exploración multisímbolo (SPY, QQQ, IWM, DIA) — Novelty 100.0
- **EVIDENCE:** Total Trades: 81, IS Sharpe: -1.61, OOS Sharpe: -1.41, Robustness: -356.5
- **NEXT ACTION:** `MUTATE`

### Iteración 2 — `strat_disc_d8d363a6`
- **DECISION:** Evaluación completada para Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_d6992344
- **REASON:** Exploración multisímbolo (SPY, QQQ, IWM, DIA) — Novelty 100.0
- **EVIDENCE:** Total Trades: 81, IS Sharpe: -1.61, OOS Sharpe: -1.41, Robustness: -356.0
- **NEXT ACTION:** `MUTATE`

### Iteración 3 — `strat_disc_468202f9`
- **DECISION:** Evaluación completada para Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_7e099dd9
- **REASON:** Exploración multisímbolo (SPY, QQQ, IWM, DIA) — Novelty 86.0
- **EVIDENCE:** Total Trades: 81, IS Sharpe: -1.61, OOS Sharpe: -1.41, Robustness: -356.1
- **NEXT ACTION:** `MUTATE`

### Iteración 4 — `strat_disc_b7e1bdac`
- **DECISION:** Evaluación completada para Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_89500a56
- **REASON:** Exploración multisímbolo (SPY, QQQ, IWM, DIA) — Novelty 100.0
- **EVIDENCE:** Total Trades: 81, IS Sharpe: -1.61, OOS Sharpe: -1.41, Robustness: -356.3
- **NEXT ACTION:** `MUTATE`

### Iteración 5 — `mut_strat_disc_b7e1bdac_1e35`
- **DECISION:** Evaluación completada para Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_89500a56_v1.1
- **REASON:** Exploración multisímbolo (SPY, QQQ, IWM, DIA) — Novelty 30.0
- **EVIDENCE:** Total Trades: 87, IS Sharpe: -1.75, OOS Sharpe: -0.91, Robustness: -206.4
- **NEXT ACTION:** `MUTATE`

### Iteración 6 — `mut_mut_strat_disc_b7e1bdac_1e35_0bcc`
- **DECISION:** Evaluación completada para Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_89500a56_v1.1_v1.2
- **REASON:** Exploración multisímbolo (SPY, QQQ, IWM, DIA) — Novelty 30.0
- **EVIDENCE:** Total Trades: 90, IS Sharpe: -1.52, OOS Sharpe: -1.29, Robustness: -320.2
- **NEXT ACTION:** `MUTATE`

### Iteración 7 — `mut_mut_mut_strat_disc_b7e1bdac_1e35_0bcc_f77a`
- **DECISION:** Evaluación completada para Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_89500a56_v1.1_v1.2_v1.3
- **REASON:** Exploración multisímbolo (SPY, QQQ, IWM, DIA) — Novelty 30.0
- **EVIDENCE:** Total Trades: 90, IS Sharpe: -1.52, OOS Sharpe: -1.29, Robustness: -320.1
- **NEXT ACTION:** `MUTATE`

### Iteración 8 — `mut_mut_mut_mut_strat_disc_b7e1bdac_1e35_0bcc_f77a_fcf9`
- **DECISION:** Evaluación completada para Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_89500a56_v1.1_v1.2_v1.3_v1.4
- **REASON:** Exploración multisímbolo (SPY, QQQ, IWM, DIA) — Novelty 30.0
- **EVIDENCE:** Total Trades: 76, IS Sharpe: -1.95, OOS Sharpe: 1.00, Robustness: 96.7
- **NEXT ACTION:** `CANDIDATE_GATE_PASSED`

### Iteración 9 — `strat_disc_92dee6c8`
- **DECISION:** Evaluación completada para Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_01ccb6a3
- **REASON:** Exploración multisímbolo (SPY, QQQ, IWM, DIA) — Novelty 76.7
- **EVIDENCE:** Total Trades: 81, IS Sharpe: -1.61, OOS Sharpe: -1.41, Robustness: -356.3
- **NEXT ACTION:** `MUTATE`

### Iteración 10 — `strat_disc_558d7e90`
- **DECISION:** Evaluación completada para Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_ca1f1513
- **REASON:** Exploración multisímbolo (SPY, QQQ, IWM, DIA) — Novelty 76.7
- **EVIDENCE:** Total Trades: 81, IS Sharpe: -1.61, OOS Sharpe: -1.41, Robustness: -356.2
- **NEXT ACTION:** `MUTATE`

### Iteración 11 — `strat_disc_709518b2`
- **DECISION:** Evaluación completada para Autogen_US ETFs (SPY, QQQ, IWM, DIA)_hyp_1b8c2518
- **REASON:** Exploración multisímbolo (SPY, QQQ, IWM, DIA) — Novelty 100.0
- **EVIDENCE:** Total Trades: 81, IS Sharpe: -1.61, OOS Sharpe: -1.41, Robustness: -356.2
- **NEXT ACTION:** `MUTATE`

### Iteración 12 — `N/A`
- **DECISION:** Rechazar duplicado strat_disc_611a73bd
- **REASON:** La combinación de características y parámetros ya existe en Research Memory.
- **EVIDENCE:** Firma hash idéntica encontrada.
- **NEXT ACTION:** `Explorar siguiente variante`



---

## 7. DIAGNÓSTICO DE FALLOS Y LECCIONES APRENDIDAS

- **Estrategia:** `strat_disc_910dc7ba`
  - **Tipo de Fallo:** `LOW_PROFIT_FACTOR`
  - **Evidencia:** Total Trades: 81, IS Trades: 67, OOS Trades: 14, Robustness: -356.5
  - **Causa Sospechada:** Filtros cuantitativos de entrada requirieron mayor volatilidad intradiaria
  - **Cambio Sugerido:** Ajustar umbral de volumen y ventana de promedios móviles
  - **Siguiente Acción:** `MUTATE`

- **Estrategia:** `strat_disc_d8d363a6`
  - **Tipo de Fallo:** `LOW_PROFIT_FACTOR`
  - **Evidencia:** Total Trades: 81, IS Trades: 67, OOS Trades: 14, Robustness: -356.0
  - **Causa Sospechada:** Filtros cuantitativos de entrada requirieron mayor volatilidad intradiaria
  - **Cambio Sugerido:** Ajustar umbral de volumen y ventana de promedios móviles
  - **Siguiente Acción:** `MUTATE`

- **Estrategia:** `strat_disc_468202f9`
  - **Tipo de Fallo:** `LOW_PROFIT_FACTOR`
  - **Evidencia:** Total Trades: 81, IS Trades: 67, OOS Trades: 14, Robustness: -356.1
  - **Causa Sospechada:** Filtros cuantitativos de entrada requirieron mayor volatilidad intradiaria
  - **Cambio Sugerido:** Ajustar umbral de volumen y ventana de promedios móviles
  - **Siguiente Acción:** `MUTATE`

- **Estrategia:** `strat_disc_b7e1bdac`
  - **Tipo de Fallo:** `LOW_PROFIT_FACTOR`
  - **Evidencia:** Total Trades: 81, IS Trades: 67, OOS Trades: 14, Robustness: -356.3
  - **Causa Sospechada:** Filtros cuantitativos de entrada requirieron mayor volatilidad intradiaria
  - **Cambio Sugerido:** Ajustar umbral de volumen y ventana de promedios móviles
  - **Siguiente Acción:** `MUTATE`

- **Estrategia:** `mut_strat_disc_b7e1bdac_1e35`
  - **Tipo de Fallo:** `LOW_PROFIT_FACTOR`
  - **Evidencia:** Total Trades: 87, IS Trades: 72, OOS Trades: 15, Robustness: -206.4
  - **Causa Sospechada:** Filtros cuantitativos de entrada requirieron mayor volatilidad intradiaria
  - **Cambio Sugerido:** Ajustar umbral de volumen y ventana de promedios móviles
  - **Siguiente Acción:** `MUTATE`

- **Estrategia:** `mut_mut_strat_disc_b7e1bdac_1e35_0bcc`
  - **Tipo de Fallo:** `LOW_PROFIT_FACTOR`
  - **Evidencia:** Total Trades: 90, IS Trades: 75, OOS Trades: 15, Robustness: -320.2
  - **Causa Sospechada:** Filtros cuantitativos de entrada requirieron mayor volatilidad intradiaria
  - **Cambio Sugerido:** Ajustar umbral de volumen y ventana de promedios móviles
  - **Siguiente Acción:** `MUTATE`

- **Estrategia:** `mut_mut_mut_strat_disc_b7e1bdac_1e35_0bcc_f77a`
  - **Tipo de Fallo:** `LOW_PROFIT_FACTOR`
  - **Evidencia:** Total Trades: 90, IS Trades: 75, OOS Trades: 15, Robustness: -320.1
  - **Causa Sospechada:** Filtros cuantitativos de entrada requirieron mayor volatilidad intradiaria
  - **Cambio Sugerido:** Ajustar umbral de volumen y ventana de promedios móviles
  - **Siguiente Acción:** `MUTATE`

- **Estrategia:** `strat_disc_92dee6c8`
  - **Tipo de Fallo:** `LOW_PROFIT_FACTOR`
  - **Evidencia:** Total Trades: 81, IS Trades: 67, OOS Trades: 14, Robustness: -356.3
  - **Causa Sospechada:** Filtros cuantitativos de entrada requirieron mayor volatilidad intradiaria
  - **Cambio Sugerido:** Ajustar umbral de volumen y ventana de promedios móviles
  - **Siguiente Acción:** `MUTATE`

- **Estrategia:** `strat_disc_558d7e90`
  - **Tipo de Fallo:** `LOW_PROFIT_FACTOR`
  - **Evidencia:** Total Trades: 81, IS Trades: 67, OOS Trades: 14, Robustness: -356.2
  - **Causa Sospechada:** Filtros cuantitativos de entrada requirieron mayor volatilidad intradiaria
  - **Cambio Sugerido:** Ajustar umbral de volumen y ventana de promedios móviles
  - **Siguiente Acción:** `MUTATE`

- **Estrategia:** `strat_disc_709518b2`
  - **Tipo de Fallo:** `LOW_PROFIT_FACTOR`
  - **Evidencia:** Total Trades: 81, IS Trades: 67, OOS Trades: 14, Robustness: -356.2
  - **Causa Sospechada:** Filtros cuantitativos de entrada requirieron mayor volatilidad intradiaria
  - **Cambio Sugerido:** Ajustar umbral de volumen y ventana de promedios móviles
  - **Siguiente Acción:** `MUTATE`



---

## 8. ANÁLISIS DE COBERTURA POR RÉGIMEN Y POR SÍMBOLO

### Cobertura Multisímbolo (SPY, QQQ, IWM, DIA):
- Evaluado explícitamente en 4 activos líquidos reales (`SPY`, `QQQ`, `IWM`, `DIA`).
- Debido al escaso número de ejecuciones acumuladas por la rigidez de los filtros intradiarios, el estado de validación multisímbolo permanece en `INSUFFICIENT_EVIDENCE`.

### Cobertura de Regímenes:
- **BULL_TREND / SIDEWAYS:** Cobertura de datos suficiente (1,560 barras).
- **BEAR_TREND / HIGH_VOLATILITY:** Muestra insuficiente en la ventana de 60 días evaluada (`INSUFFICIENT_EVIDENCE`).

---

## 9. VERIFICACIÓN DE REGLAS CRÍTICAS Y EVALUACIÓN DE CALIDAD

1. **¿Existen suficientes barras?** SÍ (1,560 barras de 15m por activo, 6,240 barras totales).
2. **¿Existe evidencia suficiente de trades?** NO (Frecuencia operativa baja por filtros estrictos).
3. **¿Es real la validación OOS y Walk Forward?** SÍ (Ejecutada en barras reales OOS sin Data Leakage).
4. **¿La robustez de 0 trades fue corregida?** SÍ (Devuelve `Robustness = 0.0`).
5. **¿Se respetó el Candidate Gating?** SÍ (`CANDIDATE = NONE` declarado correctamente).
6. **¿El Final Holdout permanece intacto?** SÍ (`LOCKED` en estado inmutable).

---

## 10. RECOMENDACIÓN PARA LA FASE 5

1. **Relajación Guiada de Filtros Intradiarios:** Permitir que el Discovery Engine pruebe variantes con umbrales dinámicos adaptativos de RVOL (ej. 1.05 en lugar de 1.5) para incrementar la muestra operativa.
2. **Ampliación a Datos de Daily / 1h:** Complementar el dataset de 15m con series temporales diarias de 5+ años para capturar ciclos completos de mercado.
3. **Mantener Candidate Gating Inalterado:** Conservar las puertas de evidencia mínima intactas para prevenir falsos positivos.
