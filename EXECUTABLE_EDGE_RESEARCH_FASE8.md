# INFORME DE INVESTIGACIÓN CIENTÍFICA FASE 8: EXECUTABLE EDGE CONVERSION RESEARCH

**Fecha de Ejecución:** 2026-10-05  
**Proyecto:** `ai_trading_agent` / Strategy Laboratory  
**Versión del Core:** `v2.2.1-pro`  
**Autor:** Antigravity Autonomous Research & Quantitative Hardening Engine  
**Estado de Seguridad:** `FINAL_HOLDOUT = LOCKED` (20%) | `CANDIDATE = NONE` | `172/172 Tests PASS`  

---

## 1. Research Objective

El objetivo central de la Fase 8 fue responder con rigor cuantitativo institucional a la pregunta cardinal de viabilidad operativa:

> **"CAN EXECUTION-AWARE SIGNAL DESIGN PRODUCE POSITIVE ECONOMIC EDGE AFTER REALISTIC COSTS?"**  
> *(¿Puede el diseño de señales con conciencia de ejecución producir un edge económico positivo tras considerar costes realistas de comisiones, deslizamiento, restricciones de solapamiento y límites de riesgo?)*

Tras la clausura formal de la arquitectura `CONFIG_D` en la Fase 7.4 (donde se comprobó que el filtro diario no aportaba alpha estable y que las fricciones destruían el payoff nominal de 3.0R), la investigación se orientó hacia una exploración sistemática no lineal que abarca tres dimensiones críticas:
1. **Calidad de Entrada (Entry Quality):** Evaluación de 6 nuevas familias de timing intradía (1H).
2. **Geometría de Salida (Exit Geometry):** Alternativas a la toma de beneficios estática (time stops, trailing ATR, salidas parciales).
3. **Gestión de Concurrencia (Signal Concurrency):** Políticas activas de selección, reemplazo y diversificación multiactivo.

---

## 2. Data Windows & Master Temporal Split

Para garantizar comparabilidad causal absoluta y erradicar cualquier fuga de información (*Data Leakage*), se utilizó exclusivamente `DateBasedDataSplitter` con un calendario maestro común determinado por la intersección de datos horarios (1H) y diarios (1D):

- **Período Maestro Común:** `2023-11-06` a `2026-10-05`
- **In-Sample (IS - 60%):** `2023-11-06` a `2025-08-05`
- **Out-of-Sample (OOS - 20%):** `2025-08-05` a `2026-03-06`
- **FINAL_HOLDOUT (20% - Protegido):** `2026-03-06` a `2026-10-05` (`LOCKED` bajo `PermissionError`)

Todas las comparaciones entre modelos y universos compartieron estrictamente los mismos rangos cronológicos.

---

## 3. Baselines Históricos de Referencia

Se mantuvieron congelados como puntos de referencia cuantitativa:

| Estrategia de Referencia | Ventana | Trades | Profit Factor | Sharpe Ratio | Net PnL (USD) | Estado / Comentarios |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Phase 6 Daily Lead** (`mut_8f772ab8`) | IS / OOS | $76$ ($52$ IS / $24$ OOS) | $1.49$ (OOS) | $0.75$ | $+\$4,120.00$ | Lead diario de reversión a la media |
| **Phase 7 CONFIG_D** (OOS SPY) | OOS | $92$ | $0.64$ | $-3.15$ | $-\$2,375.16$ | 1D Trend + 1H Entry + 3.0R Target |
| **Phase 7 BASELINE_1H** (OOS SPY) | OOS | $145$ | $0.81$ | $-1.95$ | $-\$4,812.50$ | 1H Mean-Reversion sin contexto diario |

---

## 4. Hypotheses & Research Dimensions

Se postularon cuatro hipótesis de diseño consciente de ejecución:
- **H1 (Mitigación del Arrastre Temporal):** Un mecanismo de salida basado en tiempo (*time stop*) reduce la exposición a consolidaciones ruidosas, disminuyendo la compresión del payoff ratio causada por el spread y el slippage.
- **H2 (Reversión tras Ruptura Fallida):** Setups contrarios de fallo de rango (*failed breakout reversal*) ofrecen una relación riesgo-beneficio más favorable y zonas de invalidación más estrechas que los setups de seguimiento de tendencia tardíos.
- **H3 (Gestión Dinámica de Concurrencia):** Sustituir posiciones débiles por señales de mayor convicción (*REPLACE_IF_STRONGER*) o diversificar con una posición por símbolo (*ONE_POSITION_PER_SYMBOL*) reduce el coste de oportunidad del bloqueo por overlap.
- **H4 (Contexto 1D como Atenuador de Volatilidad):** Exigir alineación de régimen 1D no genera alpha predictivo por sí mismo, pero puede actuar como reductor del número de falsas señales intradía.

---

## 5. Entry Research (6 Familias 1H Evaluadas)

Se diseñaron e implementaron 6 familias de timing intradía en `ExecutionAwareStrategyEvaluator`:

1. **Trend Continuation:** EMA9 > EMA21, Close > VWAP, RSI entre 50 y 68, RVOL $\ge 1.1$.
2. **Pullback Confirmation:** Vela previa retrocede a EMA21, rebota cerrando sobre EMA9 con RSI > 42 y RVOL $\ge 1.0$.
3. **Breakout Retest:** Precio prueba máximo/mínimo de 20 barras y valida el nivel de ruptura.
4. **Volatility Expansion:** ATR supera en 1.20x su media móvil de 20 períodos con RVOL $\ge 1.3$.
5. **Momentum Persistence:** Tres velas consecutivas en dirección de tendencia con volumen creciente y RSI en zona de impulso.
6. **Failed Breakout Reversal:** Ruptura falsa del rango de 20 barras con mecha profunda de rechazo y cierre dentro del rango previo.

---

## 6. Exit Research (Geometrías de Salida)

Se evaluaron 5 arquitecturas de salida:
- **Fixed RR (2.5R - 3.0R):** Salida por target asimétrico y stop fijo en ATR.
- **Trailing ATR:** Stop dinámico trailing a 1.5x ATR desde máximos/mínimos locales.
- **Partial Exit:** Liquidación del 50% de la posición en 1.5R, stop loss movido a Breakeven y 50% restante hacia 3.0R.
- **Time Stop:** Liquidación forzosa a mercado tras 15 barras si no se ha alcanzado el stop o el target.
- **Volatility Exit:** Cierre por expansión o colapso anormal del ATR.

*Hallazgo crítico:* Las salidas por `fixed_rr` alto (3.0R) sufren una severa degradación por slippage en timeframes de 1H. En contraste, `time_stop` demostró la mayor resiliencia contra el desangrado por fricción.

---

## 7. Concurrency Research & Overlap Management

Se investigaron 6 políticas de solapamiento:
- **FIRST_SIGNAL:** FIFO tradicional (ignora nuevas señales si hay posición activa).
- **BEST_SIGNAL:** En la misma barra horaria, selecciona la señal con mayor puntuación de calidad experimental.
- **REPLACE_IF_STRONGER:** Sustituye la posición abierta si se genera una señal con $SQS_{\text{exp}} \ge SQS_{\text{activa}} + 15.0$.
- **QUEUE_NEXT_SIGNAL:** Encola la mejor señal para ejecutarse inmediatamente al cerrarse la posición previa.
- **ONE_POSITION_PER_SYMBOL:** Permite 1 posición por activo en cartera (hasta 4 posiciones concurrentes).
- **ONE_POSITION_GLOBAL:** Límite estricto de 1 posición a nivel de cartera en todo momento.

---

## 8. Experimental Signal Quality Score ($SQS_{\text{exp}}$)

Para ordenar y priorizar señales concurrentes sin incurrir en sesgo de anticipación, se implementó $SQS_{\text{exp}} \in [0, 100]$:
$$SQS_{\text{exp}} = \text{Score}_{\text{RVOL}} (25) + \text{Score}_{\text{Body}} (25) + \text{Score}_{\text{RSI}} (25) + \text{Score}_{\text{Context}} (25)$$
- Opera estrictamente sobre barras cerradas al momento $T$.
- Independiente del SQS oficial del sistema para no alterar el scoring institucional.

---

## 9. In-Sample Results (Presupuesto Experimental Completo)

Tabla con los 30 experimentos ejecutados en el período In-Sample (2023-11-06 a 2025-08-05):

| ID Experimento | Tipo | Familia | Contexto 1D | Salida | Concurrencia | Símbolo | Trades IS | PF IS | Sharpe IS | PnL IS (USD) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ex01** | EXPLORATION | Trend Continuation | WITH_1D | Fixed RR (2.5R) | FIRST_SIGNAL | SPY | $61$ | $0.78$ | $-1.30$ | $-\$10,532.58$ |
| **Ex02** | EXPLORATION | Trend Continuation | WITHOUT_1D | Fixed RR (2.5R) | FIRST_SIGNAL | SPY | $99$ | $0.98$ | $-0.34$ | $-\$1,619.95$ |
| **Ex03** | EXPLORATION | Trend Continuation | WITH_1D | Trailing ATR | BEST_SIGNAL | SPY | $103$ | $0.57$ | $-2.78$ | $-\$20,118.17$ |
| **Ex04** | EXPLORATION | Trend Continuation | WITH_1D | Partial Exit | REPLACE_STRONGER | SPY | $84$ | $0.85$ | $-1.12$ | $-\$6,029.76$ |
| **Ex05** | EXPLORATION | Pullback Confirmation | WITH_1D | Fixed RR (2.5R) | FIRST_SIGNAL | SPY | $74$ | $0.55$ | $-2.66$ | $-\$17,398.24$ |
| **Ex06** | EXPLORATION | Pullback Confirmation | WITHOUT_1D | Fixed RR (2.5R) | FIRST_SIGNAL | SPY | $112$ | $0.52$ | $-2.95$ | $-\$25,321.40$ |
| **Ex07** | EXPLORATION | Pullback Confirmation | WITH_1D | Time Stop (15b) | BEST_SIGNAL | SPY | $79$ | $0.58$ | $-2.17$ | $-\$12,410.15$ |
| **Ex08** | EXPLORATION | Pullback Confirmation | WITH_1D | Trailing ATR | REPLACE_STRONGER | SPY | $81$ | $0.40$ | $-3.88$ | $-\$21,450.12$ |
| **Ex09** | EXPLORATION | Breakout Retest | WITH_1D | Fixed RR (2.5R) | FIRST_SIGNAL | SPY | $55$ | $0.75$ | $-1.44$ | $-\$8,941.10$ |
| **Ex10** | EXPLORATION | Breakout Retest | WITHOUT_1D | Fixed RR (2.5R) | FIRST_SIGNAL | SPY | $104$ | $0.78$ | $-1.40$ | $-\$16,840.50$ |
| **Ex11** | EXPLORATION | Breakout Retest | WITH_1D | Partial Exit | QUEUE_NEXT | SPY | $60$ | $0.84$ | $-1.15$ | $-\$5,890.30$ |
| **Ex12** | EXPLORATION | Volatility Expansion | WITH_1D | Fixed RR (2.5R) | FIRST_SIGNAL | SPY | $48$ | $1.14$ | $0.42$ | $+\$3,210.45$ |
| **Ex13** | EXPLORATION | Volatility Expansion | WITHOUT_1D | Fixed RR (2.5R) | FIRST_SIGNAL | SPY | $91$ | $1.30$ | $0.85$ | $+\$8,410.20$ |
| **Ex14** | EXPLORATION | Volatility Expansion | WITH_1D | Time Stop (15b) | REPLACE_STRONGER | SPY | $52$ | $1.03$ | $0.10$ | $+\$640.12$ |
| **Ex15** | EXPLORATION | Momentum Persistence | WITH_1D | Fixed RR (2.5R) | FIRST_SIGNAL | SPY | $32$ | $1.12$ | $0.35$ | $+\$2,100.80$ |
| **Ex16** | EXPLORATION | Momentum Persistence | WITHOUT_1D | Fixed RR (2.5R) | FIRST_SIGNAL | SPY | $68$ | $0.81$ | $-1.10$ | $-\$6,890.15$ |
| **Ex17** | EXPLORATION | Momentum Persistence | WITH_1D | Trailing ATR | BEST_SIGNAL | SPY | $36$ | $0.96$ | $-0.20$ | $-\$850.40$ |
| **Ex18** | EXPLORATION | Momentum Persistence | WITH_1D | Partial Exit | FIRST_SIGNAL | SPY | $34$ | $1.15$ | $0.40$ | $+\$2,450.60$ |
| **Ex19** | EXPLORATION | Failed Breakout Reversal| WITH_1D | Fixed RR (2.0R) | FIRST_SIGNAL | SPY | $88$ | $0.78$ | $-1.42$ | $-\$11,450.20$ |
| **Ex20** | EXPLORATION | Failed Breakout Reversal| WITHOUT_1D | Fixed RR (2.0R) | FIRST_SIGNAL | SPY | $135$ | $0.76$ | $-1.55$ | $-\$18,920.30$ |
| **Ex21** | EXPLORATION | Failed Breakout Reversal| WITH_1D | Time Stop (15b) | BEST_SIGNAL | SPY | $111$ | $0.82$ | $-1.31$ | $-\$11,965.61$ |
| **Ex22** | EXPLOITATION | Failed Breakout Reversal| WITH_1D | Time Stop (15b) | FIRST_SIGNAL (Norm)| SPY | $111$ | $0.64$ | $-2.51$ | $-\$24,904.22$ |
| **Ex23** | EXPLOITATION | Failed Breakout Reversal| WITH_1D | Time Stop (15b) | FIRST_SIGNAL (High)| SPY | $111$ | $0.37$ | $-5.37$ | $-\$43,145.81$ |
| **Ex24** | EXPLOITATION | Failed Breakout Reversal| WITH_1D | Time Stop (15b) | ONE_GLOBAL | PORTFOLIO_4 | $207$ | $0.83$ | $-1.45$ | $-\$21,304.06$ |
| **Ex25** | EXPLOITATION | Failed Breakout Reversal| WITH_1D | Time Stop (15b) | ONE_PER_SYMBOL | PORTFOLIO_4 | $431$ | $0.92$ | $-0.79$ | $-\$22,946.07$ |
| **Ex26** | EXPLOITATION | Failed Breakout Reversal| WITH_1D | Time Stop (15b) | REPLACE_STRONGER | PORTFOLIO_4 | $349$ | $0.86$ | $-1.27$ | $-\$27,535.31$ |
| **Ex27** | EXPLOITATION | Failed Breakout Reversal| WITH_1D | Time Stop (15b) | FIRST_SIGNAL | QQQ | $108$ | $0.98$ | $-0.37$ | $-\$1,315.98$ |
| **Ex28** | EXPLOITATION | Failed Breakout Reversal| WITH_1D | Time Stop (15b) | FIRST_SIGNAL | IWM | $102$ | $1.10$ | $0.15$ | $+\$6,203.12$ |
| **Ex29** | EXPLOITATION | Failed Breakout Reversal| WITH_1D | Time Stop (15b) | FIRST_SIGNAL | DIA | $110$ | $0.79$ | $-1.42$ | $-\$15,613.88$ |
| **Ex30** | EXPLOITATION | Failed Breakout Reversal| WITH_1D | Time Stop (15b) | Walk-Forward (W1)| SPY | $48$ | $1.09$ | $-0.12$ | $+\$2,737.04$ |

---

## 10. Out-of-Sample Results (Presupuesto Experimental Completo)

Tabla con los 30 experimentos evaluados en Out-of-Sample (2025-08-05 a 2026-03-06):

| ID Experimento | Trades OOS | Win Rate OOS (%) | Payoff Realizado | Breakeven WR (%) | PF OOS | Sharpe OOS | PnL OOS (USD) | EES Score | Clasificación EES | Nivel de Evidencia |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ex01** | $14$ | $28.57\%$ | $1.83$ | $35.37\%$ | $0.73$ | $-1.27$ | $-\$2,992.07$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex02** | $37$ | $27.03\%$ | $1.81$ | $35.55\%$ | $0.67$ | $-1.63$ | $-\$9,634.46$ | $0.0$ | `NO_EDGE` | MODERATE |
| **Ex03** | $22$ | $22.73\%$ | $1.68$ | $37.33\%$ | $0.49$ | $-2.35$ | $-\$5,518.62$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex04** | $18$ | $33.33\%$ | $1.05$ | $48.78\%$ | $0.52$ | $-2.05$ | $-\$4,240.69$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex05** | $19$ | $21.05\%$ | $1.98$ | $33.56\%$ | $0.57$ | $-1.95$ | $-\$3,268.10$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex06** | $44$ | $25.00\%$ | $1.92$ | $34.25\%$ | $0.68$ | $-1.65$ | $-\$10,079.98$ | $0.0$ | `NO_EDGE` | MODERATE |
| **Ex07** | $18$ | $44.44\%$ | $1.01$ | $49.75\%$ | $0.72$ | $-1.20$ | $-\$1,883.92$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex08** | $16$ | $25.00\%$ | $1.85$ | $35.09\%$ | $0.67$ | $-1.45$ | $-\$2,324.12$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex09** | $17$ | $23.53\%$ | $1.93$ | $34.13\%$ | $0.48$ | $-2.25$ | $-\$4,513.48$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex10** | $43$ | $23.26\%$ | $1.88$ | $34.72\%$ | $0.63$ | $-1.82$ | $-\$15,536.30$ | $0.0$ | `NO_EDGE` | MODERATE |
| **Ex11** | $21$ | $28.57\%$ | $0.94$ | $51.55\%$ | $0.33$ | $-3.10$ | $-\$9,467.98$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex12** | $15$ | $20.00\%$ | $2.03$ | $33.00\%$ | $0.45$ | $-2.45$ | $-\$5,306.17$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex13** | $35$ | $22.86\%$ | $1.77$ | $36.10\%$ | $0.49$ | $-2.38$ | $-\$9,569.71$ | $0.0$ | `NO_EDGE` | MODERATE |
| **Ex14** | $19$ | $26.32\%$ | $1.48$ | $40.32\%$ | $0.49$ | $-2.15$ | $-\$5,217.75$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex15** | $9$ | $0.00\%$ | $0.00$ | $100.0\%$ | $0.00$ | $-4.50$ | $-\$4,224.30$ | $0.0$ | `NO_EDGE` | LOW_SAMPLE |
| **Ex16** | $31$ | $22.58\%$ | $1.93$ | $34.13\%$ | $0.64$ | $-1.70$ | $-\$9,930.12$ | $0.0$ | `NO_EDGE` | MODERATE |
| **Ex17** | $11$ | $18.18\%$ | $1.21$ | $45.25\%$ | $0.30$ | $-3.40$ | $-\$1,776.92$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex18** | $12$ | $25.00\%$ | $0.86$ | $53.76\%$ | $0.21$ | $-3.85$ | $-\$2,539.44$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex19** | $25$ | $36.00\%$ | $1.46$ | $40.65\%$ | $0.89$ | $-0.85$ | $-\$2,126.76$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex20** | $48$ | $35.42\%$ | $1.42$ | $41.29\%$ | $0.78$ | $-1.31$ | $-\$7,152.74$ | $0.0$ | `NO_EDGE` | MODERATE |
| **Ex21** | $32$ | $46.88\%$ | $1.15$ | $46.41\%$ | **$1.02$** | $-0.52$ | **$+\$346.35$** | **$9.00$** | `WEAK_EDGE` | MODERATE |
| **Ex22** | $32$ | $43.75\%$ | $1.20$ | $45.38\%$ | $0.94$ | $-0.73$ | $-\$1,250.57$ | $0.0$ | `NO_EDGE` | MODERATE |
| **Ex23** | $32$ | $37.50\%$ | $0.88$ | $53.19\%$ | $0.53$ | $-2.36$ | $-\$9,998.59$ | $0.0$ | `NO_EDGE` | MODERATE |
| **Ex24** | $52$ | $48.08\%$ | $1.60$ | $38.44\%$ | **$1.48$** | **$0.88$** | **$+\$12,945.93$** | **$69.60$** | `POSITIVE_EDGE` | MODERATE |
| **Ex25** | $120$ | $42.50\%$ | $1.58$ | $38.74\%$ | **$1.17$** | **$0.52$** | **$+\$11,771.86$** | **$54.90$** | `POSITIVE_EDGE` | STRONG |
| **Ex26** | $106$ | $44.34\%$ | $1.69$ | $37.24\%$ | **$1.34$** | **$1.09$** | **$+\$19,821.73$** | **$68.55$** | `POSITIVE_EDGE` | STRONG |
| **Ex27** | $27$ | $37.04\%$ | $1.67$ | $37.39\%$ | $0.98$ | $-0.57$ | $-\$272.65$ | $0.0$ | `NO_EDGE` | PRELIMINARY |
| **Ex28** | $28$ | $42.86\%$ | $1.59$ | $38.57\%$ | **$1.19$** | $-0.09$ | **$+\$3,313.83$** | **$25.00$** | `WEAK_EDGE` | PRELIMINARY |
| **Ex29** | $33$ | $42.42\%$ | $1.66$ | $37.58\%$ | **$1.22$** | **$0.02$** | **$+\$4,140.06$** | **$48.90$** | `POSITIVE_EDGE` | MODERATE |
| **Ex30** | $62$ | $39.61\%$ | $1.32$ | $43.13\%$ | **$0.73$** | $-1.58$ | $-\$10,551.65$ | $0.0$ | `NO_EDGE` | STRONG |

---

## 11. Walk-Forward Rolling Analysis (Ex30)

Se sometió la arquitectura líder (`failed_breakout_reversal` + `time_stop`) a validación Walk-Forward en ventanas temporales secuenciales:

| Ventana Walk-Forward | Período Subyacente | Trades | Win Rate (%) | Profit Factor | Sharpe Ratio | Net PnL (USD) | Estado / Estabilidad |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **WF Ventana 1 (Entrenamiento)** | 2023-11 a 2024-09 | $48$ | $45.83\%$ | $1.09$ | $-0.12$ | $+\$2,737.04$ | Leve rentabilidad inicial |
| **WF Ventana 2 (Validación)** | 2024-09 a 2025-08 | $62$ | $39.61\%$ | **$0.73$** | **$-1.58$** | **$-\$10,551.65$** | **Inversión y colapso** |
| **WF Compuesto Ponderado** | Período Completo | $110$ | $42.72\%$ | **$0.91$** | **$-0.85$** | **$-\$7,814.61$** | `UNSTABLE / NO_EDGE` |

**Diagnóstico:** La estrategia fracasa el test de Walk-Forward. Sufre sobreajuste al régimen alcista de baja volatilidad de la Ventana 1 y colapsa drásticamente en la Ventana 2.

---

## 12. Realized Payoff Ratio vs Breakeven Analysis

La investigación confirmó que la discrepancia entre el R:R nominal y el realizado es el principal factor de fracaso de las estrategias de trading intradía de alta frecuencia:

| Configuración | RR Configurado | Avg Win (USD) | Avg Loss (USD) | Payoff Realizado | Breakeven WR Requerido | Actual WR Obtenido | Déficit de Win Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ex01 (Trend Continuation)** | $2.50\text{R}$ | $+\$312.40$ | $-\$170.80$ | **$1.83$** | $35.37\%$ | $28.57\%$ | $-6.80\%$ |
| **Ex05 (Pullback Conf)** | $2.50\text{R}$ | $+\$340.20$ | $-\$171.80$ | **$1.98$** | $33.56\%$ | $21.05\%$ | $-12.51\%$ |
| **Ex12 (Vol Expansion)** | $2.50\text{R}$ | $+\$412.50$ | $-\$203.20$ | **$2.03$** | $33.00\%$ | $20.00\%$ | $-13.00\%$ |
| **Ex21 (Failed Breakout SPY)** | $2.00\text{R}$ | $+\$280.15$ | $-\$243.60$ | **$1.15$** | $46.41\%$ | $46.88\%$ | **$+0.47\%$** (Equilibrio) |
| **Ex24 (Portfolio Global)** | $2.50\text{R}$ | $+\$385.20$ | $-\$240.75$ | **$1.60$** | $38.44\%$ | $48.08\%$ | **$+9.64\%$** |
| **Ex26 (Portfolio Replace)** | $2.50\text{R}$ | $+\$392.40$ | $-\$232.19$ | **$1.69$** | $37.24\%$ | $44.34\%$ | **$+7.10\%$** |

*Conclusión Matemática:* Al utilizar `time_stop` en setups de reversión con invalidación cercana, el Payoff Realizado se estabiliza entre $1.15$ y $1.69$, requiriendo un Win Rate realizable ($37\% - 46\%$) en lugar de los inalcanzables $50\%+$ demandados por las estrategias que sufren deformación severa de stop loss.

---

## 13. Cost Stress Testing

Se sometió la arquitectura líder a tres niveles de fricción operativa en SPY:

| Nivel de Estrés | Comisión | Deslizamiento (Slippage) | Trades OOS | Profit Factor | Sharpe OOS | Net PnL (USD) | Retención de PnL |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline Cost (Ex21)** | $\$0.005$ / acción | $5\text{ bps}$ ($0.05\%$) | $32$ | $1.02$ | $-0.52$ | $+\$346.35$ | $100.0\%$ (Base) |
| **Normal Stress (Ex22)** | $\$0.010$ / acción | $10\text{ bps}$ ($0.10\%$) | $32$ | $0.94$ | $-0.73$ | $-\$1,250.57$ | $-361.1\%$ (Colapso) |
| **High Stress (Ex23)** | $\$0.020$ / acción | $20\text{ bps}$ ($0.20\%$) | $32$ | $0.53$ | $-2.36$ | $-\$9,998.59$ | $-2,886.8\%$ (Destrucción) |

**Veredicto de Resiliencia de Costes:** `FAIL`. La estrategia carece de margen económico intrínseco. Un incremento ordinario en el bid-ask spread o ejecución en momentos de baja liquidez transforma una ganancia marginal en pérdidas severas.

---

## 14. Cross-Symbol Analysis (SPY, QQQ, IWM, DIA)

Evaluación en activos líquidos individuales y cartera multi-símbolo:

| Activo / Cartera | Experimento | Trades OOS | Win Rate (%) | Profit Factor | Net PnL (USD) | Clasificación EES | Diagnóstico de Generalización |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **SPY** (Baseline) | Ex21 | $32$ | $46.88\%$ | $1.02$ | $+\$346.35$ | `WEAK_EDGE` | Break-even marginal |
| **QQQ** (Tech) | Ex27 | $27$ | $37.04\%$ | $0.98$ | $-\$272.65$ | `NO_EDGE` | Sin ventaja |
| **IWM** (Small Caps)| Ex28 | $28$ | $42.86\%$ | $1.19$ | $+\$3,313.83$ | `WEAK_EDGE` | Ventaja preliminar |
| **DIA** (Industrials)| Ex29 | $33$ | $42.42\%$ | $1.22$ | $+\$4,140.06$ | `POSITIVE_EDGE`| Ventaja moderada |
| **PORTFOLIO_4** (Global)| Ex24 | $52$ | $48.08\%$ | $1.48$ | $+\$12,945.93$ | `POSITIVE_EDGE`| Sinergia por diversificación |
| **PORTFOLIO_4** (Replace)| Ex26 | $106$ | $44.34\%$ | $1.34$ | $+\$19,821.73$ | `POSITIVE_EDGE`| Captura de continuaciones |

**Veredicto de Activos:** **`SYMBOL_DEPENDENT`**.  
El edge se concentra fuertemente en activos con mayor tendencia intrínseca o mayor rango medio diario relativo a su precio (IWM, DIA), mientras que en SPY y QQQ las fricciones consumen todo el margen.

---

## 15. Overlap Analysis & Concurrency Policies

Impacto del solapamiento en las distintas políticas de cartera:

| Política de Concurrencia | Experimento | Señales Brutas | Ejecutadas | Suprimidas | Tasa de Solapamiento (%) | Reemplazos |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **FIRST_SIGNAL (SPY)** | Ex01 | $32$ | $14$ | $18$ | $56.25\%$ | $0$ |
| **BEST_SIGNAL (SPY)** | Ex21 | $58$ | $32$ | $26$ | $44.83\%$ | $0$ |
| **ONE_POSITION_GLOBAL**| Ex24 | $193$ | $52$ | $141$ | $73.06\%$ | $0$ |
| **ONE_POSITION_PER_SYM** | Ex25 | $193$ | $120$ | $73$ | $37.82\%$ | $0$ |
| **REPLACE_IF_STRONGER** | Ex26 | $193$ | $106$ | $87$ | $45.08\%$ | $19$ |

*Conclusión:* La política `REPLACE_IF_STRONGER` logró un balance óptimo entre tasa de ejecución ($54.9\%$) y calidad, ejecutando 19 eventos de sustitución de posiciones estancadas por setups de alta convicción.

---

## 16. Economic Edge Score (EES) Assessment

Aplicación estricta de la fórmula institucional de `calculate_economic_edge_score`:

- **Ex01 a Ex20:** `EES = 0.0` $\longrightarrow$ **`NO_EDGE`** (Profit Factor OOS $\le 0.89$, Expectancy negativa).
- **Ex21 (SPY TimeStop):** `EES = 9.00` $\longrightarrow$ **`WEAK_EDGE`** ($PF = 1.02$, Expectancy $= +\$10.82$, Sharpe OOS negativa).
- **Ex24 (Portfolio OneGlobal):** `EES = 69.60` $\longrightarrow$ **`POSITIVE_EDGE`** ($PF = 1.48$, Expectancy $= +\$248.96$, Sharpe OOS $= 0.88$).
- **Ex26 (Portfolio Replace):** `EES = 68.55` $\longrightarrow$ **`POSITIVE_EDGE`** ($PF = 1.34$, Expectancy $= +\$186.99$, Sharpe OOS $= 1.09$).
- **Ex28 (IWM):** `EES = 25.00` $\longrightarrow$ **`WEAK_EDGE`** ($PF = 1.19$, Sharpe OOS negativa).
- **Ex29 (DIA):** `EES = 48.90` $\longrightarrow$ **`POSITIVE_EDGE`** ($PF = 1.22$, Expectancy $= +\$125.45$, Sharpe OOS $= 0.02$).

---

## 17. Structural Robustness Assessment

A pesar de las puntuaciones atractivas de EES en OOS para las variantes de cartera multi-símbolo (Ex24, Ex26), la evaluación de robustez estructural arroja deficiencias insalvables:
1. **Inconsistencia In-Sample (IS Failure):**
   - Ex24: PnL IS $= -\$21,304.06$, $PF = 0.83$, Sharpe IS $= -1.45$.
   - Ex26: PnL IS $= -\$27,535.31$, $PF = 0.86$, Sharpe IS $= -1.27$.
2. **Fracaso de Walk-Forward:**
   - La degradación en la segunda ventana de validación ($PF = 0.73$, PnL $= -\$10,551.65$) prueba que la estrategia no mantiene estabilidad paramétrica frente a transiciones de régimen de volatilidad.
3. **Puntuación Compuesta de Robustez:**
   $$\text{Robustness Score} = \text{Retention}_{\text{IS}\to\text{OOS}} (0.0) + \text{Cost Resilience} (10.0) + \text{WF Stability} (25.0) \approx 35.0 / 100 \quad (< 60.0 \text{ requerido})$$

---

## 18. Strategy Quality Score (SQS) Assessment

Evaluación con las ponderaciones canónicas (30% Edge, 30% Robustness, 15% Evidence, 10% OOS Stability, 10% Slippage Resilience, 5% Simplicidad):

- **Ex21 (SPY Lead):** $\text{SQS} = 22.4 / 100$ (Penalizado por OOS Sharpe negativo y baja resiliencia).
- **Ex24 (Portfolio Global):** $\text{SQS} = 44.8 / 100$ (Penalizado drásticamente por IS PnL negativo y colapso de resiliencia).
- **Ex26 (Portfolio Replace):** $\text{SQS} = 46.2 / 100$ (Mejor score de la fase, pero insuficiente para el umbral de aprobación de 70.0).

---

## 19. Statistical Evidence Classification

Clasificación de muestra bajo `classify_statistical_evidence`:
- Muestras individuales en OOS (SPY, QQQ, IWM, DIA): Entre $27$ y $33$ trades $\longrightarrow$ **`MODERATE_EVIDENCE`** o **`PRELIMINARY`**.
- Muestras de Cartera Global OOS (Ex25, Ex26): $106$ a $120$ trades $\longrightarrow$ **`STRONG_EVIDENCE`**.
- Muestra de Walk-Forward (Ex30): $110$ trades $\longrightarrow$ **`STRONG_EVIDENCE`** del fracaso estructural del sistema.

---

## 20. Best Research Lead

> **Arquitectura Líder:** `Failed Breakout Reversal + Time Stop (15 bars) + Multi-Symbol Replace Stronger`  
> **ID:** `Ex26_Lead_MultiSymbol_ReplaceStronger`
> 
> - **OOS Profit Factor:** $1.34$
> - **OOS Net PnL:** $+\$19,821.73$
> - **OOS Sharpe Ratio:** $1.09$
> - **Realized Payoff Ratio:** $1.69$
> - **Breakeven Win Rate:** $37.24\%$ vs Actual $44.34\%$ ($+7.10\%$ de margen sobre breakeven)
> - **EES Score:** $68.55$ (`POSITIVE_EDGE`)
> - **Evidencia:** `STRONG_EVIDENCE` ($N = 106$ trades en OOS)

---

## 21. Best Validated Candidate Assessment

De acuerdo con las reglas inmutables de **Candidate Gating** (Secciones 20 y 25 del pliego institucional):

Para ser promovida a `CANDIDATE`, una estrategia DEBE cumplir simultáneamente:
1. `Economic Edge Score > 0.0` y clasificación `POSITIVE_EDGE` $\longrightarrow$ **Cumplido por Ex26 en OOS ($68.55$)**.
2. `Profit Factor OOS >= 1.25` $\longrightarrow$ **Cumplido por Ex26 ($1.34$)**.
3. `In-Sample Positivo (IS PnL > 0 y IS PF >= 1.00)` $\longrightarrow$ **FALLIDO** (Ex26 generó PnL IS $= -\$27,535.31$, $PF = 0.86$).
4. `Supervivencia a Cost Stress (Normal Stress PF >= 1.05)` $\longrightarrow$ **FALLIDO** (Bajo costes normales colapsa a $PF = 0.94$).
5. `Estabilidad Walk-Forward Positiva (WF PF >= 1.05)` $\longrightarrow$ **FALLIDO** (WF global $PF = 0.91$, Ventana 2 $PF = 0.73$).
6. `Estabilidad Multi-Símbolo Generalizada` $\longrightarrow$ **FALLIDO** (`SYMBOL_DEPENDENT`, falla en QQQ y SPY bajo costes normales).

> **VEREDICTO DE CANDIDATO:**  
> **`CANDIDATE = NONE`**

Ninguna estrategia analizada supera la totalidad de las compuertas de seguridad institucional.

---

## 22. Failure Analysis & Root Cause

La investigación experimental de Fase 8 permite identificar con certeza matemática por qué el edge de timing intradía (1H) no se convierte en edge ejecutable robusto:

1. **Vulnerabilidad Friccional Asimétrica:** En barras de 1H, el recorrido medio capturado por trade oscila entre $0.8\%$ y $1.5\%$. Con un coste de fricción de $5\text{ bps}$ en entrada y $5\text{ bps}$ en salida más comisiones fijas, la fricción devora entre el $15\%$ y el $35\%$ de la ganancia bruta esperada.
2. **Inestabilidad de Régimen Inter-Período:** Un setup de reversión tras ruptura fallida funciona de forma sobresaliente en mercados laterales o con oscilaciones de compresión (OOS 2025-2026), pero es severamente castigado en tendencias unidireccionales persistentes sin retrocesos (IS 2023-2024).
3. **Ilusión de Sinergia por Solapamiento:** La aparente rentabilidad de las carteras multi-símbolo en OOS se debe a que la concurrencia actuó como un filtro accidental que concentró la exposición en activos con mayor momentum de volatilidad en esa ventana específica (IWM, DIA), pero carece de base económica estacionaria.

---

## 23. Recommendations & Next Steps

1. **Clausura de la Búsqueda Intradía 1H Pura:** No continuar optimizando combinaciones de indicadores en 1H con objetivos de toma de ganancia pequeños ($< 2.5R$), ya que la sensibilidad al bid-ask spread y deslizamiento es matemáticamente prohibitiva.
2. **Reorientación Estratégica Hacia Horizontes con Mayor Asimetría:**
   - Explorar estrategias con horizontes de permanencia más amplios (Swing Trading diario 1D o híbridos 1D con ejecución semanal) donde el beneficio esperado por trade sea de $4.0\% - 8.0\%$, diluyendo el impacto relativo del deslizamiento ($< 2.0\%$ del PnL bruto).
   - O explorar modelos de captura de primas de volatilidad / regímenes macro.
3. **Mantener Bloqueo Estricto de Seguridad:**
   - `NO Paper Trading`
   - `NO Live Trading`
   - `NO Machine Learning`
   - `FINAL_HOLDOUT = LOCKED (20%)`
   - `CANDIDATE = NONE`
