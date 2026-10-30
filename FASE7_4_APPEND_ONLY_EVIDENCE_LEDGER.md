# ORACLEBOT V2 — FASE 7.4
# ESPECIFICACIÓN DEL LIBRO MAYOR DE EVIDENCIA CRIPTOGRÁFICA INMUTABLE (BLOQUE E)

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Módulo:** `ai_trading_agent.strategy_lab.shadow.crypto_ledger`  
**Fecha:** 30 de octubre de 2026

---

## 1. PRINCIPIO DE INMUTABILIDAD Y EVIDENCIA FORWARD

El propósito del `ShadowEvidenceLedger` es proporcionar un registro append-only de grado forense que demuestre con certeza matemática que:
1. Ninguna operación fue alterada retroactivamente tras conocer el resultado del mercado.
2. Ningún parámetro fue reajustado durante la recopilación.
3. Todas las sesiones bursátiles fueron registradas de forma exhaustiva, incluyendo expresamente los días en que el sistema decidió abstenerse de operar (`NO_SIGNAL`).

---

## 2. MECANISMO DE ENCADENAMIENTO CRIPTOGRÁFICO (BLOCK-HASH CHAINING)

El ledger implementa una estructura criptográfica encadenada inspirada en registros distribuidos inmutables:

$$H_0 = \text{GENESIS\_PREV\_HASH} = \text{"0000000000000000000000000000000000000000000000000000000000000000"}$$

$$H_i = \text{SHA-256}\left(H_{i-1} \;\Big|\; \text{canonical\_json}(\text{Payload}_i)\right)$$

Donde $\text{canonical\_json}$ ordena lexicográficamente todas las claves y utiliza delimitadores estandarizados sin espacios, garantizando que la huella digital sea idéntica en cualquier plataforma o lenguaje de programación.

### 2.1 Campos Obligatorios por Entrada
Cada línea del archivo `.jsonl` contiene la tupla canónica completa:
1. `entry_id`: Identificador idempotente único (ej. `EVAL-SIG-MR_VolCond_ZScore_V1-QQQ-20261102`).
2. `entry_index`: Índice correlativo incremental ($0, 1, 2, \dots$).
3. `campaign_id`: ID oficial de la campaña (`CAMP-SHADOW-20261030-MR-VOL-1`).
4. `strategy_id`: Nombre canónico de la estrategia.
5. `strategy_fingerprint_sha256`: Hash de 64 caracteres de la estrategia congelada.
6. `market_date`: Fecha bursátil en formato ISO (`YYYY-MM-DD`).
7. `timestamp_utc`: Marca de tiempo de evaluación precisa.
8. `symbol`: Símbolo del activo evaluado.
9. `event_type`: Tipo de evento (`SIGNAL_GENERATED`, `ORDER_FILLED`, `POSITION_CLOSED`, `NO_SIGNAL`, etc.).
10. `signal_direction`: Dirección operativa (`BUY`, `SELL`, `HOLD`, `NO_TRADE`).
11. `reason`: Justificación cuantitativa explícita de la decisión.
12. `bar_hash_sha256`: Hash criptográfico de la barra diaria utilizada como insumo.
13. `simulated_order`: Diccionario con detalles de la orden encolada.
14. `simulated_fill`: Diccionario con detalles del llenado y costes reales.
15. `open_position`: Estado de la posición (precio medio, stop, target, barras acumuladas).
16. `realized_gross_pnl`: Beneficio bruto cerrado en USD.
17. `realized_net_pnl`: Beneficio neto cerrado en USD.
18. `costs_usd`: Suma de slippage y comisiones en USD.
19. `portfolio_cash`: Efectivo disponible en la cartera.
20. `portfolio_equity`: Valor liquidativo mark-to-market.
21. `drawdown_pct`: Drawdown porcentual acumulado.
22. `prev_entry_hash`: Hash del bloque inmediatamente anterior $H_{i-1}$.
23. `entry_hash`: Hash resultante del bloque actual $H_i$.

---

## 3. DETECCIÓN AUTOMÁTICA DE MANIPULACIONES (*TAMPER DETECTION*)

El método `verify_chain_integrity()` recorre todo el historial desde el bloque génesis hasta el último registro:
- Si un solo bit o carácter de una sesión pasada es modificado en el disco, el hash recomputado no coincidirá con `entry_hash`, o el bloque siguiente presentará un `prev_entry_hash` discordante.
- En caso de alteración, el sistema aborta de inmediato con la excepción irreversible `LedgerTamperDetectedError`, bloqueando el motor e impidiendo la adición de nueva evidencia sobre un historial corrompido.

---

## 4. REGISTRO OBLIGATORIO DE DÍAS SIN SEÑAL (*NO_SIGNAL*)

En cumplimiento estricto del Bloque C de la directiva, el evaluador emite una entrada en el ledger para cada activo del universo durante cada sesión bursátil válida, aun cuando no se cumplan los criterios de entrada:
- `event_type`: `NO_SIGNAL`
- `signal_direction`: `NO_TRADE`
- `reason`: Explicación de por qué no se activó la compuerta cuantitativa (ej. *"Condición de sobreventa o expansión no alcanzada"* o *"Fuera de ventana de rebalanceo"*).

Esto previene el sesgo de selección y prueba fehacientemente que el sistema evaluó el mercado diariamente.

---

## 5. PERSISTENCIA Y RECONCILIACIÓN ANTE REINICIOS

- **Formato primario:** Archivo JSON Lines (`shadow_ledger_<strategy_id>.jsonl`) en modo append atómico.
- **Formato de operaciones:** Archivo CSV tabular (`shadow_trades_<strategy_id>.csv`) generado de forma continua para análisis en hojas de cálculo y Pandas.
- **Resiliencia:** Al reiniciar el proceso o el servidor, el ledger lee el archivo `.jsonl`, verifica íntegramente la cadena de hashes y restaura las posiciones y contadores de capital sin duplicar eventos ni fabricar datos sintéticos.
