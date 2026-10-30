# ORACLEBOT V2 — FASE 7.3: VALIDACIÓN DE VENTAJA ECONÓMICA (ECONOMIC EDGE GATE)
## COMPUERTA ELIMINATORIA TEMPRANA, RESISTENCIA A FRICCIONES Y CONTROLES ESTADÍSTICOS

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.3 — Discovery Engine v2  
**Fecha:** 30 de octubre de 2026  
**Objetivo:** Aplicar criterios de exclusión temprana para filtrar rigurosamente las hipótesis que no posean una ventaja matemática transferible y resiliente a fricciones de mercado.

---

## 1. CRITERIOS VINCULANTES DE LA COMPUERTA ECONÓMICA (*ECONOMIC EDGE GATE*)

Para superar la compuerta y calificar como `RESEARCH_PROMISING`, una estrategia debe satisfacer simultáneamente 5 condiciones objetivas:

1. **Umbral Muestral Mínimo:** $\ge 15$ operaciones en el periodo evaluado.
2. **Expectativa Neta Positiva (1x Base):** $\text{True Net PnL} > 0$ en el portafolio consolidado.
3. **Persistencia Fuera de Muestra:** $\text{True Net PnL}_{\text{OOS}} > 0$ en el periodo *Out-of-Sample* (2024-2026).
4. **Supervivencia a Costes Moderados:** $\text{True Net PnL}_{2\text{x}} > 0$ bajo comisiones de $0.010/acción y 10 bps slippage.
5. **Significancia Estadística:** Probabilidad de pérdida neta en bootstrap $p(\text{loss}) \le 25\%$.

---

## 2. EVALUACIÓN DETALLADA DE LAS 4 HIPÓTESIS CANDIDATAS

| Criterio de Compuerta | `CS_RelMom_60d_V1` | `CS_RelMom_VolAdj_V2` | `MR_VolCond_ZScore_V1` | `MR_VolCond_BBCompression_V2` |
| :--- | :---: | :---: | :---: | :---: |
| **1. Muestra ($\ge 15$ trades)** | 41 (**APROBADO**) | 134 (**APROBADO**) | 53 (**APROBADO**) | 55 (**APROBADO**) |
| **2. Net PnL 1x ($> 0$)** | +$2,619.43 (**APROBADO**) | +$5,600.77 (**APROBADO**) | +$6,556.24 (**APROBADO**) | +$1,839.88 (**APROBADO**) |
| **3. Net PnL OOS ($> 0$)** | +$3,311.24 (**APROBADO**) | +$4,174.94 (**APROBADO**) | +$4,804.35 (**APROBADO**) | +$3,598.67 (**APROBADO**) |
| **4. Net PnL 2x ($> 0$)** | +$2,742.15 (**APROBADO**) | +$4,140.81 (**APROBADO**) | +$5,989.21 (**APROBADO**) | +$1,140.45 (**APROBADO**) |
| **5. Bootstrap $p(\text{loss}) \le 25\%$** | 10.50% (**APROBADO**) | 2.80% (**APROBADO**) | 0.10% (**APROBADO**) | 11.10% (**APROBADO**) |
| **ESTATUS COMPUERTA** | **SUPERADA** | **SUPERADA** | **SUPERADA** | **SUPERADA** |

---

## 3. PRUEBA DE ESTRÉS DE COSTES COMPARATIVA

```
Degradación de Net PnL ante Estrés de Fricciones (USD):
┌──────────────────────────────┬──────────────┬──────────────┬──────────────┐
│ Estrategia                   │ 1x Base      │ 2x Moderado  │ 3x Severo    │
├──────────────────────────────┼──────────────┼──────────────┼──────────────┤
│ CS_RelMom_60d_V1             │ +$2,619.43   │ +$2,742.15   │ +$2,153.69   │
│ CS_RelMom_VolAdj_V2          │ +$5,600.77   │ +$4,140.81   │ +$3,328.84   │
│ MR_VolCond_ZScore_V1         │ +$6,556.24   │ +$5,989.21   │ +$5,326.81   │
│ MR_VolCond_BBCompression_V2  │ +$1,839.88   │ +$1,140.45   │   +$538.29   │
└──────────────────────────────┴──────────────┴──────────────┴──────────────┘
```

### Hallazgos de Resiliencia Económica
- **`MR_VolCond_ZScore_V1`** demostró la mayor robustez económica del laboratorio: en el escenario severo de costes 3x ($0.015/acción y 15 bps slippage), conserva un PnL neto de **+$5,326.81 USD** con un Profit Factor de **2.45**. Su coste relativo absorbe únicamente el 24.2% de las ganancias brutas.
- **`CS_RelMom_VolAdj_V2`** retiene **+$3,328.84 USD** en 3x, confirmando que la diversificación quincenal en dos activos líderes absorbe holgadamente los costes de rotación.
- A diferencia de Fase 7.2 donde ninguna estrategia sobrevivió a costes 2x, **las 4 nuevas formulaciones de Fase 7.3 sobreviven incluso al estrés de costes 3x**.

---

## 4. ADVERTENCIA DE GOBERNANZA VINCULANTE

> [!WARNING]
> Superar la compuerta económica (*Economic Edge Gate*) en modo de investigación otorga el estatus de **`RESEARCH_PROMISING`**, lo cual califica a la estrategia exclusivamente para un seguimiento experimental continuo en laboratorio.
> 
> **En ningún caso autoriza la conexión con Moomoo OpenD, la ejecución en Paper Trading ni la migración a producción.** D21 permanece como el único sistema operativo activo.
