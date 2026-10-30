# DISEÑO DE IDEMPOTENCIA TRANSACCIONAL D21
## BLINDAJE INSTITUCIONAL CONTRA DUPLICACIÓN DE ÓRDENES, CONCURRENCIA Y CAÍDAS

**Módulo:** `ai_trading_agent.execution.fidelity.idempotency`  
**Clase:** `TransactionalIdempotencyManager`  
**Fecha de Implementación:** 30 de Octubre de 2026  
**Estado:** **PROBADO Y CERTIFICADO (8/8 TEST SCENARIOS PASSED)**

---

## 1. MOTIVACIÓN Y OBJETIVOS

En la ejecución cuantitativa institucional, los reintentos automáticos, la concurrencia entre hilos o procesos, los reinicios intempestivos del servidor y los retardos o cortes de conectividad con el broker pueden provocar **duplicación catastrófica de órdenes**.

El módulo de Idempotencia Transaccional tiene por objetivo:
1. Garantizar que **exactamente una orden** pueda ser enviada para un mismo símbolo, dirección y barra de evaluación dentro de una sesión bursátil.
2. Hacer imposible que dos evaluaciones simultáneas generen dos órdenes paralelas.
3. Asegurar que tras un reinicio del sistema, cualquier orden pendiente de confirmación sea **reconciliada contra el libro de órdenes del broker** antes de permitir cualquier nueva acción.

---

## 2. DERIVACIÓN DE LA CLAVE DE IDEMPOTENCIA (SHA-256)

La clave de idempotencia es una cadena hexadecimal determinista de 64 caracteres generada mediante el algoritmo SHA-256 sobre una tupla canónica:

$$\text{Token} = \text{Fingerprint} : \text{FechaSesionNY} : \text{Símbolo} : \text{Dirección} : \text{TimestampBarra}$$

$$\text{IdempotencyKey} = \text{SHA-256}(\text{Token})$$

### Ejemplo Concreto:
- `strategy_fingerprint`: `f885ec2db2422308`
- `market_session_date`: `2026-10-30` (Zona horaria `America/New_York`)
- `symbol`: `QQQ`
- `signal_direction`: `SELL`
- `evaluation_bar_timestamp`: `2026-10-30T16:00:00-04:00`

**Token generado:**
```
f885ec2db2422308:2026-10-30:QQQ:SELL:2026-10-30T16:00:00-04:00
```
**Hash SHA-256 resultante:**
```
a38e8cb50b329ea1be6b18538fd940bca808fa7270b557b49cfddc4c47864e44
```

> **Alineación Temporal:** El uso estricto de la fecha de la sesión bursátil en hora de Nueva York (`America/New_York`) previene fallos por salto de día en UTC (que ocurre a las 20:00 ET en invierno / 19:00 ET en verano).

---

## 3. ESQUEMA DE PERSISTENCIA EN SQLITE

El gestor crea y mantiene la tabla transaccional `order_idempotency_records`:

```sql
CREATE TABLE IF NOT EXISTS order_idempotency_records (
    idempotency_key TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    strategy_fingerprint TEXT NOT NULL,
    market_session_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    signal_direction TEXT NOT NULL,
    evaluation_bar_timestamp TEXT NOT NULL,
    state TEXT NOT NULL,
    order_id TEXT,
    client_order_id TEXT,
    broker TEXT NOT NULL,
    reservation_timestamp TEXT NOT NULL,
    submission_timestamp TEXT,
    completion_timestamp TEXT,
    error_message TEXT,
    reconciliation_notes TEXT
);
```

La restricción `PRIMARY KEY` sobre `idempotency_key` garantiza atomicidad a nivel del motor de base de datos relacional: cualquier intento concurrente de inserción para la misma clave disparará de forma inmediata una excepción `sqlite3.IntegrityError`, impidiendo el avance a la fase de envío.

---

## 4. MÁQUINA DE ESTADOS TRANSACCIONALES

El ciclo de vida de una orden sigue una máquina de estados determinista de 7 fases:

```
          [Evaluación de Señal]
                    │
                    ▼
               ┌─────────┐
               │ RESERVED│ ◄─── (Inserción atómica en SQLite)
               └────┬────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  SUBMISSION_PENDING   │ ◄─── (Preparando payload de orden)
        └───────────┬───────────┘
                    │
                    ▼
               ┌─────────┐
               │SUBMITTED│ ◄─── (Transmitida al broker vía API)
               └────┬────┘
                    │
      ┌─────────────┴─────────────┐
      ▼                           ▼
┌────────────┐        ┌─────────────────────────────────┐
│ACKNOWLEDGED│        │ UNKNOWN_RECONCILIATION_REQUIRED │ ◄─── (Timeout de red o caída)
└─────┬──────┘        └───────────────┬─────────────────┘
      │                               │
      ├───────────────────┐           │ (Reconciliación con ledger de Moomoo)
      ▼                   ▼           ▼
  ┌────────┐         ┌──────────┐
  │ FILLED │         │ REJECTED │
  └────────┘         └──────────┘
```

### Definición de Estados:
1. `RESERVED`: Bloqueo atómico adquirido en base de datos. Ninguna otra orden para este símbolo/barra puede crearse.
2. `SUBMISSION_PENDING`: Generación del ID de orden cliente y preparación de la llamada API.
3. `SUBMITTED`: Mensaje emitido al gateway del broker (Moomoo Open API).
4. `ACKNOWLEDGED`: El broker confirmó la recepción de la orden y devolvió un `order_id`.
5. `FILLED`: Orden ejecutada total o parcialmente según confirmación del broker.
6. `REJECTED`: Orden rechazada por el broker o abortada de forma segura tras validación.
7. `UNKNOWN_RECONCILIATION_REQUIRED`: Fallo o timeout durante la comunicación. Requiere consulta forzada del ledger antes de cualquier reintento.

---

## 5. COBERTURA Y VERIFICACIÓN DE PRUEBAS UNITARIAS

El archivo `ai_trading_agent/tests/test_idempotency_protection.py` contiene 8 escenarios de prueba exhaustivos ejecutados con `pytest`:

| Nro | Escenario de Prueba | Comportamiento Verificado | Resultado |
| :---: | :--- | :--- | :---: |
| 1 | `test_1_concurrent_evaluations_same_symbol_suppressed` | 4 hilos concurrentes intentan reservar la misma orden. Exactamente 1 hilo adquiere la reserva; 3 son suprimidos. | **PASSED** |
| 2 | `test_2_restart_after_reserved_state` | Reinicio del sistema tras `RESERVED`. La reconciliación verifica que no hay orden en el broker y cancela la reserva de forma limpia. | **PASSED** |
| 3 | `test_3_restart_after_submitted_before_ack` | Caída del sistema tras el envío. Al reiniciar, el sistema consulta el broker, encuentra la orden ejecutada y transiciona a `FILLED`. | **PASSED** |
| 4 | `test_4_broker_timeout_transitions_to_unknown_reconciliation` | Timeout de red en la llamada del broker. El registro pasa a `UNKNOWN_RECONCILIATION_REQUIRED` evitando reenvíos a ciegas. | **PASSED** |
| 5 | `test_5_response_lost_broker_has_order` | La orden fue aceptada por el broker pero la respuesta HTTP se perdió. La reconciliación confirma la orden existente en el broker. | **PASSED** |
| 6 | `test_6_re_evaluation_same_bar_blocked` | Una re-evaluación periódica de la misma barra de mercado es bloqueada inmediatamente al detectar registro existente. | **PASSED** |
| 7 | `test_7_utc_date_rollover_during_ny_session` | Comprueba que dos eventos en la misma sesión de NY con diferente fecha UTC preservan la misma fecha de sesión y son dedupicados. | **PASSED** |
| 8 | `test_8_end_to_end_state_transitions` | Ciclo de vida completo desde `RESERVED` hasta `FILLED` con timestamps de inicio, envío y finalización. | **PASSED** |

**Resultado de la Suite:** `8 passed in 0.45s` (100% de éxito).
