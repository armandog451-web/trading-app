# DELIVERABLE 07 — VEREDICTO DE HIPÓTESIS DE DESCUBRIMIENTO (H1 A H5)
## Estrategia Base: `ST_EMA200_V1`

---

| ID | Nombre de Hipótesis | Trades Base | PnL Base | PF Base | Trades Mod | PnL Mod | PF Mod | $\Delta$ PF | $\Delta$ PnL | Estado | Veredicto |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **H1** | Regime ADX > 25.0 | 75 | $4449.2 | 1.42 | 36 | $1793.8 | 1.36 | -0.06 | $-2655.4 | RECHAZADA | RECHAZADA (No mejora o reduce trades excesivamente) |
| **H2** | RVOL > 1.2x SMA20 | 75 | $4449.2 | 1.42 | 62 | $3546.8 | 1.40 | -0.02 | $-902.4 | RECHAZADA | RECHAZADA (Filtro demasiado restrictivo o sin edge) |
| **H3** | ATR Volatility Expansion (ATR > SMA20) | 75 | $4449.2 | 1.42 | 53 | $3487.1 | 1.48 | +0.06 | $-962.0 | RECHAZADA | RECHAZADA |
| **H4** | Session Timing Core (10:00 - 15:00 ET) | 75 | $4449.2 | 1.42 | 31 | $1074.2 | 1.23 | -0.19 | $-3374.9 | RECHAZADA | RECHAZADA (No aporta ventaja) |
| **H5** | Adaptive SuperTrend Trailing Stop | 75 | $4449.2 | 1.42 | 85 | $5990.2 | 1.65 | +0.23 | $+1541.1 | ACEPTADA | CONFIRMADA (Trailing Stop captura tendencias largas) |
