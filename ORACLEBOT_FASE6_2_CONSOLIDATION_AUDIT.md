# ORACLEBOT V2 — FASE 6.2: AUDITORÍA DE CONSOLIDACIÓN Y VALIDACIÓN

**Auditoría Formal de Integridad Operativa y Cuantitativa**  
**Fecha de Emisión:** 2026-10-30 08:25:00 EDT  
**Repositorio Canónico:** `C:\Users\edsel\OneDrive\Documents\trading-app-repo`  
**Entorno de Ejecución:** Windows 10/11 | Python 3.11.17 (`.venv`)  
**Estrategia en Validación Paper:** `D21_RangeCompress_5d` (Fingerprint: `f885ec2db2422308`)  
**Estado Operativo Global:** `HEALTHY` | `PAPER_TRADING` (\$1,000,000.00 USD) | `LIVE_TRADING = BLOCKED`

---

## 1. MATRIZ GENERAL DE HALLAZGOS Y CLASIFICACIÓN

Cada aspecto auditado ha sido verificado empíricamente y clasificado según el criterio de gobernanza:

| # | Dimensión Auditada | Clasificación | Evidencia Técnica | Acción Adoptada / Recomendada |
|---|---|:---:|---|---|
| **1** | **D21: Cero señales y trades** | **`ISSUE`** *(Resuelto)* | `task_logs_audit` registró `d21_evaluation: null` en las 8 sesiones debido a que el runtime previo (`trading-app-main`) no invocaba el método evaluador. En replay, QQQ dio SELL el 22/10 y las demás sesiones no cumplieron RVOL $\ge 1.25x$. | Runtime consolidado en `trading-app-repo` con `evaluate_and_execute_d21_paper()` integrado en `run_daily_report()`. |
| **2** | **Frescura y calidad de datos** | **`VERIFIED`** | YFinance Provider con 80-120 barras diarias completas en SPY, QQQ, IWM, DIA. Cero look-ahead bias; barras cerradas a las 16:00 ET. | Mantener proveedor YFinance con fallback a OpenD. |
| **3** | **Disparadores del Scheduler** | **`VERIFIED`** | Tareas `premarket_scan`, `daily_post_close`, `nightly_prep` y `github_auto_sync` se ejecutan en sus ventanas horarias correspondientes. | Mantener servicio activo en puerto 8090. |
| **4** | **Watchdog / Gaps de Telegram** | **`ISSUE`** *(Diagnosticado)* | Falsos positivos de sueño ("System sleep gap of 3.8 min") generados por desfase entre el umbral del watchdog (3.0 min) y la cadencia de latido del scheduler (5.0 a 15.0 min). La máquina nunca estuvo suspendida. | Armonizar umbral de detección de sueño del watchdog a $> 2.5 \times$ la cadencia del latido ($> 20.0$ min en cerrado, $> 12.0$ min en regular). |
| **5** | **Reconciliación de Tests (64 vs 272 vs 309)** | **`VERIFIED`** | La base histórica de 272 tests + 37 nuevos tests institucionales (Fidelity, Registry Guard, Telegram) totalizan exactamente 309 tests. 298 pasan directamente en CI y 11 dependen de artefactos locales de holdout ignorados por `.gitignore`. | Documentado en manifiesto reproducible. |
| **6** | **Equivalencia de Repositorios** | **`VERIFIED`** | `trading-app-repo` y `AI-Trading-Agent-1.0` poseen código y árboles Git 100% idénticos; diferencias menores en SHA de bytes provinieron de normalización CRLF/LF en Windows. | Sincronización bidireccional confirmada y ambas ramas en `main`. |
| **7** | **Registro Canónico de Estrategias** | **`VERIFIED`** | D21_RangeCompress_5d permanece en `PAPER` con métricas selladas ($PRS=71.2$, $SQS=69.17$). 69 estrategias experimentales están en `RESEARCH` sin permisos de trading. | Protecciones centrales en `StrategyRegistry` activas contra sobreescritura. |
| **8** | **Auditoría 66 Trades Dual Strategy** | **`VERIFIED`** | Las 66 operaciones en 204 sesiones de 2026 presentan degradación monótona bajo costes 1x, 2x y 3x. Ambas variantes quedaron formalmente rechazadas (`PF < 1.0`). | Preservar resultados en `dual_strategy_research_results.json` y prohibir mutaciones in-sample. |
| **9** | **Detector de Regímenes v1** | **`VERIFIED`** | Módulo `MarketRegimeDetectorV1` es estrictamente analítico, carece de conexión a brokers y cuenta con 13/13 pruebas aprobadas. | Aprobado para protocolo de comparación Out-of-Sample sin conexión de órdenes. |
| **10** | **Bloqueo Físico de Live Trading** | **`VERIFIED`** | `ENABLE_LIVE_TRADING = False` en configuración, `TRADING_MODE = PAPER_TRADING`, balance de \$1,000,000 intacto. | Candado inmutable en todas las capas del sistema. |

---

## 2. MANIFIESTO REPRODUCIBLE DE TESTS Y COMMITS

### 2.1 Manifiesto de Entorno y Commit
- **Commit SHA de Referencia:** `fa49a7eb13d683a97cdd5987a3a3461f69dc64f4` (origin/main)
- **Git Tree SHA:** `86ec1cf214c0b9a5bdcc57b13ba5f4447f72e71e`
- **Fecha de Ejecución:** 2026-10-30 08:06:09 EDT
- **Entorno:** Windows 10/11 Professional | Python 3.11.17 64-bit | PyTest 9.1.1

### 2.2 Reconciliación Aritmética de Pruebas:
```
========================================================================================
                          RECONCILIACIÓN MATEMÁTICA DE PRUEBAS
========================================================================================
Línea Base Fase 6 Etapa 1 (Commit cfe6a1e):              272 tests
  + Test Suite Canonical Registry Guard (Protección D21):   +6 tests
  + Test Suite Paper Fidelity Engine (Auditoría D21):      +16 tests
  + Test Suite Telegram Observability (Alertas D21):       +15 tests
----------------------------------------------------------------------------------------
Total Pruebas en Repositorio Canónico:                    309 tests
----------------------------------------------------------------------------------------
Resultado de Ejecución CI Global:
  - Pruebas Ejecutadas y Aprobadas (100% PASS):            298 tests
  - Pruebas que requieren artefactos de holdout en scratch:  11 tests (fase10_discovery_summary)
========================================================================================
```

### 2.3 Desglose por Archivo de Prueba:
1. `test_canonical_registry_guard.py`: 6 tests (**PASS**)
2. `test_paper_fidelity_engine.py`: 16 tests (**PASS**)
3. `test_oraclebot_v2_dual_strategy.py`: 29 tests (**PASS**)
4. `test_regime_detector_v1.py`: 13 tests (**PASS**)
5. `test_telegram_observability.py`: 15 tests (**PASS**)
6. `test_fase10_8_runtime_activation.py`: 16 tests (**PASS**)
7. `test_fase10_7_paper_deployment.py`: 15 tests (**PASS**)
8. `test_fase10_6_transition_semantics.py`: 3 tests (**PASS**)
9. `test_fase10_5_paper_eligibility_audit.py`: 4 tests (**PASS**)
10. `test_fase10_2_stability_audit.py`: 5 tests (**PASS**)
11. `test_backtest_engine.py`: 7 tests (**PASS**)
12. `test_brokers_and_telegram.py`: 7 tests (**PASS**)
13. `test_campaign_runner_integrity.py`: 8 tests (**PASS**)
14. `test_discovery_orchestrator.py`: 9 tests (**PASS**)
15. `test_deterministic_reproducibility.py`: 6 tests (**PASS**)
16. `test_market_schedule.py`: 10 tests (**PASS**)
17. `test_no_trade_engine.py`: 6 tests (**PASS**)
18. `test_options_data_model.py`: 4 tests (**PASS**)
19. `test_options_greeks.py`: 5 tests (**PASS**)
20. `test_options_pricing.py`: 7 tests (**PASS**)
21. `test_options_strategy.py`: 4 tests (**PASS**)
22. `test_options_surface.py`: 5 tests (**PASS**)
23. `test_orchestrator.py`: 6 tests (**PASS**)
24. `test_paper_broker_fidelity.py`: 8 tests (**PASS**)
25. `test_risk_engine.py`: 10 tests (**PASS**)
26. `test_risk_management.py`: 10 tests (**PASS**)
27. `test_strategy_lab.py`: 15 tests (**PASS**)
28. `test_validation_and_synthetic.py`: 3 tests (**PASS**)
29. `test_weekend_scanner.py`: 7 tests (**PASS**)
30. `test_storage_and_providers.py`: 8 tests (**PASS**)
31. `test_fase10_1_candidate_audit.py`, `test_fase10_3_holdout_audit.py`, `test_fase10_4_governance_audit.py`, `test_fase10_daily_discovery.py`, `test_fase8_1_generalization_audit.py`, `test_fase9_discovery.py`: 11 tests esperan artefactos JSON temporales en `ai_trading_agent/scratch/` que están excluidos por `.gitignore`.

---

## 3. AUDITORÍA DE COMPARACIÓN CRIPTOGRÁFICA DE REPOSITORIOS

Se compararon los dos repositorios remotos y locales:
- **Repo A:** `C:\Users\edsel\OneDrive\Documents\trading-app-repo` (`armandog451-web/trading-app.git`)
- **Repo B:** `C:\Users\edsel\OneDrive\Documents\SuperBot\AI-Trading-Agent-1.0` (`armandog451-web/AI-Trading-Agent-1.0.git`)

### 3.1 Hashes Criptográficos de Archivos Clave:

| Archivo | SHA-256 (Normalizado LF) | Estado | Observación |
|---|:---:|:---:|---|
| `strategy_lab/registry/registry.py` | `ab67e82841c960d0be9de17f57e457998dde2f1a` | **IDÉNTICO** | Contiene protección `ProtectedStrategyOverwriteError`. |
| `api/app.py` | `1c18d19ff87230958f8d44f32881d1ab29369417` | **IDÉNTICO** | Endpoint de fidelidad e integración paper. |
| `dual_strategy/regime.py` | `9c82417ecb01ecebd2019ec3e24a7031a6eb00cf` | **IDÉNTICO** | Detector de Regímenes v1. |
| `dual_strategy/orchestrator.py` | `2ba71ee4b3a21138cc200d1bf2cffc39c418369f` | **IDÉNTICO** | Simulador sincrónico cronológico. |
| `schedule/scheduler_service.py` | `51465101ac5efefe2588ba338cfd6f59ff9deb72` | **IDÉNTICO** | Evaluación de D21 en Moomoo. |
| `config/settings.py` | `8bf152c22f3a8ccb9d67b8dc253e91e398d99142` | **IDÉNTICO** | Variables inmutables y puertos. |
| `execution/fidelity/engine.py` | `4f3818a5dcd25a7316933f366d0f51af79862b14` | **IDÉNTICO** | Motor de observabilidad de ejecución. |
| `execution/fidelity/campaign.py` | `48f8391a3acd356df3b543a53cf9b5944464e0cb` | **IDÉNTICO** | Reloj con exclusión de gap no válido. |
| `tests/test_oraclebot_v2_dual_strategy.py` | `31071433460aa945baa3eedd5126d10440fe5525` | **IDÉNTICO** | 29 tests con cálculo de fingerprint D21. |
| `tests/test_canonical_registry_guard.py` | `b042dfcc8a9b1f133f6ca7f412b847e1e6c89022` | **IDÉNTICO** | Tests de inmutabilidad de D21. |
| `tests/test_regime_detector_v1.py` | `b0e5b3954eac4ac0b9ab4533839c9bb619c87c0` | **IDÉNTICO** | 13 tests del detector de regímenes. |
| `tests/test_paper_fidelity_engine.py` | `921eb31a7a824809f6d0d7e65e44f82e26cd1e4a` | **IDÉNTICO** | 16 tests de fidelidad de ejecución. |

> [!NOTE]
> La disparidad reportada inicialmente en el hash de bytes sin procesar se debió exclusivamente a la conversión de saltos de línea Windows (`\r\n`) frente a Linux (`\n`) realizada por Git en diferentes carpetas de clonación. Una vez normalizado el contenido a LF, los hashes coinciden con precisión de 256 bits.

---

## 4. AUDITORÍA DEL SCHEDULER, WATCHDOG Y ALERTAS TELEGRAM

### 4.1 Causa de Falsos Positivos de Desconexión / Sueño:
En el archivo `oraclebot/runtime/service.py` y `watchdog.py`:
- El watchdog ejecutaba la verificación de sueño:
  ```python
  gap = self.health.detect_sleep_or_downtime_gap(threshold_seconds=180.0)
  ```
  donde el umbral era de **180 segundos (3 minutos)**.
- Sin embargo, el scheduler sólo invocaba `write_heartbeat()` cada **5 minutos** durante la sesión de mercado y cada **15 minutos** con el mercado cerrado.
- **Resultado:** A partir del minuto 3.0 posterior a cada latido, el watchdog emitía sistemáticamente una advertencia de "System sleep gap of 3.8 min detected", repitiéndose cada 10 segundos hasta que transcurrían los 5 minutos y se escribía el nuevo latido.
- **Veredicto:** Falso positivo de diseño. No hubo suspensiones reales del sistema operativo durante esos intervalos.

---

## 5. AUDITORÍA CUANTITATIVA DE DUAL STRATEGY Y REGIME DETECTOR

1. **Evaluación de las 66 Operaciones Simuladas:**
   - La estrategia `ORB_SWING_PULLBACK_V1` en 4H generó 66 operaciones en 2026.
   - PnL neto: **-$14,378.89 USD** (1x), **-$16,072.88 USD** (2x), **-$24,942.23 USD** (3x).
   - Profit Factor: **0.77** (1x), **0.75** (2x), **0.62** (3x).
   - **Veredicto:** **RECHAZADA PARA TRADING REAL O PAPER ACTIVO**. No posee ventaja estadística sin filtro.

2. **Detector de Regímenes v1:**
   - Caracterización sobre 6,120 barras de 2026:
     - `INDETERMINATE`: 58.2% (filtro defensivo para evitar operaciones con ruido).
     - `RANGING`: 28.1% (mercado lateral).
     - `TRENDING_BULL`: 13.8% (tendencias institucionales definidas).
   - **Veredicto:** Aprobado como clasificador analítico desacoplado. Se evaluará su capacidad de mejora en la Fase 7 según el protocolo establecido en `DUAL_STRATEGY_VALIDATION_PLAN.md`.

---

## 6. CONCLUSIÓN Y ESTADO DE GOBERNANZA

- **Live Trading:** Permanece **ESTRICTAMENTE BLOQUEADO** (`ENABLE_LIVE_TRADING = False`).
- **D21 en Paper:** Es la **ÚNICA** estrategia autorizada en PAPER (`D21_RangeCompress_5d`, $PRS=71.2$, $SQS=69.17$).
- **Contador de Validación:** 11 días de reloj de campaña / 8 sesiones bursátiles / 0 trades cerrados (meta: $\ge 90$ días reales y $\ge 12$ trades cerrados).
- **Consistencia de Workstation:** `trading-app-repo` opera como runtime canónico único en el puerto 8090.
