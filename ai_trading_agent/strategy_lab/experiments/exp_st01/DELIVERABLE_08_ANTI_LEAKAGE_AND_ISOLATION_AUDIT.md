# DELIVERABLE 08 — AUDITORÍA FORENSE ANTI-LEAKAGE Y PROTOCOLO DE AISLAMIENTO
## Proyecto: OracleBot v2 / Strategy Laboratory | EXP-ST01

---

### 1. CONTROL DE FUGAS DE INFORMACIÓN (ANTI-LEAKAGE)

1. **Causalidad Temporal de Ejecución ($T 	o T+1$):**
   - Todas las señales se calculan estrictamente al cierre de la barra $T$.
   - La entrada al mercado se ejecuta hipotéticamente al precio `Open` de la barra $T+1$ con deslizamiento aditivo.
   - Prohibición absoluta de ejecuciones ficticias al precio `Close` de la misma barra que generó la señal.
2. **Cálculo Incremental de Indicadores:**
   - Wilder's Smoothing ATR y EMA(200) implementados de forma causal estado a estado (`IncrementalSuperTrend`).
   - Se verificó discrepancia cero (0 diferencias) entre el cálculo vectorizado y el procesamiento barra a barra en tiempo real.
3. **Resolución Conservadora de Colisiones Intra-Barra:**
   - Si en la misma barra $k$ el rango `[Low, High]` alcanza simultáneamente el nivel de Stop Loss y Take Profit, el motor aplica de forma forzosa la regla conservadora: **Stop Loss es ejecutado primero** (peor caso). Cero sesgo optimista.

---

### 2. PROTOCOLO DE AISLAMIENTO INSTITUCIONAL

- **Broker Conectado:** Ninguno en EXP-ST01. Modos `moomoo_client` desvinculados.
- **Estrategia en Producción PAPER D21:** `D21_RangeCompress_5d` (Fingerprint `f885ec2db2422308`, Capital virtual $1,000,000 USD) intacta, aislada y sin modificaciones.
- **Trading LIVE:** Estrictamente desactivado (`ENABLE_LIVE_TRADING = False`).
- **Persistencia Aislada:** Todos los datos y resultados se confinan a `ai_trading_agent/strategy_lab/experiments/exp_st01/`.
