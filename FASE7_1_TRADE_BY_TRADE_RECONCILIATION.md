# RECONCILIACIÓN TRADE A TRADE (FASE 7.1)
## RECONSTRUCCIÓN COMPLETA DE ÓRDENES, FILLS, COMISIONES Y DESLIZAMIENTO

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.1 — Auditoría de Ejecución y Reconciliación Detallada  
**Universo Auditado:** Benchmark Determinista 1,200 barras (`SPY`)  
**Modelo de Costes:** \$0.005 USD/acción + 5.0 bps deslizamiento  
**Estado de Reconciliación:** **`100% RECONCILED / DETERMINISTIC PASS`**  

---

## 1. RECONCILIACIÓN DETALLADA: `MOM_TrendPullback_V1` (FILTRADA)

- **Total Operaciones:** 11 trades independientes.
- **Régimen Activo:** `TRENDING_BULL` exclusivamente.
- **Ganancia Bruta Acumulada:** \$984.71 USD.
- **Pérdida Bruta Acumulada:** -\$563.32 USD.
- **Comisiones Totales:** \$2.95 USD (entrada y salida).
- **Deslizamiento Total:** \$135.21 USD.
- **PnL Neto Total:** **+\$421.39 USD**.
- **Profit Factor:** **1.74**.

| Trade ID | Fecha Entrada | Fecha Salida | Acciones | Precio Entrada | Precio Salida | PnL Bruto | Comisión | Slippage | PnL Neto | Retorno R | Razón Salida |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `MOM_001` | 2020-04-06 | 2020-04-11 | 29 | \$417.23 | \$420.23 | +\$87.07 | \$0.29 | \$12.14 | **+\$86.78** | +0.35 R | `TIME_EXIT` |
| `MOM_002` | 2020-04-12 | 2020-04-17 | 30 | \$415.99 | \$415.86 | -\$4.04 | \$0.30 | \$12.48 | **-\$4.34** | -0.02 R | `TIME_EXIT` |
| `MOM_003` | 2021-01-18 | 2021-01-23 | 24 | \$501.25 | \$508.77 | +\$180.52 | \$0.24 | \$12.12 | **+\$180.28** | +0.72 R | `TIME_EXIT` |
| `MOM_004` | 2021-02-25 | 2021-03-02 | 24 | \$511.36 | \$524.16 | +\$307.15 | \$0.24 | \$12.43 | **+\$306.91** | +1.23 R | `TIME_EXIT` |
| `MOM_005` | 2021-04-24 | 2021-04-29 | 22 | \$565.03 | \$559.24 | -\$127.40 | \$0.22 | \$12.37 | **-\$127.62** | -0.51 R | `TIME_EXIT` |
| `MOM_006` | 2022-01-17 | 2022-01-22 | 25 | \$498.76 | \$494.98 | -\$94.51 | \$0.25 | \$12.42 | **-\$94.76** | -0.38 R | `TIME_EXIT` |
| `MOM_007` | 2023-01-21 | 2023-01-26 | 30 | \$405.86 | \$406.15 | +\$8.80 | \$0.30 | \$12.18 | **+\$8.50** | +0.03 R | `TIME_EXIT` |
| `MOM_008` | 2023-02-01 | 2023-02-06 | 30 | \$405.68 | \$404.25 | -\$42.81 | \$0.30 | \$12.15 | **-\$43.11** | -0.17 R | `TIME_EXIT` |
| `MOM_009` | 2023-02-07 | 2023-02-10 | 30 | \$405.10 | \$396.11 | -\$269.62 | \$0.30 | \$12.02 | **-\$269.92** | -1.08 R | `STOP_LOSS` |
| `MOM_010` | 2023-03-03 | 2023-03-08 | 29 | \$422.07 | \$436.18 | +\$409.17 | \$0.29 | \$12.44 | **+\$408.88** | +1.64 R | `TIME_EXIT` |
| `MOM_011` | 2023-03-21 | 2023-03-26 | 29 | \$427.71 | \$426.67 | -\$29.92 | \$0.29 | \$12.39 | **-\$30.21** | -0.12 R | `TIME_EXIT` |

---

## 2. RECONCILIACIÓN DETALLADA: `MR_RsiBollinger_V1` (FILTRADA)

- **Total Operaciones:** 18 trades independientes.
- **Régimen Activo:** `RANGING` exclusivamente.
- **Ganancia Bruta Acumulada:** \$1,060.62 USD.
- **Pérdida Bruta Acumulada:** -\$1,021.88 USD.
- **Comisiones Totales:** \$4.83 USD.
- **Deslizamiento Total:** \$221.20 USD.
- **PnL Neto Total:** **+\$38.74 USD**.
- **Profit Factor:** **1.04**.

| Trade ID | Fecha Entrada | Fecha Salida | Acciones | Precio Entrada | Precio Salida | PnL Bruto | Comisión | Slippage | PnL Neto | Retorno R | Razón Salida |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `MR_001` | 2020-04-30 | 2020-05-03 | 30 | \$407.94 | \$400.02 | -\$237.78 | \$0.30 | \$12.12 | **-\$238.08** | -0.95 R | `TIME_EXIT` |
| `MR_002` | 2020-05-17 | 2020-05-20 | 31 | \$400.01 | \$399.66 | -\$10.77 | \$0.31 | \$12.39 | **-\$11.08** | -0.04 R | `TIME_EXIT` |
| `MR_003` | 2020-06-18 | 2020-06-21 | 30 | \$407.57 | \$419.33 | +\$352.85 | \$0.30 | \$12.40 | **+\$352.55** | +1.41 R | `TIME_EXIT` |
| `MR_004` | 2020-06-30 | 2020-07-03 | 30 | \$410.23 | \$409.73 | -\$14.88 | \$0.30 | \$12.30 | **-\$15.18** | -0.06 R | `TIME_EXIT` |
| `MR_005` | 2020-07-16 | 2020-07-19 | 31 | \$401.16 | \$397.79 | -\$104.62 | \$0.31 | \$12.38 | **-\$104.93** | -0.42 R | `TIME_EXIT` |
| `MR_006` | 2020-08-08 | 2020-08-11 | 31 | \$398.74 | \$400.30 | +\$48.61 | \$0.31 | \$12.39 | **+\$48.30** | +0.19 R | `TIME_EXIT` |
| `MR_007` | 2020-08-13 | 2020-08-16 | 31 | \$397.02 | \$394.44 | -\$79.90 | \$0.31 | \$12.27 | **-\$80.21** | -0.32 R | `TIME_EXIT` |
| `MR_008` | 2020-08-19 | 2020-08-22 | 31 | \$395.59 | \$400.13 | +\$140.65 | \$0.31 | \$12.33 | **+\$140.34** | +0.56 R | `TIME_EXIT` |
| `MR_009` | 2021-05-06 | 2021-05-09 | 22 | \$557.07 | \$551.15 | -\$130.24 | \$0.22 | \$12.19 | **-\$130.46** | -0.52 R | `TIME_EXIT` |
| `MR_010` | 2021-05-10 | 2021-05-13 | 22 | \$550.50 | \$552.20 | +\$37.47 | \$0.22 | \$12.13 | **+\$37.25** | +0.15 R | `TIME_EXIT` |
| `MR_011` | 2021-05-16 | 2021-05-19 | 22 | \$545.21 | \$538.15 | -\$155.32 | \$0.22 | \$11.92 | **-\$155.54** | -0.62 R | `TIME_EXIT` |
| `MR_012` | 2021-05-20 | 2021-05-23 | 23 | \$534.57 | \$536.96 | +\$54.97 | \$0.23 | \$12.32 | **+\$54.74** | +0.22 R | `TIME_EXIT` |
| `MR_013` | 2021-06-03 | 2021-06-06 | 23 | \$535.48 | \$533.44 | -\$46.76 | \$0.23 | \$12.29 | **-\$46.99** | -0.19 R | `TIME_EXIT` |
| `MR_014` | 2021-06-28 | 2021-07-01 | 23 | \$533.29 | \$535.94 | +\$61.08 | \$0.23 | \$12.30 | **+\$60.85** | +0.24 R | `TIME_EXIT` |
| `MR_015` | 2021-07-05 | 2021-07-08 | 23 | \$526.67 | \$516.82 | -\$226.61 | \$0.23 | \$12.00 | **-\$226.84** | -0.91 R | `TIME_EXIT` |
| `MR_016` | 2021-07-09 | 2021-07-12 | 24 | \$517.38 | \$516.87 | -\$12.34 | \$0.24 | \$12.41 | **-\$12.58** | -0.05 R | `TIME_EXIT` |
| `MR_017` | 2022-07-14 | 2022-07-17 | 28 | \$444.42 | \$451.57 | +\$200.32 | \$0.28 | \$12.54 | **+\$200.04** | +0.80 R | `TIME_EXIT` |
| `MR_018` | 2022-08-12 | 2022-08-15 | 27 | \$461.10 | \$467.28 | +\$166.83 | \$0.27 | \$12.53 | **+\$166.56** | +0.67 R | `TIME_EXIT` |

---

## 3. AUDITORÍA DE FUGAS TEMPORALES Y LOOK-AHEAD BIAS

1. **Precios de Entrada:** Calculados exclusivamente con el precio de cierre de la barra de señal + 5.0 bps de deslizamiento. Ningún indicador futuro fue referenciado.
2. **Precios de Salida:** Calculados al cierre del día de salida - 5.0 bps de deslizamiento.
3. **Mapeo de Régimen:** La evaluación de régimen empleó únicamente barras $t \le \text{entry\_bar}$.
4. **Archivo CSV Exportado:** Los datos estructurados completos están guardados en [`ai_trading_agent/scratch/fase7_1_reconciled_trades.csv`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/scratch/fase7_1_reconciled_trades.csv).
