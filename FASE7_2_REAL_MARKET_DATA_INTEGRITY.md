# ORACLEBOT V2 — FASE 7.2: AUDITORÍA DE INTEGRIDAD DE DATOS REALES DE MERCADO
## TRAZABILIDAD, CALENDARIO OFICIAL Y CERTIFICACIÓN ANTIDATOS SINTÉTICOS

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.2 — Validación Multiactivo  
**Fecha de certificación:** 30 de octubre de 2026  
**Auditor:** Anti-Overfitting & Data Integrity Engine  
**Proveedor de datos:** `yfinance_provider` (Datos históricos oficiales NYSE/NASDAQ ajustados por dividendos y splits)

---

## 1. INTRODUCCIÓN Y ANTECEDENTES FORENSES

Durante la Fase 7.1A se descubrió que los 1,200 registros utilizados en las simulaciones iniciales de la Fase 7.0 y 7.1 correspondían a series sintéticas generadas mediante Movimiento Browniano Geométrico (GBM) con incrementos de calendario $+1\text{ día}$. Dicho dataset adolecía de:
- Un 72.4% de operaciones situadas en fines de semana o feriados federales estadounidenses.
- Ausencia de microestructura real de subasta y correlación de volatilidad.
- Falsación de métricas de backtesting.

En cumplimiento con el mandato de la Fase 7.2, **se prohibió de manera absoluta el uso de cualquier dato sintético**. La totalidad de los experimentos cuantitativos de la Fase 7.2 se ejecutó sobre datos auténticos de mercado, verificados barra a barra.

---

## 2. MANIFIESTO DE INTEGRIDAD DE LOS 6 ACTIVOS EVALUADOS

Todos los activos fueron extraídos con un historial continuo de **1,200 barras diarias oficiales** que cubren el periodo **2022-01-20 a 2026-10-30** (4.78 años de actividad bursátil real).

| Símbolo | Tipo de Activo | Barras | Fecha Inicio | Fecha Fin | Hash SHA-256 Canónico | Barras Inválidas Calendario |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SPY** | S&P 500 ETF Trust | 1,200 | 2022-01-20 | 2026-10-30 | `b6bb4ae911726485cdd5d2baf3d7ff6e0e96cb70027ca717809c835f8d22bcf8` | **0 (0.00%)** |
| **QQQ** | Invesco QQQ Trust (Nasdaq) | 1,200 | 2022-01-20 | 2026-10-30 | `b45cecb69fb34b88e92c999a50e29d730f2753a5b7017cb22e49a550b59fb52f` | **0 (0.00%)** |
| **IWM** | iShares Russell 2000 ETF | 1,200 | 2022-01-20 | 2026-10-30 | `4a89bf618937e2bf63911c448f0e81aae3f75acd57d66bdfc19edb5b47526676` | **0 (0.00%)** |
| **DIA** | SPDR Dow Jones Industrial Average | 1,200 | 2022-01-20 | 2026-10-30 | `397e86a32f7ce1fecee7584443ae7f8e8ac1bf38a65a0bdeb129a5912ee5634b` | **0 (0.00%)** |
| **XLF** | Financial Select Sector SPDR | 1,200 | 2022-01-20 | 2026-10-30 | `68d5e0aa8955a42c04358fd7585c939509d20bb33ca1a213a722063785380bb6` | **0 (0.00%)** |
| **XLE** | Energy Select Sector SPDR | 1,200 | 2022-01-20 | 2026-10-30 | `e58a42b96fb14552ca865314a989a02ed137993681da67c7402ced79a5aa8bfd` | **0 (0.00%)** |

---

## 3. AUDITORÍA DE CALENDARIO Y SESIONES BURSÁTILES

Cada timestamp de barra y cada fecha de entrada/salida de operación fue sometida al servicio `MarketCalendarService` de OracleBot (`America/New_York`):

1. **Fines de semana:** Cero barras en días sábado o domingo en los 6 activos ($0 / 7,200$).
2. **Feriados Oficiales NYSE:** Ninguna barra fue registrada en festivos bursátiles reconocidos (Martin Luther King Jr. Day, Presidents' Day, Good Friday, Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving Day, Christmas Day).
3. **Cierres Anticipados (Early Closes):** Tratados correctamente según los horarios oficiales de subasta de 13:00 ET.
4. **Validez del universo de trades:** El 100.00% de las 565 operaciones registradas en el CSV exportado (`fase7_2_multiasset_trades.csv`) presentan `calendar_valid = True`.

---

## 4. DISTRIBUCIÓN DE REGÍMENES DE MERCADO POR ACTIVO

El clasificador determinista `MarketRegimeV1` arrojó la siguiente distribución de regímenes en las 1,200 barras de cada activo:

```
Distribución de Regímenes (2022 - 2026):
┌────────┬─────────────────┬───────────┬─────────────────┐
│ Activo │ TRENDING_BULL   │ RANGING   │ INDETERMINATE   │
├────────┼─────────────────┼───────────┼─────────────────┤
│ SPY    │ 248 (20.7%)     │ 402 (33.5%)│ 550 (45.8%)     │
│ QQQ    │ 227 (18.9%)     │ 442 (36.8%)│ 531 (44.2%)     │
│ IWM    │ 118 ( 9.8%)     │ 451 (37.6%)│ 631 (52.6%)     │
│ DIA    │ 157 (13.1%)     │ 386 (32.2%)│ 657 (54.8%)     │
│ XLF    │ 185 (15.4%)     │ 377 (31.4%)│ 638 (53.2%)     │
│ XLE    │ 159 (13.2%)     │ 538 (44.8%)│ 503 (41.9%)     │
├────────┼─────────────────┼───────────┼─────────────────┤
│ TOTAL  │ 1,094 (15.2%)   │ 2,596 (36.1%) 3,510 (48.8%) │
└────────┴─────────────────┴───────────┴─────────────────┘
```

### Observaciones Estructurales
- El régimen **`INDETERMINATE`** representa el **48.8%** del tiempo a lo largo de todo el universo de ETFs diarios. La regla de gobernanza de abstención protege al sistema de operar en mercados erráticos casi la mitad de los días.
- El régimen lateral **`RANGING`** es el más frecuente entre los regímenes activos (36.1%), con especial prevalencia en energía (`XLE`: 44.8%).
- El régimen alcista puro **`TRENDING_BULL`** con alta eficiencia direccional ($\text{ADX} \ge 25 \land \text{ER} \ge 0.35$) es escaso en activos diversificados (solo 9.8% en IWM y 13.1% en DIA).

---

## 5. CONCLUSIÓN DE INTEGRIDAD DE DATOS

Se certifica que la totalidad de los datos analizados en la Fase 7.2 proviene de fuentes de mercado institucionales reales, verificables mediante sus correspondientes hashes SHA-256. El riesgo de contaminación por datos sintéticos queda formalmente erradicado.
