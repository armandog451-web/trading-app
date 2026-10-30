# ORACLEBOT V2 — FASE 7.4
# DISEÑO DEL RUNTIME AUTÓNOMO Y PLANIFICADOR POST-CIERRE (BLOQUE C)

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Módulo:** `ai_trading_agent.strategy_lab.shadow`  
**Fecha:** 30 de octubre de 2026

---

## 1. PRINCIPIO DE DESACOPLAMIENTO OPERATIVO RESPECTO A D21

Para garantizar la estabilidad del supervisor 24/7 y proteger la campaña de certificación de D21 en Moomoo PAPER, el evaluador Shadow opera bajo un ciclo de vida **completamente independiente y desacoplado**.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR CENTRAL 24/7 (ORACLEBOT)                      │
│                                                                                  │
│   ┌───────────────────────────────────┐    ┌─────────────────────────────────┐   │
│   │    SCHEDULER D21 OPERATIVO        │    │    SHADOW EVALUATOR SCHEDULER   │   │
│   │    - Hora: 16:15:00 ET            │    │    - Hora: 16:30:00 ET          │   │
│   │    - Broker: Moomoo PAPER         │    │    - Broker: NINGUNO (AIR-GAP)  │   │
│   │    - Símbolos: SPY, QQQ, IWM, DIA │    │    - Símbolos: 6 ETFs           │   │
│   │    - Destino: SQLite / PAPER API  │    │    - Destino: Crypto Ledger     │   │
│   └───────────────────────────────────┘    └─────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

Ambos planificadores no comparten hilos, memoria de ejecución ni descriptores de conexión al broker.

---

## 2. CADENCIA DIARIA Y CICLOS DE EVALUACIÓN

El ciclo operativo diario del evaluador Shadow se estructura en tres fases claramente diferenciadas:

### Fase 1: Sesión Bursátil Activa (09:30 a 16:00 ET)
- **Apertura (09:30:00 ET):** Si existen órdenes de entrada encoladas desde el cierre de la sesión anterior $T-1$, el simulador procesa los fills al precio real de apertura con deslizamiento (`process_session_open_fills`).
- **Durante la sesión:** Monitoreo pasivo de disponibilidad de datos y comprobación de salud de procesos. Queda estrictamente prohibido generar órdenes anticipadas o ficticias durante la barra intradía.

### Fase 2: Consolidación Post-Cierre (16:30:00 ET)
- Transcurridos 30 minutos del toque de campana del NYSE (permitiendo la liquidación de las subastas de cierre oficiales):
  1. Descarga de barras cerradas de los 6 ETFs a través de `DataIntegrityGate`.
  2. Evaluación de salidas de posiciones abiertas (Stop-Loss, Take-Profit o Time-Exit).
  3. Ejecución de los modelos de señal para Candidate A y Candidate B.
  4. Encolamiento de órdenes hipotéticas para ejecutarse en la apertura de la siguiente sesión $T+1$.
  5. Escritura atómica en el ledger criptográfico `.jsonl` y exportación tabular.
  6. Actualización de los relojes de validación e hitos.

### Fase 3: Fines de Semana y Feriados
- Verificación exhaustiva de integridad matemática de la cadena SHA-256 (`verify_chain_integrity`).
- Generación de reportes semanales y cálculo de métricas acumuladas.
- Prohibición estricta de simular sesiones en días no laborables.

---

## 3. RESILIENCIA Y MANEJO DE ESTADOS EN MEMORIA

1. **Estado en Memoria:** Las posiciones abiertas y órdenes pendientes residen en el simulador `ShadowExecutionSimulator`.
2. **Espejo en Disco:** Cada cambio de estado se escribe de forma síncrona en el archivo `.jsonl` y en los archivos de reloj `validation_clock_<strategy_id>.json`.
3. **Recuperación tras Reinicio:** En caso de rearranque del servicio, el método `_load_and_verify_chain` reconstruye el estado exacto de la cartera desde el disco, garantizando una continuidad operativa sin pérdida de datos ni duplicación de registros.
