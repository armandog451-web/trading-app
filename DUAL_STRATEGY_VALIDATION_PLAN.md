# PROTOCOLO DE VALIDACIÓN Y CONTROL CUANTITATIVO: DUAL STRATEGY & REGIME DETECTOR V1
**Documento:** `DUAL_STRATEGY_VALIDATION_PLAN.md`  
**Fase de Gobernanza:** OracleBot v2 — Fase 6.2  
**Fecha:** 2026-10-30 08:20:00 EDT  
**Repositorio Canónico:** `C:\Users\edsel\OneDrive\Documents\trading-app-repo`  
**Estado:** `ESTRICTAMENTE SIMULADO / ANALYSIS_ONLY` (Cero órdenes en vivo)

---

## 1. OBJETIVO Y MARCO DE APLICACIÓN

El presente protocolo define los requerimientos de validación económica, diseño experimental y segregación temporal independiente para el framework **Dual Strategy** (`ORB_INTRADAY_BREAKOUT_V1` y `ORB_SWING_PULLBACK_V1`) y el clasificador **Regime Detector v1** (`MarketRegimeDetectorV1`), asegurando que **ninguna estrategia no validada tenga permisos de promoción ni de envío de órdenes**.

---

## 2. AUDITORÍA DE LAS 66 OPERACIONES SIMULADAS Y SENSIBILIDAD A COSTES

En la Fase 6 Etapa 0 se completó la auditoría y corrección del simulador cronológico multi-activo sobre 204 sesiones del año 2026 (15 activos líquidos).

### 2.1 Resultados Auditados del Simulador Sincrónico (Variante 5 Swing 4H):

| Escenario de Costes | Comisiones ($/acción) | Slippage (bps) | Total Trades | Win Rate (%) | Profit Factor | Expectancy (R) | Net PnL ($) | Max Drawdown (%) | Veredicto |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Costes 1x (Base)** | \$0.005 | 5.0 bps | 66 | 33.3% | 0.77 | -0.16 R | -$14,378.89 | 2.13% | **REJECTED** |
| **Costes 2x (Estrés)** | \$0.010 | 10.0 bps | 65 | 33.8% | 0.75 | -0.19 R | -$16,072.88 | 2.21% | **REJECTED** |
| **Costes 3x (Severo)** | \$0.015 | 15.0 bps | 63 | 30.2% | 0.62 | -0.29 R | -$24,942.23 | 2.85% | **REJECTED** |

### 2.2 Hallazgos de Integridad Cuantitativa:
1. **Sensibilidad Monótona:** La degradación de Net PnL y Profit Factor es estrictamente monótona a medida que aumentan los costes por deslizamiento y comisiones, confirmando que se corrigió el fallo de acumulación del disyuntor que previamente generaba anomalías no lineales.
2. **Rechazo Estratégico Obligatorio:** Ninguna variante no filtrada de `ORB_SWING_PULLBACK_V1` demostró ventaja estadística (PF < 1.0 y PnL negativo en todos los niveles de fricción).
3. **Inmutabilidad de Evidencia:** Los resultados quedan formalmente sellados en `dual_strategy_research_results.json` y están estrictamente prohibidas las mutaciones de hiperparámetros sobre este mismo conjunto de datos.

---

## 3. EVALUACIÓN Y PROTOCOLO DE COMPARACIÓN: REGIME DETECTOR V1

### 3.1 Arquitectura del Detector (`MarketRegimeDetectorV1`):
El detector opera exclusivamente como filtro analítico independiente y genera tres estados mutuamente excluyentes:
- **`TRENDING_BULL`:** $\text{ADX}_{14} \ge 25.0 \;\land\; \text{ER}_{20} \ge 0.35 \;\land\; \text{Close} > \text{SMA}_{50}$ (13.8% de las barras en 2026).
- **`RANGING`:** $\text{ADX}_{14} < 20.0 \;\land\; \text{ER}_{20} < 0.25$ (28.1% de las barras en 2026).
- **`INDETERMINATE`:** Zonas de transición, ruido o divergencias (58.2% de las barras en 2026).

### 3.2 Protocolo de Comparación Filtrado vs. Sin Filtro:

Para evaluar la capacidad del detector de regímenes de convertir una estrategia perdedora en un sistema viable o reducir el drawdown, se establece la siguiente matriz de contraste:

```
                            MATRIZ EXPERIMENTAL DE VALIDACIÓN
┌───────────────────────────────┬──────────────────────────────────┬─────────────────────────────────┐
│ Métrica                       │ Estrategia Base (Sin Filtro)     │ Estrategia Filtrada por Régimen │
├───────────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ Entrada ORB Swing             │ Cualquiera en soporte/pullback   │ SOLO cuando Regime=TRENDING_BULL│
│ Filtro Defensivo              │ Ninguno                          │ Bloqueo en INDETERMINATE/RANGING│
│ Expectativa Mínima            │ PF < 1.0 (Línea Base: 0.77)      │ PF >= 1.25                      │
│ Reducción de Operaciones      │ 66 trades en 204 sesiones        │ Reducción esperada: >= 60%      │
│ Drawdown Máximo Tolerado      │ 2.13%                            │ <= 1.00%                        │
└───────────────────────────────┴──────────────────────────────────┴─────────────────────────────────┘
```

---

## 4. PARTICIÓN TEMPORAL INDEPENDIENTE Y AISLAMIENTO DE DATOS

Para evitar el sesgo de sobreajuste por reutilización (*data snooping*):
1. **Conjunto de Diseño (In-Sample):** 2026-01-01 a 2026-06-30. Utilizado únicamente para calibrar los umbrales de ADX y Kaufman ER.
2. **Conjunto de Validación Ciega (Out-of-Sample):** 2026-07-01 a 2026-10-20. Partición temporal sobre la que se evalúa la efectividad del filtro de régimen sin reoptimizar parámetros.
3. **Conjunto Holdout Cerrado:** Q4 2026 en adelante (Forward Prospectivo). Estrictamente bloqueado hasta la emisión de la autorización formal de la Fase 7.

---

## 5. SALVAGUARDAS DE SEGURIDAD OPERATIVA

1. **Desacoplamiento Absoluto de Órdenes:**
   El módulo `ai_trading_agent/dual_strategy/regime.py` no posee métodos de conexión con `PaperBroker`, `UnifiedBroker` ni ningún API de broker. Su ejecución es 100% analítica.
2. **Aislamiento de D21:**
   D21_RangeCompress_5d permanece como la **única estrategia en PAPER**. Dual Strategy y Regime Detector están catalogados en estado `RESEARCH` y carecen de autorización para transitar a `PAPER` o `APPROVED` sin una revisión formal por comité.
3. **Bloqueo Live Trading:**
   `ENABLE_LIVE_TRADING = False` en `.env` y validación estricta de variables de entorno inmutables.
