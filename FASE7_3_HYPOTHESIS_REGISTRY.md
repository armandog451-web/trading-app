# ORACLEBOT V2 — FASE 7.3: REGISTRO INMUTABLE DE HIPÓTESIS CUANTITATIVAS
## EXPERIMENT REGISTRY, PARÁMETROS CONGELADOS Y FINGERPRINTS DETERMINISTAS

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.3 — Strategy Discovery Engine v2  
**Fecha de Registro:** 30 de octubre de 2026  
**Presupuesto de Búsqueda:** Exactamente 4 hipótesis candidatas empíricas + 1 hipótesis conceptual de asignación.  
**Modo:** `RESEARCH / ANALYSIS_ONLY`

---

## 1. TABLA GENERAL DEL REGISTRO DE INVESTIGACIÓN

| Hipótesis ID | Estrategia ID | Familia Cuantitativa | Fingerprint SHA-256 | Parámetros Clave | Estatus Fase 7.3 | RankScore |
| :---: | :---: | :--- | :---: | :--- | :---: | :---: |
| **H-MOM-REL-1** | `CS_RelMom_60d_V1` | Cross-Sectional Momentum | `165345c108cdefb9` | Rebalance 20d, Lookback 60d, SMA120 trend | **`RESEARCH_PROMISING`** | **0.957** |
| **H-MOM-REL-2** | `CS_RelMom_VolAdj_V2` | Cross-Sectional Momentum | `7460c8f0c2373832` | Rebalance 10d, Sharpe Mom 60d, Top 2 | **`RESEARCH_PROMISING`** | **0.832** |
| **H-MR-VOL-1** | `MR_VolCond_ZScore_V1` | Volatility-Conditioned Reversion | `adf4788b0f20132a` | Z-Score(20) $\le -2.0$, ATR exp $\ge 1.10$, RSI4 $\le 20$ | **`RESEARCH_PROMISING`** | **1.000** |
| **H-MR-VOL-2** | `MR_VolCond_BBCompression_V2` | Volatility-Conditioned Reversion | `68d2ea20522ef5e0` | BBW $\le$ Pct25, Close $\le$ Lower BB, RSI4 $\le 25$ | **`RESEARCH_PROMISING`** | **1.000** |
| **H-ALLOC-1** | `ALLOC_Adaptive_V1` | Adaptive Allocation | Conceptual | Asignación dinámica en función del régimen | *EN DISEÑO* | N/A |

---

## 2. DETALLE ESPECÍFICO DE CADA HIPÓTESIS REGISTRADA

### Hipótesis H-MOM-REL-1: Cross-Sectional Relative Momentum 60d
- **Estrategia:** `CS_RelMom_60d_V1`
- **Familia:** Familia A (Momentum Relativo Cross-Seccional)
- **Tesis Económica:** En lugar de exigir múltiples filtros absolutos de tendencia que provocan inanición de señales (como ocurrió en Fase 7.2 con MOM V1), ordenar cross-seccionalmente el universo de los 6 ETFs por su retorno a 60 días y rotar mensualmente (cada 20 sesiones) hacia el activo líder captura el liderazgo sectorial sin sobreajuste.
- **Parámetros Congelados:**
  - `rebalance_period`: 20 sesiones bursátiles (~1 mes calendario)
  - `momentum_lookback`: 60 sesiones (~3 meses)
  - `trend_filter_sma`: 120 sesiones (condición de tendencia alcista primaria)
  - `max_holding`: 20 sesiones
  - `stop_loss_pct`: 3.5%
  - `profit_target_pct`: 6.0%
- **Fingerprint:** `165345c108cdefb9`

---

### Hipótesis H-MOM-REL-2: Volatility-Adjusted Relative Momentum (Sharpe Momentum)
- **Estrategia:** `CS_RelMom_VolAdj_V2`
- **Familia:** Familia A (Momentum Relativo Ajustado por Volatilidad)
- **Tesis Económica:** Ajustar el momentum por la volatilidad realizada del activo ($\text{Sharpe Mom} = R_{60} / \sigma_{60}$) evita sobreponderar activos altamente volátiles con tendencias erráticas (e.g. energía o small caps) y favorece tendencias estables. Una rotación quincenal (cada 10 sesiones) entre los dos mejores activos diversifica el riesgo.
- **Parámetros Congelados:**
  - `rebalance_period`: 10 sesiones (~2 semanas)
  - `momentum_lookback`: 60 sesiones
  - `top_assets`: 2 activos simultáneos
  - `max_holding`: 10 sesiones
  - `stop_loss_pct`: 3.0%
  - `profit_target_pct`: 5.0%
- **Fingerprint:** `7460c8f0c2373832`

---

### Hipótesis H-MR-VOL-1: Volatility-Conditioned Reversion (Z-Score & ATR Expansion)
- **Estrategia:** `MR_VolCond_ZScore_V1`
- **Familia:** Familia B (Reversión Condicionada a Volatilidad)
- **Tesis Económica:** La reversión a la media no depende de un régimen lateral abstracto, sino de una sobrerreacción en presencia de expansión de volatilidad. Entrar cuando el precio está a más de 2 desviaciones estándar por debajo de su media de 20 días ($Z \le -2.0$) con RSI(4) $\le 20$ y el ATR(14) está expandiéndose ($\text{ATR}_{14} / \text{SMA}(\text{ATR}_{14}, 50) \ge 1.10$) captura rebotes por sobreventa tras liquidaciones forzadas.
- **Parámetros Congelados:**
  - `z_lookback`: 20 sesiones
  - `z_threshold`: -2.0 desviaciones estándar
  - `atr_period`: 14 sesiones
  - `atr_expansion_mult`: 1.10x
  - `rsi4_threshold`: 20.0
  - `max_holding`: 4 sesiones
  - `stop_loss_pct`: 2.5%
  - `profit_target_pct`: 3.5%
- **Fingerprint:** `adf4788b0f20132a`

---

### Hipótesis H-MR-VOL-2: Low-Volatility Compression Mean Reversion
- **Estrategia:** `MR_VolCond_BBCompression_V2`
- **Familia:** Familia B (Reversión en Compresión de Volatilidad)
- **Tesis Económica:** En periodos de compresión extrema de volatilidad (Bollinger Band Width en el cuartil inferior histórico, percentil 25), los toques a la banda inferior con sobreventa de corto plazo (RSI(4) $\le 25$) tienen alta probabilidad de volver a la media central antes de que ocurra una ruptura direccional.
- **Parámetros Congelados:**
  - `bb_lookback`: 20 sesiones
  - `bb_mult`: 2.0 desviaciones
  - `bbw_percentile`: 25.0%
  - `rsi4_threshold`: 25.0
  - `max_holding`: 3 sesiones
  - `stop_loss_pct`: 2.0%
  - `profit_target_pct`: 3.0%
- **Fingerprint:** `68d2ea20522ef5e0`

---

### Hipótesis H-ALLOC-1: Market Regime Adaptive Allocation (Diseño Conceptual)
- **Estrategia:** `ALLOC_Adaptive_V1`
- **Familia:** Familia C (Asignación Adaptativa de Portafolio)
- **Tesis Económica:** Asignar ponderación dinámica entre estrategias de Momentum y Reversión a la media según el régimen macro.
- **Estatus:** Se mantiene en fase conceptual de diseño hasta que las estrategias individuales completen su maduración de investigación.
