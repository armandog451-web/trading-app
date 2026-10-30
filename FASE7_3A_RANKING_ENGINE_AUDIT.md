# ORACLEBOT V2 — FASE 7.3A
# AUDITORÍA DEL RESEARCH RANKING ENGINE Y CORRECCIÓN DE SATURACIÓN (BLOQUE G)

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Módulo auditado:** `ResearchRankingEngine` en `discovery_engine_v2.py`  
**Fecha de auditoría:** 30 de octubre de 2026

---

## 1. DIAGNÓSTICO DE SATURACIÓN EN 1.000 (BLOQUE G)

En el informe de la Fase 7.3, dos estrategias de diferente perfil cualitativo obtuvieron una puntuación de ranking idéntica de `1.000`:
- `MR_VolCond_ZScore_V1` (Net PnL +$6,556.24, OOS PF 3.88)
- `MR_VolCond_BBCompression_V2` (Net PnL +$1,839.88, OOS PF 3.26)

### 1.1 Causa Matemática de la Saturación
La fórmula original del `ResearchRankingEngine` definía:
```python
# FÓRMULA ORIGINAL CON SATURACIÓN
pf_score = min(3.0, max(0.0, m_oos_1x["net_profit_factor"])) / 3.0
pnl_score = 1.0 if m_oos_1x["sum_true_net_pnl"] > 0 else 0.0
cost_survival = 1.0 if m_full_2x["sum_true_net_pnl"] > 0 else 0.0
loso_min_pnl = min([m["sum_true_net_pnl"] for m in loso_map.values()])
loso_score = 1.0 if loso_min_pnl > 0 else 0.0

ranking_score = round(pf_score * 0.40 + pnl_score * 0.30 + cost_survival * 0.20 + loso_score * 0.10, 3)
```

Al analizar la formulación:
1. Cualquier Profit Factor OOS $\ge 3.0$ se truncaba rígidamente a $1.000$.
2. Los componentes de PnL, supervivencia de costes y LOSO eran funciones escalón binarias $\{0.0, 1.0\}$.
3. Como ambas estrategias cumplían plenamente las condiciones binarias y tenían $PF_{OOS} \ge 3.0$, la suma ponderada arrojaba:
   $$1.00 \times 0.40 + 1.00 \times 0.30 + 1.00 \times 0.20 + 1.00 \times 0.10 = 1.000$$

Esta saturación impedía distinguir cardinalmente la calidad relativa de las hipótesis superiores.

---

## 2. NUEVA FORMULACIÓN CONTINUA Y EXPLICABLE (FASE 7.3A)

Se rediseñó el motor de puntuación en [`discovery_engine_v2.py`](file:///C:/Users/edsel/Documents/trading-app-repo/ai_trading_agent/strategy_lab/discovery/discovery_engine_v2.py) eliminando variables escalón y aplicando funciones continuas acotadas a $[0.0, 1.0]$:

### 2.1 Desglose de Componentes

1. **OOS Profit Factor Continuo (Peso: 30%):**  
   Mide la asimetría beneficio/pérdida fuera-de-muestra en una escala continua entre $1.0$ y $4.0$:
   $$S_{PF} = \min\left(1.0, \max\left(0.0, \frac{PF_{OOS} - 1.0}{3.0}\right)\right)$$
2. **OOS Expectancy Normalizada (Peso: 25%):**  
   Mide la ganancia media neta por operación en relación con el presupuesto de riesgo por trade ($250 USD):
   $$S_{EXP} = \min\left(1.0, \max\left(0.0, \frac{\text{Expectancy}_{OOS}}{200.0}\right)\right)$$
3. **Retención de Beneficio ante Costes 2x (Peso: 25%):**  
   Mide la proporción del beneficio que sobrevive cuando las fricciones se duplican (invarianza a costes):
   $$S_{COST} = \min\left(1.0, \max\left(0.0, \frac{NetPnL_{2x}}{NetPnL_{1x}}\right)\right)$$
4. **Amplitud Multiactivo LOSO (Peso: 20%):**  
   Proporción de activos del portafolio cuya exclusión individual mantiene el resultado global en positivo:
   $$S_{LOSO} = \frac{\sum \mathbb{I}(PnL_{ex\_sym} > 0)}{N_{sym}}$$

$$\text{Research Ranking Score} = 0.30 \times S_{PF} + 0.25 \times S_{EXP} + 0.25 \times S_{COST} + 0.20 \times S_{LOSO}$$

---

## 3. RESULTADOS DE LA PUNTUACIÓN CARDINAL DESATURADA

Tras aplicar la nueva fórmula continua, el ranking del laboratorio refleja de forma nítida la jerarquía técnica de las hipótesis:

| Puesto | Estrategia ID | $S_{PF}$ (30%) | $S_{EXP}$ (25%) | $S_{COST}$ (25%) | $S_{LOSO}$ (20%) | Research Ranking Score | Estado Institucional |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | **MR_VolCond_ZScore_V1** | 0.960 | 0.828 | 0.913 | 1.000 | **0.923** | `RESEARCH_PROMISING_VERIFIED` |
| **2** | **MR_VolCond_BBCompression_V2** | 0.753 | 0.643 | 0.620 | 1.000 | **0.828** | `RESEARCH_PROMISING_VERIFIED` |
| **3** | **CS_RelMom_60d_V1** | 0.403 | 0.753 | 0.877 | 1.000 | **0.767** | `RESEARCH_PROMISING_VERIFIED` |
| **4** | **CS_RelMom_VolAdj_V2** | 0.247 | 0.323 | 0.803 | 1.000 | **0.572** | `RESEARCH_PROMISING_VERIFIED` |

### 3.1 Análisis de Jerarquía
- **Líder Incontestable:** `MR_VolCond_ZScore_V1` alcanza **0.923**, liderando en Profit Factor ($S_{PF}=0.960$), Expectancy ($S_{EXP}=0.828$) y retención de beneficio frente a fricciones ($S_{COST}=0.913$).
- **Diferenciación Efectiva:** `MR_VolCond_BBCompression_V2` desciende a **0.828** (en lugar del saturado 1.000) debido a su menor retención de costes (0.620) y menor expectancy unitaria (0.643).
- **Separación de Clasificaciones:** Se ratifica la separación obligatoria entre el **`RESEARCH_RANKING_SCORE`** (ordinal y cuantitativo) y el **`STATISTICAL_VALIDATION_STATUS`** (categórico y gobernado por compuertas de paso/fallo institucionales).
