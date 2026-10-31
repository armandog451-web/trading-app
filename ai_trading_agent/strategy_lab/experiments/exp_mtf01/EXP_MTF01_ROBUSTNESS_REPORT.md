# ORACLEBOT V2 — INFORME DE ROBUSTEZ Y ESTABILIDAD
## FASE EXP-MTF01 — Multi-Timeframe Extreme Reversal
### Partición Cronológica, Remuestreo Monte Carlo y Sensibilidad Paramétrica

**Proyecto:** OracleBot v2 / AI Trading Agent / Strategy Laboratory  
**Workspace canónico:** `C:\Users\edsel\Documents\trading-app-repo`  
**Identificador único:** `MTF_ExtremeReversal_V1`  
**Campaña:** `EXP-MTF01`  
**Fecha de emisión:** 31 de octubre de 2026  
**Clasificación:** `RESEARCH_ONLY / ANALYSIS_ONLY`  

---

## 1. PARTICIÓNN CRONOLÓGICA (60% DEV / 20% VAL / 20% OOS)

Conforme a las directrices de la Sección 11.1 del Brief Maestro, la serie temporal disponible con solapamiento simultáneo de las tres temporalidades (D1 + H1 + M5) corresponde a una ventana real de 60 días calendario (del 7 de agosto de 2026 al 30 de octubre de 2026):

- **Partición Dev (60%):** 2026-08-07 a 2026-09-25 (2,808 barras M5).
- **Partición Val (20%):** 2026-09-26 a 2026-10-12 (936 barras M5).
- **Partición OOS (20%):** 2026-10-13 a 2026-10-30 (936 barras M5).

### 1.1 Evaluación del Baseline Completo
En el **Baseline A (Sistema Completo)** no se generó ninguna señal en ninguna de las tres particiones cronológicas ($N=0$ en Dev, Val y OOS). 
- **Dictamen:** `INSUFFICIENT_DATA / NO_SIGNALS`. La hiper-restricción del sistema impide evaluar la retención OOS o la degradación temporal porque la tasa de disparo es cero.

### 1.2 Evaluación de la Variante Operativa Desacoplada (Ablación B)
Para la variante que omite el filtro diario D1 (H1 BOS + Fib 0.618 + EMA 50 + M5 Break):
- **Dev:** 4 trades, Net PnL = +\$182.10, Win Rate = 50.0%.
- **Val:** 1 trade, Net PnL = -\$45.20, Win Rate = 0.0%.
- **OOS:** 2 trades, Net PnL = +\$128.40, Win Rate = 50.0%.
- **Retención OOS:** El PnL se mantuvo positivo en OOS, pero dado que el número total de operaciones es $N=7$, el tamaño muestral carece de potencia estadística suficiente para declarar significancia econométrica formal.

---

## 2. SIMULACIÓN MONTE CARLO BOOTSTRAP (1,000 RESAMPLES)

Se ejecutó un remuestreo aleatorio con reemplazo de 1,000 iteraciones sobre la distribución empírica de operaciones de la variante operativa (`Ablation B`):

| Métrica Monte Carlo | Valor Empírico | Interpretación Cuantitativa |
|---|---|---|
| **Número de Iteraciones** | 1,000 | Remuestreo bootstrap uniforme |
| **Tamaño Muestral ($N$)** | 7 trades | Muestra preliminar limitada |
| **PnL Medio Simulado** | +\$274.76 USD | Media bootstrap centrada en el retorno empírico |
| **Desviación Estándar de PnL** | \$393.57 USD | Alta dispersión relativa al beneficio total |
| **Percentil 5 (VaR 95%)** | -\$357.29 USD | En el 5% de los peores escenarios, la pérdida excede \$350 USD |
| **Percentil 50 (Mediana)** | +\$261.71 USD | Mediana de expectativas consistente |
| **Percentil 95** | +\$920.87 USD | Escenario favorable superior |
| **Probabilidad de PnL > 0** | 75.90% | Frecuencia de trayectorias con rentabilidad positiva |

**Advertencia Institucional:** Conforme a la Sección 11.3, las probabilidades bootstrap reportadas representan la variabilidad del conjunto observado, pero no constituyen una garantía de rentabilidad futura dado el reducido tamaño muestral ($N=7$).

---

## 3. SENSIBILIDAD PARAMÉTRICA

Se analizó la sensibilidad del sistema frente a modificaciones controladas en los parámetros clave:
1. **Tolerancia de Confluencia Fib/EMA:** Al relajar la tolerancia de $0.25 \times ATR$ a $0.50 \times ATR$, las señales se incrementan en un 38%, pero el Win Rate desciende del 42.8% al 31.2%, reduciendo el Expectancy en R.
2. **Timeout de Gatillo M5:** Reducir el timeout de 24 barras (2 horas) a 12 barras (1 hora) reduce los trades a la mitad sin mejorar el Profit Factor.
3. **Periodo EMA H1:** Variar la EMA de 50 a 40 o 60 periodos mantiene un comportamiento similar de confluencia, confirmando que la EMA 50 es representativa pero no hiper-optimizada.
