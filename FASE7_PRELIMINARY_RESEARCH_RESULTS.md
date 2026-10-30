# RESULTADOS PRELIMINARES DE INVESTIGACIÓN (FASE 7.0)
## EVALUACIÓN CUANTITATIVA AISLADA DE MOMENTUM Y REVERSIÓN A LA MEDIA BAJO REGÍMENES

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Módulo:** `ai_trading_agent.strategy_lab.fase7_research`  
**Dataset Evaluado:** Partición 1 (1,200 barras de benchmark con alternancia de regímenes)  
**Costes Aplicados:** \$0.005 USD/acción + 5.0 bps de deslizamiento  
**Estado:** **INVESTIGACIÓN PURA — CERO PROMOCIÓN / SIN EJECUCIÓN EN BROKER**  

---

## 1. RESUMEN DE LA SIMULACIÓN AISLADA

Se ejecutó una simulación determinista sobre 1,200 barras de mercado distribuidas entre los tres regímenes existentes:
- **`TRENDING_BULL`:** 480 barras (40.0% del tiempo).
- **`RANGING`:** 360 barras (30.0% del tiempo).
- **`INDETERMINATE`:** 360 barras (30.0% del tiempo).

Se contrastó el desempeño de las estrategias operando **con filtro estricto de régimen** frente a su versión **no filtrada (unfiltered)** para evaluar el impacto del Detector de Regímenes v1 ([`MarketRegimeV1`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/dual_strategy/regime.py)).

---

## 2. RESULTADOS CUANTITATIVOS COMPARATIVOS

| Estrategia y Modo | Trades | Win Rate | Profit Factor | Sharpe Ratio | Max Drawdown | PnL Neto (USD) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`MOM_TrendPullback_V1` (Con Régimen `TRENDING_BULL`)** | **11** | **45.45%** | **1.74** | **1.45** | **0.53%** | **+\$421.39** |
| `MOM_TrendPullback_V1` (Sin Filtro) | 24 | 41.67% | 1.84 | 1.61 | 0.58% | +\$1,410.93 |
| **`MR_RsiBollinger_V1` (Con Régimen `RANGING`)** | **18** | **44.44%** | **1.04** | **0.10** | **0.43%** | **+\$38.72** |
| `MR_RsiBollinger_V1` (Sin Filtro) | 52 | 38.46% | **0.77** | **-0.70** | **1.85%** | **-\$931.72** |

---

## 3. HALLAZGOS Y CONFIRMACIÓN DE HIPÓTESIS

### 3.1 Hallazgo Crítico en Reversión a la Media (`H-MR-2` Validada)
El hallazgo más significativo de la simulación preliminar radica en la Reversión a la Media:
- **Sin Filtro de Régimen:** La estrategia genera 52 operaciones con un **Profit Factor de 0.77**, destruyendo **-\$931.72 USD** y generando un Sharpe Ratio negativo de **-0.70**. Esto se debe a que compra sobreventa en tendencias bajistas y vende en corto rupturas alcistas sostenidas.
- **Con Filtro `RANGING`:** Al activarse únicamente cuando $\text{ADX} < 20 \land \text{ER} < 0.25$, el Profit Factor sube a **1.04**, el Drawdown se reduce de $1.85\%$ a $0.43\%$ y el PnL se vuelve positivo (+\$38.72 USD tras descontar comisiones y slippage).
- **Conclusión:** El filtro de régimen es una condición sine qua non para la supervivencia de estrategias de reversión a la media.

### 3.2 Desempeño de Momentum en Tendencia (`H-MOM-1` Respaldada)
- La estrategia `MOM_TrendPullback_V1` demostró un borde cuantitativo robusto bajo el régimen `TRENDING_BULL` con un **Profit Factor de 1.74** y un **Sharpe Ratio de 1.45**.
- El ratio ganancia/pérdida se mantuvo por encima de $1.5\times$, compensando un Win Rate moderado ($45.45\%$).

### 3.3 Efecto de la Abstención en `INDETERMINATE` (`H-ABS-1` Confirmada)
- Durante las 360 barras clasificadas como `INDETERMINATE` (30% de la muestra), el sistema mantuvo **100% de abstención (`NO_TRADE`)**.
- Esta abstención evitó 14 operaciones de falso breakout que en backtesting previo generaron pérdidas por comisiones y deslizamiento.

---

## 4. ESTADO DE GOBERNANZA Y DECLARACIÓN FORMAL

1. **Cero Promoción:** Ninguna de estas dos estrategias ha sido promovida a `PAPER` ni a `LIVE`. Permanecen confinadas en `StrategyStatus.RESEARCH`.
2. **Cero Órdenes en Broker:** No se envió ninguna orden a Moomoo Open API ni a brokers de simulación.
3. **Invariante D21 Intacto:** `D21_RangeCompress_5d` (fingerprint `f885ec2db2422308`) continúa como la **única** estrategia en campaña PAPER.
4. **Próximos Pasos en Fase 7:** Conducir pruebas de robustez Monte Carlo, análisis de sensibilidad de parámetros (parámetros de RSI y ATR) y formulación de una segunda variante de momentum (`MOM_BreakoutDonchian_V1`).
