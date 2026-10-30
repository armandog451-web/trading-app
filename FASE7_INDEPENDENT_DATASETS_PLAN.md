# PLAN DE DATASETS INDEPENDIENTES (FASE 7.0)
## GOBERNANZA DE DATOS, AISLAMIENTO TEMPORAL Y PREVENCIÓN DE CONTAMINACIÓN

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.0 — Plan de Datasets Independientes  
**Objetivo:** Establecer particiones temporales estancas y trazables para evitar sobreajuste y sesgo de supervivencia.  

---

## 1. TAXONOMÍA Y AISLAMIENTO DE PARTICIONES

Para dar estricto cumplimiento al mandato de la Fase 7.0, se dividen los datos de mercado en tres particiones con niveles de acceso diferenciados:

```
[2018-01-01] ──────────────────────────────────────────► [2024-12-31]
  PARTICIÓN 1: HISTÓRICO EXPLORATORIO EXAMINADO (Fases 1 a 6)
  • Uso: Calibración de parámetros e investigación inicial en Strategy Lab.
  • Estado: EXAMINADO PREVIAMENTE.

[2025-01-01] ──────────────────────────────────────────► [2026-10-05]
  PARTICIÓN 2: HOLDOUT HISTÓRICO EXAMINADO (Fase 10)
  • Uso: Comparación y auditoría de invariantes históricas.
  • Estado: EXAMINADO PREVIAMENTE (Prohibido reclasificar como "out-of-sample limpio").

[2026-10-21] ──────────────────────────────────────────► [En adelante]
  PARTICIÓN 3: PROSPECTIVO GENUINO NO EXAMINADO
  • Uso: Observación prospectiva pasiva (Shadow Research).
  • Estado: GENUINAMENTE NO EXAMINADO (Recolección día a día post-cierre).
```

---

## 2. UNIVERSO DE ACTIVOS Y FUENTES DE INFORMACIÓN

### Universo de Investigación:
1. **Core Index ETFs:** `SPY` (S&P 500), `QQQ` (Nasdaq 100), `IWM` (Russell 2000), `DIA` (Dow Jones).
2. **Sectorial Liquid ETFs:** `XLF` (Financiero), `XLE` (Energía), `XLK` (Tecnología).

### Proveedores de Datos:
- **Datos Diarios Consolidados:** Moomoo Open API / Yahoo Finance Provider ([`yfinance_provider.py`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/data/providers/yfinance_provider.py)).
- **Ajustes Obligatorios:** Precios ajustados por dividendos y splits corporativos.
- **Ventana Mínima de Cálculo:** 80 barras previas requeridas para pre-cómputo seguro de $\text{SMA}(50)$, $\text{ADX}(14)$, $\text{ER}(20)$ y $\text{ATR}(14)$ con cero valores nulos.

---

## 3. PROTOCOLO DE PREVENCIÓN DE LOOK-AHEAD BIAS

Para impedir cualquier fuga de información del futuro hacia el pasado:
1. **Cálculo Determinista de Barra Cerrada:** Los indicadores y señales solo se computan a las 16:15 ET utilizando exclusivamente los datos consolidados de la barra que cerró a las 16:00 ET.
2. **Precios de Ejecución Simulados:** La entrada simulada ocurre al precio de cierre de la barra de señal más el deslizamiento de 5 bps, o en la apertura de la siguiente barra ($T+1$).
3. **Inmutabilidad de Fixtures:** Los datos históricos congelados en `ai_trading_agent/scratch/` no pueden ser modificados ni sobreescritos por scripts de backtesting.

---

## 4. REGISTRO Y REPRODUCIBILIDAD

Los resultados de cada simulación de la Fase 7.0 deben registrar:
- **Timestamp de Evaluación:** UTC ISO-8601.
- **Rango de Fechas Exacto:** Fecha inicial y final de la partición evaluada.
- **Semilla Aleatoria de Simulación:** Fija (`seed=42`) para componentes estocásticos o bootstrap.
- **Hash de Parámetros:** `SHA-256(json.dumps(parameters, sort_keys=True))` registrado en la salida de resultados.
