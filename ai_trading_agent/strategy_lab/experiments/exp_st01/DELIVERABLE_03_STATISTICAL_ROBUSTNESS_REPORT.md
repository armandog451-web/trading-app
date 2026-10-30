# DELIVERABLE 03 — REPORTE DE ROBUSTEZ ESTADÍSTICA Y CONTROL ANTISOBREAJUSTE
## Estrategia: `ST_EMA200_V1` | Activo Analizado: GLD_H1

---

### 1. VALIDACIÓN CRONOLÓGICA (60% DEV / 20% VAL / 20% OOS)

| Partición | Trades | Net PnL ($) | Win Rate (%) | Profit Factor |
| :--- | :---: | :---: | :---: | :---: |
| **Development (60%)** | 43 | $556.33 | 44.2% | 1.08 |
| **Validation (20%)** | 12 | $1211.50 | 58.3% | 1.99 |
| **Out-of-Sample (20%)** | 13 | $876.12 | 53.8% | 1.50 |

- **Ratio OOS / Dev:** 4.72

---

### 2. SIMULACIÓN MONTE CARLO (1,000 ITERACIONES BOOTSTRAP)

- **Iteraciones:** 1000
- **Probabilidad de Esperanza Matemática Positiva:** 92.0%
- **Mediana Net PnL:** $4439.80
- **Intervalo de Confianza 95% PnL:** [$-1737.94, $10201.38]
- **Value at Risk (VaR 95% PnL):** $-771.00
- **Mediana Drawdown Máximo:** $1956.89
- **Drawdown Máximo al 95% de Confianza:** $4001.71

---

### 3. EFICIENCIA WALK-FORWARD (VENTANAS CRONOLÓGICAS)

| Ventana | Periodo IS | IS Trades | IS PnL | IS PF | Periodo OOS | OOS Trades | OOS PnL | OOS PF | WFE Ratio |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| W1 | 2023-12-04 a 2024-07-02 | 15 | $361.5 | 1.16 | 2024-07-03 a 2025-02-03 | 13 | $998.1 | 1.56 | 2.76 |
| W2 | 2023-12-04 a 2025-02-03 | 31 | $1451.3 | 1.32 | 2025-02-03 a 2025-09-03 | 10 | $-1007.2 | 0.55 | -1.39 |
| W3 | 2023-12-04 a 2025-09-03 | 43 | $556.3 | 1.08 | 2025-09-03 a 2026-04-06 | 12 | $1211.5 | 1.99 | 6.53 |
| W4 | 2023-12-04 a 2026-04-06 | 59 | $3249.4 | 1.40 | 2026-04-06 a 2026-10-30 | 13 | $876.1 | 1.50 | 1.08 |
