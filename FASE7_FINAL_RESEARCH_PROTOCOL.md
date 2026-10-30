# PROTOCOLO DE INVESTIGACIÓN INSTITUCIONAL FASE 7.0 (CORREGIDO)
## EXPLORACIÓN CONTROLADA DE ESTRATEGIAS MOMENTUM Y REVERSIÓN A LA MEDIA

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.0 — Protocolo de Investigación Cuantitativa Aislada  
**Modo Operativo Mandatorio:** `RESEARCH / ANALYSIS_ONLY`  
**Conexión a Broker:** **ESTRICTAMENTE BLOQUEADA (AIR-GAPPED)**  
**Fecha de Emisión:** 30 de Octubre de 2026  
**Aprobación:** AUTORIZACIÓN CONDICIONADA FASE 7.0  

---

## 1. PRINCIPIOS DE GOBERNANZA Y AISLAMIENTO FÍSICO

En estricto cumplimiento de la autorización institucional para la Fase 7.0, se establecen las siguientes restricciones innegociables:

1. **Aislamiento Total de Producción:** Todas las hipótesis, modelos y algoritmos de la Fase 7.0 se desarrollan y evalúan exclusivamente en el módulo `ai_trading_agent.strategy_lab.fase7_research`.
2. **Cero Conexión a Brokers:** Queda físicamente prohibido conectar cualquier estrategia de la Fase 7.0 a Moomoo (`TrdEnv.SIMULATE` o `REAL`), al `PaperFidelityEngine` o a adaptadores de broker. Cualquier intento de envío dispara una excepción `ResearchIsolationViolation`.
3. **Inmutabilidad Absoluta de D21:** `D21_RangeCompress_5d` continúa siendo la **única** estrategia autorizada en la campaña de validación PAPER. Sus reglas, parámetros, fingerprint `f885ec2db2422308`, límites de riesgo y contadores históricos permanecen inalterados.
4. **Modo Operativo del Sistema:** El servidor opera bajo la guarda `ANALYSIS_ONLY`. La bandera `ENABLE_LIVE_TRADING` permanece en `False` (físicamente bloqueada).

---

## 2. RESTRICCIÓN ESTRICTA DE REGÍMENES DE MERCADO

La investigación utilizará **única y exclusivamente** los tres regímenes existentes en el Detector de Regímenes v1 ([`MarketRegimeV1`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/dual_strategy/regime.py)):

| Régimen Existente | Criterios Cuantitativos Deterministas | Familia de Estrategia Permitida |
| :--- | :--- | :--- |
| **`TRENDING_BULL`** | $\text{ADX}(14) \ge 25 \land \text{ER}(20) \ge 0.35 \land \text{Close} > \text{SMA}(50)$ | **Momentum / Trend Pullback** |
| **`RANGING`** | $\text{ADX}(14) < 20 \land \text{ER}(20) < 0.25$ | **Mean Reversion (RSI / Bollinger)** |
| **`INDETERMINATE`** | Transición, alta dispersión o condiciones ambiguas | **ABSTENCIÓN OBLIGATORIA (`NO_TRADE`)** |

> **Regla de Abstención Institucional:** Ante el régimen `INDETERMINATE`, ambas familias de estrategias deben emitir `SignalDirection.NO_TRADE` de forma inmediata. Se prohíbe operar en mercados sin estructura direccional o lateral definida.

---

## 3. PROTOCOLO TEMPORAL CORREGIDO: DISTINCIÓN ENTRE DATOS EXAMINADOS Y PROSPECTIVOS

Para garantizar la honestidad intelectual y evitar el sesgo de supervivencia o "data snooping", se corrige formalmente el protocolo de datos, distinguiendo explícitamente el histórico ya examinado en fases anteriores de los datos genuinamente no examinados:

```
┌─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┐
│     PARTICIÓN 1: HISTÓRICO      │     PARTICIÓN 2: AUDITORÍA      │     PARTICIÓN 3: PROSPECTIVO    │
│     EXPLORATORIO EXAMINADO      │     HOLDOUT PREVIO EXAMINADO    │     GENUINO NO EXAMINADO        │
├─────────────────────────────────┼─────────────────────────────────┼─────────────────────────────────┤
│    2018-01-01 a 2024-12-31      │    2025-01-01 a 2026-10-05      │     2026-10-21 en adelante      │
│                                 │                                 │                                 │
│ • Datos examinados en Fases 1-6 │ • Datos evaluados en Fase 10    │ • Datos de mercado en vivo      │
│ • Utilizados para formulación   │   (Holdout ciego histórico)     │   recolectados sesión a sesión  │
│   de hipótesis y calibración    │ • NO pueden tratarse como datos │ • PROHIBIDO retro-alimentar     │
│   inicial de indicadores        │   desconocidos en Fase 7        │   en entrenamiento              │
└─────────────────────────────────┴─────────────────────────────────┴─────────────────────────────────┘
```

### Reglas de Uso de Particiones:
1. **Partición 1 (Histórico Exploratorio):** Permite calibración de parámetros (ej. períodos de RSI, umbrales de ADX, distancias de ATR).
2. **Partición 2 (Holdout Previo Examinado):** Se utiliza únicamente como referencia de contraste histórico. **No se computa como evidencia out-of-sample limpia**, dado que fue auditada previamente en la Fase 10.3.
3. **Partición 3 (Prospectivo Genuino):** Se nutre exclusivamente de las sesiones cerradas a partir de la restauración canónica (2026-10-21). Las estrategias de Fase 7 solo observarán esta partición en modo "shadow" analítico una vez que concluyan su fase de laboratorio.

---

## 4. MODELO DE COSTES Y CONDICIONES DE AUDITORÍA

Todo backtest preliminar en Fase 7.0 debe incorporar obligatoriamente el siguiente modelo de fricción:
- **Comisión:** \$0.005 USD por acción (doble vía: entrada y salida).
- **Deslizamiento (Slippage):** 5.0 bps ($0.05\%$) sobre el precio de cierre de la barra.
- **Riesgo Máximo por Operación:** 0.25% del capital analítico asignado (\$2,500 USD sobre \$1,000,000 USD).
- **Capacidad de Concurrencia:** Máximo 2 posiciones abiertas simultáneas.

---

## 5. POLÍTICA DE PROMOCIÓN

- **Cero Promoción Automática:** Ninguna estrategia desarrollada en Fase 7.0 puede promocionarse a `PAPER` sin una sesión formal de revisión, auditoría de robustez Monte Carlo y autorización expresa del usuario.
- **Estado de Registro:** Todas las variantes quedan registradas en `StrategyStatus.RESEARCH`.
