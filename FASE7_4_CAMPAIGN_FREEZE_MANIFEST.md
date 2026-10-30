# ORACLEBOT V2 — FASE 7.4
# MANIFIESTO INSTITUCIONAL DE CONGELAMIENTO CRIPTOGRÁFICO DE CAMPAÑAS (BLOQUE A)

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fecha y hora oficial de congelamiento:** `2026-10-30T16:00:00Z`  
**Sesión bursátil T0 (Primera sesión prospectiva):** `2026-11-02` (Lunes hábil NYSE)  
**Estado oficial:** `COLLECTING_EVIDENCE`

---

## 1. ESPECIFICACIÓN DEL CONGELAMIENTO DE CÓDIGO Y ENTORNO

Antes de procesar cualquier dato prospectivo, se congeló de forma inmutable la versión del motor de descubrimiento y backtest:

- **Archivo de código base:** `ai_trading_agent/strategy_lab/discovery/discovery_engine_v2.py`
- **Hash SHA-256 completo del código (64 hex):**  
  `e83b4fd3f7c4e209864ea511c5658e3cb1a3a41982b6b55d78ec335c02bc57ae`
- **Entorno de ejecución:** Python 3.11.17 / Windows x86_64
- **Modo de Gobernanza:** `RESEARCH / ANALYSIS_ONLY` (Trading LIVE bloqueado físicamente)
- **Conexión a Broker:** `AIR_GAPPED_NONE` (Cero credenciales, cero sockets)

---

## 2. CAMPAÑA 1: CANDIDATO A — `MR_VolCond_ZScore_V1`

### 2.1 Identificadores Inmutables
- **Campaign ID:** `CAMP-SHADOW-20261030-MR-VOL-1`
- **Strategy ID:** `MR_VolCond_ZScore_V1`
- **Hipótesis ID:** `H-MR-VOL-1`
- **Familia Cuantitativa:** `VOLATILITY_CONDITIONED_REVERSION`
- **Fingerprint Combinado SHA-256 (64 hex):**  
  `00ee941191ec4d515f401f89c6691461fffa34eeb8b688bb0272cbb09ba66d62`

### 2.2 Hiperparámetros Congelados
```json
{
  "z_lookback": 20,
  "z_threshold": -2.0,
  "atr_period": 14,
  "atr_expansion_mult": 1.10,
  "rsi_period": 4,
  "rsi_threshold": 20.0,
  "max_holding": 4,
  "stop_loss_pct": 0.025,
  "profit_target_pct": 0.035
}
```
- **Hash SHA-256 de parámetros:**  
  `2f0914d9e03d42ae3a7b69b2d3550e501a3556bfcf5b3dc43ef6ff5733f01908`

### 2.3 Reglas Operativas y de Riesgo
- **Universo Elegible:** `SPY`, `QQQ`, `IWM`, `DIA`, `XLF`, `XLE`.
- **Capital Asignado:** $100,000.00 USD (Virtual de laboratorio, completamente aislado de D21).
- **Riesgo por Operación:** $250.00 USD (0.25% del subportafolio).
- **Límite de Concurrencia:** Máximo 1 posición simultánea por activo (hasta 6 en total).
- **Política Temporal:** `SIGNAL_AT_CLOSE_T_EXECUTE_AT_OPEN_T_PLUS_1`.

### 2.4 Referencia Histórica Congelada (Línea Base Retrospectiva)
> [!WARNING]
> Estas métricas corresponden a `PREVIOUSLY_EXAMINED_HISTORICAL_DATA` (2022–2026) y se registran **únicamente como punto de comparación analítico**, quedando estrictamente excluidas de los contadores forward de la Fase 7.4.
- Operaciones históricas: 53
- Net PnL histórico: +$6,556.24 USD
- Net Profit Factor histórico: 2.94
- Sharpe histórico: 1.43
- Drawdown máximo histórico: 0.63%
- Research Ranking Score: 0.923

---

## 3. CAMPAÑA 2: CANDIDATO B — `CS_RelMom_VolAdj_V2`

### 3.1 Identificadores Inmutables
- **Campaign ID:** `CAMP-SHADOW-20261030-MOM-REL-2`
- **Strategy ID:** `CS_RelMom_VolAdj_V2`
- **Hipótesis ID:** `H-MOM-REL-2`
- **Familia Cuantitativa:** `CROSS_SECTIONAL_MOMENTUM`
- **Fingerprint Combinado SHA-256 (64 hex):**  
  `d6a74be66a01cb6982823674646ec39d1b09b52a1290bb353cfc0ea8881249b6`

### 3.2 Hiperparámetros Congelados
```json
{
  "rebalance_period": 10,
  "momentum_lookback": 60,
  "top_n_assets": 2,
  "max_holding": 10,
  "stop_loss_pct": 0.030,
  "profit_target_pct": 0.050
}
```
- **Hash SHA-256 de parámetros:**  
  `719ec0ea9f2a996f01da0e69dc033e5fbcf67e231145b59724032d849fa86141`

### 3.3 Reglas Operativas y de Riesgo
- **Universo Elegible:** `SPY`, `QQQ`, `IWM`, `DIA`, `XLF`, `XLE`.
- **Capital Asignado:** $100,000.00 USD virtual.
- **Riesgo por Operación:** $250.00 USD.
- **Límite de Concurrencia:** Máximo 2 posiciones simultáneas en toda la cartera.
- **Política Temporal:** `SIGNAL_AT_CLOSE_T_EXECUTE_AT_OPEN_T_PLUS_1`.

### 3.4 Referencia Histórica Congelada
- Operaciones históricas: 133
- Net PnL histórico: +$6,115.96 USD
- Net Profit Factor histórico: 1.52
- Sharpe histórico: 0.94
- Drawdown máximo histórico: 1.60%
- Research Ranking Score: 0.572

---

## 4. ESTRATEGIAS ARCHIVADAS (SIN EJECUCIÓN FORWARD)

En cumplimiento de la orden directiva, las siguientes estrategias permanecen congeladas en archivo de investigación secundaria, **sin ejecución prospectiva activa**:
1. `MR_VolCond_BBCompression_V2` (H-MR-VOL-2)
2. `CS_RelMom_60d_V1` (H-MOM-REL-1)
