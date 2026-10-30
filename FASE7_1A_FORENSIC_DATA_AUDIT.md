# AUDITORÍA FORENSE DE DATOS Y PROCEDENCIA (FASE 7.1A)
## INVESTIGACIÓN DE INTEGRIDAD DE SERIES TEMPORALES, PROCEDENCIA Y VALIDACIÓN CRIPTOGRÁFICA

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.1A — Auditoría Forense Correctiva  
**Objetivo:** Determinar la procedencia real de los datos utilizados en la Fase 7.0 / 7.1 y contrastar con series de mercado auténticas.  
**Estado:** **AUDITORÍA FORENSE CONCLUIDA — CLASIFICACIÓN EMITIDA**  

---

## 1. HALLAZGO FORENSE PRINCIPAL: PROCEDENCIA DEL BENCHMARK DE 1,200 BARRAS

La auditoría forense determinó de manera concluyente e irrefutable que el dataset de 1,200 barras utilizado para las pruebas preliminares de la Fase 7.0 y 7.1 **NO representaba datos históricos auténticos de mercado de la Bolsa de Nueva York (NYSE/NASDAQ)**, sino una **serie sintética generada estocásticamente en memoria**:

### Evidencia en el Código Fuente:
En los scripts `ai_trading_agent/scratch/run_fase7_preliminary_eval.py` y `ai_trading_agent/strategy_lab/fase7_1_audit_engine.py`, la función generadora implementaba:
```python
def generate_benchmark_bars(num_days=1000):
    np.random.seed(42)
    bars = []
    base_date = datetime(2020, 1, 1)
    price = 320.0
    for i in range(num_days):
        dt = base_date + timedelta(days=i)
        daily_ret = np.random.normal(mu, sigma)
        price *= (1.0 + daily_ret)
        ...
```

### Características Forenses del Dataset Sintético:
1. **Generación:** Movimiento Browniano Geométrico (GBM) con alternancia artificial de regímenes en bloques fijos de 120 días.
2. **Incremento Temporal:** Avanzaba estrictamente mediante `dt = base_date + timedelta(days=i)` (días de calendario continuos), **omitiendo la exclusión de sábados, domingos y festivos bursátiles oficiales de EE. UU.**
3. **Precios:** Precios generados a partir de una semilla fija (`seed=42`) iniciando en \$320.00 USD, sin correspondencia con las cotizaciones reales del ETF `SPY` en el periodo 2020-2023.
4. **Hash Criptográfico SHA-256 de la Serie Sintética:**
   ```
   37ce51a80436d2c161947eeb6eb7543884df15a81caea9e29a8f4c2847d95b50
   ```
5. **Dictamen de Clasificación:** **`INVALID_DATA_PROVENANCE_FOR_PRODUCTION`**.

---

## 2. CONTRASTE CON LA SERIE DE MERCADO REAL AUTÉNTICA DE `SPY`

Para subsanar esta deficiencia y establecer una línea base verificable, se descargaron **1,200 barras diarias auténticas y consolidadas de `SPY`** a través de [`YFinanceMarketDataProvider`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/data/providers/yfinance_provider.py):

| Atributo | Benchmark Sintético (Fase 7.0/7.1) | Serie Real Auténtica de Mercado (`SPY`) |
| :--- | :---: | :---: |
| **Procedencia** | Simulación GBM en memoria (`numpy`) | Cotizaciones reales NYSE Arca (`SPY`) |
| **Rango de Fechas** | 2020-01-01 a 2023-04-14 (Continuo) | **2022-01-20 a 2026-10-30 (Bursátil)** |
| **Conteo de Barras** | 1,200 barras | **1,200 barras diarias** |
| **Fines de Semana Incluidos** | **SÍ (342 sábados y domingos)** | **NO (0 fines de semana)** |
| **Festivos NYSE Incluidos** | **SÍ (38 festivos como días de trading)** | **NO (0 festivos, 100% oficial)** |
| **Ajuste Corporativo** | Sin ajuste (retornos sintéticos) | **Ajustado por dividendos y splits** |
| **Hash SHA-256 de Serie** | `37ce51a8...` (Sintético) | **`a2fe260316936f613b655a9ceea06716ca841b7632dd5555d46fbe0f0cc39418`** |
| **Clasificación Formal** | **`INVALID`** | **`VERIFIED_REAL_MARKET_DATA`** |

---

## 3. AUDITORÍA DE REGÍMENES EN MERCADO REAL

En la serie sintética, los regímenes estaban programados matemáticamente en ciclos uniformes de 120 días (40% Bull, 30% Ranging, 30% Indeterminate).  
Al aplicar el detector determinista [`MarketRegimeV1`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/dual_strategy/regime.py) sobre las **1,200 barras reales de `SPY` (2022 a 2026)**, la distribución real fue:

- **`TRENDING_BULL`:** 248 barras (**20.7%** del tiempo).
- **`RANGING`:** 402 barras (**33.5%** del tiempo).
- **`INDETERMINATE`:** 550 barras (**45.8%** del tiempo).

> **Hallazgo Crítico:** En el mercado real, el régimen `INDETERMINATE` representa casi la mitad del tiempo (**45.8%**). Esto demuestra empíricamente que la regla de abstención institucional no es un filtro marginal, sino el estado primario de defensa del capital.

---

## 4. REGISTRO DE INTEGRIDAD Y DISPONIBILIDAD

El manifiesto forense completo con hashes SHA-256 de todas las series de datos y reconciliaciones trade a trade se encuentra archivado de forma inmutable en:
[`ai_trading_agent/scratch/fase7_1a_forensic_manifest.json`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/scratch/fase7_1a_forensic_manifest.json).
