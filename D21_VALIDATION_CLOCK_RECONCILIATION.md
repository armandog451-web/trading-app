# D21 VALIDATION CLOCK RECONCILIATION — FASE 6.3

**Estrategia:** `D21_RangeCompress_5d`  
**Fingerprint:** `f885ec2db2422308`  
**Fecha de Corte:** 2026-10-30  
**Ubicación del Tracker:** `ai_trading_agent.execution.fidelity.campaign`  
**Commit SHA:** `f44f397022cfd186c5e916a008003a21e5f118eb`  
**Estado:** `PASS` (Reconciliación Rigurosa de 4 Contadores)

---

## 1. OBJETIVO DE LA RECONCILIACIÓN

Desacoplar de forma transparente los días calendario transcurridos de los días en que el sistema estuvo operando y de las sesiones en que la estrategia realmente evaluó el mercado. 

Ninguna campaña de validación puede computar como "días de observación válidos" periodos en los cuales el runtime estuvo inactivo o el evaluador no fue invocado.

---

## 2. DESGLOSE FORENSE DE LA LÍNEA TEMPORAL

```
2026-10-05: Inicio formal de la campaña Paper Validation de D21.
2026-10-06 al 2026-10-20 (15 días): Brecha de desconexión (INVALID OBSERVATION GAP).
             - Servidor fuera de línea o sin runtime activo.
             - EXCLUIDO ESTRICTAMENTE de la observación verificada.
2026-10-21: Restauración del runtime canónico (CANONICAL RUNTIME RESTORED).
             - Reanudación de la presencia activa del servidor.
2026-10-21 al 2026-10-29 (7 sesiones de mercado completadas):
             - Servidor activo 24/7.
             - Omitida la invocación de D21 en el proceso previo.
             - Sesiones válidamente evaluadas por D21: 0.
2026-10-30 (Hoy): Sesión bursátil 8 activa en curso.
             - Pipeline corregido, verificado y listo para evaluar a las 16:15 ET.
```

---

## 3. LOS CUATRO CONTADORES INDEPENDIENTES INSTITUCIONALES

En `ai_trading_agent/execution/fidelity/campaign.py` y en el endpoint `/health`, el reloj se expone en cuatro contadores mutuamente excluyentes:

| Contador | Valor Actual | Objetivo | Definición Rigurosa |
| :--- | :---: | :---: | :--- |
| `calendar_days_active` | **26 días** | — | Total de días calendario transcurridos desde el inicio oficial el 2026-10-05 hasta hoy 2026-10-30. |
| `market_sessions_completed` | **7 sesiones** (8 en curso) | — | Total de sesiones bursátiles regulares de NYSE (lunes a viernes, excluyendo festivos) completadas desde la restauración canónica el 2026-10-21 hasta ayer 2026-10-29. |
| `d21_valid_evaluation_sessions` | **0 sesiones** | **$\ge 90$** | Sesiones bursátiles en las cuales `evaluate_and_execute_d21_paper()` fue efectivamente ejecutado y persistido. Hoy (2026-10-30) será la primera sesión formal al cierre de las 16:15 ET. |
| `paper_closed_trades` | **0 trades** | **$\ge 12$** | Trades cerrados reales persistidos en SQLite para la estrategia D21. Prohibido fabricar trades artificiales. |

---

## 4. CRITERIO DE CUMPLIMIENTO PARA COMITÉ DE GOBERNANZA

Para que la estrategia `D21_RangeCompress_5d` sea evaluada por el comité de inversión y considere cualquier promoción, **deben cumplirse simultáneamente ambas condiciones**:

$$\text{d21\_valid\_evaluation\_sessions} \ge 90$$
$$\mathbf{Y}$$
$$\text{paper\_closed\_trades} \ge 12$$

### Estado Actual:
* **Sesiones de Evaluación:** `0 / 90` (Faltan 90 sesiones).
* **Trades Cerrados:** `0 / 12` (Faltan 12 trades).
* **Veredicto:** `PAPER_VALIDATION_ACTIVE` / `INSUFFICIENT_EVIDENCE`.
* **Prohibición:** Queda terminantemente prohibido emitir cualquier dictamen de `PASS` de validación hasta alcanzar ambos umbrales con evidencia viva comprobable.

---

## 5. CONCLUSIÓN

* **Estado:** `PASS`
* **Veredicto:** El reloj de validación de D21 refleja exclusivamente evidencia genuina, separando con exactitud los días de servidor activo de las sesiones realmente evaluadas por la estrategia.
