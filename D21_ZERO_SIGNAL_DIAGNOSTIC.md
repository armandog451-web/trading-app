# D21 ZERO SIGNAL DIAGNOSTIC & FORENSIC AUDIT
**Estrategia Auditada:** `D21_RangeCompress_5d` (Daily Range Compression Breakout)  
**Universo:** `SPY`, `QQQ`, `IWM`, `DIA` (Timeframe: `1D`)  
**Fecha de Auditoría:** 2026-10-30 08:15:00 EDT  
**Entorno Canónico:** `C:\Users\edsel\OneDrive\Documents\trading-app-repo`  
**Clasificación de Hallazgo:** `ISSUE` (Identificado, diagnosticado y resuelto en runtime canónico)

---

## 1. RESUMEN EJECUTIVO DEL DIAGNÓSTICO

Tras 11 días reportados como "observación paper", el sistema registra **0 señales y 0 trades cerrados**. La investigación forense determinó que la causa se descompone en **dos vectores concurrentes**:

1. **Defecto Arquitectónico en Runtime Previo (Causa Primaria):**  
   El proceso que estuvo en ejecución continua entre el 21 y el 30 de octubre de 2026 correspondía a la carpeta `trading-app-main` (ahora archivada). La versión de [`scheduler_service.py`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/schedule/scheduler_service.py) en dicho workspace ejecutaba el método `run_daily_report()` pero **no invocaba** la función evaluadora `evaluate_and_execute_d21_paper()`. En los registros de auditoría de SQLite (`task_logs_audit`), las 8 ejecuciones diarias de `daily_post_close` registraron de forma invariable:
   ```json
   "d21_evaluation": null
   ```
   **Conclusión:** El bucle de decisión de D21 **nunca fue ejecutado en vivo** por el scheduler del runtime anterior.

2. **Condiciones de Mercado y Filtro de Régimen Cuantitativo (Causa Secundaria):**  
   Al ejecutar un replay cuantitativo estricto con barras históricas reales 1D descargadas de YFinance entre el 21 y el 29 de octubre:
   - En **7 de las 8 sesiones**, el mercado operó en consolidación de baja volatilidad con volumen relativo deprimido ($\text{RVOL} \in [0.61x, 1.06x]$), incumpliendo el umbral mandatorio de $\text{RVOL} \ge 1.25x$ o manteniéndose dentro del canal Donchian de 20 días.
   - En **1 sesión** (el **22 de octubre de 2026**), el activo `QQQ` **cumplió matemáticamente las 3 condiciones de venta**:
     $$\text{Close}=\$704.47 \le \text{Low}_{20}=\$707.23 \quad\land\quad \text{RVOL}=1.76x \ge 1.25x \quad\land\quad \text{Close} < \text{SMA}_{50}=\$725.98$$
     Esta señal fue **omitida en el runtime real** debido exclusivamente al Defecto Arquitectónico #1.

---

## 2. DESGLOSE TEMPORAL EXACTO: CALENDARIO VS. MERCADO VS. EVALUACIONES

| Dimensión Temporal | Conteo | Detalle y Fechas |
| :--- | :---: | :--- |
| **Días Calendario Totales (Campaña)** | **26 días** | Del 2026-10-05 al 2026-10-30 (inclusive). |
| **Gap Inválido Excluido** | **15 días** | Del 2026-10-06 al 2026-10-20 (divergencia de workspaces). |
| **Días Calendario de Validación Real** | **11 días** | Oct 5 + Oct 21 a Oct 30 (26 - 15 = 11). |
| **Días de Fin de Semana (Cerrados)** | **2 días** | Sábado 24 y Domingo 25 de Octubre de 2026. |
| **Sesiones Bursátiles Completas (NYSE)** | **8 sesiones** | Oct 5, 21, 22, 23, 26, 27, 28 y 29 de Octubre de 2026. |
| **Sesión en Curso (Premarket/Abierta)** | **1 sesión** | Oct 30 de Octubre de 2026 (en curso a las 08:15 EDT). |
| **Sesiones con Runtime Activo 24/7** | **8 sesiones** | Proceso Uvicorn/Scheduler activo en la máquina. |
| **Sesiones Realmente Evaluadas por D21** | **`0 sesiones`** | **`ISSUE`**: `evaluate_and_execute_d21_paper()` ausente en el scheduler del workspace activo. |

---

## 3. AUDITORÍA MATEMÁTICA SESIÓN POR SESIÓN (REPLAY REAL 1D)

Reglas congeladas de D21_RangeCompress_5d (Fingerprint `f885ec2db2422308`):
- **BULL BREAKOUT:** $\text{Close} \ge \text{High}_{20} \;\land\; \text{RVOL} \ge 1.25 \;\land\; \text{Close} > \text{SMA}_{50}$
- **BEAR BREAKOUT:** $\text{Close} \le \text{Low}_{20} \;\land\; \text{RVOL} \ge 1.25 \;\land\; \text{Close} < \text{SMA}_{50}$

### Replay Forense sobre Datos Oficiales (YFinance Bar Provider):

| Fecha | Símbolo | Close ($) | Donchian 20d ($) | RVOL (20d) | SMA 50d ($) | Cumple Reglas? | Veredicto Cuantitativo |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **2026-10-21** | `SPY` | 773.09 | [758.79 - 781.62] | 0.79x | 767.35 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `QQQ` | 725.20 | [707.23 - 762.86] | 0.93x | 726.35 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `IWM` | 276.48 | [269.88 - 286.18] | 0.62x | 287.13 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `DIA` | 527.70 | [504.59 - 526.17] | 0.80x | 522.50 | No | `LOW_RVOL (0.80x < 1.25x)` (Ruptura sin volumen) |
| **2026-10-22** | `SPY` | 763.96 | [758.79 - 781.62] | 1.33x | 767.22 | No | `NO_DONCHIAN_BREAKOUT` (Dentro de rango) |
| | **`QQQ`** | **704.47** | **[707.23 - 762.86]** | **1.76x** | **725.98** | **SÍ** | **`SIGNAL FOUND: QQQ SELL (Ruptura Donchian + RVOL 1.76x)`** |
| | `IWM` | 276.67 | [269.88 - 284.64] | 1.00x | 286.63 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `DIA` | 527.89 | [504.59 - 527.79] | 0.81x | 522.35 | No | `LOW_RVOL (0.81x < 1.25x)` |
| **2026-10-23** | `SPY` | 759.97 | [758.79 - 781.62] | 0.82x | 766.90 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `QQQ` | 704.40 | [701.90 - 762.86] | 0.82x | 725.44 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `IWM` | 275.75 | [269.88 - 284.64] | 0.81x | 286.09 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `DIA` | 521.37 | [504.59 - 528.45] | 0.90x | 522.06 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| **2026-10-26** | `SPY` | 765.37 | [758.68 - 781.62] | 0.79x | 766.72 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `QQQ` | 712.20 | [701.16 - 762.86] | 0.91x | 725.08 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `IWM` | 276.99 | [269.88 - 284.64] | 0.61x | 285.54 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `DIA` | 522.97 | [504.59 - 528.45] | 0.70x | 521.82 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| **2026-10-27** | `SPY` | 769.66 | [758.68 - 781.62] | 0.72x | 766.69 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `QQQ` | 721.25 | [701.16 - 762.86] | 0.85x | 724.92 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `IWM` | 280.18 | [269.88 - 284.64] | 0.75x | 285.08 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `DIA` | 523.28 | [504.59 - 528.45] | 0.81x | 521.63 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| **2026-10-28** | `SPY` | 772.31 | [758.68 - 781.62] | 0.79x | 766.83 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `QQQ` | 725.61 | [701.16 - 762.86] | 0.83x | 725.10 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `IWM` | 281.29 | [269.88 - 284.64] | 0.76x | 284.72 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `DIA` | 524.68 | [504.59 - 528.45] | 0.84x | 521.50 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| **2026-10-29** | `SPY` | 769.36 | [758.68 - 781.62] | 1.06x | 766.87 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `QQQ` | 715.34 | [701.16 - 762.86] | 1.03x | 725.10 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `IWM` | 284.01 | [269.88 - 284.64] | 0.89x | 284.38 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |
| | `DIA` | 522.73 | [504.59 - 528.45] | 0.90x | 521.31 | No | `NO_DONCHIAN_BREAKOUT, LOW_RVOL` |

---

## 4. ESTADO DE LOS DATOS Y CADENCIA DE DISPARO DEL SCHEDULER

1. **Disponibilidad y Frescura de Barras:**
   - Proveedor: `YFinanceProvider` con almacenamiento en caché local.
   - Barras disponibles: 80 a 120 barras diarias por símbolo (supera holgadamente el mínimo de 50 requerido para Donchian20, SMA50 y ATR14).
   - Barras cerradas: Las barras diarias se consideran cerradas a las 16:00:00 ET (NYSE/NASDAQ Close).
   - **Calidad:** `VERIFIED` (Sin gaps internos ni datos corruptos).

2. **Disparadores del Scheduler:**
   - La tarea `daily_post_close` se programa para las **16:15:00 ET**.
   - En el código canónico actual de `trading-app-repo` ([`scheduler_service.py`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/schedule/scheduler_service.py#L498)), dicha tarea ejecuta:
     ```python
     d21_eval = await self.evaluate_and_execute_d21_paper()
     ```
   - Este método itera sobre `['SPY', 'QQQ', 'IWM', 'DIA']`, precalcula los features sobre barras cerradas, valida contra `PortfolioRiskEngine` y despacha la orden simulada a `MoomooBrokerAdapter` (`TrdEnv.SIMULATE`).
   - El test institucional `test_16_d21_direct_moomoo_execution_pipeline` en `test_fase10_8_runtime_activation.py` verifica formalmente este pipeline y pasa al 100%.

---

## 5. IMPACTO SOBRE EL RELOJ DE VALIDACIÓN Y ACCIONES OBLIGATORIAS

1. **Reajuste Contable de Sesiones Validadas:**
   - De los 11 días reportados como "observación paper", únicamente las sesiones a partir de hoy (30 de octubre) en las que `evaluate_and_execute_d21_paper` corre activamente en el backend canónico representan **evaluación computacional activa**.
   - La señal de QQQ del 22 de octubre **NO debe ser fabricada retrospectivamente** (violaría la regla mandatoria: *"No fabricar trades históricos"*).
   - El contador de trades se mantiene rigurosamente en **`0 / 12`**.

2. **Acción Preventiva de Gobernanza:**
   - Se mantiene el servidor central en el puerto 8090 apuntando de forma única e indiscutible a `trading-app-repo`.
   - Se añade verificación en el endpoint `/health` que no solo reporte el estado de D21, sino el timestamp de la última ejecución efectiva de `evaluate_and_execute_d21_paper`.
