# CONTROL ANTISOBREAJUSTE Y GOBERNANZA DE DATOS (FASE 7.1)
## PREVENCIÓN DE SESGOS, SEPARACIÓN DE PARTICIONES Y REGISTRO DE EXPERIMENTOS

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.1 — Auditoría de Integridad Metodológica  
**Estado:** **PROTOCOLIZADO Y CERTIFICADO**  

---

## 1. CLASIFICACIÓN INSTITUCIONAL DE DATASETS

Para erradicar el riesgo de optimización espuria (data snooping) y sesgo de selección múltiple, los datos de mercado se catalogan bajo tres niveles estrictos de exposición previa:

```
┌─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┐
│          CATEGORÍA 1            │          CATEGORÍA 2            │          CATEGORÍA 3            │
│          EXPLORATORIO           │           VALIDACIÓN            │           PROSPECTIVO           │
│      PREVIOUSLY EXAMINED        │      REPEATEDLY EXAMINED        │          FROZEN / UNSEEN        │
├─────────────────────────────────┼─────────────────────────────────┼─────────────────────────────────┤
│    2018-01-01 a 2024-12-31      │    2025-01-01 a 2026-10-05      │     2026-10-21 en adelante      │
│                                 │                                 │                                 │
│ • Datos examinados en Fases 1-6 │ • Evaluado en auditoría Fase 10 │ • Observación en tiempo real    │
│ • Permitido para formulación y  │ • PROHIBIDO tratar como holdout │ • Congelado criptográficamente  │
│   calibración inicial           │   ciego genuino en Fase 7       │ • Prohibido re-entrenar         │
└─────────────────────────────────┴─────────────────────────────────┴─────────────────────────────────┘
```

> **Dictamen sobre Evidencia Prospectiva:**  
> Dado que la restauración canónica ocurrió el 2026-10-21 y solo han transcurrido 7 sesiones bursátiles completadas, se emite formalmente la clasificación:
> $$\mathbf{INSUFFICIENT\_PROSPECTIVE\_EVIDENCE}$$
> Ninguna estrategia de la Fase 7 cuenta con muestra prospectiva suficiente para graduación.

---

## 2. FINGERPRINTS CRIPTOGRÁFICOS DE VARIANTES DE FASE 7

Cada variante de investigación cuenta con una firma determinista SHA-256 basada en su configuración inmutable:

| Estrategia | Parámetros Clave Congelados | Fingerprint (SHA-256 Truncado) | Estado de Ciclo de Vida |
| :--- | :--- | :---: | :---: |
| **`MOM_TrendPullback_V1`** | `ema_fast: 20, sma_slow: 50, min_rsi: 40, max_rsi: 60, min_rvol: 1.2, max_holding: 5` | `d1b72e50cf16e914` | `RESEARCH` |
| **`MR_RsiBollinger_V1`** | `rsi_period: 4, rsi_oversold: 25, bb_period: 20, bb_std: 2.0, max_holding: 3` | `a8c9e54807494a2b` | `RESEARCH` |
| **`D21_RangeCompress_5d`** | *Estrategia Canónica PAPER (Inalterada)* | `f885ec2db2422308` | `PAPER` |

---

## 3. CONTROL DE SELECCIÓN MÚLTIPLE Y SESGO DE CONFIRMACIÓN

1. **Penalización de Múltiples Comparaciones:** Al evaluar dos familias de estrategias con dos variantes de régimen (4 pruebas simultáneas), el umbral de significancia estadística $\alpha = 0.05$ se ajusta mediante la corrección de Bonferroni a $\alpha' = 0.0125$.
2. **Preservación de Resultados Negativos:** El colapso de la Reversión a la Media sin filtro ($PF = 0.77$) y el fallo de Mean Reversion bajo estrés 2× ($PF = 0.84$) quedan formalmente registrados como evidencia negativa para impedir que futuros ciclos intenten re-optimizar esta misma arquitectura.
3. **Prohibición de "Curve-Fitting":** Queda estrictamente prohibido alterar los umbrales de RSI (25), Bandas de Bollinger (2.0) o ADX (25) tras observar los resultados de esta auditoría sobre la misma muestra.
