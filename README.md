# TradePulse: Institutional Quantitative Day Trading Engine

Sistema integral de trading algorítmico e intraday para Acciones y ETFs de EE.UU., estructurado bajo una **Arquitectura de Confluencia Jerárquica Top-Down** de 5 capas:

1. **Capa 1 (Macro & Política Monetaria)**: Monitoreo de tasas del Tesoro (10Y y 2Y), diferencial de la curva de rendimientos (inversión vs desinversión), tasa de fondos de la Fed, inflación CPI e índice DXY para establecer el sesgo macroeconómico (`BULLISH`, `BEARISH` o `NEUTRAL`).
2. **Capa 2 (Fundamentales & Earnings)**: Detección de sorpresas de beneficios (EPS), catalizadores corporativos y filtrado de acciones elegibles para Day Trading.
3. **Capa 3 (Sentimiento, VIX & Opciones)**: Medición del régimen de volatilidad con el índice VIX, ratio Put/Call de CBOE (detección de complacencia o pánico) y reporte COT de la CFTC (posicionamiento de dinero institucional en futuros).
4. **Capa 4 (Técnico, Liquidez & Volumen Intraday)**: Cálculo continuo de VWAP (con bandas de desviación estándar), detección de niveles estructurales de liquidez (*PDH, PDL, PMH, PML*), volumen relativo (RVOL) y barridos de liquidez (*Liquidity Sweeps*).
5. **Capa 5 (Motor de Riesgo & R:R)**:
   - **Circuit Breaker Diario**: Apagado automático de operaciones si se alcanza el límite de pérdida diaria (ej. -2%).
   - **Dimensionamiento al 1%**: Cálculo exacto del tamaño de lote según la distancia al Stop Loss.
   - **Filtro Estricto R:R**: Rechazo automático de setups con ratio menor a 1:2.
   - **Cierre Forzoso a las 15:50 EST**: Cierre automático de posiciones antes del cierre de mercado para evitar riesgo nocturno (overnight).

---

## Modos de Operación

- **Backtest Studio**: Simulador histórico con métricas cuantitativas completas: Win Rate, Profit Factor, Max Drawdown %, Ratio de Sharpe y Curva de Equidad interactiva.
- **Paper Trading en Vivo (Alpaca Paper)**: Conexión con la API oficial de Alpaca Markets en entorno simulado con Bracket Orders OCO nativas.
- **Trading Real (Alpaca Live)**: Ejecución con capital real activando las credenciales de producción.
- **Botón de Pánico**: Cancelación inmediata de todas las órdenes activas y cierre a mercado de todas las posiciones abiertas en un solo clic.

---

## Estructura del Proyecto

```
trading-app/
├── backend/
│   ├── app/
│   │   ├── engines/           # Módulos cuantitativos (Macro, Sentimiento, Técnico, Riesgo, Orquestador)
│   │   ├── core/              # Conector Alpaca, Escáner, Bot Runner y Notificador
│   │   ├── backtest/          # Motor de simulación histórica y cálculo de métricas
│   │   ├── models/            # Modelos SQLite SQLAlchemy y esquemas Pydantic
│   │   ├── api/               # Endpoints REST (Dashboard, Factores, Backtest, Settings)
│   │   └── main.py            # Servidor FastAPI
│   ├── tests/                 # Pruebas unitarias automatizadas con pytest
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/        # Cockpit, Gráfico TradingView, Radar Macro, Opciones, Screener
│   │   ├── services/api.js    # Conexión HTTP REST
│   │   └── App.jsx
│   └── package.json
├── start.ps1                  # Lanzador PowerShell conjunto
└── start.bat                  # Lanzador de doble clic para Windows
```

---

## Cómo Iniciar la Aplicación

### Opción 1: Con doble clic en Windows
Haz doble clic sobre el archivo **`start.bat`**.

### Opción 2: Desde la consola PowerShell
```powershell
.\start.ps1
```

- **Dashboard Web**: [http://localhost:5173](http://localhost:5173)
- **Documentación API FastAPI**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Configuración de Claves de API (Opcional)
La aplicación cuenta con emulación inteligente por defecto para poder probar el funcionamiento de inmediato.
Para conectar tus cuentas reales:
1. Haz clic en el icono de tuerca (**Configuración**) en la esquina superior derecha del Dashboard.
2. Ingresa tu **Alpaca API Key ID** y **Alpaca Secret Key**.
3. (Opcional) Activa alertas de Telegram ingresando tu Bot Token y Chat ID.
