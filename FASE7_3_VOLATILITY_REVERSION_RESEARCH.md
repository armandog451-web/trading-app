# ORACLEBOT V2 — FASE 7.3: INVESTIGACIÓN DE REVERSIÓN CONDICIONADA A VOLATILIDAD
## RESULTADOS CUANTITATIVOS DE LA FAMILIA B: `MR_VolCond_ZScore_V1` Y `MR_VolCond_BBCompression_V2`

**Familia de Investigación:** Familia B — Volatility-Conditioned Mean Reversion  
**Estrategias Evaluadas:** `MR_VolCond_ZScore_V1` (Fingerprint `adf4788b0f20132a`), `MR_VolCond_BBCompression_V2` (Fingerprint `68d2ea20522ef5e0`)  
**Universo:** `SPY`, `QQQ`, `IWM`, `DIA`, `XLF`, `XLE` (1,199 barras cerradas por activo)  
**Periodo:** 2022-01-20 a 2026-10-29 (4.78 años)

---

## 1. COMPARATIVA CON LA FALLIDA FORMULACIÓN MR V1 DE FASE 7.2

En la Fase 7.2, la estrategia `MR_RsiBollinger_V1` fue rechazada categóricamente porque su rentabilidad residía única y exclusivamente en SPY. Al excluir SPY, el portafolio perdía -$889.38 y el 66.7% de los activos eran deficitarios.

El cambio de paradigma en la **Familia B (Fase 7.3)** radicó en **eliminar el filtro estático de régimen RANGING** y reemplazarlo por la **dinámica intrínseca de volatilidad**:
1. Entrar solo cuando hay una anomalía estocástica real ($Z \le -2.0$ desviaciones respecto a la media de 20 días).
2. Exigir expansión del Rango Verdadero Medio ($\text{ATR}_{14} / \text{SMA}(\text{ATR}_{14}, 50) \ge 1.10$), asegurando que la caída representa una capitulación de liquidez y no una digestión pasiva.
3. Confirmar sobreventa extrema intradiaria con $\text{RSI}(4) \le 20.0$.

---

## 2. MATRIZ CUANTITATIVA DE RENDIMIENTO (ESCENARIO 1X BASE)

| Métrica | `MR_VolCond_ZScore_V1` | `MR_VolCond_BBCompression_V2` | Comparativa vs MR V1 (Fase 7.2) |
| :--- | :---: | :---: | :---: |
| **Operaciones Totales** | 53 | 55 | Muestra equilibrada |
| **Tasa de Acierto (Win Rate)** | **62.26%** | 52.73% | Superior al 53.9% previo |
| **True Gross PnL** | **+$7,123.14** | +$2,539.06 | Triplica las ganancias brutas |
| **Costes Totales (Slippage + Comm)** | $566.90 | $699.18 | Reducción de rotación innecesaria |
| **True Net PnL** | **+$6,556.24** | **+$1,839.88** | **+1,057% superior a Fase 7.2** (+$566.33) |
| **Net Profit Factor** | **2.94** | **1.47** | Excelente asimetría riesgo/beneficio |
| **Ratio de Sharpe (Anualizado)** | **1.43** | 0.59 | Desempeño institucional de alta calidad |
| **Max Drawdown %** | **0.63%** | 0.78% | Mínimo impacto en la equidad |
| **Cost Drag %** | **7.96%** | 27.54% | **Arrastre por fricciones mínimo** (vs 69.7% previo) |

---

## 3. RENDIMIENTO DESGLOSADO POR ACTIVO (`MR_VolCond_ZScore_V1`)

A diferencia del fracaso multiactivo de Fase 7.2, `MR_VolCond_ZScore_V1` demostró rentabilidad en **5 de los 6 activos** del universo evaluado:

| Símbolo | Activo | Operaciones | Win Rate | True Net PnL | Net PF | Drawdown Máx % |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **SPY** | S&P 500 | 10 | 70.0% | +$1,253.94 | 2.39 | 0.18% |
| **QQQ** | Nasdaq 100 | 6 | 100.0% | +$2,098.79 | 999.0 | 0.00% |
| **DIA** | Dow Jones | 9 | 44.4% | +$471.61 | 2.13 | 0.22% |
| **XLF** | Finanzas | 14 | 50.0% | +$747.92 | 1.69 | 0.28% |
| **XLE** | Energía | 7 | 85.7% | +$1,999.30 | 387.71 | 0.08% |
| **IWM** | Russell 2000 | 7 | 42.9% | -$15.32 | 0.98 | 0.35% |
| **PORTAFOLIO** | **Universo Completo** | **53** | **62.26%** | **+$6,556.24** | **2.94** | **0.63%** |

---

## 4. VALIDACIÓN WALK-FORWARD: PERSISTENCIA FUERA DE MUESTRA (OOS)

- **In-Sample (Train 2022-2024):** 24 operaciones, Net PnL +$1,751.89, Net PF 2.02, Win Rate 54.2%.
- **Out-of-Sample (Test 2024-2026):** 29 operaciones, Net PnL **+$4,804.35**, Net PF **3.88**, Win Rate **69.0%**, Sharpe **1.80**.
- La aceleración en el periodo Out-of-Sample confirma que la captura de caídas con volatilidad expandida se benefició de los episodios de estrés de mercado en 2024-2026, sin degradación por curve-fitting.

---

## 5. RESISTENCIA A ESTRÉS DE COSTES Y REMUESTREO BOOTSTRAP

### Estrés de Costes
- **Escenario 1x Base:** Net PnL +$6,556.24 | Net PF 2.94 | Drag 7.96%
- **Escenario 2x Moderado:** Net PnL **+$5,989.21** | Net PF **2.67** | Drag 15.92%
- **Escenario 3x Severo:** Net PnL **+$5,326.81** | Net PF **2.45** | Drag 24.20%
- Incluso en el peor escenario operativo (3x costes), la estrategia conserva más del 81% de su rentabilidad neta.

### Remuestreo Bootstrap (1,000 Iteraciones)
- Probabilidad de pérdida neta: **$p(\text{loss}) = 0.001$ (0.10%)**.
- Intervalo de Confianza 95% Net PnL: **[+$2,469.34, +$11,084.02 USD]**.
- Intervalo de Confianza 95% Net PF: **[1.56, 6.44]**.
- La ventaja económica es **estadísticamente significativa con $p < 0.01$**.

---

## 6. VALIDACIÓN CRUZADA LOSO

| Subconjunto Evaluado | Operaciones Restantes | True Net PnL | Net PF | Estatus |
| :--- | :---: | :---: | :---: | :--- |
| **Portafolio Base** | 53 | **+$6,556.24** | 2.94 | Baseline |
| **EXCLUDING_SPY** | 43 | +$5,302.30 | 3.14 | **ROBUSTO (Supera el test crítico)** |
| **EXCLUDING_QQQ** | 47 | +$4,457.45 | 2.32 | **ROBUSTO** |
| **EXCLUDING_IWM** | 46 | +$6,571.56 | 3.73 | **ROBUSTO** |
| **EXCLUDING_DIA** | 44 | +$6,084.63 | 3.05 | **ROBUSTO** |
| **EXCLUDING_XLF** | 39 | +$5,808.32 | 3.53 | **ROBUSTO** |
| **EXCLUDING_XLE** | 46 | +$4,556.94 | 2.35 | **ROBUSTO** |

---

## 7. CONCLUSIÓN DE LA FAMILIA B

`MR_VolCond_ZScore_V1` alcanza la puntuación máxima de ranking (**RankScore 1.000**) y aprueba con excelencia todos los criterios de la compuerta económica. Se clasifica formalmente como **`RESEARCH_PROMISING`**.
