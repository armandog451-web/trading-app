# ESTADO ACTUAL DEL RELOJ DE VALIDACIÓN D21
## DESGLOSE DE CONTADORES INDEPENDIENTES, CONTABILIDAD DE BRECHAS Y CRITERIOS DE GRADUACIÓN

**Estrategia:** `D21_RangeCompress_5d`  
**Fingerprint Inmutable:** `f885ec2db2422308`  
**Inicio Formal de Campaña:** 05 de Octubre de 2026  
**Fecha de Referencia:** 30 de Octubre de 2026  
**Estado:** **CAMPAÑA DE VALIDACIÓN ACTIVA (EVIDENCIA EN PROCESO DE RECOLECCIÓN)**

---

## 1. DESGLOSE DE LOS CUATRO CONTADORES INDEPENDIENTES

Para eliminar la confusión histórica entre días de calendario y sesiones de trading reales, el sistema desacopló el progreso de validación en cuatro contadores cuantitativos independientes, expuestos en `/health`:

| Contador | Valor Actual | Meta Mínima Requerida | Estado de Cumplimiento |
| :--- | :---: | :---: | :---: |
| **1. Días Calendario Activos** (`calendar_days_active`) | 26 | N/A | Informativo (desde 2026-10-05) |
| **2. Sesiones Bursátiles Completadas** (`market_sessions_completed`) | 7 | N/A | Informativo (sesión 8 en curso) |
| **3. Sesiones Válidas Evaluadas por D21** (`d21_valid_evaluation_sessions`) | **0 / 90** | $\ge 90$ sesiones | **En progreso (0.0%)** |
| **4. Trades Cerrados en PAPER** (`paper_closed_trades`) | **0 / 12** | $\ge 12$ trades cerrados | **En progreso (0.0%)** |

> **Nota Crítica sobre la Sesión de Hoy:** La sesión bursátil del 30 de octubre de 2026 está actualmente activa. A las **16:15 ET**, el scheduler evaluará las barras de cierre de mercado. Al completarse dicha evaluación satisfactoriamente, el contador `d21_valid_evaluation_sessions` registrará su **primera sesión prospectiva válida (1 / 90)**.

---

## 2. CONTABILIDAD FORMAL DE LA BRECHA HISTÓRICA (GAP)

De acuerdo con la auditoría de consolidación, se certifica la exclusión estricta del periodo en que el runtime no estuvo disponible:

- **Inicio de la Campaña Original:** 2026-10-05 (1 sesión evaluada).
- **Brecha Operativa Inválida:** 2026-10-06 hasta 2026-10-20 (15 días calendario).
- **Causa:** Ausencia del proceso servidor estandarizado en el host local.
- **Tratamiento:** **EXCLUSIÓN TOTAL**. Ningún día dentro de este rango es contabilizado como sesión válida de observación ni permite inferencia de señales retrospectivas.
- **Restauración del Runtime Canónico:** 2026-10-21.
- **Sesiones Bursátiles Posteriores a la Restauración:** 21, 22, 23, 26, 27, 28 y 29 de octubre (7 sesiones de mercado regulares completadas).

---

## 3. ESTADO DE LOS CRITERIOS DE GRADUACIÓN DE CAMPAÑA

El protocolo institucional prohíbe emitir un veredicto final de `PASS` o `FAIL` hasta que se alcancen de forma conjunta ambos umbrales obligatorios:

```
Observation Days:
0 / 90  (Próxima actualización: 16:15 ET -> 1 / 90)

Closed Trades:
0 / 12  (Esperando señales legítimas de compresión de rango)
```

### Reglas de Evaluación Post-Campaña:
1. **Factor de Beneficio (Profit Factor):** Requerido $\ge 1.30$ en PAPER.
2. **Win Rate:** Requerido $\ge 50.0\%$ con ratio ganancia/pérdida favorable.
3. **Máximo Drawdown:** No debe exceder el 10.0% del capital virtual ($100,000 USD sobre la cuenta de $1,000,000 USD).
4. **Deslizamiento Medio (Mean Slippage):** Tolerancia máxima de 3 bps ($0.03\%$) respecto al precio teórico de la barra diaria.
5. **Drag de Comisiones:** No debe erosionar más del 15% del PnL bruto generado.

---

## 4. INTEGRIDAD DE LA ESTRATEGIA Y GOBERNANZA

- **Estrategia Autorizada:** `D21_RangeCompress_5d` (única autorizada en PAPER).
- **Fingerprint de Reglas:** `f885ec2db2422308` (inalterado).
- **Prohibición de Forzado:** No se generarán órdenes artificiales para acelerar el contador de trades. La estrategia opera exclusivamente bajo sus condiciones estadísticas originales.
- **Dictamen:** La campaña continúa en estado **PAPER_VALIDATION_ACTIVE** con rigor metodológico absoluto.
