# ORACLEBOT V2 — FASE 7.2: INFORME DE ROBUSTEZ ESTADÍSTICA
## REMUESTREO BOOTSTRAP, VALIDACIÓN CRUZADA LOSO Y CONTROL DE SOBREAJUSTE

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.2 — Validación Cuantitativa Multiactivo  
**Fecha:** 30 de octubre de 2026  
**Metodología:**
- Remuestreo Bootstrap no paramétrico (1,000 iteraciones, $IC_{95\%}$).
- Validación cruzada *Leave-One-Symbol-Out* (LOSO).
- Evaluación de significancia estadística frente a la hipótesis nula ($H_0: \text{Expectancy} \le 0$).

---

## 1. REMUESTREO BOOTSTRAP (1,000 ITERACIONES, IC 95%)

El análisis Bootstrap evalúa la estabilidad del PnL neto, la tasa de acierto y el Profit Factor frente al orden y combinación de las operaciones históricas.

### Resultados de Remuestreo para las Estrategias Canónicas (Filtradas, Coste 1x)

| Métrica | `MR_RsiBollinger_V1` ($N=102$) | `MOM_TrendPullback_V1` ($N=9$) |
| :--- | :---: | :---: |
| **Net PnL Observado** | +$566.33 USD | -$130.49 USD |
| **Intervalo de Confianza 95% PnL** | **[-$3,880.15, +$4,962.29]** | **[-$1,233.17, +$953.82]** |
| **Win Rate Observado** | 53.92% | 55.56% |
| **Intervalo de Confianza 95% WR** | [45.10%, 62.75%] | [22.22%, 88.89%] |
| **Net Profit Factor Observado** | 1.06 | 0.84 |
| **Intervalo de Confianza 95% PF** | [0.66, 1.69] | [0.16, 7.31] |
| **Probabilidad de Pérdida Neta $p(\text{Loss})$** | **41.30%** | **60.30%** |
| **Significancia Estadística ($p < 0.05$)** | **NO SIGNIFICATIVO ($p = 0.413$)** | **NO SIGNIFICATIVO ($p = 0.603$)** |

### Conclusiones del Bootstrap
1. **Mean Reversion:** El intervalo de confianza del 95% abarca desde una pérdida de -$3,880 hasta una ganancia de +$4,962. La probabilidad de que una muestra aleatoria de trades genere pérdidas netas es del **41.3%**. En estadística cuantitativa, no es posible rechazar la hipótesis nula de que la estrategia no posee ventaja económica real.
2. **Momentum:** Con solo 9 operaciones, la dispersión del intervalo es enorme y la probabilidad de pérdida es del **60.3%**. La estrategia carece de potencia estadística.

---

## 2. VALIDACIÓN CRUZADA LEAVE-ONE-SYMBOL-OUT (LOSO)

Para determinar si los resultados agregados dependen de un único activo atípico (como SPY), se evaluó el rendimiento del portafolio excluyendo sistemáticamente un activo a la vez.

### Resultados LOSO para `MR_RsiBollinger_V1` (Filtrada, Coste 1x Base)

| Excluyendo Símbolo | Activos Restantes | Operaciones | Win Rate | True Net PnL | Net PF | Sharpe | Max DD % | Impacto / Conclusión |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Ninguno (Portafolio Base)** | 6 activos | 102 | 53.92% | **+$566.33** | 1.06 | 0.11 | 2.45% | Baseline con los 6 activos |
| **EXCLUDING_SPY** | 5 activos | 80 | 50.00% | **-$889.38** | **0.89** | **-0.18** | **2.48%** | **COLAPSO A PÉRDIDAS (Dependencia crítica de SPY)** |
| **EXCLUDING_QQQ** | 5 activos | 85 | 52.94% | +$615.62 | 1.08 | 0.13 | 1.90% | Mejora marginal (elimina pérdidas de QQQ) |
| **EXCLUDING_IWM** | 5 activos | 87 | 54.02% | **-$41.91** | **0.99** | **-0.00** | **3.04%** | Cae a pérdidas marginales |
| **EXCLUDING_DIA** | 5 activos | 87 | 56.32% | +$1,083.21 | 1.13 | 0.21 | 1.94% | Mejora al excluir pérdidas industriales |
| **EXCLUDING_XLF** | 5 activos | 86 | 55.81% | +$1,151.17 | 1.14 | 0.22 | 1.88% | Mejora al excluir pérdidas bancarias |
| **EXCLUDING_XLE** | 5 activos | 85 | 54.12% | +$912.94 | 1.12 | 0.21 | 1.82% | Mejora al excluir pérdidas energéticas |

### Veredicto del Análisis LOSO
- El test LOSO aporta **prueba matemática concluyente de falta de generalización**:
  $$\text{Net PnL}_{(\text{Excluyendo SPY})} = -\$889.38 \quad (\text{Net PF } 0.89)$$
- La supuesta rentabilidad observada en el portafolio total no es una propiedad intrínseca de la regla de reversión a la media en Bollinger Bands y RSI, sino un efecto concentrado exclusivamente en SPY. Cuando se remueve SPY, el sistema se convierte en un generador neto de pérdidas.

---

## 3. CONTROL DE COMPARACIONES MÚLTIPLES Y CURVE-FITTING

En conformidad con las directrices de la Fase 7.2:
- Los parámetros no fueron recalibrados ni optimizados durante la ejecución de las pruebas multiactivo.
- Se mantuvieron congelados los fingerprints canónicos `571529bf959e44ef` y `5d10c8c90e6f73a6`.
- El hecho de haber resistido la tentación de re-optimizar parámetros para que DIA o XLF fueran rentables ha protegido al sistema de caer en una trampa de sobreajuste clásico.

---

## 4. CONCLUSIÓN DE ROBUSTEZ ESTADÍSTICA

La evidencia estadística acumulada (Bootstrap $p=0.413$, fracaso de LOSO ante la exclusión de SPY y alta dispersión en Sharpe ratios) dictamina que **ninguna de las dos estrategias ha superado el umbral de robustez cuantitativa institucional**.
