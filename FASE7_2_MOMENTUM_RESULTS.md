# ORACLEBOT V2 — FASE 7.2: INFORME DE RESULTADOS DE MOMENTUM
## EVALUACIÓN CUANTITATIVA, FRECUENCIA OPERATIVA Y VIABILIDAD DE `MOM_TrendPullback_V1`

**Estrategia:** `MOM_TrendPullback_V1`  
**Familia:** Momentum / Retroceso a Media en Tendencia (Trend Pullback)  
**Fingerprint SHA-256:** `5d10c8c90e6f73a6`  
**Parámetros Congelados:**
- `ema_fast`: 20
- `sma_slow`: 50
- `min_rsi`: 40.0
- `max_rsi`: 60.0
- `min_rvol`: 1.20
- `atr_mult_stop`: 1.5
- `atr_mult_tp`: 2.5
- `max_holding_days`: 5
- `stop_loss`: -2.0%
- `profit_target`: +3.5%
**Regla de Régimen Canónica:** Operativa autorizada exclusivamente en `MarketRegimeV1.TRENDING_BULL`.

---

## 1. DESEMPEÑO CRUZADO BAJO RÉGIMEN FILTRADO (`TRENDING_BULL`) — ESCENARIO BASE 1X

Bajo la regla canónica, la estrategia solo evalúa entradas cuando el mercado es clasificado en tendencia alcista consolidada ($\text{ADX} \ge 25 \land \text{ER} \ge 0.35 \land \text{Close} > \text{SMA50}$).

### Tabla Detallada por Activo (Costes 1x: $0.005/acción, 5 bps slippage)

| Activo | Operaciones | Frecuencia Anual | Win Rate | True Gross PnL | Deslizamiento | Comisiones | True Net PnL | Net PF | Sharpe | Max DD % |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SPY** | 2 | 0.42 trades/año | 100.0% | +$299.91 | $14.91 | $10.40 | +$274.60 | 999.0 | 1.91 | 0.00% |
| **QQQ** | 0 | 0.00 trades/año | 0.0% | $0.00 | $0.00 | $0.00 | $0.00 | 0.00 | 0.00 | 0.00% |
| **IWM** | 1 | 0.21 trades/año | 0.0% | -$352.03 | $6.29 | $6.30 | -$364.62 | 0.00 | N/A | 0.36% |
| **DIA** | 3 | 0.63 trades/año | 66.67% | +$56.34 | $21.89 | $16.00 | +$18.45 | 1.11 | 0.05 | 0.16% |
| **XLF** | 2 | 0.42 trades/año | 50.0% | +$190.00 | $11.40 | $11.40 | +$167.20 | 3.75 | 0.56 | 0.06% |
| **XLE** | 1 | 0.21 trades/año | 0.0% | -$215.00 | $5.56 | $5.56 | -$226.12 | 0.00 | N/A | 0.23% |
| **PORTAFOLIO** | **9** | **1.89 trades/año** | **55.56%** | **-$20.78** | **$60.05** | **$49.66** | **-$130.49** | **0.84** | **-0.12** | **0.41%** |

---

## 2. ANÁLISIS DE LA HIPER-RESTRICCIÓN Y HAMBRUNA DE SEÑALES

El problema crítico que descalifica a `MOM_TrendPullback_V1` es la **hambruna extrema de operaciones** provocada por la conjunción de 7 filtros simultáneos:
1. Régimen `TRENDING_BULL`: Requiere $\text{ADX} \ge 25$, $\text{ER} \ge 0.35$ y $\text{Close} > \text{SMA50}$.
2. Condición de retesteo: $\text{Low} \le \text{EMA20} \times 1.01 \land \text{Close} \ge \text{EMA20} \times 0.99$.
3. Rango de RSI neutral-alcista: $40 \le \text{RSI}(14) \le 60$.
4. Volumen relativo anómalo: $\text{RVOL} \ge 1.20$.

### Impacto en la Muestra
- En 4.78 años (1,200 días bursátiles reales) por activo, evaluando 7,200 barras en total, el sistema únicamente halló **9 oportunidades en todo el mercado estadounidense**.
- En el ETF tecnológico más líquido del mundo (**QQQ**), el número de operaciones generadas fue **CERO**.
- Una frecuencia de 1.89 operaciones al año a nivel de portafolio no permite diversificar el riesgo, no ofrece significancia estadística y hace imposible amortizar costes fijos o comisiones operativas.

---

## 3. DESEMPEÑO ECONÓMICO Y COSTE OPERATIVO

Aun cuando la tasa de acierto superficial fue del 55.6% (5 aciertos de 9), la economía neta de la estrategia es deficitaria:
- **True Gross PnL:** -$20.78 USD.
- **Deslizamiento:** -$60.05 USD.
- **Comisiones:** -$49.66 USD.
- **True Net PnL:** **-$130.49 USD**.
- **Net Profit Factor:** **0.84**.

Las pocas pérdidas ocurridas (como la de IWM por -$364.62 y XLE por -$226.12) borraron por completo las escasas ganancias obtenidas en SPY y XLF.

---

## 4. EXPERIMENTO COMPARATIVO: SIN FILTRO DE RÉGIMEN (`UNFILTERED`)

Para discernir si la causa residía en el filtro de régimen o en la definición del pullback, se evaluó `MOM_TrendPullback_V1` en modo no filtrado:

| Modo | Operaciones | Frecuencia Anual | Win Rate | True Gross PnL | Deslizamiento + Comisiones | True Net PnL | Net PF | Sharpe | Max DD % | Cost Drag % |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FILTRADO (`TRENDING_BULL`)** | 9 | 1.89 trades/año | 55.56% | -$20.78 | $109.71 | **-$130.49** | 0.84 | -0.12 | 0.41% | N/A (Loss) |
| **SIN FILTRO (Todos)** | 187 | 39.27 trades/año | 56.15% | +$6,067.89 | $2,394.64 | **+$3,673.25** | 1.20 | 0.48 | 1.74% | 39.46% |

### Análisis de la Comparativa
1. Al eliminar el filtro de régimen, las operaciones aumentan de 9 a 187 (un incremento del 1,977%).
2. Sin filtro, la estrategia genera +$3,673.25 en 1x (con beneficios en SPY +$764, QQQ +$1,549, IWM +$2,365).
3. Sin embargo, al aplicar el estrés de costes obligatorio:
   - **Costes 2x:** El PnL neto cae un 60.4% a +$1,456.16 (Net PF 1.08).
   - **Costes 3x:** El PnL neto colapsa a **-$891.64** (Net PF 0.96).

---

## 5. CONCLUSIÓN Y VEREDICTO DE MOMENTUM

`MOM_TrendPullback_V1` en su formulación institucional filtrada es **inoperante por inanición de señales y PnL neto negativo**. En su versión sin filtro, su ventaja se desvanece ante fricciones moderadas.

Se clasifica formalmente como **`RESEARCH_REJECTED`**. No se autoriza su avance a ninguna fase prospectiva.
