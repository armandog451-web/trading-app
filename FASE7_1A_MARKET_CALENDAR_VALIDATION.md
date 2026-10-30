# VALIDACIÓN DE CALENDARIO BURSÁTIL NYSE/NASDAQ (FASE 7.1A)
## AUDITORÍA FORENSE DE FECHAS, FINES DE SEMANA, FESTIVOS Y FUGAS TEMPORALES

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.1A — Auditoría Forense de Calendario Bursátil  
**Motor de Validación:** [`MarketCalendarService`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/schedule/market_calendar.py) (`America/New_York`)  
**Bolsas Auditadas:** New York Stock Exchange (NYSE) / NASDAQ  
**Estado:** **DEFICIENCIA EN SERIE SINTÉTICA IDENTIFICADA — PROTOCOLO CORREGIDO**  

---

## 1. AUDITORÍA FORENSE DE FECHAS EN EL BENCHMARK SINTÉTICO ORIGINAL

Se realizó un escaneo exhaustivo sobre las fechas de entrada y salida de las 29 operaciones reportadas en la Fase 7.1 utilizando el servicio canónico [`MarketCalendarService.is_trading_day()`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/schedule/market_calendar.py#L122):

### Resumen del Fallo de Calendario:
- **Momentum Filtrada:** **7 de las 11 operaciones (63.6%)** tenían fechas de entrada o salida en días no hábiles.
- **Mean Reversion Filtrada:** **14 de las 18 operaciones (77.8%)** tenían fechas de entrada o salida en días no hábiles.
- **Tasa Global de Invalidez de Calendario:** **21 de 29 operaciones (72.4%)** ocurrieron en fines de semana o festivos bursátiles.

---

## 2. DETALLE DE OPERACIONES CON FECHAS INVÁLIDAS

### 2.1 Estrategia `MOM_TrendPullback_V1`:
| Trade ID | Fecha Entrada | Día Semana | Válido Entrada | Fecha Salida | Día Semana | Válido Salida | Causa de Invalidez |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `MOM_001` | 2020-04-06 | Lunes | SÍ | 2020-04-11 | **Sábado** | **NO** | Salida en fin de semana |
| `MOM_002` | 2020-04-12 | **Domingo** | **NO** | 2020-04-17 | Viernes | SÍ | Entrada en fin de semana (Domingo de Resurrección) |
| `MOM_003` | 2021-01-18 | **Lunes** | **NO** | 2021-01-23 | **Sábado** | **NO** | Entrada en Martin Luther King Jr. Day (Festivo NYSE) y salida en Sábado |
| `MOM_004` | 2021-02-25 | Jueves | SÍ | 2021-03-02 | Martes | SÍ | **VÁLIDA (Día Hábil)** |
| `MOM_005` | 2021-04-24 | **Sábado** | **NO** | 2021-04-29 | Jueves | SÍ | Entrada en fin de semana |
| `MOM_006` | 2022-01-17 | **Lunes** | **NO** | 2022-01-22 | **Sábado** | **NO** | Entrada en Martin Luther King Jr. Day (Festivo NYSE) y salida en Sábado |
| `MOM_007` | 2023-01-21 | **Sábado** | **NO** | 2023-01-26 | Jueves | SÍ | Entrada en fin de semana |
| `MOM_008` | 2023-02-01 | Miércoles | SÍ | 2023-02-06 | Lunes | SÍ | **VÁLIDA (Día Hábil)** |
| `MOM_009` | 2023-02-07 | Martes | SÍ | 2023-02-10 | Viernes | SÍ | **VÁLIDA (Día Hábil)** |
| `MOM_010` | 2023-03-03 | Viernes | SÍ | 2023-03-08 | Miércoles | SÍ | **VÁLIDA (Día Hábil)** |
| `MOM_011` | 2023-03-21 | Martes | SÍ | 2023-03-26 | **Domingo** | **NO** | Salida en fin de semana |

---

### 2.2 Estrategia `MR_RsiBollinger_V1`:
De las 18 operaciones de Reversión a la Media, 14 presentaron anomalías:
- Salidas en Domingo: `MR_001` (2020-05-03), `MR_003` (2020-06-21), `MR_005` (2020-07-19), `MR_007` (2020-08-16), `MR_009` (2021-05-09), `MR_012` (2021-05-23), `MR_013` (2021-06-06), `MR_017` (2022-07-17).
- Entradas en Domingo / Sábado: `MR_002` (2020-05-17), `MR_006` (2020-08-08), `MR_011` (2021-05-16).
- Operaciones en Festivos Oficiales:
  - `MR_004`: Salida el 2020-07-03 (Viernes, día festivo observado por el 4 de Julio en NYSE).
  - `MR_015`: Entrada el 2021-07-05 (Lunes, día festivo observado por el 4 de Julio en NYSE).

---

## 3. IMPACTO FINANCIERO DE LA FUGA DE CALENDARIO

1. **Distorsión del Período de Tenencia:** Un `TIME_EXIT` de 5 barras en una serie de calendario continuo equivale a 5 días cronológicos (ej. entra lunes, sale sábado). En el mercado real, un horizonte de 5 sesiones bursátiles dura **7 días cronológicos** al abarcar el fin de semana.
2. **Riesgo de Gap de Fin de Semana Oculto:** El modelo sintético asumió continuidad de precios entre viernes y sábado, y entre sábado y domingo, ignorando los gaps de apertura del lunes provocados por noticias de fin de semana.
3. **Conclusión de Integridad:** Las 29 operaciones del benchmark sintético son **`METODOLÓGICAMENTE INVÁLIDAS`** para representar ejecuciones bursátiles reproducibles.

---

## 4. VERIFICACIÓN Y VALIDACIÓN EN LA SERIE REAL DE `SPY`

Para asegurar la integridad del marco de investigación hacia adelante, se auditó la serie real de 1,200 barras de `SPY` (2022 a 2026):
- **Barras Auditadas:** 1,200 sesiones.
- **Validación con `market_calendar.is_trading_day()`:** **1,200 de 1,200 válidas (100%)**.
- **Operaciones Generadas en Serie Real:**
  - `MOM_TrendPullback_V1`: 2 operaciones. **100% en días hábiles**.
  - `MR_RsiBollinger_V1`: 22 operaciones. **100% en días hábiles**.
- **Invariante Institucional Establecido:** A partir de la Fase 7.1A, todo backtest en el Strategy Laboratory debe validar cada barra contra `market_calendar.is_trading_day()`. Cualquier barra que caiga en fin de semana o festivo será rechazada en tiempo de compilación.
