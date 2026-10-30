# AUDITORÍA ESTADÍSTICA Y BOOTSTRAP (FASE 7.1)
## ANÁLISIS DE INCERTIDUMBRE, REMUESTREO (1,000 ITERACIONES) E INTERVALOS DE CONFIANZA 95%

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.1 — Auditoría Estadística Avanzada  
**Metodología:** Remuestreo Bootstrap con Reemplazo ($B = 1,000$, Semilla Fija = 42)  
**Nivel de Confianza:** 95% Bilateral ($\alpha = 0.05$)  

---

## 1. TABLA COMPARATIVA DE MÉTRICAS ESTADÍSTICAS

| Métrica Cuantitativa | `MOM_TrendPullback` (Filtrada) | `MOM_TrendPullback` (Sin Filtro) | `MR_RsiBollinger` (Filtrada) | `MR_RsiBollinger` (Sin Filtro) | Cartera Combinada |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Muestra de Trades ($N$)** | **11** | 24 | **18** | 52 | 29 |
| **Trades Ganadores / Perdedores** | 5 / 6 | 10 / 14 | 8 / 10 | 20 / 32 | 13 / 16 |
| **Win Rate** | **45.45%** | 41.67% | **44.44%** | 38.46% | 44.83% |
| **Ganancia Media (USD)** | **\$198.27** | \$258.98 | **\$132.58** | \$104.99 | \$157.84 |
| **Pérdida Media (USD)** | **\$94.99** | \$84.21 | **\$102.19** | \$94.73 | \$99.49 |
| **Ratio Ganancia / Pérdida** | **2.09×** | 3.08× | **1.30×** | 1.11× | 1.59× |
| **Expectativa Neta (USD/trade)** | **+\$38.31** | +\$58.79 | **+\$2.15** | -\$17.92 | +\$15.87 |
| **Expectativa Neta en R** | **+0.153 R** | +0.235 R | **+0.009 R** | -0.072 R | +0.063 R |
| **Profit Factor** | **1.74** | **1.84** | **1.04** | **0.77** | **1.29** |
| **Sharpe Ratio Anualizado** | **1.38** | 1.61 | **0.10** | -0.70 | 0.67 |
| **Sortino Ratio Anualizado** | **3.22** | 3.84 | **0.19** | -0.84 | 1.39 |
| **Máximo Drawdown (USD / %)** | \$526.91 (0.53%) | \$583.12 (0.58%) | \$431.25 (0.43%) | \$1,850.40 (1.85%) | \$641.95 (0.64%) |
| **Factor de Recuperación** | **0.80** | 2.42 | **0.09** | -0.50 | 0.72 |
| **Exposición Temporal** | **4.42%** | 9.80% | **4.50%** | 12.80% | 8.92% |
| **Duración Media (días)** | **4.8 días** | 4.9 días | **3.0 días** | 3.0 días | 3.7 días |
| **Racha Máxima de Pérdidas** | **2 trades** | 3 trades | **2 trades** | 6 trades | 3 trades |

> **Metodología de Anualización Documentada:**  
> Se utilizó la fórmula estándar de Sharpe trade-based:
> $$\text{Sharpe} = \frac{\mu_{\text{pnl}}}{\sigma_{\text{pnl}}} \times \sqrt{\frac{252}{\text{Duración Media}}}$$
> Para Sortino, el denominador corresponde a la desviación estándar semicorregida únicamente sobre retornos negativos ($\sigma_{\text{downside}}$).

---

## 2. RESULTADOS DEL REMUESTREO BOOTSTRAP (1,000 ITERACIONES)

Para estimar el intervalo de confianza real de los parámetros frente al error muestral, se corrieron 1,000 repeticiones con reemplazo:

### 2.1 `MOM_TrendPullback_V1` (Filtrada - $N=11$)
- **Expectativa Media Bootstrap:** +\$39.92 USD.
- **Intervalo de Confianza 95% Expectativa:** **[-$62.32, +$151.17] USD**.
- **Probabilidad de Expectativa Positiva $P(\text{Exp} > 0)$:** **77.6%**.
- **Profit Factor Medio Bootstrap:** 3.33 (sesgado al alza por denominadores cercanos a cero).
- **Intervalo de Confianza 95% Profit Factor:** **[0.24, 11.96]**.
- **Probabilidad de $PF > 1.0$:** **77.6%**.
- **Intervalo 95% Win Rate:** [18.18%, 72.73%].

### 2.2 `MR_RsiBollinger_V1` (Filtrada - $N=18$)
- **Expectativa Media Bootstrap:** +\$2.65 USD.
- **Intervalo de Confianza 95% Expectativa:** **[-$63.58, +$73.21] USD**.
- **Probabilidad de Expectativa Positiva $P(\text{Exp} > 0)$:** **53.0%**.
- **Profit Factor Medio Bootstrap:** 1.36.
- **Intervalo de Confianza 95% Profit Factor:** **[0.26, 3.93]**.
- **Probabilidad de $PF > 1.0$:** **53.0%**.
- **Intervalo 95% Win Rate:** [22.22%, 66.67%].

### 2.3 `MR_RsiBollinger_V1` (Sin Filtro - $N=52$)
- **Expectativa Media Bootstrap:** -\$18.08 USD.
- **Intervalo de Confianza 95% Expectativa:** **[-$66.54, +$34.17] USD**.
- **Probabilidad de Expectativa Positiva $P(\text{Exp} > 0)$:** **24.9%** (75.1% probabilidad de pérdida).
- **Profit Factor Medio Bootstrap:** 0.82 [IC 95%: 0.34, 1.60].

---

## 3. INTERPRETACIÓN ESTADÍSTICA RIGUROSA

1. **Vulnerabilidad Muestral en Muestras Pequeñas ($N < 30$):**
   - Aunque `MOM_TrendPullback_V1` tiene un Profit Factor observado de 1.74, el IC 95% de su expectativa [-$62.32, +$151.17] **abarca valores negativos significativos**. Esto significa que existe un $22.4\%$ de probabilidad de que el rendimiento observado sea fruto del ruido aleatorio o la suerte muestral.
   - Conforme a la regla mandatoria: *Muestras de 11 y 18 operaciones no pueden considerarse estadísticamente demostradas*.
2. **Colapso Estadístico de Mean Reversion:**
   - La probabilidad de que `MR_RsiBollinger_V1` tenga una expectativa positiva en la distribución real es de **53.0%**, lo que equivale estadísticamente a **lanzar una moneda al aire**. No existe ventaja cuantitativa distinguible del ruido.
3. **Clasificación Formal:**
   - `MOM_TrendPullback_V1`: **`INCONCLUSIVE`** (Evidencia preliminar promisoria pero estadísticamente no concluyente).
   - `MR_RsiBollinger_V1`: **`INCONCLUSIVE / REJECTED`** (Borde económico marginal no separable del azar).
   - `MR_RsiBollinger_V1` (Sin Filtro): **`NEGATIVE_EVIDENCE`** (Falsación confirmada de borde).
