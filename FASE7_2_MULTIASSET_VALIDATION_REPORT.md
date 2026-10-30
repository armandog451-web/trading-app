# ORACLEBOT V2 — FASE 7.2: INFORME EJECUTIVO DE VALIDACIÓN MULTIACTIVO
## GENERALIZACIÓN ESTADÍSTICA, ROBUSTEZ CUANTITATIVA Y CONTROL ANTISOBREAJUSTE

**Proyecto:** OracleBot v2 / Dual Strategy / Strategy Laboratory  
**Workspace canónico:** `trading-app-repo`  
**Fecha de auditoría:** 30 de octubre de 2026  
**Entorno:** Python 3.11 / Windows / FastAPI (Puerto 8090)  
**Modo operativo Fase 7.2:** `RESEARCH / ANALYSIS_ONLY` (Air-Gapped de brokers)  
**Supervisor 24/7:** OracleBot (PID 2436)  
**Broker PAPER activo:** Moomoo (`TrdEnv.SIMULATE`) — Exclusivo D21 ($1,000,000 USD)

---

## 1. RESUMEN EJECUTIVO Y DICTAMEN GENERAL

La Fase 7.2 sometió a auditoría cuantitativa rigurosa las dos familias de estrategias experimentales del Strategy Laboratory:
1. **`MR_RsiBollinger_V1`** (Mean Reversion orientada a régimen lateral `RANGING`).
2. **`MOM_TrendPullback_V1`** (Momentum orientado a tendencia alcista `TRENDING_BULL`).

La prueba se ejecutó sobre un universo de **6 activos reales** representativos del mercado estadounidense:
- `SPY` (S&P 500 — Baseline exploratorio)
- `QQQ` (Nasdaq 100 — Sector Tecnológico / Alta beta)
- `IWM` (Russell 2000 — Small Caps / Alta volatilidad)
- `DIA` (Dow Jones 30 — Industrial / Gran capitalización)
- `XLF` (Financial Select Sector — Financiero / Ciclo de tasas)
- `XLE` (Energy Select Sector — Energía / Materias primas)

Cada activo fue evaluado con **1,200 barras diarias reales auténticas** (20 de enero de 2022 al 30 de octubre de 2026, 4.8 años), verificadas contra el calendario bursátil oficial NYSE/NASDAQ (cero datos sintéticos, cero operaciones en fines de semana o feriados).

### Dictamen de Gobernanza Cuantitativa

| Estrategia | Fingerprint SHA-256 | Operaciones Evaluadas | Net PnL (1x Base) | Net Profit Factor | Veredicto Formal Fase 7.2 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`MR_RsiBollinger_V1`** | `571529bf959e44ef` | 102 | +$566.33 | 1.06 | **`RESEARCH_REJECTED`** |
| **`MOM_TrendPullback_V1`** | `5d10c8c90e6f73a6` | 9 | -$130.49 | 0.84 | **`RESEARCH_REJECTED`** |

---

## 2. RESPUESTAS CONCRETAS A LAS 5 PREGUNTAS CLAVE DE LA MISIÓN

### Pregunta 1: ¿Mean Reversion posee una ventaja económica que se generaliza fuera de SPY?
> **RESPUESTA: NO.**
> - En `SPY`, la estrategia obtuvo un resultado aparentemente positivo (+$1,455.71, Net PF 2.21, WR 68.2%).
> - Sin embargo, al extenderse a los demás activos, **fracasó en 4 de los 5 activos restantes**:
>   - `QQQ`: -$49.29 (Net PF 0.97)
>   - `DIA`: -$516.88 (Net PF 0.64)
>   - `XLF`: -$584.84 (Net PF 0.56)
>   - `XLE`: -$346.61 (Net PF 0.83)
> - El análisis *Leave-One-Symbol-Out* (LOSO) demostró que al excluir SPY, el Net PnL de Mean Reversion colapsa a **-$889.38** (Net PF 0.89). La supuesta ventaja no es intrínseca a la estrategia, sino un sobreajuste accidental a las características históricas específicas de SPY en dicho periodo.

### Pregunta 2: ¿Momentum es viable pese a su frecuencia extremadamente baja?
> **RESPUESTA: NO.**
> - Bajo el filtro estricto `TRENDING_BULL` ($\text{ADX} \ge 25 \land \text{ER} \ge 0.35$), la estrategia generó únicamente **9 operaciones en 4.8 años a lo largo de todo el universo multiactivo** (frecuencia anualizada de 1.89 trades/año para todo el portafolio).
> - En `QQQ` generó **0 operaciones** en 1,200 barras.
> - El PnL neto agregado fue **negativo (-$130.49, Net PF 0.84)**.
> - Con un tamaño muestral de $N=9$ y un $p(\text{pérdida})$ bootstrap del **60.3%**, la estrategia carece tanto de viabilidad económica como de significancia estadística.

### Pregunta 3: ¿Los filtros de régimen mejoran la calidad económica de las estrategias?
> **RESPUESTA: NO PROVEEN VENTAJA ECONÓMICA SUFICIENTE.**
> - Para Mean Reversion, el filtro `RANGING` redujo las operaciones de 267 a 102, pero el Net PnL cayó de +$3,107.94 a +$566.33, aumentando el arrastre por costes (cost drag) del 52.0% al 69.7%.
> - Para Momentum, el filtro `TRENDING_BULL` fue tan hiper-restrictivo que eliminó el 95.2% de las señales, convirtiendo un resultado sin filtro de +$3,673.25 (187 trades) en -$130.49 (9 trades).
> - En ninguna de las dos estrategias el filtro de régimen logró transformar una lógica débil en un sistema con robustez institucional.

### Pregunta 4: ¿Los resultados sobreviven a comisiones, deslizamiento y estrés de costes?
> **RESPUESTA: NO.**
> - **Mean Reversion:** En el escenario base (1x), el PnL neto es de +$566.33 con un cost drag del 69.7%. Al duplicar los costes (2x: $0.010/acción, 10 bps slippage), el PnL neto cae a **-$734.68**. Con costes 3x ($0.015/acción, 15 bps slippage), colapsa a **-$1,984.41** (cost drag 203.4%).
> - **Momentum:** Nace con PnL neto negativo en 1x (-$130.49) y se deteriora monótonamente a -$240.17 en 2x y -$349.89 en 3x.
> - Ninguna de las dos estrategias presenta margen de seguridad económica ante fricciones operativas reales.

### Pregunta 5: ¿Existe evidencia suficiente para justificar una futura campaña prospectiva?
> **RESPUESTA: NO.**
> - Ambas estrategias quedan **formalmente desestimadas** para cualquier avance a entornos de Paper Trading o validación prospectiva con Moomoo.
> - No se autoriza la activación de ninguna estrategia adicional. D21 se mantiene como la única estrategia en evaluación operativa PAPER.

---

## 3. RESUMEN DE LA MATRIZ MULTIACTIVO (ESCENARIO BASE 1X)

### Mean Reversion (`MR_RsiBollinger_V1` — Con Filtro `RANGING`)
- **Capital por trade:** $100,000 nocional (riesgo máximo $250 / 0.25%).
- **Fricciones:** $0.005/acción comisión, 5.0 bps slippage.

| Símbolo | Activo | Operaciones | Win Rate | True Gross PnL | Deslizamiento | Comisiones | True Net PnL | Net PF | Sharpe | Max DD % |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SPY** | S&P 500 | 22 | 68.18% | +$1,729.89 | $162.78 | $111.40 | **+$1,455.71** | 2.21 | 0.78 | 0.36% |
| **QQQ** | Nasdaq 100 | 17 | 58.82% | +$162.47 | $117.56 | $94.20 | **-$49.29** | 0.97 | -0.03 | 1.17% |
| **IWM** | Russell 2000 | 15 | 53.33% | +$804.19 | $104.95 | $91.00 | **+$608.24** | 1.33 | 0.23 | 0.53% |
| **DIA** | Dow Jones 30 | 15 | 40.00% | -$327.47 | $98.41 | $91.00 | **-$516.88** | 0.64 | -0.36 | 0.53% |
| **XLF** | Finanzas | 16 | 43.75% | -$368.62 | $110.42 | $105.80 | **-$584.84** | 0.56 | -0.33 | 0.83% |
| **XLE** | Energía | 17 | 52.94% | -$133.08 | $112.53 | $101.00 | **-$346.61** | 0.83 | -0.13 | 1.19% |
| **TOTAL** | **Portafolio** | **102** | **53.92%** | **+$1,867.38** | **$706.65** | **$594.40** | **+$566.33** | **1.06** | **0.11** | **2.45%** |

### Momentum (`MOM_TrendPullback_V1` — Con Filtro `TRENDING_BULL`)

| Símbolo | Activo | Operaciones | Win Rate | True Gross PnL | Deslizamiento | Comisiones | True Net PnL | Net PF | Sharpe | Max DD % |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SPY** | S&P 500 | 2 | 100.0% | +$299.91 | $14.91 | $10.40 | +$274.60 | 999.0 | 1.91 | 0.00% |
| **QQQ** | Nasdaq 100 | 0 | 0.0% | $0.00 | $0.00 | $0.00 | $0.00 | 0.00 | 0.00 | 0.00% |
| **IWM** | Russell 2000 | 1 | 0.0% | -$352.03 | $6.29 | $6.30 | -$364.62 | 0.00 | N/A | 0.36% |
| **DIA** | Dow Jones 30 | 3 | 66.67% | +$56.34 | $21.89 | $16.00 | +$18.45 | 1.11 | 0.05 | 0.16% |
| **XLF** | Finanzas | 2 | 50.0% | +$190.00 | $11.40 | $11.40 | +$167.20 | 3.75 | 0.56 | 0.06% |
| **XLE** | Energía | 1 | 0.0% | -$215.00 | $5.56 | $5.56 | -$226.12 | 0.00 | N/A | 0.23% |
| **TOTAL** | **Portafolio** | **9** | **55.56%** | **-$20.78** | **$60.05** | **$49.66** | **-$130.49** | **0.84** | **-0.12** | **0.41%** |

---

## 4. IMPACTO DEL ESTRÉS DE COSTES

```
Evolución de Net PnL según Escenario de Costes:
┌─────────────────────────┬──────────────┬──────────────┬──────────────┐
│ Estrategia              │ Base (1x)    │ Mod (2x)     │ Extremo (3x) │
├─────────────────────────┼──────────────┼──────────────┼──────────────┤
│ MR_RsiBollinger_V1 (F)  │  +$566.33    │  -$734.68    │ -$1,984.41   │
│ MOM_TrendPullback_V1 (F)│  -$130.49    │  -$240.17    │   -$349.89   │
└─────────────────────────┴──────────────┴──────────────┴──────────────┘
```

---

## 5. ESTADO PARALELO DE D21 (GOVERNANCE SHIELD)

Mientras el Strategy Laboratory realizaba esta validación cuantitativa multiactivo en total aislamiento de broker, D21 mantuvo sus garantías operativas:
- **Broker:** Moomoo (`TrdEnv.SIMULATE`), capital $1,000,000 USD intacto.
- **Fingerprint:** `f885ec2db2422308` (sin modificaciones).
- **Endpoint `/health`:** Estado `HEALTHY`, telemetría D21 activa, próxima evaluación programada a las 16:15 ET.
- **Cero órdenes no autorizadas.**
