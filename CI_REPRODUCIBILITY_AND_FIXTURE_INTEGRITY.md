# INTEGRIDAD DE FIXTURES Y REPRODUCIBILIDAD DE CI
## MANIFIESTO CRIPTOGRÁFICO DE PRUEBAS, AISLAMIENTO DE HOLDOUT Y EVOLUCIÓN DE LA SUITE

**Entorno de Ejecución:** Windows / Python 3.11.17 / pytest-9.1.1  
**Repositorio Principal:** `armandog451-web/trading-app` (`trading-app-repo`)  
**Fecha de Certificación:** 30 de Octubre de 2026  
**Resultado de CI:** **317 / 317 PASSED (100%)**

---

## 1. RECONCILIACIÓN HISTÓRICA DE LA SUITE DE PRUEBAS

Durante la evolución del proyecto, la cantidad de pruebas reportadas varió entre diferentes ejecuciones debido a la incorporación gradual de suites y al alcance de los descubrimientos de fases anteriores:

| Fase / Hito | Cantidad de Pruebas | Alcance de la Suite |
| :--- | :---: | :--- |
| **Línea Base Inicial** | 64 | Pruebas básicas de backtest y APIs de conexión |
| **Fase 6.1 (Consolidación)** | 272 | Incorporación de Suite Dual Strategy, Regime Detector v1 y Hardening |
| **Fase 6.3 (Estabilización)** | 309 | Incorporación de auditorías de gobernanza de Fase 10 (Fase 10.1 a 10.8) |
| **Fase 6.4 (Certificación)** | **317** | Incorporación de los 8 escenarios de Idempotencia Transaccional |

**Reconciliación:** La diferencia entre 309 y 317 corresponde exactamente a las 8 pruebas institucionales de idempotencia añadidas en `ai_trading_agent/tests/test_idempotency_protection.py`.

---

## 2. MANIFIESTO CRIPTOGRÁFICO DE FIXTURES HISTÓRICOS

Para permitir que las pruebas de auditoría de fases anteriores (Fase 7 a Fase 10) sean ejecutadas de forma reproducible sin depender de bases de datos volátiles ni consultar endpoints externos, se crearon fixtures estáticos sellados en `ai_trading_agent/scratch/`:

| Archivo Fixture | Tamaño (Bytes) | Hash SHA-256 | Propósito de Auditoría |
| :--- | :---: | :--- | :--- |
| `fase10_discovery_summary.json` | 1,351 | `f1d218b04466da1a66d7da55cb60744379f6c12ed8adf6d4a2d2a6c4a10c736e` | Fixture para pruebas de candidatos Fase 10.1 y 10.2 (D21 y D13) |
| `HOLDOUT_EVAL_20261005_183221_f885ec2db2422308_results.json` | 543 | `a2890279635e3a63858abcd571f025205622b9aaa06c22110a7eef2e70ecf41b` | Fixture para validación de holdout ciego original de D21 (Fase 10.3) |
| `fase8_1_audit_summary.json` | 1,643 | `17ebf607bf1fe1189a417599c6c3025f69c98b50b0ea42ab339301ac9ff9b338` | Fixture de generalización y sensibilidad de costes (Fase 8.1) |
| `fase9_discovery_summary.json` | 327 | `0623a7559ff06b83e293daae4e2e151c1e0bf8c636bc5596b783b64782cb9d69` | Fixture de robustez para descubrimiento de bordes (Fase 9) |

### Protocolo de Integridad de Holdout:
1. **Inmutabilidad:** Los hashes SHA-256 de estos fixtures están registrados en las aserciones de los tests de auditoría correspondientes.
2. **Aislamiento Estricto:** Estos fixtures pertenecen al conjunto histórico de desarrollo y **jamás son utilizados por el motor en vivo ni para simular datos prospectivos**.
3. **No Contaminación:** Los datos en tiempo real de D21 se alimentan de fuentes cerradas de mercado a través del broker Moomoo en el entorno PAPER.

---

## 3. REPORTE DE EJECUCIÓN COMPLETA DE CI

La suite completa fue ejecutada dentro del repositorio canónico `trading-app-repo` con el entorno virtual oficial `.venv`:

```
============================= test session starts =============================
platform win32 -- Python 3.11.17, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\edsel\OneDrive\Documents\trading-app-repo
plugins: anyio-4.15.1, platformdirs-4.12.3
collected 317 items

ai_trading_agent\tests\test_api_and_explanation.py ......                [  1%]
ai_trading_agent\tests\test_backtest_engine.py .......                   [  4%]
ai_trading_agent\tests\test_brokers_and_telegram.py .......              [  6%]
ai_trading_agent\tests\test_campaign_runner_integrity.py ........        [  8%]
ai_trading_agent\tests\test_canonical_registry_guard.py ......           [ 10%]
ai_trading_agent\tests\test_fase10_1_candidate_audit.py .....            [ 12%]
ai_trading_agent\tests\test_fase10_2_stability_audit.py .....            [ 13%]
ai_trading_agent\tests\test_fase10_3_holdout_audit.py ....               [ 15%]
ai_trading_agent\tests\test_fase10_4_governance_audit.py .....           [ 16%]
ai_trading_agent\tests\test_fase10_5_paper_eligibility_audit.py ....     [ 17%]
ai_trading_agent\tests\test_fase10_6_transition_semantics.py ...         [ 18%]
ai_trading_agent\tests\test_fase10_7_paper_deployment.py ....            [ 20%]
ai_trading_agent\tests\test_fase10_8_runtime_activation.py .........     [ 23%]
ai_trading_agent\tests\test_fase10_daily_discovery.py .......            [ 25%]
ai_trading_agent\tests\test_fase7_2_temporal_alignment.py ....           [ 26%]
ai_trading_agent\tests\test_fase7_3_reconciliation.py ........           [ 29%]
ai_trading_agent\tests\test_fase7_4_accounting_repair.py .....           [ 30%]
ai_trading_agent\tests\test_fase7_integrity_audit.py .....               [ 32%]
ai_trading_agent\tests\test_fase8_1_generalization_audit.py ....         [ 33%]
ai_trading_agent\tests\test_fase8_executable_edge.py .....               [ 35%]
ai_trading_agent\tests\test_fase9_discovery.py ........                  [ 37%]
ai_trading_agent\tests\test_idempotency_protection.py ........           [ 40%]
ai_trading_agent\tests\test_indicators_and_regime.py ...                 [ 41%]
ai_trading_agent\tests\test_market_schedule.py ........                  [ 43%]
ai_trading_agent\tests\test_multi_timeframe_synchronization.py .....     [ 45%]
ai_trading_agent\tests\test_oraclebot_v2_dual_strategy.py .............. [ 49%]
...............                                                          [ 54%]
ai_trading_agent\tests\test_orchestrator.py ..                           [ 54%]
ai_trading_agent\tests\test_paper_fidelity_engine.py ................    [ 59%]
ai_trading_agent\tests\test_phase2_strategies.py ........                [ 62%]
ai_trading_agent\tests\test_quantitative_hardening.py .................. [ 68%]
...............                                                          [ 72%]
ai_trading_agent\tests\test_regime_detector_v1.py .............          [ 76%]
ai_trading_agent\tests\test_risk_and_safety.py ...........               [ 80%]
ai_trading_agent\tests\test_storage_and_providers.py ....                [ 81%]
ai_trading_agent\tests\test_strategies_and_aggregator.py ..              [ 82%]
ai_trading_agent\tests\test_strategy_discovery.py ................       [ 87%]
ai_trading_agent\tests\test_strategy_lab.py ...............              [ 92%]
ai_trading_agent\tests\test_telegram_observability.py ...............    [ 96%]
ai_trading_agent\tests\test_validation_and_synthetic.py ...              [ 97%]
ai_trading_agent\tests\test_weekend_scanner.py .......                   [100%]

================= 317 passed, 6 warnings in 67.84s (0:01:07) ==================
```

---

## 4. CERTIFICACIÓN DE REPRODUCIBILIDAD

1. **Determinismo:** El 100% de los 317 tests son reproducibles en cualquier entorno local con Python 3.11 y las dependencias de `requirements.txt`.
2. **Cero Dependencias Ocultas:** No se requieren llamadas a APIs con costo o credenciales activas para la ejecución de la suite de CI.
3. **Aislamiento Seguro:** La suite puede ejecutarse de forma segura sin alterar la base de datos de producción (`trading_app.db`) gracias al uso de bases de datos temporales (`tempfile.TemporaryDirectory`).
