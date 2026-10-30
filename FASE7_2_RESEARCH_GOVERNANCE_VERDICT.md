# ORACLEBOT V2 — FASE 7.2: DICTAMEN FINAL DE GOBERNANZA DE INVESTIGACIÓN
## CLASIFICACIÓN INSTITUCIONAL DE ESTRATEGIAS, DECISIÓN DE PASO A PRODUCCIÓN Y SALVAGUARDAS

**Autoridad de Gobernanza:** OracleBot Quantitative Review Board  
**Workspace Canónico:** `trading-app-repo`  
**Fase Auditada:** Fase 7.2 — Validación Multiactivo con Mercado Real  
**Fecha de Dictamen:** 30 de octubre de 2026  
**Veredicto General:** **DESESTIMACIÓN DE AMBAS ESTRATEGIAS EXPERIMENTALES (`RESEARCH_REJECTED`)**

---

## 1. MARCO NORMATIVO DE CLASIFICACIÓN CUANTITATIVA

De acuerdo con el estándar institucional de OracleBot v2, toda estrategia experimental evaluada en el Strategy Laboratory debe ser clasificada en una de cuatro categorías:

1. **`RESEARCH_PROMISING`:** Expectativa matemática neta estadísticamente significativa ($p < 0.05$), Profit Factor neto $> 1.30$, supervivencia probada al estrés de costes 2x y 3x, frecuencia operativa anual $\ge 12\text{ trades/año}$, y generalización demostrada en al menos el 70% de los activos evaluados.
2. **`RESEARCH_INCONCLUSIVE`:** Métricas positivas pero con dispersión muestral amplia, o sensibilidad moderada a fricciones que requiere mayor acumulación de datos o reformulación teórica.
3. **`RESEARCH_REJECTED`:** Fracaso en generalización multiactivo, PnL neto negativo o no resiliente a costes moderados (2x), frecuencia inoperante, o dependencia crítica de un único activo.
4. **`INVALID`:** Defectos metodológicos, sesgos de supervivencia, lookahead bias o datos sintéticos no declarados.

---

## 2. DICTAMEN ESPECÍFICO POR ESTRATEGIA

### Estrategia: `MR_RsiBollinger_V1`
- **Familia:** Reversión a la Media
- **Target Regime:** `RANGING`
- **Fingerprint:** `571529bf959e44ef`
- **Resumen Cuantitativo:**
  - Operaciones: 102
  - Net PnL (1x Base): +$566.33 USD | Net PF: 1.06 | Cost Drag: 69.67%
  - Net PnL (2x Moderado): **-$734.68 USD** | Net PF: 0.93
  - Net PnL (3x Extremo): **-$1,984.41 USD** | Net PF: 0.81
  - Desempeño ex-SPY (LOSO): **-$889.38 USD** (Pérdidas en 4 de 6 activos: QQQ, DIA, XLF, XLE)
  - Bootstrap $p(\text{Pérdida Neta})$: **41.30%**
- **CLASIFICACIÓN FORMAL:** **`RESEARCH_REJECTED`**
- **Fundamento Técnico:** La estrategia no generaliza fuera de SPY. Su aparente rentabilidad inicial era un artefacto de sobreajuste local a SPY. No resiste un estrés de costes moderado (2x) y su significancia estadística es nula.

---

### Estrategia: `MOM_TrendPullback_V1`
- **Familia:** Momentum / Trend Pullback
- **Target Regime:** `TRENDING_BULL`
- **Fingerprint:** `5d10c8c90e6f73a6`
- **Resumen Cuantitativo:**
  - Operaciones: 9 en 4.78 años a lo largo de 6 activos (1.89 trades/año para todo el portafolio)
  - Frecuencia en QQQ: **0 operaciones**
  - Net PnL (1x Base): **-$130.49 USD** | Net PF: 0.84
  - Net PnL (2x Moderado): **-$240.17 USD**
  - Net PnL (3x Extremo): **-$349.89 USD**
  - Bootstrap $p(\text{Pérdida Neta})$: **60.30%**
- **CLASIFICACIÓN FORMAL:** **`RESEARCH_REJECTED`**
- **Fundamento Técnico:** La estrategia sufre de una inanición severa de señales generada por el apilamiento excesivo de filtros técnicos en barras diarias. Además de no ser operable en la práctica, su expectativa matemática neta es deficitaria.

---

## 3. RESOLUCIÓN DE GOBERNANZA Y DIRECTRICES VINCULANTES

1. **Bloqueo Absoluto de Despliegue Prospectivo:**
   Queda terminantemente prohibido conectar, activar o migrar `MR_RsiBollinger_V1` o `MOM_TrendPullback_V1` a entornos Moomoo PAPER o LIVE.

2. **Inmutabilidad y Preservación de D21:**
   La estrategia `D21_RangeCompress_5d` (fingerprint `f885ec2db2422308`) se mantiene como la **ÚNICA** estrategia autorizada en PAPER trading con capital virtual de $1,000,000 USD. Ningún código de investigación de Fase 7 ha perturbado ni perturbará el runtime de D21.

3. **Estado del Strategy Laboratory:**
   El módulo `ai_trading_agent.strategy_lab` permanece en modo estricto `RESEARCH / ANALYSIS_ONLY`.

4. **Recomendaciones para Futuras Fases de Investigación:**
   - Para estrategias de Momentum: Investigar marcos temporales intradiarios (e.g. 1h, 15m) o relajar filtros estáticos en favor de ordenamiento de momentum relativo cross-seccional.
   - Para estrategias de Mean Reversion: Incorporar métricas de régimen basadas en volatilidad implícita (VIX) o spreads de crédito antes de entrar en sobreventas técnicas.
   - Preservar la regla de oro: **Rechazar tempranamente modelos no robustos antes de comprometer capital**.
