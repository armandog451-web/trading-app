# WATCHDOG & HEARTBEAT VALIDATION REPORT — FASE 6.3

**Módulo:** `OracleBot Runtime Supervisor` (`oraclebot.runtime.watchdog`, `oraclebot.runtime.health`)  
**Fecha de Validación:** 2026-10-30T13:31:00Z  
**Commit de Referencia:** `f44f397022cfd186c5e916a008003a21e5f118eb`  
**Supervisor PID Activo:** `2436`  
**Estado:** `PASS` (Cero Falsos Positivos Verificados)

---

## 1. DESCRIPCIÓN DEL PROBLEMA PREVIO

En las Fases 6.1 y 6.2 se producían alertas intermitentes de Telegram y registros repetidos:
```text
System sleep or downtime gap detected: 3.8 minutes
```
### Análisis Causa-Raíz:
* El watchdog supervisaba cada ciclo de 10 segundos buscando si `now - last_heartbeat > 180s`.
* El scheduler bursátil únicamente emitía el heartbeat cada 5 minutos (300 segundos) en sesión regular y cada 15 minutos (900 segundos) con mercado cerrado.
* En consecuencia, entre el segundo 181 y el segundo 300 (o 900), el watchdog interpretaba erróneamente la inactividad del scheduler como una suspensión del sistema operativo (PC sleep / freeze).

---

## 2. ARQUITECTURA TÉCNICA IMPLEMENTADA

Se desacopló completamente la generación de latidos de salud respecto a las tareas bursátiles del scheduler:

```python
# Parámetros de Temporización Institucional
HEARTBEAT_INTERVAL_SECONDS = 60       # Latido periódico autónomo cada 60s
WATCHDOG_CHECK_INTERVAL_SECONDS = 30  # Inspección del supervisor cada 30s
WATCHDOG_STALE_THRESHOLD_SECONDS = 180# Umbral de estancamiento de heartbeat (> 3 min)
RECOVERY_CONFIRMATION_HEARTBEATS = 2  # Confirmación de recuperación requerida
```

### Características de Seguridad:
1. **Escritura Atómica:** El archivo `runtime/heartbeat.json` se escribe primero en un archivo temporal `.tmp` y se renombra atómicamente, previniendo condiciones de carrera ante lecturas concurrentes.
2. **Reloj Monotónico:** Se utiliza `time.monotonic()` en conjunción con `time.time()` (UTC). Las pausas de proceso o derivas del reloj del sistema no inducen transiciones espurias.
3. **Máquina de Estados de 6 Estados:**
   * `HEALTHY`: Latido activo (< 180s), componentes en estado normal.
   * `DEGRADED`: Fallo transitorio en proveedor de datos o conexión no crítica.
   * `STALE_HEARTBEAT`: Brecha de latido entre 180s y 300s.
   * `SCHEDULER_STALLED`: Ausencia de ticks del scheduler por más de 300s.
   * `PROCESS_OFFLINE`: Brecha superior a 300s o proceso detenido.
   * `RECOVERED`: Transición formal tras 2 latidos consecutivos exitosos antes de restaurar `HEALTHY`.
4. **Deduplicación de Alertas Telegram:** Las alertas solo se despachan cuando ocurre un cambio genuino entre `old_state` y `new_state`, evitando inundaciones en el chat.

---

## 3. PRUEBAS DE ESTRÉS Y VALIDACIÓN AUTOMATIZADA

Se ejecutó la suite `tests/test_runtime_24_7.py` en `OracleBot` arrojando **17/17 PASS (100%)**:

```text
tests/test_runtime_24_7.py::TestRuntime247::test_24_7_security PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_forward_t0_persistence PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_market_holiday PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_paper_state_persistence PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_provider_failure_degraded PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_runtime_restart PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_runtime_single_instance PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_scheduler_market_awareness PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_sleep_gap_detection PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_telegram_failure_nonfatal PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_ui_close_does_not_stop_runtime PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_watchdog_recovery PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_watchdog_scheduler_stalled PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_watchdog_stale_heartbeat_and_offline PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_watchdog_state_machine_healthy_normal_operation PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_watchdog_transition_deduplication PASSED
tests/test_runtime_24_7.py::TestRuntime247::test_watchdog_two_heartbeat_recovery_confirmation PASSED
============================= 17 passed in 0.31s ==============================
```

### Resultados de las Pruebas de Comportamiento:
* **Operación Normal:** Cero transiciones ni alertas disparadas durante la emisión regular cada 60s.
* **Bloqueo Simulado del Scheduler:** Detectado con precisión a los 300s de inactividad de ticks, transitando a `SCHEDULER_STALLED`.
* **Retardo de Heartbeat (200s):** Clasificado como `STALE_HEARTBEAT` a los 180s y despachado exactamente una vez a Telegram.
* **Pausa Prolongada (350s):** Clasificado como `PROCESS_OFFLINE`.
* **Recuperación con Confirmación:** Al restaurar el servicio, el primer latido se registra como candidato (1/2 requeridos); tras el segundo latido consecutivo (2/2), se declara `RECOVERED` y se restaura el estado `HEALTHY`.
* **Deduplicación:** Evaluaciones continuas en estado degradado no emitieron alertas duplicadas.

---

## 4. ESTADO EN MEMORIA Y EVIDENCIA VIVA

El proceso supervisor fue reiniciado limpiamente mediante `scripts/restart_oraclebot_runtime.py`, adoptando el nuevo PID `2436`.
Contenido del heartbeat en vivo (`runtime/heartbeat.json`):
```json
{
  "timestamp": "2026-10-30T13:09:11.346123+00:00",
  "runtime_id": "RUN_1793365751",
  "status": "HEALTHY",
  "uptime_seconds": 1285.4,
  "system_mode": "SHADOW_PAPER",
  "forward_status": "ACTIVE",
  "telegram_status": "HEALTHY",
  "scheduler_status": "ACTIVE",
  "active_pid": 2436,
  "monotonic_timestamp": 241589.2,
  "d21_evaluation_status": "HEALTHY",
  "broker_paper_status": "CONNECTED"
}
```

---

## 5. CONCLUSIÓN Y VEREDICTO

* **Estado del Módulo:** `PASS`
* **Veredicto:** El supervisor de runtime y el sistema de latidos operan de manera determinista, inmune a desfases temporales y con cero falsos positivos bajo operación normal.
