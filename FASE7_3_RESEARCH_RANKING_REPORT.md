# ORACLEBOT V2 — FASE 7.3: INFORME DE RANKING DE INVESTIGACIÓN CUANTITATIVA
## JERARQUIZACIÓN EXPLICABLE DE HIPÓTESIS, MATRIZ MULTIDIMENSIONAL Y PRIORIZACIÓN

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.3 — Discovery Engine v2  
**Fecha:** 30 de octubre de 2026  
**Autoridad Evaluadora:** Research Ranking Engine  
**Modo:** `RESEARCH / ANALYSIS_ONLY`

---

## 1. METODOLOGÍA DEL RESEARCH RANKING ENGINE

El ranking de investigación de OracleBot v2 evalúa de manera multidimensional y explicable el potencial de cada hipótesis candidata. No utiliza cajas negras ni optimización estocástica; pondera cuatro dimensiones de robustez:

$$\text{RankScore} = 0.40 \cdot S_{\text{PF\_OOS}} + 0.30 \cdot S_{\text{PnL\_OOS}} + 0.20 \cdot S_{\text{CostStress}} + 0.10 \cdot S_{\text{LOSO}}$$

Donde:
- $S_{\text{PF\_OOS}}$: Profit Factor Out-of-Sample normalizado ($\min(1.0, \text{PF}_{\text{OOS}} / 3.0)$).
- $S_{\text{PnL\_OOS}}$: Indicador binario de rentabilidad neta fuera de muestra ($1.0$ si $\text{Net PnL}_{\text{OOS}} > 0$).
- $S_{\text{CostStress}}$: Supervivencia a fricciones ($1.0$ si $\text{Net PnL}_{2\text{x}} > 0$; $0.5$ si solo $\text{Net PnL}_{1\text{x}} > 0$).
- $S_{\text{LOSO}}$: Consistencia multiactivo ($1.0$ si el peor subconjunto LOSO es positivo).

---

## 2. TABLA OFICIAL DE RANKING CUANTITATIVO (FASE 7.3)

| Posición | Estrategia ID | Hipótesis ID | Familia | RankScore | OOS Net PnL | OOS Net PF | 3x Net PnL | $p(\text{loss})$ | Estado Institucional |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **#1** | **`MR_VolCond_ZScore_V1`** | `H-MR-VOL-1` | Volatility Reversion | **1.000** | **+$4,804.35** | **3.88** | **+$5,326.81** | **0.1%** | **`RESEARCH_PROMISING`** |
| **#2** | **`MR_VolCond_BBCompression_V2`** | `H-MR-VOL-2` | Volatility Reversion | **1.000** | +$3,598.67 | **5.19** | +$538.29 | 11.1% | **`RESEARCH_PROMISING`** |
| **#3** | **`CS_RelMom_60d_V1`** | `H-MOM-REL-1` | Relative Momentum | **0.957** | +$3,311.24 | 2.68 | +$2,153.69 | 10.5% | **`RESEARCH_PROMISING`** |
| **#4** | **`CS_RelMom_VolAdj_V2`** | `H-MOM-REL-2` | Relative Momentum | **0.832** | +$4,174.94 | 1.74 | +$3,328.84 | **2.8%** | **`RESEARCH_PROMISING`** |

---

## 3. ANÁLISIS COMPARATIVO DE LOS DOS CANDIDATOS LÍDERES

### Candidato #1: `MR_VolCond_ZScore_V1` (Reversión a la Media con Z-Score y Expansión de ATR)
- **Fortalezas Críticas:**
  - Máxima resiliencia a costes del laboratorio: cost drag de solo **7.96%** en 1x y **24.2%** en 3x.
  - Drawdown máximo excepcionalmente bajo: **0.63%**.
  - Generalización multiactivo probada: rentable en 5 de los 6 activos evaluados (`SPY`, `QQQ`, `DIA`, `XLF`, `XLE`) y empate técnico en `IWM` (-$15 USD).
  - Prácticamente cero probabilidad de pérdida en bootstrap ($p = 0.001$).
- **Prioridad de Investigación:** Candidata predilecta para estudios de microestructura y diseño de órdenes limitadas.

### Candidato #4 (Líder en Frecuencia y Diversificación): `CS_RelMom_VolAdj_V2`
- **Fortalezas Críticas:**
  - Mayor base muestral del laboratorio (**134 operaciones**, 28 trades/año).
  - Mayor ganancia neta acumulada en periodo completo: **+$5,600.77 USD** (1x) y **+$3,328.84 USD** (3x).
  - Resuelve el cuello de botella de la inactividad operativa sin sacrificar solidez estadística ($p(\text{loss}) = 2.8\%$).
- **Prioridad de Investigación:** Candidata ideal para análisis de costos de rebalanceo y asignación multi-activo continua.

---

## 4. PROPÓSITO DEL RANKING Y DIRECTRICES DE GOBERNANZA

1. El ranking tiene como único objetivo **ordenar las prioridades teóricas y experimentales** dentro del Strategy Laboratory.
2. **Ningún puntaje autoriza la activación de trading automatizado o asignación de capital virtual en Moomoo PAPER.**
3. Todas las estrategias permanecen en la rama de investigación (`RESEARCH`), garantizando la estabilidad operativa del entorno.
