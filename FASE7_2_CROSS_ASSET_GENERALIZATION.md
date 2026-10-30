# ORACLEBOT V2 — FASE 7.2: INFORME DE GENERALIZACIÓN MULTIACTIVO
## ANÁLISIS COMPARATIVO DE ACTIVOS: SPY VS QQQ VS IWM VS DIA VS XLF VS XLE

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.2 — Validación Cuantitativa Multiactivo  
**Fecha:** 30 de octubre de 2026  
**Universo:** 6 ETFs sectoriales e índices estadounidenses de alta liquidez

---

## 1. PERFIL ESTRUCTURAL DE LOS ACTIVOS EVALUADOS

| Símbolo | Nombre Completo | Clase de Activo / Sector | Comportamiento Típico | Distribución RANGING | Distribución TRENDING_BULL |
| :---: | :--- | :--- | :--- | :---: | :---: |
| **SPY** | SPDR S&P 500 ETF Trust | Gran Capitalización / Mercado Amplio | Tendencia estable, alta absorción de liquidez | 33.5% | 20.7% |
| **QQQ** | Invesco QQQ Trust | Tecnología / Crecimiento / Nasdaq 100 | Alta beta, momentum fuerte, reversiones violentas | 36.8% | 18.9% |
| **IWM** | iShares Russell 2000 ETF | Pequeña Capitalización (Small Caps) | Ruido intradiario, alta dispersión, menor eficiencia | 37.6% | 9.8% |
| **DIA** | SPDR Dow Jones Industrial Avg | Industrial / Valor / Cíclico | Baja volatilidad relativa, menor dispersión | 32.2% | 13.1% |
| **XLF** | Financial Select Sector SPDR | Bancario / Financiero / Seguros | Sensibilidad a curvas de tipos y política monetaria | 31.4% | 15.4% |
| **XLE** | Energy Select Sector SPDR | Petróleo, Gas y Servicios de Energía | Fuerte correlación con materias primas, ciclos de shock | 44.8% | 13.2% |

---

## 2. MATRIZ DE RENDIMIENTO COMPARATIVO CRUZADO (ESCENARIO 1X BASE)

### Mean Reversion (`MR_RsiBollinger_V1` — Con Filtro `RANGING`)

```
Rendimiento Net PnL por Activo ($ USD):
  +$1,455.71 ───■ SPY (S&P 500)
    +$608.24 ───■ IWM (Russell 2000)
      -$49.29 ───■ QQQ (Nasdaq 100)
     -$346.61 ───■ XLE (Energía)
     -$516.88 ───■ DIA (Dow Jones)
     -$584.84 ───■ XLF (Finanzas)
```

| Métrica | SPY | QQQ | IWM | DIA | XLF | XLE | Portafolio |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Operaciones** | 22 | 17 | 15 | 15 | 16 | 17 | **102** |
| **Win Rate** | **68.18%** | 58.82% | 53.33% | 40.00% | 43.75% | 52.94% | **53.92%** |
| **True Gross PnL** | +$1,729.89 | +$162.47 | +$804.19 | -$327.47 | -$368.62 | -$133.08 | **+$1,867.38** |
| **Costes Totales** | $274.18 | $211.76 | $195.95 | $189.41 | $216.22 | $213.53 | **$1,301.05** |
| **True Net PnL** | **+$1,455.71** | **-$49.29** | **+$608.24** | **-$516.88** | **-$584.84** | **-$346.61** | **+$566.33** |
| **Net Profit Factor** | **2.21** | 0.97 | 1.33 | 0.64 | 0.56 | 0.83 | **1.06** |
| **Sharpe Ratio** | **0.78** | -0.03 | 0.23 | -0.36 | -0.33 | -0.13 | **0.11** |
| **Max Drawdown %**| 0.36% | 1.17% | 0.53% | 0.53% | 0.83% | 1.19% | **2.45%** |

---

## 3. FACTORES EXPLICATIVOS DE LA DIVERGENCIA SECTORIAL

### ¿Por qué funcionó en SPY e IWM pero fracasó en los demás?

1. **SPY (Efecto Liquidez Universal y Regresión Institucional):**
   - SPY representa el índice más líquido del planeta, arbitrado constantemente por miles de algoritmos de market making. Las desviaciones extremas de corto plazo (RSI(4) < 25) en rangos laterales son rápidamente arbitradas por flujos pasivos de rebalanceo, produciendo el rebote esperado hacia la media.
2. **QQQ (El Riesgo de Tendencia Persistente en Crecimiento):**
   - El sector tecnológico tiende a exhibir "falsos rangos". Cuando una acción líder (e.g. NVDA, AAPL, MSFT) reporta resultados o catalizadores macro, el índice penetra la banda de Bollinger y continúa cayendo sin rebotar durante varios días, activando el Stop Loss de 2.0% o el Time Exit en mínimos.
3. **DIA y XLF (Fracaso por Asimetría de Tendencia Negativa):**
   - En sectores tradicionales como bancos e industriales, los periodos de baja volatilidad frecuentemente precedieron caídas graduales pero persistentes asociadas a tensiones en la curva de rendimientos (2022-2023). La estrategia compraba caídas que resultaban ser inicios de caídas mayores.
4. **XLE (El Comportamiento de Commodity):**
   - El sector energético no opera como una cesta diversificada tradicional; está dominado por shocks geopolíticos y precios de futuros de crudo. Las bandas de Bollinger no representan barreras estocásticas válidas cuando el subyacente experimenta saltos discontinuos.

---

## 4. CONCLUSIÓN DE GENERALIZACIÓN

Una estrategia robusta debe demostrar eficacia a través de múltiples clases de activos no perfectamente correlacionadas. La falla de `MR_RsiBollinger_V1` en el 66.7% de los activos evaluados y la ausencia de señales operables de `MOM_TrendPullback_V1` confirman que **los modelos carecen de invariancia frente a la dinámica sectorial y no son generalizables**.
