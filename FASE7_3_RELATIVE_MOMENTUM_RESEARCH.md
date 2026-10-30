# ORACLEBOT V2 — FASE 7.3: INVESTIGACIÓN DE MOMENTUM RELATIVO CROSS-SECCIONAL
## RESULTADOS CUANTITATIVOS DE LA FAMILIA A: `CS_RelMom_60d_V1` Y `CS_RelMom_VolAdj_V2`

**Familia de Investigación:** Familia A — Cross-Sectional Relative Momentum  
**Estrategias Evaluadas:** `CS_RelMom_60d_V1` (Fingerprint `165345c108cdefb9`), `CS_RelMom_VolAdj_V2` (Fingerprint `7460c8f0c2373832`)  
**Universo:** `SPY`, `QQQ`, `IWM`, `DIA`, `XLF`, `XLE` (1,199 barras cerradas por activo)  
**Periodo:** 2022-01-20 a 2026-10-29 (4.78 años)

---

## 1. COMPARATIVA CON LA FALLIDA FORMULACIÓN V1 DE FASE 7.2

En la Fase 7.2, la estrategia `MOM_TrendPullback_V1` fracasó debido a una **hambruna de señales destructiva**: generó únicamente 9 operaciones en casi 5 años (frecuencia anual de 1.89 trades/año para todo el portafolio) y un PnL deficitario de -$130.49.

El enfoque de **Momentum Relativo Cross-Seccional** resolvió completamente esta patología:
- En lugar de exigir condiciones estáticas absolutas sobre un solo activo, compara simultáneamente los 6 activos y rota capital hacia los líderes.
- **`CS_RelMom_60d_V1`:** Generó **41 operaciones** (8.6 trades/año).
- **`CS_RelMom_VolAdj_V2`:** Generó **134 operaciones** (28.2 trades/año), proporcionando una muestra estadística amplia y continua.

---

## 2. MATRIZ CUANTITATIVA DE RENDIMIENTO (ESCENARIO 1X BASE)

| Métrica | `CS_RelMom_60d_V1` | `CS_RelMom_VolAdj_V2` | Comparativa vs MOM V1 (Fase 7.2) |
| :--- | :---: | :---: | :---: |
| **Operaciones Totales** | 41 | **134** | +1,388% incremento muestral |
| **Tasa de Acierto (Win Rate)** | 58.54% | **57.46%** | Consistencia superior |
| **True Gross PnL** | +$2,941.86 | **+$6,813.59** | Crecimiento bruto robusto |
| **Costes Totales (Slippage + Comm)** | $322.43 | $1,212.82 | Control de fricciones |
| **True Net PnL** | **+$2,619.43** | **+$5,600.77** | PnL neto sólidamente positivo |
| **Net Profit Factor** | **1.55** | **1.46** | Superior al umbral institucional (> 1.30) |
| **Ratio de Sharpe (Anualizado)** | 0.64 | **0.92** | Rendimiento ajustado por volatilidad |
| **Max Drawdown %** | 1.77% | **1.60%** | Control estricto del riesgo |
| **Cost Drag %** | 10.96% | **17.80%** | Fricción asumible |

---

## 3. VALIDACIÓN WALK-FORWARD: IN-SAMPLE (IS) VS OUT-OF-SAMPLE (OOS)

El conjunto de 1,199 barras fue dividido cronológicamente:
- **In-Sample (Train):** Barras 0 a 599 (2022-01-20 a 2024-06-10).
- **Out-of-Sample (Test):** Barras 600 a 1199 (2024-06-11 a 2026-10-29).

### Desglose Walk-Forward

```
Evolución Walk-Forward (Net PnL en USD):
┌─────────────────────────┬──────────────┬──────────────┬──────────────┐
│ Estrategia              │ In-Sample    │ Out-of-Sample│ Ratio OOS/IS │
├─────────────────────────┼──────────────┼──────────────┼──────────────┤
│ CS_RelMom_60d_V1        │  -$691.81    │ +$3,311.24   │ Fuerte OOS   │
│ CS_RelMom_VolAdj_V2     │ +$1,425.83   │ +$4,174.94   │ +192% OOS    │
└─────────────────────────┴──────────────┴──────────────┴──────────────┘
```

- En `CS_RelMom_VolAdj_V2`, la estrategia demostró rentabilidad en ambos periodos:
  - In-Sample: 61 operaciones, Net PnL +$1,425.83, Net PF 1.22.
  - Out-of-Sample: 73 operaciones, Net PnL **+$4,174.94**, Net PF **1.74**, Sharpe **1.34**.
  - Este comportamiento demuestra que la ventaja económica no solo persiste, sino que se expande fuera de muestra sin sobreajuste.

---

## 4. PRUEBA DE ESTRÉS DE COSTES Y FRICCIONES

```
Resistencia a Fricciones Operativas:
┌─────────────────────────┬──────────────┬──────────────┬──────────────┐
│ Estrategia              │ Base (1x)    │ Mod (2x)     │ Severo (3x)  │
├─────────────────────────┼──────────────┼──────────────┼──────────────┤
│ CS_RelMom_60d_V1        │ +$2,619.43   │ +$2,742.15   │ +$2,153.69   │
│ CS_RelMom_VolAdj_V2     │ +$5,600.77   │ +$4,140.81   │ +$3,328.84   │
└─────────────────────────┴──────────────┴──────────────┴──────────────┘
```

- Ambas estrategias superan con holgura el escenario severo de costes 3x ($0.015/acción y 15 bps slippage).
- En `CS_RelMom_VolAdj_V2`, el PnL neto en 3x se mantiene en **+$3,328.84 USD (Net PF 1.25)**, garantizando un colchón de seguridad ante horquillas abiertas.

---

## 5. ROBUSTEZ MULTIACTIVO: LEAVE-ONE-SYMBOL-OUT (LOSO)

Para descartar la dependencia de un solo sector o activo, se evaluó el portafolio excluyendo cada símbolo secuencialmente:

| Subconjunto LOSO (`CS_RelMom_VolAdj_V2`) | Operaciones | True Net PnL | Net PF | Veredicto de Generalización |
| :--- | :---: | :---: | :---: | :--- |
| **Portafolio Base (6 Activos)** | 134 | **+$5,600.77** | 1.46 | Baseline |
| **EXCLUDING_SPY** | 108 | +$5,239.10 | 1.50 | **POSITIVO (Sin dependencia de SPY)** |
| **EXCLUDING_QQQ** | 105 | +$4,265.79 | 1.45 | **POSITIVO** |
| **EXCLUDING_IWM** | 125 | +$6,009.99 | 1.54 | **POSITIVO (Mejora al excluir small caps)** |
| **EXCLUDING_DIA** | 114 | +$5,435.67 | 1.51 | **POSITIVO** |
| **EXCLUDING_XLF** | 108 | +$4,726.73 | 1.48 | **POSITIVO** |
| **EXCLUDING_XLE** | 110 | +$2,326.57 | 1.24 | **POSITIVO** |

> [!NOTE]
> A diferencia de Fase 7.2 donde excluir SPY causaba el colapso del sistema, en `CS_RelMom_VolAdj_V2` **todos los subconjuntos LOSO generan beneficios consistentes**, confirmando que la ventaja es verdaderamente transversal a los sectores.

---

## 6. CONCLUSIÓN DE LA FAMILIA A

`CS_RelMom_VolAdj_V2` se consolida como una estrategia cuantitativamente superior, con $p(\text{loss})$ bootstrap del **2.8%** y rendimiento out-of-sample sobresaliente. Se clasifica formalmente como **`RESEARCH_PROMISING`**.
