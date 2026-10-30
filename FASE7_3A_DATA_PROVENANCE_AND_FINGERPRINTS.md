# ORACLEBOT V2 — FASE 7.3A
# INFORME DE PROVENIENCIA DE DATOS, CALENDARIO BURSÁTIL Y HASHES CRIPTOGRÁFICOS

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Módulo:** `ai_trading_agent.strategy_lab.discovery`  
**Fecha de auditoría:** 30 de octubre de 2026  
**Auditoría de datos:** 1,199 barras cerradas por activo (2022-01-20 a 2026-10-29)

---

## 1. ESPECIFICACIÓN DEL UNIVERSO DE ACTIVOS Y PROVENIENCIA

La investigación y validación del Strategy Discovery Engine v2 se apoya en un universo institucional diversificado de 6 fondos cotizados (ETFs) de máxima liquidez:

1. **SPY:** SPDR S&P 500 ETF Trust (Mercado general de gran capitalización).
2. **QQQ:** Invesco QQQ Trust (Tecnología y crecimiento Nasdaq-100).
3. **IWM:** iShares Russell 2000 ETF (Pequeña capitalización y sensibilidad cíclica).
4. **DIA:** SPDR Dow Jones Industrial Average ETF (Industria y valor tradicional).
5. **XLF:** Financial Select Sector SPDR Fund (Sector bancario y financiero).
6. **XLE:** Energy Select Sector SPDR Fund (Sector energético y materias primas).

### 1.1 Fuente y Precios de Mercado
- **Proveedor primario:** API oficial de Yahoo Finance (`yfinance_provider`).
- **Naturaleza de las series:** Precios de cierre diarios dividendo-ajustados (`Adj Close`), reconciliados con splits y distribuciones corporativas.
- **Ventana temporal:** 2022-01-20 a 2026-10-29.
- **Conteo exacto por activo:** 1,199 barras diarias completas.

---

## 2. AUDITORÍA DE CALENDARIO NYSE Y ELIMINACIÓN DE BARRAS NO CERRADAS

Para prevenir el sesgo más común en investigación cuantitativa (*lookahead bias* e inconsistencia de datos intradía), el motor cuenta con una compuerta estricta: `DataIntegrityGate`.

### 2.1 Verificación de Cierre y Descarte de la Barra 2026-10-30
Durante la sesión de hoy (30 de octubre de 2026), los mercados se encuentran abiertos y operando. Cualquier barra con marca temporal del `2026-10-30` refleja únicamente precios intradía en evolución y no un precio de cierre definitivo.
- **Acción del DataIntegrityGate:** Todo registro con fecha igual o posterior a la sesión en curso antes de las 16:00 ET es interceptado y purgado automáticamente.
- **Auditoría Forense de Fase 7.2 y 7.3:** Se confirmó mediante auditoría retrospectiva que 0 órdenes y 0 señales se generaron en la barra del `2026-10-30`. El conjunto de datos cerrado finaliza taxativamente en el `2026-10-29`.

### 2.2 Validación de Calendario NYSE/Nasdaq
Todas las marcas temporales se contrastaron con el calendario bursátil de Estados Unidos:
- **Días festivos validados:** Martin Luther King Jr. Day, Washington's Birthday (Presidents' Day), Good Friday, Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving Day y Christmas Day.
- **Cierres anticipados (13:00 ET):** Black Friday y vísperas festivas verificadas sin gaps anómalos.
- **Continuidad de fines de semana:** Ninguna barra contiene marcas temporales en sábado ni domingo.

---

## 3. HASHES SHA-256 INMUTABLES DE LOS DATASETS SANEADOS

A continuación se registran los fingerprints criptográficos calculados sobre el contenido CSV estandarizado de cada serie temporal saneada:

| Activo | Total Barras Cerradas | Fecha Inicial | Fecha Final | Hash SHA-256 Completo del Dataset |
| :--- | :---: | :---: | :---: | :--- |
| **SPY** | 1,199 | 2022-01-20 | 2026-10-29 | `9f199dfcf0aa8f9f7831d0537be6c0aa5e5ba79b3240f930e620dbfa87494f6c` |
| **QQQ** | 1,199 | 2022-01-20 | 2026-10-29 | `726d6b40dd294b2c2eafe8ba4e4ca06706019313ea32cb5e69bf8d3a12a762c2` |
| **IWM** | 1,199 | 2022-01-20 | 2026-10-29 | `d25bcde3e3bbd84ca4a3ff0d645ef59bb4b2a8d3883a9ce4255776d6349c25f8` |
| **DIA** | 1,199 | 2022-01-20 | 2026-10-29 | `5e2b0091e0a4e60df244d79da933ba0c090623a31e843f545a90e3ebcb3d629a` |
| **XLF** | 1,199 | 2022-01-20 | 2026-10-29 | `d3c22b78983dbd4d03e9ea4c7fc55a80800d9894e637775ae7a8c886c99c6827` |
| **XLE** | 1,199 | 2022-01-20 | 2026-10-29 | `0522bfc2c2c3d8f48c1e9fa83ba5c4325a39282513c83f1a8cfe52b6fac64ac0` |

---

## 4. FINGERPRINTS DE CÓDIGO Y ESTRATEGIAS CANDIDATAS

Para garantizar que el código de investigación permanezca inalterado tras la auditoría, se computan los hashes SHA-256 de las especificaciones canónicas:

| Hipótesis ID | Estrategia ID | Fingerprint Canónico (SHA-256 truncado a 16 hex) |
| :--- | :--- | :--- |
| **H-MOM-REL-1** | `CS_RelMom_60d_V1` | `165345c108cdefb9` |
| **H-MOM-REL-2** | `CS_RelMom_VolAdj_V2` | `7460c8f0c2373832` |
| **H-MR-VOL-1** | `MR_VolCond_ZScore_V1` | `adf4788b0f20132a` |
| **H-MR-VOL-2** | `MR_VolCond_BBCompression_V2` | `68d2ea20522ef5e0` |

Cualquier alteración futura en tesis conceptual o hiperparámetros alterará el fingerprint, invalidando automáticamente la certificación previa.
