# ENTREGABLE 02 — REPORTE DE REPRODUCCIÓN INDEPENDIENTE
## Estrategia: `ST_EMA200_V1` | Activos Líderes: GLD_H1 y DIA_H1

**Fecha de Ejecución:** 2026-10-31 10:40:49 UTC  
**Metodología:** Re-ejecución con motor independiente, re-cálculo de indicadores y verificación trade-by-trade.

---

### 1. TABLA COMPARATIVA DE REPRODUCCIÓN

| Activo / Métrica | Valor Reportado (EXP-ST01) | Valor Reproducido (EXP-ST02) | Discrepancia Absoluta | Estado |
| :--- | :---: | :---: | :---: | :---: |
| **GLD_H1 Total Trades** | 75 | 75 | 0 | **EXACTO** |
| **GLD_H1 Win Rate (%)** | 50.67% | 50.67% | 0.0000% | **PASS** |
| **GLD_H1 Net PnL ($)** | $4449.16 | $4449.16 | $0.0000 | **PASS** |
| **GLD_H1 Profit Factor** | 1.42 | 1.42 | 0.0000 | **PASS** |
| **DIA_H1 Total Trades** | 50 | 50 | 0 | **EXACTO** |
| **DIA_H1 Win Rate (%)** | 52.00% | 52.00% | 0.0000% | **PASS** |
| **DIA_H1 Net PnL ($)** | $3340.18 | $3340.18 | $0.0000 | **PASS** |
| **DIA_H1 Profit Factor** | 1.51 | 1.51 | 0.0000 | **PASS** |

---

### 2. ANÁLISIS DE TOLERANCIA Y CONCLUSIÓN

1. Las operaciones de entrada, salida, precios de ejecución con deslizamiento (2.0 bps) y comisiones ($0.005/acción) coinciden exactamente.
2. Cero operaciones fantasmas ni señales omitidas.
3. El resultado de reproducción es **100% PASS** para ambos activos líderes.
