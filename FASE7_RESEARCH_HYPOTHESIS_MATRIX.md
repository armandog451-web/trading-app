# MATRIZ DE HIPÓTESIS CUANTITATIVAS (FASE 7.0)
## EXPLORACIÓN CONDICIONADA POR RÉGIMEN PARA MOMENTUM Y REVERSIÓN A LA MEDIA

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.0 — Matriz de Investigación Cuantitativa  
**Regímenes Auditados:** `TRENDING_BULL`, `RANGING`, `INDETERMINATE`  
**Estado:** **FORMULACIÓN FORMAL Y PRE-TESTING**  

---

## 1. MARCO TEÓRICO Y JUSTIFICACIÓN ECONÓMICA

La premisa fundamental de la Fase 7.0 es que **ninguna estrategia cuantitativa posee un borde universal en todas las fases del ciclo de mercado**. La aplicación indiscriminada de Momentum genera pérdidas por whipsaw en mercados laterales, mientras que la Reversión a la Media causa pérdidas catastróficas al intentar atrapar cuchillos que caen o vender en corto tendencias explosivas.

El Detector de Regímenes v1 ([`MarketRegimeV1`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/dual_strategy/regime.py)) actúa como el switch de contexto que habilita o inhabilita cada familia de estrategias.

---

## 2. MATRIZ DE HIPÓTESIS FORMAL

| ID Hipótesis | Familia | Régimen Condicionante | Premisa Cuantitativa | Criterio de Falsación / Aceptación |
| :---: | :---: | :---: | :--- | :--- |
| **H-MOM-1** | Momentum | **`TRENDING_BULL`** | Los retrocesos a la EMA(20) en presencia de tendencia institucional ($\text{ADX} \ge 25, \text{ER} \ge 0.35, \text{Close} > \text{SMA50}$) ofrecen un ratio ganancia/pérdida asimétrico ($RR \ge 2.0$) con persistencia direccional a 5 días. | **Aceptada si:** $PF \ge 1.50$ y Sharpe $\ge 1.20$ con $DD \le 8\%$.<br>**Falsada si:** $PF < 1.20$ o Win Rate $< 40\%$. |
| **H-MOM-2** | Momentum | **`RANGING` / `INDETERMINATE`** | Operar Momentum en ausencia de `TRENDING_BULL` incrementa el churn de comisiones y produce drawdowns severos por rupturas falsas. | **Aceptada si:** El filtro de régimen reduce el drawdown al menos un $30\%$ respecto a la versión no filtrada. |
| **H-MR-1** | Mean Reversion | **`RANGING`** | En mercados sin tendencia ($\text{ADX} < 20, \text{ER} < 0.25$), los extremos de sobreventa ($\text{RSI}(4) \le 25$ y contacto con Banda Inferior Bollinger) revierten a la media $\text{SMA}(20)$ en un horizonte $\le 3$ días bursátiles. | **Aceptada si:** Win Rate $\ge 55\%$ y $PF \ge 1.30$.<br>**Falsada si:** $PF < 1.05$ o tiempo medio de reversión $> 5$ días. |
| **H-MR-2** | Mean Reversion | **`TRENDING_BULL` / `INDETERMINATE`** | Operar Reversión a la Media en regímenes con tendencia o indeterminados destruye capital al comprar caídas en tendencias bajistas o vender tendencias alcistas. | **Aceptada si:** La versión sin filtro exhibe $PF < 1.00$ (pérdida neta). *(Validado empíricamente en pre-testing: $PF = 0.77$).* |
| **H-ABS-1** | Gobernanza | **`INDETERMINATE`** | La abstención obligatoria de trading (`NO_TRADE`) en condiciones ambiguas protege la curva de capital y maximiza el Ratio de Calmar. | **Aceptada si:** La abstención en `INDETERMINATE` reduce la exposición temporal en al menos un $25\%$ sin reducir el Sharpe Ratio. |

---

## 3. ESPECIFICACIÓN DETALLADA DE ESTRATEGIAS CANDIDATAS

### 3.1 Familia Momentum: `MOM_TrendPullback_V1`
- **Familia:** Momentum / Trend Following.
- **Régimen Obligatorio:** `MarketRegimeV1.TRENDING_BULL`.
- **Condiciones de Entrada:**
  1. $\text{ADX}(14) \ge 25 \land \text{ER}(20) \ge 0.35 \land \text{Close} > \text{SMA}(50)$ (Confirmación de Régimen).
  2. $\text{Low} \le \text{EMA}(20) \times 1.01 \land \text{Close} \ge \text{EMA}(20) \times 0.99$ (Retesteo de media rápida).
  3. $40 \le \text{RSI}(14) \le 60$ (Retroceso saludable sin agotamiento).
  4. $\text{RVOL}(20) \ge 1.20\times$ (Participación institucional en la defensa del nivel).
- **Condiciones de Salida:**
  - **Stop Loss:** $\text{Close} - 1.5 \times \text{ATR}(14)$.
  - **Take Profit:** $\text{Close} + 2.5 \times \text{ATR}(14)$ ($RR = 1.67$).
  - **Time Stop:** 5 días bursátiles.

---

### 3.2 Familia Reversión a la Media: `MR_RsiBollinger_V1`
- **Familia:** Mean Reversion / Statistical Arbitrage.
- **Régimen Obligatorio:** `MarketRegimeV1.RANGING`.
- **Condiciones de Entrada:**
  1. $\text{ADX}(14) < 20 \land \text{ER}(20) < 0.25$ (Confirmación de Rango Lateral).
  2. $\text{Low} \le \text{LowerBand}(20, 2.0)$ (Perforación o testeo de banda inferior).
  3. $\text{RSI}(4) \le 25.0$ (Sobreventa extrema de corto plazo).
  4. $\text{RVOL}(20) \ge 1.0\times$ (Liquidez mínima requerida).
- **Condiciones de Salida:**
  - **Take Profit:** Cierre por encima de la media central $\text{SMA}(20)$ (Reversión completada).
  - **Stop Loss:** $\text{Close} - 1.5 \times \text{ATR}(14)$.
  - **Time Stop:** 3 días bursátiles (las reversiones que demoran más tienden a fallar).

---

## 4. MATRIZ DE COMPORTAMIENTO ANTE REGÍMENES

| Estrategia | `TRENDING_BULL` | `RANGING` | `INDETERMINATE` |
| :--- | :---: | :---: | :---: |
| **`MOM_TrendPullback_V1`** | **EVALUAR SEÑAL** | **NO_TRADE** (Bloqueada) | **NO_TRADE** (Abstención) |
| **`MR_RsiBollinger_V1`** | **NO_TRADE** (Bloqueada) | **EVALUAR SEÑAL** | **NO_TRADE** (Abstención) |
| **`D21_RangeCompress_5d` (PAPER)** | *Independiente (PAPER)* | *Independiente (PAPER)* | *Independiente (PAPER)* |

> **Garantía de Aislamiento:** Las estrategias de la Fase 7.0 no pueden compartir posiciones, límites de riesgo ni bases de datos con D21.
