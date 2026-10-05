# INFORME DE AUDITORÍA FASE 7.4: MATCHED SIGNAL & EXECUTION ACCOUNTING REPAIR

**Fecha de Ejecución:** 2026-10-05  
**Proyecto:** `ai_trading_agent` / Strategy Laboratory  
**Versión del Core:** `v2.2.1-pro`  
**Autor:** Antigravity Autonomous Research & Quantitative Hardening Engine  
**Estado de Seguridad:** `FINAL_HOLDOUT = LOCKED` (20%) | `CANDIDATE = NONE` | `167/167 Tests PASS`  

---

## 1. Executive Summary

La Fase 7.4 se ejecutó en cumplimiento estricto del protocolo institucional de reparación contable y consistencia causal entre generación de señales y ejecución realizada.

En la Fase 7.3, la investigación detectó dos irregularidades críticas que motivaron la activación inmediata de la condición de parada (`STOP CONDITION`):
1. **Discrepancia de generador:** El análisis emparejado de señales (*Paired Signal Analysis*) evaluaba la estrategia `BASELINE_1H` (Mean Reversion), mientras que la simulación de cartera ejecutaba `CONFIG_D` (Trend Context + Pullback/Momentum con salida asimétrica).
2. **Discrepancia contable y de payoff:** El breakeven teórico de $25.0\%$ deducido de un objetivo nominal de $3.0R$ no concordaba con el comportamiento real, y la cascada contable presentaba desfases respecto al PnL neto realizado.

En esta Fase 7.4 se repararon formalmente estas deficiencias:
- **Exact Generator Match:** Se sustituyó el generador de `BASELINE_1H` en el análisis de señales por el generador idéntico de `CONFIG_D`, validado mediante huella digital criptográfica (*deterministic fingerprint*) de 16 caracteres hexadecimales: `4a33b2af0f92aaa7`.
- **Muestra estadística suficiente:** Con el generador alineado, el número de señales evaluadas pasó del $N=7$ atípico a $N=5,377$ en In-Sample ($2,504$ permitidas y $2,873$ rechazadas) y $N=1,603$ en Out-of-Sample ($741$ permitidas y $862$ rechazadas).
- **Reconciliación matemática de Payoff y Breakeven:** Se demostró analíticamente por qué un ratio configurado de $3.0R$ se degrada a un *Payoff Ratio* real de $2.02$ (IS) y $2.42$ (OOS) debido a la compresión bid-ask del *slippage* ($5$ bps en entrada y salida) y comisiones fijas, elevando el Win Rate de equilibrio (*Breakeven Win Rate*) del $25.0\%$ nominal a $33.11\%$ (IS) y $29.21\%$ (OOS). Dado que los Win Rates reales fueron $27.31\%$ y $23.79\%$ respectivamente, el PnL neto es inevitablemente deficitario.
- **Cascada contable exacta ($\Delta = \$0.0000 \le \$0.01$):** Se reconstruyó la identidad contable canónica entre el PnL teórico a precios mid, el deslizamiento total de ejecución, las comisiones de liquidación y los redondeos de centavos, cerrando con discrepancia nula.
- **Auditoría de Overlap y concurrencia:** Se separó la restricción de factibilidad operativa ($1$ sola posición simultánea) de la calidad intrínseca de señal.
- **Veredictos concluyentes:**
  - *Información Predictiva (Filtro 1D):* **INCONCLUSIVE** (pequeño delta en OOS de $+\$6.07$, negativo en IS de $-\$7.38$).
  - *Edge Económico Ejecutable:* **NOT_SUPPORTED** ($PF = 0.76$, Sharpe anualizado = $-3.15$, PnL neto = $-\$6,559.98$).

---

## 2. Generator Identity & Fingerprint

Para evitar cualquier disparidad causal entre las señales analizadas y las órdenes enviadas al motor de ejecución, se unificó la lógica del generador intradía de `CONFIG_D` en todas las capas del laboratorio.

### 2.1. Especificación Unificada del Generador CONFIG_D
- **Timeframe de contexto:** 1D cerrado (SMA20, SMA50, EMA9, EMA21, sin look-ahead).
- **Timeframe de ejecución:** 1H cerrado.
- **Regla Long:** $(RSI_{14} \le 45.0 \lor (EMA_9 > EMA_{21} \land Close > VWAP)) \land RVOL \ge 1.1$.
- **Regla Short:** $(RSI_{14} \ge 55.0 \lor (EMA_9 < EMA_{21} \land Close < VWAP)) \land RVOL \ge 1.1$.
- **Stop Loss:** $Close \mp (ATR_{14} \times 1.2 \times 0.9)$.
- **Take Profit:** $Close \pm (Risk \times 3.0)$ (Salida asimétrica configurada a $3.0R$).

### 2.2. Huellas Digitales Criptográficas Deterministas (Fingerprints)
Se implementó el método determinista SHA256 sobre la especificación completa de reglas y parámetros:

| Entidad de Evaluación | Fingerprint (SHA256 Truncado) | Estado de Concordancia |
| :--- | :---: | :---: |
| `config_d_signal_generator_fingerprint` | `4a33b2af0f92aaa7` | Referencia Canónica |
| `paired_signal_generator_fingerprint` | `4a33b2af0f92aaa7` | **100% IDENTICAL (MATCH)** |
| `baseline_1h_generator_fingerprint` | `d720f41ab9102ca1` | Mutuamente Excluyente |

**Aserción Institucional:**
$$\text{config\_d\_signal\_generator\_fingerprint} \equiv \text{paired\_signal\_generator\_fingerprint} \quad [\text{PASS}]$$

---

## 3. Matched Signal Analysis (In-Sample & Out-of-Sample)

Con el generador de `CONFIG_D` operando tanto en el análisis prospectivo como en la simulación, se evaluaron todas las señales brutas generadas en el período cronológico común alineado (2024-01-01 a 2024-09-30).

### 3.1. Evaluación In-Sample (IS: 2024-01-01 a 2024-06-30)
- **Total Señales Brutas 1H Generadas:** $5,377$
- **Aceptadas por Filtro 1D (Allowed):** $2,504$ ($46.57\%$)
- **Rechazadas por Filtro 1D (Rejected):** $2,873$ ($53.43\%$)
- **Acceptance Rate:** $46.57\%$

| Métrica Prospectiva (Horizonte 10 barras) | ALLOWED BY 1D | REJECTED BY 1D | Delta ($\Delta = \text{All} - \text{Rej}$) |
| :--- | :---: | :---: | :---: |
| **Número de Señales ($N$)** | $2,504$ | $2,873$ | $-369$ |
| **Win Rate Prospectivo (%)** | $35.82\%$ | $37.94\%$ | $-2.12\%$ |
| **Expectancy (USD / 100 shares)** | $+\$14.27$ | $+\$21.65$ | **$-\$7.38$** |
| **Profit Factor Prospectivo** | $1.12$ | $1.18$ | $-0.06$ |
| **MFE (Price Points)** | $\$2.78$ | $\$2.86$ | $-\$0.08$ |
| **MAE (Price Points)** | $\$2.33$ | $\$2.30$ | $+\$0.03$ |

### 3.2. Evaluación Out-of-Sample (OOS: 2024-07-01 a 2024-09-30)
- **Total Señales Brutas 1H Generadas:** $1,603$
- **Aceptadas por Filtro 1D (Allowed):** $741$ ($46.23\%$)
- **Rechazadas por Filtro 1D (Rejected):** $862$ ($53.77\%$)
- **Acceptance Rate:** $46.23\%$

| Métrica Prospectiva (Horizonte 10 barras) | ALLOWED BY 1D | REJECTED BY 1D | Delta ($\Delta = \text{All} - \text{Rej}$) |
| :--- | :---: | :---: | :---: |
| **Número de Señales ($N$)** | $741$ | $862$ | $-121$ |
| **Win Rate Prospectivo (%)** | $35.09\%$ | $34.80\%$ | $+0.29\%$ |
| **Expectancy (USD / 100 shares)** | $+\$22.78$ | $+\$16.71$ | **$+\$6.07$** |
| **Profit Factor Prospectivo** | $1.18$ | $1.13$ | $+0.05$ |
| **MFE (Price Points)** | $\$2.93$ | $\$2.93$ | $\$0.00$ |
| **MAE (Price Points)** | $\$2.53$ | $\$2.39$ | $+\$0.14$ |

### 3.3. Resolución de la Objeción Estadística de Fase 7.3
En Fase 7.3, la discrepancia de generador produjo un subconjunto Allowed residual de apenas $N=7$ señales, lo que invalidaba cualquier inferencia estadística.  
En Fase 7.4, el generador emparejado generó $N=741$ señales permitidas y $N=862$ señales rechazadas en OOS ($N=2,504$ y $N=2,873$ en IS). La objeción de tamaño muestral queda **definitivamente resuelta y superada**.

---

## 4. Filter Attribution Re-Evaluation

A partir de los datos empíricos obtenidos con el generador emparejado:

1. **¿El filtro 1D mejora la calidad de la señal de CONFIG_D?**
   - **En In-Sample:** No. La expectativa media de las señales permitidas ($+\$14.27$) fue menor que la de las rechazadas ($+\$21.65$), con un Win Rate $2.12\%$ inferior.
   - **En Out-of-Sample:** Muestra una mejora marginal. La expectativa media subió de $+\$16.71$ a $+\$22.78$ ($+\$6.07$ por cada 100 acciones), y el Profit Factor aumentó levemente de $1.13$ a $1.18$.
2. **Comparación Allowed vs Rejected:**
   - La diferencia de Win Rate es prácticamente nula en OOS ($+0.29\%$).
   - El MFE promedio es idéntico en OOS ($\$2.93$ vs $\$2.93$), mientras que el MAE es ligeramente superior en las señales permitidas ($\$2.53$ vs $\$2.39$), indicando que las operaciones permitidas soportan drawdowns intradía similares o levemente mayores.
3. **¿El filtro agrega alpha predictivo o destruye oportunidades?**
   - En términos de selección direccional, el filtro rechaza el $53.77\%$ de las señales en OOS. Dado que el grupo rechazado generó una expectativa positiva robusta de $+\$16.71$ con $PF = 1.13$, el filtro 1D descarta un volumen considerable de operaciones rentables.
   - La inconsistencia inter-período (IS destructivo vs OOS marginalmente positivo) concluye que el filtro **no posee un alpha predictivo estable**.

---

## 5. Realized Payoff & Breakeven Derivation

### 5.1. Definición y Fórmula Canónica
El Win Rate de equilibrio (*Breakeven Win Rate*) para cualquier sistema de trading viene dado estrictamente por:
$$\text{Breakeven Win Rate} = \frac{1}{1 + \text{Payoff Ratio}} = \frac{1}{1 + \frac{\overline{\text{Win}}}{\overline{\text{Loss}}}}$$

- **Configuración Nominal:** Con un target asimétrico de $3.0R$, el breakeven teórico ideal (sin fricción) es:
  $$\text{Breakeven}_{\text{teórico}} = \frac{1}{1 + 3.0} = 25.00\%$$

### 5.2. Métricas Realizadas en Ejecución

| Parámetro | In-Sample (IS) Realizado | Out-of-Sample (OOS) Realizado |
| :--- | :---: | :---: |
| **Trades Totales ($N$)** | $875$ | $311$ |
| **Trades Ganadores / Perdedores** | $239\text{ W} / 636\text{ L}$ | $74\text{ W} / 237\text{ L}$ |
| **Ganancia Promedio ($\overline{\text{Win}}$)** | $+\$279.16$ | $+\$275.60$ |
| **Pérdida Promedio ($\overline{\text{Loss}}$)** | $-\$138.20$ | $-\$113.73$ |
| **Payoff Ratio Realizado** | **$2.02$** | **$2.42$** |
| **Breakeven Win Rate Realizado** | **$33.11\%$** | **$29.21\%$** |
| **Win Rate Real Efectivo** | **$27.31\%$** | **$23.79\%$** |
| **Déficit de Win Rate respecto a Breakeven** | **$-5.80\%$** | **$-5.42\%$** |

### 5.3. Explicación Causal de la Degradación de 3.0R a 2.02R - 2.42R
1. **Compresión por Fricción de Slippage ($5$ bps):**
   - En una entrada Long a $\$450.00$, el fill se ejecuta a $\$450.225$ ($+\$0.225$).
   - En una salida a Stop Loss a $\$440.00$, el fill se ejecuta a $\$439.78$ ($-\$0.22$ adicional de pérdida).
   - En una salida a Take Profit a $\$480.00$, el fill se ejecuta a $\$479.76$ ($-\$0.24$ de ganancia mutilada).
   - Esto expande la pérdida promedio un $\approx 4.5\%$ y contrae la ganancia promedio un $\approx 3.2\%$.
2. **Impacto Fijo de Comisiones ($0.005$ USD/acción):**
   - Las comisiones se deducen directamente del resultado neto, reduciendo asimétricamente el ratio beneficio/riesgo neto.
3. **Dinámica Intradía de Gaps:**
   - Si una barra horaria abre con un gap adverso por debajo del Stop Loss, la pérdida ejecutada supera el $1.0R$ nominal. En cambio, las tomas de ganancia están estrictamente acotadas al precio objetivo de $3.0R$.
4. **Conclusión Matemática:**
   Dado que el Win Rate real ($27.31\%$ en IS y $23.79\%$ en OOS) es sistemáticamente inferior al Breakeven Win Rate requerido ($33.11\%$ y $29.21\%$), la esperanza matemática del sistema es inevitablemente negativa:
   $$\mathbb{E}[\text{PnL}] = (0.2379 \times 275.60) - (0.7621 \times 113.73) = 65.56 - 86.67 = -\$21.11 \text{ por trade}$$

---

## 6. Exact Accounting Waterfall (IS & OOS)

### 6.1. Definición Canónica Única de Métricas
Para eliminar cualquier ambigüedad contable en todo el proyecto:
- **Ideal Mid-Price PnL:** Resultado teórico libre de fricción evaluado a precios mid sin slippage ni comisiones:
  $$\text{Ideal Mid PnL} = \sum_{i=1}^N \left(P_{\text{mid, exit}}^{(i)} - P_{\text{mid, entry}}^{(i)}\right) \times Q_i$$
- **Slippage Drag:** Impacto monetario total del deslizamiento acumulado en entradas y salidas:
  $$\text{Slippage Drag} = \sum_{i=1}^N \left[\left|P_{\text{fill, entry}}^{(i)} - P_{\text{mid, entry}}^{(i)}\right| + \left|P_{\text{fill, exit}}^{(i)} - P_{\text{mid, exit}}^{(i)}\right|\right] \times Q_i$$
- **Gross Realized PnL:** PnL bruto realizado a precios fill reales, antes de comisiones:
  $$\text{Gross Realized PnL} = \text{Ideal Mid PnL} - \text{Slippage Drag} = \sum_{i=1}^N \left(P_{\text{fill, exit}}^{(i)} - P_{\text{fill, entry}}^{(i)}\right) \times Q_i$$
- **Exit Commission:** Comisión institucional cobrada al liquidar la orden ($0.005$ USD/acción):
  $$\text{Exit Commission} = \sum_{i=1}^N Q_i \times 0.005$$
- **Net Realized PnL:** PnL neto efectivamente registrado en la cuenta de capital:
  $$\text{Net Realized PnL} = \text{Gross Realized PnL} - \text{Exit Commission} + \text{Rounding}$$

### 6.2. Cascada Contable In-Sample (IS: 875 Trades)

| Componente Contable | Monto (USD) | Impacto / Naturaleza |
| :--- | :---: | :--- |
| **Ideal Mid-Price PnL** | **$-\$3,971.72$** | PnL teórico libre de fricción |
| $(-)$ Entry Slippage Drag | $-\$8,485.65$ | Deslizamiento de apertura (5 bps) |
| $(-)$ Exit Slippage Drag | $-\$8,486.70$ | Deslizamiento de cierre (5 bps) |
| **$(=)$ Subtotal Slippage Drag** | **$-\$16,972.35$** | **Arrastre total por slippage** |
| **$(=)$ Gross Realized PnL** | **$-\$20,944.07$** | **PnL bruto a precios fill** |
| $(-)$ Exit Commissions | $-\$232.95$ | Comisiones institucionales |
| $(+)$ Rounding Adjustment | $+\$0.06$ | Ajuste de redondeo de centavos |
| **$(=)$ Net Realized PnL** | **$-\$21,176.96$** | **PnL neto realizado final** |
| **Verificación de Identidad ($\Delta$)** | **$\$0.0000$** | **EXACT MATCH ($\le \$0.01$)** |

### 6.3. Cascada Contable Out-of-Sample (OOS: 311 Trades)

| Componente Contable | Monto (USD) | Impacto / Naturaleza |
| :--- | :---: | :--- |
| **Ideal Mid-Price PnL** | **$-\$390.42$** | PnL teórico libre de fricción |
| $(-)$ Entry Slippage Drag | $-\$3,050.12$ | Deslizamiento de apertura (5 bps) |
| $(-)$ Exit Slippage Drag | $-\$3,050.62$ | Deslizamiento de cierre (5 bps) |
| **$(=)$ Subtotal Slippage Drag** | **$-\$6,100.74$** | **Arrastre total por slippage** |
| **$(=)$ Gross Realized PnL** | **$-\$6,491.16$** | **PnL bruto a precios fill** |
| $(-)$ Exit Commissions | $-\$68.78$ | Comisiones institucionales |
| $(-)$ Rounding Adjustment | $-\$0.045$ | Ajuste de redondeo de centavos |
| **$(=)$ Net Realized PnL** | **$-\$6,559.985$** | **PnL neto realizado final** |
| **Verificación de Identidad ($\Delta$)** | **$\$0.0000$** | **EXACT MATCH ($\le \$0.01$)** |

---

## 7. Overlap & Concurrency Analysis

Dado que el sistema ejecuta una estrategia monomercado con capacidad máxima de **1 sola posición activa simultánea**, muchas señales válidas generadas son descartadas por concurrencia.

### 7.1. Cuantificación de Concurrencia
- **In-Sample (IS):**
  - Señales Permitidas por 1D: $2,504$
  - Señales Ejecutadas: $875$ ($34.94\%$)
  - Señales Suprimidas por Posición Activa (Overlap): $1,629$ ($65.06\%$)
  - **Tasa de Concurrencia (Concurrency Rate):** $65.06\%$
- **Out-of-Sample (OOS):**
  - Señales Permitidas por 1D: $741$
  - Señales Ejecutadas: $311$ ($41.97\%$)
  - Señales Suprimidas por Posición Activa (Overlap): $430$ ($58.03\%$)
  - **Tasa de Concurrencia (Concurrency Rate):** $58.03\%$

### 7.2. Evaluación del Contrafactual: Ejecutadas vs Suprimidas

| Muestra | Subconjunto | Número ($N$) | Win Rate (%) | Expectancy (USD/100sh) | Profit Factor |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **In-Sample** | **Ejecutadas** | $875$ | $36.80\%$ | $+\$18.91$ | $1.16$ |
| | **Suprimidas (Overlap)** | $1,629$ | $35.24\%$ | $+\$11.78$ | $1.10$ |
| | *Delta (Ejecutadas - Suprimidas)* | | $+1.56\%$ | **$+\$7.13$** | $+0.06$ |
| **Out-of-Sample** | **Ejecutadas** | $311$ | $33.12\%$ | $+\$6.32$ | $1.05$ |
| | **Suprimidas (Overlap)** | $430$ | $36.51\%$ | $+\$34.67$ | $1.29$ |
| | *Delta (Ejecutadas - Suprimidas)* | | $-3.39\%$ | **$-\$28.35$** | $-0.24$ |

### 7.3. Interpretación del Impacto de la Regla de Posición Única
- **En In-Sample:** La regla de posición única actuó como un filtro beneficioso: las señales ejecutadas tuvieron mayor rendimiento ($+\$18.91$) que las omitidas ($+\$11.78$).
- **En Out-of-Sample:** La regla perjudicó la rentabilidad: las señales bloqueadas tenían una expectativa prospectiva superior ($+\$34.67$ vs $+\$6.32$), demostrando que la primera señal que abre una posición suele atrapar el inicio de consolidaciones ruidosas, impidiendo tomar mejores continuaciones posteriores.

---

## 8. Execution Feasibility vs Signal Quality Separation

Es imperativo separar formalmente dos conceptos que se confundieron en fases anteriores:

1. **Restricción de Factibilidad Operativa (*Execution Feasibility*):**
   - Una cuenta con capital limitado y control estricto de margen solo puede asignar riesgo a un trade simultáneo.
   - El hecho de que una señal no se ejecute no invalida su existencia causal, sino que refleja una restricción de capacidad de inventario.
2. **Calidad Intrínseca de la Señal (*Prospective Signal Quality*):**
   - La calidad predictiva de un setup técnico debe medirse prospectivamente en un horizonte fijo independiente del estado de cartera.
   - La evidencia demuestra que las señales brutas tienen una leve expectativa teórica positiva ($+\$22.78$ en OOS a 10 barras), pero esa expectativa es enteramente teórica y desaparece al enfrentar la ejecución secuencial dependiente de trayectorias.

---

## 9. Comprehensive Comparison Table

Tabla consolidada que resume todas las arquitecturas y subconjuntos analizados en Fase 7.4 bajo el marco temporal alineado común:

| Configuración / Subconjunto | Ventana | Trades / Señales | Win Rate (%) | Payoff / PF | Expectancy / Sharpe | Net Realized PnL | EES Score | Estado / Veredicto |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **CONFIG_D (Executed Trades)** | IS | $875$ | $27.31\%$ | $2.02$ / $0.77$ | $\text{Sh} = -3.85$ | $-\$21,176.96$ | $0.0$ | `NO_EDGE` |
| **CONFIG_D (Executed Trades)** | OOS | $311$ | $23.79\%$ | $2.42$ / $0.76$ | $\text{Sh} = -3.15$ | $-\$6,559.98$ | $0.0$ | `NO_EDGE` |
| **CONFIG_D (1H Raw Signals)** | IS | $5,377$ | $36.95\%$ | $1.15$ | $+\$18.21$ | N/A (Teórico) | N/A | Señales brutas |
| **CONFIG_D (1H Raw Signals)** | OOS | $1,603$ | $34.93\%$ | $1.15$ | $+\$19.51$ | N/A (Teórico) | N/A | Señales brutas |
| **CONFIG_D (Allowed by 1D)** | IS | $2,504$ | $35.82\%$ | $1.12$ | $+\$14.27$ | N/A (Teórico) | N/A | Señal prospectiva |
| **CONFIG_D (Allowed by 1D)** | OOS | $741$ | $35.09\%$ | $1.18$ | $+\$22.78$ | N/A (Teórico) | N/A | Señal prospectiva |
| **CONFIG_D (Rejected by 1D)** | IS | $2,873$ | $37.94\%$ | $1.18$ | $+\$21.65$ | N/A (Teórico) | N/A | Señal prospectiva |
| **CONFIG_D (Rejected by 1D)** | OOS | $862$ | $34.80\%$ | $1.13$ | $+\$16.71$ | N/A (Teórico) | N/A | Señal prospectiva |
| **CONFIG_D (Suppressed Overlap)** | IS | $1,629$ | $35.24\%$ | $1.10$ | $+\$11.78$ | N/A (Teórico) | N/A | Concurrencia |
| **CONFIG_D (Suppressed Overlap)** | OOS | $430$ | $36.51\%$ | $1.29$ | $+\$34.67$ | N/A (Teórico) | N/A | Concurrencia |

---

## 10. Final Holdout Status

- **Configuración de Seguridad:** $20\%$ del dataset total cronológico permanece estrictamente reservado como `FINAL_HOLDOUT`.
- **Estado de Aislamiento:** **LOCKED**.
- **Protección Activa:** Cualquier intento de acceso para investigación, optimización o minería de datos levanta programáticamente una excepción `PermissionError`.
- **Validación:** Confirmado en la suite de pruebas unitarias (`test_final_holdout_strict_isolation`).

---

## 11. Test Suite Verification

La suite de pruebas del sistema fue ejecutada en su totalidad tras las modificaciones y adiciones de Fase 7.4:

- **Archivo de pruebas específico:** `ai_trading_agent/tests/test_fase7_4_accounting_repair.py` (5/5 PASS).
- **Suite global ejecutada vía `run_agent_tests.py`:**
  - Total pruebas ejecutadas: **167**
  - Pruebas aprobadas: **167** ($100\%$)
  - Pruebas fallidas: **0**
  - Tiempo de ejecución: $26.71$ segundos.

---

## 12. Predictive vs Executable Edge Verdict

Se emite un dictamen formal e independiente sobre ambas interrogantes cuantitativas:

### 12.1. PREDICTIVE INFORMATION (Filtro 1D)
> **VEREDICTO: INCONCLUSIVE**  
> *Fundamentación:* Si bien en Out-of-Sample el subconjunto de señales permitidas por el filtro diario exhibió una expectativa prospectiva ligeramente superior a las rechazadas ($+\$22.78$ vs $+\$16.71$, delta de $+\$6.07$), en In-Sample ocurrió lo contrario ($+\$14.27$ vs $+\$21.65$, delta de $-\$7.38$). Además, el filtro rechaza señales altamente rentables en OOS ($N=862$, $PF=1.13$). No existe estabilidad temporal estadística que justifique considerar el filtro 1D como un predictor predictivo de alpha robusto.

### 12.2. EXECUTABLE ECONOMIC EDGE (Estrategia CONFIG_D)
> **VEREDICTO: NOT_SUPPORTED**  
> *Fundamentación:* La estrategia `CONFIG_D` colapsa económicamente al pasar de la evaluación prospectiva a la simulación con fricciones reales. En OOS genera un Profit Factor realizado de $0.76$, un Sharpe ratio anualizado de $-3.15$ y una pérdida neta de $-\$6,559.98$. La fricción combinada de comisiones y slippage ($-\$6,169.52$ en OOS) absorbe completamente cualquier ventaja teórica del generador.

---

## 13. Root Cause Conclusion

La discrepancia observada entre el aparente éxito de las señales y el fracaso de la ejecución se explica por tres causas fundamentales:

1. **Mutilación del Payoff Ratio:** El sistema no alcanza el objetivo teórico de $3.0R$ debido a que el deslizamiento y las comisiones reducen los beneficios en las tomas de ganancia y expanden las pérdidas en los stop loss, situando el Payoff real en $2.02$ - $2.42$.
2. **Win Rate Insuficiente:** Con un Payoff real de $2.42$, el sistema requiere un Win Rate mínimo del $29.21\%$ para alcanzar el punto de equilibrio. El Win Rate real obtenido en OOS fue del $23.79\%$, generando una expectativa matemática negativa inevitable.
3. **Bloqueo por Concurrencia:** La restricción de posición única impide capturar continuaciones rentables mientras la posición previa permanece abierta en drawdowns o consolidaciones intradía.

---

## 14. Next Phase Recommendation

Habiéndose cerrado la auditoría contable y de emparejamiento con rigor absoluto:
1. **No promover CONFIG_D a producción ni paper trading:** La estrategia no tiene edge económico ejecutable.
2. **Mantener CANDIDATE = NONE.**
3. **Mantener FINAL_HOLDOUT = LOCKED.**
4. **Próxima investigación recomendada:** Reorientar la investigación hacia arquitecturas donde los costos de fricción representen una fracción significativamente menor del objetivo de beneficio (e.g. timeframes diarios 1D puros con mayor distancia a SL/TP o reducción drástica de frecuencia de trading) o investigar mecanismos de salida dinámica que reduzcan el tiempo en mercado y mitiguen la degradación del payoff.

---

## 15. Stop Condition Assessment

La condición de parada institucional (`STOP CONDITION`) se mantiene formalmente **ACTIVADA**:
- No se han identificado estrategias con Economic Edge Score $> 0.0$.
- Ninguna arquitectura multi-timeframe híbrida ha logrado superar las pruebas de costes OOS.
- Se respetan todos los candados de seguridad cuantitativa:
  - `NO Paper Trading`
  - `NO Live Trading`
  - `NO Machine Learning`
  - `NO Parameter Overfitting`
  - `CANDIDATE = NONE`
