# PROTOCOLO DE INVESTIGACIÓN INSTITUCIONAL FASE 7
## EXPLORACIÓN CONTROLADA DE ESTRATEGIAS DE MOMENTUM Y REVERSIÓN A LA MEDIA

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.0 — Protocolo de Investigación Cuantitativa  
**Modo Operativo Obligatorio:** `ANALYSIS_ONLY` / `RESEARCH`  
**Conexión a Broker:** **ESTRICTAMENTE DESCONECTADO (AIR-GAPPED)**  
**Fecha:** 30 de Octubre de 2026  

---

## 1. PRINCIPIOS DE GOBERNANZA Y AISLAMIENTO

La Fase 7 tiene como objetivo investigar la viabilidad de nuevas familias de estrategias cuantitativas (Momentum y Mean Reversion) para complementar a D21 en horizontes temporales diarios y sub-diarios.

Para proteger la integridad del sistema operativo consolidado en la Fase 6.4, se establecen las siguientes restricciones innegociables:

1. **Aislamiento Total de Producción:** Todas las hipótesis, modelos y algoritmos de la Fase 7 se desarrollarán exclusivamente en el módulo `ai_trading_agent.lab` y `strategy_lab.py`.
2. **Sin Permisos de Ejecución:** Queda físicamente prohibido conectar cualquier estrategia de la Fase 7 al broker Moomoo (`TrdEnv.SIMULATE` o `REAL`), al `PaperFidelityEngine` o al motor de órdenes.
3. **Inmutabilidad de D21:** D21 continuará como la **única** estrategia autorizada en la campaña de validación PAPER. Ningún desarrollo de la Fase 7 podrá compartir bases de datos de órdenes, identificadores de estrategia o memoria de riesgo con D21.
4. **Modo Operativo:** El servidor operará en `ANALYSIS_ONLY`. La bandera `ENABLE_LIVE_TRADING` permanecerá en `False`.

---

## 2. TAXONOMÍA DE ESTRATEGIAS A INVESTIGAR

### Familia A: Momentum y Seguimiento de Tendencia
- **Objetivo:** Capturar expansiones de volatilidad y persistencia direccional tras roturas de niveles clave o consolidaciones prolongadas.
- **Universo de Activos:** ETFs de alta liquidez (`SPY`, `QQQ`, `IWM`, `XLF`, `XLE`, `XLK`) y acciones de gran capitalización.
- **Horizonte de Tenencia:** 3 a 10 días bursátiles (Swing Trading).
- **Indicadores Permitidos:** Medias móviles exponenciales adaptativas (KAMA/EMA), Canales de Donchian y volumen relativo ponderado.

### Familia B: Reversión a la Media (Mean Reversion)
- **Objetivo:** Explotar sobrerreacciones estadísticas a corto plazo en condiciones de mercado en rango o consolidación.
- **Universo de Activos:** ETFs indexados y pares cointegrados.
- **Horizonte de Tenencia:** 1 a 3 días bursátiles.
- **Indicadores Permitidos:** RSI de período corto (2 a 4 periodos), Bandas de Bollinger modificadas y Z-Score sobre desviación estándar móvil.

---

## 3. PROTOCOLO DE PARTICIÓN TEMPORAL Y CONTROL DE OVERFITTING

Para evitar el sobreajuste y la contaminación de datos (data snooping), toda estrategia candidata deberá evaluarse bajo el protocolo estricto de tres particiones temporales independientes:

```
┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
│     In-Sample (IS)      │    Out-of-Sample (OOS)  │    Blind Holdout (BH)   │
│       Entrenamiento     │       Validación        │       Auditoría         │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ 2018-01-01 a 2022-12-31 │ 2023-01-01 a 2024-12-31 │ 2025-01-01 a 2026-09-30 │
│   (Descubrimiento y     │   (Ajuste de umbrales   │  (Sello criptográfico   │
│   selección de bordes)  │   y test de robustez)   │   sin optimización)     │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

### Reglas de Evaluación:
1. **Sello del Blind Holdout:** Los datos de 2025-01-01 a 2026-09-30 están estrictamente congelados y solo podrán consultarse una única vez al finalizar el desarrollo.
2. **Degradación Máxima Aceptable:** La caída en el Sharpe Ratio o Profit Factor entre In-Sample y Out-of-Sample no debe exceder el $30\%$.
3. **Mínimo Estadístico:** Al menos 100 operaciones simuladas en el periodo completo para asegurar significancia estadística al $95\%$.

---

## 4. INTEGRACIÓN CON EL DETECTOR DE REGÍMENES V1

El Detector de Regímenes v1 (`RegimeDetectorV1`) operará como filtro de análisis analítico:
- **Regímenes Clasificados:** `BULL_TRENDING`, `BEAR_TRENDING`, `RANGING_LOW_VOL`, `RANGING_HIGH_VOL`.
- **Hipótesis a Contrastar:** Determinar si activar estrategias de Momentum exclusivamente en regímenes tendenciales y estrategias de Reversión en regímenes laterales mejora el Sharpe Ratio global respecto a estrategias no condicionadas.
- **Restricción:** El detector de regímenes solo generará etiquetas de clasificación para backtest analítico; no emitirá comandos al motor de ejecución.

---

## 5. CRITERIOS DE PROMOCIÓN A FASES POSTERIORES

Para que una estrategia candidata de la Fase 7 sea considerada para promoción a validación en PAPER (Fase 8/9):
1. **Profit Factor:** $\ge 1.50$ en In-Sample y $\ge 1.35$ en Out-of-Sample.
2. **Sharpe Ratio Anualizado:** $\ge 1.20$.
3. **Máximo Drawdown Simulado:** $\le 12.0\%$.
4. **Resistencia a Costes:** El borde debe ser positivo incluso aplicando comisiones de 0.005 USD/acción y deslizamiento de 5 bps.
5. **Cero Violaciones de Gobernanza:** Código fully unit-tested con cobertura $> 90\%$ y registro formal en el catálogo institucional.
