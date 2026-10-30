# FASE 7 RESEARCH READINESS PLAN — PROTOCOLO METODOLÓGICO INDEPENDIENTE

**Proyecto:** Strategy Laboratory & Dual Strategy Research  
**Fecha:** 2026-10-30  
**Estado:** `RESEARCH_ONLY` / `ANALYSIS_ONLY`  
**Autorización de Ejecución Conectada:** `DENEGADA` (Fase 7 requiere aprobación previa)

---

## 1. MISIÓN Y MARCO DE INVESTIGACIÓN

Este documento establece el marco metodológico estricto para investigar la viabilidad cuantitativa de una arquitectura de **Estrategia Dual Condicionada al Régimen Macro**, sin conectar ninguna estrategia experimental al broker y sin comprometer la campaña PAPER activa de `D21_RangeCompress_5d`.

---

## 2. ARQUITECTURA DE ESTRATEGIAS CANDIDATAS EN INVESTIGACIÓN

### 2.1. Estrategia A — Momentum Condicionado al Régimen
* **Condición de Activación:** Candidata a evaluar únicamente cuando `MarketRegimeDetectorV1` clasifique el régimen como:
  $$\text{Regime} = \mathbf{TRENDING\_BULL}$$
* **Hipótesis Cuantitativa:** En regímenes fuertemente tendenciales alcistas, las rupturas de momentum y continuaciones de tendencia exhiben mayor tasa de acierto y menor recorrido adverso (MAE).
* **Parámetros Tentativos:** Ruptura de Donchian de 20 días con trailing stop ATR y filtro EMA200.
* **Estado:** `RESEARCH` (Inmutable, sin enrutamiento a broker).

### 2.2. Estrategia B — Reversión a la Media
* **Condición de Activación:** Candidata a evaluar únicamente cuando `MarketRegimeDetectorV1` clasifique el régimen como:
  $$\text{Regime} = \mathbf{RANGING}$$
* **Hipótesis Cuantitativa:** En ausencia de tendencia direccional clara, los extremos de oscilación (RSI $\le 30$ o $\ge 70$, rebote en bandas Keltner/Bollinger) ofrecen reversiones con ratio beneficio/riesgo favorable.
* **Estado:** `RESEARCH` (Inmutable, sin enrutamiento a broker).

### 2.3. Estado `INDETERMINATE`
* **Regla Incondicional:** Cuando el régimen de mercado sea clasificado como `INDETERMINATE` o en periodos de transición de alta volatilidad:
  $$\text{Acción} = \mathbf{NO\_TRADE}$$
* Queda terminantemente prohibido generar órdenes experimentales en regímenes ambiguos.

---

## 3. PROTOCOLO METODOLÓGICO Y CONTROL DE SESGOS

Para evitar los errores metodológicos detectados en las Fases 7 y 8 (donde 66 trades simulados de Dual Strategy generaron pérdidas de $-\$4,510$ debido a fricciones y sobreajuste):

1. **Aislamiento de Partición Temporal:**
   * La investigación de Fase 7 deberá utilizar un conjunto de datos histórico independiente o partición walk-forward que **nunca haya sido utilizada** para afinar umbrales ni seleccionar hiperparámetros.
   * Prohibido reutilizar el dataset de holdout reservado como si fuera un blind holdout virgen.
2. **Modelo de Fricciones Realista:**
   * Toda simulación deberá incluir fricciones institucionales completas:
     * Comisiones: $\$0.005$ por acción (Interactive Brokers Tiered).
     * Deslizamiento (Slippage): Escenario base de $5.0\text{ bps}$ y prueba de estrés a $10.0\text{ bps}$.
   * Descarte automático de cualquier candidato cuyo Movement-to-Cost Ratio ($MCR$) sea inferior a $5.0\times$.
3. **Inmutabilidad del Detector de Regímenes:**
   * El `MarketRegimeDetectorV1` (basado en ADX, SMA50/SMA200 y ATR percentile) no podrá ser modificado sobre la marcha. Cualquier ajuste requerirá un nuevo versionado formal (`MarketRegimeDetectorV2`) con un fingerprint criptográfico nuevo.
4. **Cero Promoción Anticipada:**
   * Ninguna estrategia de Fase 7 podrá ser promovida a `PAPER` o conectada al broker sin cumplir previamente los 4 Early Generalization Gates (GSS $\ge 50$, Monotonía en Frontera de Costes, Supervivencia LOSO en los 4 ETFs y Rendimiento OOS robusto).

---

## 4. ESTADO DE AUTORIZACIÓN

* **Conexión al Broker:** `ESTRICTAMENTE BLOQUEADA`.
* **Trading LIVE:** `ENABLE_LIVE_TRADING = False` (Inmutable).
* **Fase 7:** `PREPARACIÓN TÉCNICA CONCLUIDA`. No se iniciará la ejecución de la Fase 7 sin la autorización formal y expresa del operador.
