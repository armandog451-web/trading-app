# ORACLEBOT V2 — FASE 7.2: INFORME DE RESULTADOS DE MEAN REVERSION
## EVALUACIÓN MULTIACTIVO DE `MR_RsiBollinger_V1` CON Y SIN FILTRO DE RÉGIMEN

**Estrategia:** `MR_RsiBollinger_V1`  
**Familia:** Reversión a la Media (Mean Reversion)  
**Fingerprint SHA-256:** `571529bf959e44ef`  
**Parámetros Congelados:**
- `rsi_period`: 4
- `rsi_oversold`: 25.0
- `bb_period`: 20
- `bb_std`: 2.0
- `min_rvol`: 1.0
- `max_holding_days`: 3
- `stop_loss`: -2.0%
- `profit_target`: +3.5%
**Regla de Régimen Canónica:** Operativa autorizada exclusivamente en `MarketRegimeV1.RANGING`.

---

## 1. DESEMPEÑO CRUZADO BAJO RÉGIMEN FILTRADO (`RANGING`) — ESCENARIO BASE 1X

Bajo la regla canónica, la estrategia solo evalúa entradas cuando el mercado es clasificado en rango lateral estricto ($\text{ADX} < 20 \land \text{ER} < 0.25$).

### Tabla Detallada por Activo (Costes 1x: $0.005/acción, 5 bps slippage)

| Activo | Operaciones | Win Rate | True Gross PnL | Deslizamiento | Comisiones | True Net PnL | Net PF | Sharpe | Sortino | Max DD % | Cost Drag % |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SPY** | 22 | 68.18% | +$1,729.89 | $162.78 | $111.40 | **+$1,455.71** | 2.21 | 0.78 | 1.18 | 0.36% | 15.85% |
| **QQQ** | 17 | 58.82% | +$162.47 | $117.56 | $94.20 | **-$49.29** | 0.97 | -0.03 | -0.05 | 1.17% | 130.34% |
| **IWM** | 15 | 53.33% | +$804.19 | $104.95 | $91.00 | **+$608.24** | 1.33 | 0.23 | 0.34 | 0.53% | 24.37% |
| **DIA** | 15 | 40.00% | -$327.47 | $98.41 | $91.00 | **-$516.88** | 0.64 | -0.36 | -0.49 | 0.53% | N/A (Loss) |
| **XLF** | 16 | 43.75% | -$368.62 | $110.42 | $105.80 | **-$584.84** | 0.56 | -0.33 | -0.46 | 0.83% | N/A (Loss) |
| **XLE** | 17 | 52.94% | -$133.08 | $112.53 | $101.00 | **-$346.61** | 0.83 | -0.13 | -0.19 | 1.19% | N/A (Loss) |
| **PORTAFOLIO** | **102** | **53.92%** | **+$1,867.38** | **$706.65** | **$594.40** | **+$566.33** | **1.06** | **0.11** | **0.16** | **2.45%** | **69.67%** |

---

## 2. ANÁLISIS DE LA ASIMETRÍA ENTRE SPY Y EL RESTO DE ACTIVOS

El hallazgo central de la Fase 7.2 respecto a Mean Reversion es la **extrema fragilidad y falta de transferibilidad fuera de SPY**:

1. **Dependencia Total de SPY:**  
   - En SPY, la estrategia produjo un retorno neto de +$1,455.71 con un Profit Factor de 2.21 y Win Rate del 68.2%.
   - La suma neta de los otros 5 activos (QQQ, IWM, DIA, XLF, XLE) es **-$889.38**.
   - **4 de los 6 activos (66.7%) tuvieron PnL neto negativo**.

2. **Divergencia de Microestructura Sectorial:**
   - En **QQQ (Tecnología):** Las sobreventas en RSI(4) por debajo de 25 a menudo no rebotan de inmediato; continúan cayendo en cascadas de liquidación debido al fuerte momentum de los semiconductores y mega-caps.
   - En **DIA y XLF (Industriales y Bancos):** Los rangos laterales con frecuencia se rompen hacia abajo durante correcciones cíclicas, provocando la activación recurrente de Stop Loss al -2.0%.
   - En **XLE (Energía):** La fuerte dependencia del precio del crudo genera tendencias direccionales intradiarias violentas que castigan las compras a la contra.

---

## 3. COMPARATIVA: CON FILTRO DE RÉGIMEN (`RANGING`) VS SIN FILTRO (`UNFILTERED`)

Para contrastar formalmente la hipótesis de régimen (H-MR-2), se ejecutó la estrategia sin filtrar por régimen de mercado (permitiendo operar en cualquier estado: `TRENDING_BULL`, `RANGING` o `INDETERMINATE`).

| Modo | Operaciones | Win Rate | True Gross PnL | Deslizamiento + Comisiones | True Net PnL | Net PF | Sharpe | Max DD % | Cost Drag % |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FILTRADO (`RANGING`)** | 102 | 53.92% | +$1,867.38 | $1,301.05 | +$566.33 | 1.06 | 0.11 | 2.45% | **69.67%** |
| **SIN FILTRO (Todos)** | 267 | 50.56% | +$6,474.68 | $3,366.74 | +$3,107.94 | 1.12 | 0.33 | 2.50% | **52.00%** |

### Diagnóstico Cuantitativo del Filtro
- En modo sin filtro, la estrategia genera más del doble de operaciones (267 vs 102).
- El PnL neto sin filtro es mayor (+3,107.94 USD), pero esto no se debe a una mayor precisión del modelo, sino a que al operar durante un mercado predominantemente alcista (2022-2026), comprar en sobreventa de RSI(4) fuera de rango lateral equivale a comprar en retroceso alcista (*dip-buying* en tendencia alcista).
- Sin embargo, **ambos modos fracasan categóricamente bajo estrés de costes**:
  - En costes 2x ($0.010/acción, 10 bps), el modo Filtrado pierde -$734.68 y el No Filtrado pierde -$67.59.
  - En costes 3x ($0.015/acción, 15 bps), el modo Filtrado pierde -$1,984.41 y el No Filtrado pierde -$3,668.92.

---

## 4. CONCLUSIÓN DE MEAN REVERSION

`MR_RsiBollinger_V1` demuestra una expectativa matemática neta insuficiente para compensar los costes de transacción en un entorno institucional multiactivo. Su rentabilidad aislada en SPY no se generaliza, demostrando ser fruto de sobreajuste histórico local.
