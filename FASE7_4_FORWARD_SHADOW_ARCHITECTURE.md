# ORACLEBOT V2 — FASE 7.4
# ARQUITECTURA DEL SISTEMA FROZEN FORWARD SHADOW VALIDATION

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Workspace canónico:** `trading-app-repo`  
**Módulo:** `ai_trading_agent.strategy_lab.shadow`  
**Fecha de implementación:** 30 de octubre de 2026  
**Modo de gobernanza:** `RESEARCH / ANALYSIS_ONLY`  
**Broker de producción/PAPER:** Moomoo (`TrdEnv.SIMULATE`) — **COMPLETAMENTE AISLADO**  
**Capital virtual D21:** $1,000,000 USD (Intacto e Inmutable)

---

## 1. MISIÓN Y VISIÓN ARQUITECTÓNICA

La **Fase 7.4** implementa el entorno institucional **Frozen Forward Shadow Validation**, diseñado para someter las dos estrategias cuantitativas líderes descubiertas y certificadas en las Fases 7.3 y 7.3A:
- **Candidato A:** `MR_VolCond_ZScore_V1` (Prioridad principal, Mean Reversion con volatilidad)
- **Candidato B:** `CS_RelMom_VolAdj_V2` (Segunda prioridad, Momentum relativo ajustado por volatilidad)

a un proceso de validación prospectiva riguroso, autónomo y causal, procesando **exclusivamente información de mercado generada con posterioridad a la fecha de congelamiento ($T_0$)**.

### 1.1 Invariantes Fundamentales de la Fase 7.4
1. **Sin Conexión a Brokers:** El sistema opera bajo un aislamiento de red y de proceso total (*air-gap*). No existen adaptadores de broker, claves de API de Moomoo ni capacidades de envío de órdenes.
2. **Prohibición de Trading PAPER y LIVE:** Ninguna estrategia experimental de la Fase 7.4 tiene autorización para enviar órdenes a Moomoo PAPER ni a cuentas reales.
3. **Inmunidad Absoluta de D21:** La estrategia canónica `D21_RangeCompress_5d` (fingerprint `f885ec2db2422308`, $1,000,000 USD virtual) continúa como la **única** autorizada en Moomoo PAPER, ejecutándose sin interferencia.
4. **Política Causal Estricta:** Toda señal calculada al cierre de una sesión $T$ se ejecuta hipotéticamente **en la apertura de la sesión negociable siguiente $T+1$**. Queda terminantemente prohibido asumir fills al precio de cierre de una barra que condiciona la señal.

---

## 2. DIAGRAMA ARQUITECTÓNICO DEL SISTEMA SHADOW

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MERCADO REAL (NYSE / NASDAQ)                         │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ (Post-Cierre 16:00 ET)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                DATA INTEGRITY GATE & NYSE CALENDAR VALIDATOR                   │
│  - Descarta barras intradía no cerradas                                         │
│  - Valida timestamps contra festivos y cierres anticipados del NYSE            │
│  - Rechaza cualquier dato anterior a T0 como evidencia forward                 │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ Barras Diarias Cerradas Saneadas
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS SHADOW EVALUATOR (FASE 7.4)                       │
│                                                                                 │
│   ┌───────────────────────────────┐     ┌───────────────────────────────────┐   │
│   │  Candidate A: MR_VolCond_V1   │     │   Candidate B: CS_RelMom_V2       │   │
│   │  (Single Asset: Z-Score/ATR)  │     │   (Cross-Sectional: Sharpe Mom)   │   │
│   └──────────────┬────────────────┘     └─────────────────┬─────────────────┘   │
└──────────────────┼────────────────────────────────────────┼─────────────────────┘
                   │ Señal T (Queue Orden T+1)              │ Señal T (Queue Orden T+1)
                   ▼                                        ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│  SHADOW SIMULATOR A (Capital $100k)   │ │  SHADOW SIMULATOR B (Capital $100k)   │
│  - Fills en Apertura T+1 con slippage │ │  - Fills en Apertura T+1 con slippage │
│  - Modelado de Gaps y Salidas Intradía│ │  - Modelado de Gaps y Salidas Intradía│
│  - Control de Concurrencia y Efectivo │ │  - Control de Concurrencia y Efectivo │
└──────────────────┬────────────────────┘ └─────────────────┬─────────────────────┘
                   │ Eventos Atómicos                       │ Eventos Atómicos
                   ▼                                        ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│     EVIDENCE LEDGER A (APPEND-ONLY)   │ │     EVIDENCE LEDGER B (APPEND-ONLY)   │
│  - Encadenamiento SHA-256 Block-Hash  │ │  - Encadenamiento SHA-256 Block-Hash  │
│  - Detección de Alteraciones (Tamper) │ │  - Detección de Alteraciones (Tamper) │
│  - Registro de Días Sin Señal         │ │  - Registro de Días Sin Señal         │
└──────────────────┬────────────────────┘ └─────────────────┬─────────────────────┘
                   │                                        │
                   └───────────────────┬────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    FORWARD VALIDATION CLOCKS & REPORTING                        │
│  - Contadores: Sesiones válidas, operaciones abiertas/cerradas, gaps, fallos    │
│  - Hitos de madurez: 20 sesiones (Salud), 60 sesiones (Prelim), 90 (Madurez)    │
│  - Reportes Diarios y Semanales Markdown/JSON                                   │
│  - Notificaciones salientes Telegram ("RESEARCH SHADOW — NO BROKER ORDERS")     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. COMPONENTES PRINCIPALES DEL SISTEMA

### 3.1 Manifiestos de Congelamiento Criptográfico (`CampaignFreezeManifest`)
Ubicados en [`ai_trading_agent/strategy_lab/shadow/freeze_manifests.py`](file:///C:/Users/edsel/Documents/trading-app-repo/ai_trading_agent/strategy_lab/shadow/freeze_manifests.py). Congelan de manera determinista:
- Código fuente exacto (`code_sha256` de 64 caracteres).
- Parámetros operativos inmutables (`parameters_sha256`).
- Huella digital combinada de la estrategia (`combined_strategy_fingerprint_sha256`).
- Universo de 6 ETFs institucionales: `SPY`, `QQQ`, `IWM`, `DIA`, `XLF`, `XLE`.
- Presupuesto de capital: $100,000 USD virtual por estrategia.

### 3.2 Simulador de Ejecución Causal (`ShadowExecutionSimulator`)
Ubicado en [`ai_trading_agent/strategy_lab/shadow/shadow_simulator.py`](file:///C:/Users/edsel/Documents/trading-app-repo/ai_trading_agent/strategy_lab/shadow/shadow_simulator.py). Implementa:
- Encolamiento de órdenes en cierre $T$ $\to$ ejecución en apertura $T+1$.
- Tres escenarios de costes paralelos (1x Base, 2x Moderado, 3x Severo).
- Modelado de aperturas con gap adverso (si el precio de apertura cae bajo el stop-loss, se llena al precio de gap real y no al stop teórico).
- Asignación de riesgo por trade ($250 USD) y límite estricto de concurrencia y liquidez disponible.

### 3.3 Libro Mayor Criptográfico Inmutable (`ShadowEvidenceLedger`)
Ubicado en [`ai_trading_agent/strategy_lab/shadow/crypto_ledger.py`](file:///C:/Users/edsel/Documents/trading-app-repo/ai_trading_agent/strategy_lab/shadow/crypto_ledger.py). Implementa:
- Encadenamiento criptográfico: cada registro incluye `prev_entry_hash` y calcula su propio `entry_hash = SHA256(prev_hash | payload)`.
- Detección inmediata de manipulaciones manuales o corrupción (`LedgerTamperDetectedError`).
- Registro obligatorio de todas las decisiones, incluidos los días con régimen de abstención o sin señal (`NO_SIGNAL`).

### 3.4 Reloj de Validación Forward (`ShadowValidationClock`)
Gestiona 8 contadores independientes por estrategia:
1. `calendar_days_since_t0`
2. `market_sessions_elapsed`
3. `valid_shadow_evaluation_sessions`
4. `shadow_signals_generated`
5. `shadow_positions_opened`
6. `shadow_positions_closed`
7. `data_quality_failures`
8. `runtime_gaps`

---

## 4. CONCLUSIÓN Y ESTADO DE AISLAMIENTO

La arquitectura se encuentra completamente desacoplada del supervisor de producción, no comparte tablas de base de datos ni memoria con Moomoo y garantiza la acumulación incorruptible de evidencia prospectiva.
