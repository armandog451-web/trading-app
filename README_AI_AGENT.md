# 🛡️ AI Trading Agent 1.0 (SuperRobot Core)

Motor algorítmico cuantitativo modular, auditable y seguro para análisis y paper trading de acciones estadounidenses.

> **Objetivo Actual:** `ANALYSIS_ONLY` y `PAPER_TRADING`.  
> **Seguridad:** Cero ejecución con dinero real habilitada por diseño.

---

## 🏛️ Arquitectura del Monolito Modular

El sistema implementa un flujo de datos estrictamente unidireccional y desacoplado:

```
Data Platform (Synthetic / Validation)
             ↓
Indicators & Market Regime Engine
             ↓
Strategy Engine (Trend & Momentum)
             ↓
Signal Aggregator & No-Trade Engine
             ↓
Deterministic Risk Engine (Position Sizing & Circuit Breakers)
             ↓
Operating Mode Gate (ANALYSIS_ONLY vs PAPER_TRADING)
             ↓
Paper Execution Broker (Slippage & Commissions)
             ↓
Portfolio Monitor (Dynamic Break-Even +1.0R)
             ↓
Trade Journal (Trazabilidad inmutable por decision_id)
```

---

## 🚀 Ejecución de Pruebas Automatizadas (Fase 1)

El proyecto cuenta con una suite completa de pruebas unitarias, de integración y de seguridad que opera **100% offline**, sin requerir conexión a internet ni credenciales externas:

```bash
python run_agent_tests.py
```

O directamente mediante `pytest`:

```bash
pytest ai_trading_agent/tests -v
```

---

## 🔒 Reglas de Seguridad Inviolables

1. **Modo `ANALYSIS_ONLY` por defecto:** Si el modo está configurado en `ANALYSIS_ONLY`, el motor de ejecución (`PaperBroker`) lanza físicamente una excepción `PermissionError` ante cualquier intento de enviar una orden.
2. **Deterministic Risk Engine:**
   * Dimensionamiento exacto basado en el 1% del capital por operación.
   * Ratio Riesgo/Beneficio mínimo estricto de 1:2.
   * Freno de emergencia diario (*Circuit Breaker* -2.0%).
   * Límite de exposición máxima del 15% por activo.
3. **No-Trade Engine:** Si dos estrategias emiten señales contradictorias (por ejemplo, una COMPRA y otra VENTA), el agregador emite inmediatamente `NO_TRADE`.
4. **Trazabilidad Inmutable:** Cada decisión genera un `decision_id` único (UUID) que permite reconstruir todo el árbol de decisión en el `TradeJournal`.

---

## 📁 Estructura del Código

```
ai_trading_agent/
├── config/
│   └── settings.py              # Configuración tipada (Pydantic Settings)
├── domain/
│   ├── enums.py                 # Enumeraciones (MarketRegime, TradingMode, etc.)
│   └── models.py                # Modelos de dominio inmutables Pydantic
├── data/
│   ├── validation.py            # Validador de física de precios y gaps
│   └── synthetic.py             # Generador determinista reproducible
├── market/
│   ├── indicators.py            # SMA, EMA, RSI, MACD, ATR, VWAP, Bollinger, RVOL
│   └── regime.py                # Clasificador de régimen de mercado
├── strategies/
│   ├── base.py                  # Interfaz BaseStrategy
│   ├── trend.py                 # Trend Following (EMA + VWAP + R:R 1:2)
│   └── momentum.py              # Momentum (RSI + MACD + RVOL)
├── signals/
│   └── aggregator.py            # Agregador y No-Trade Engine
├── risk/
│   └── engine.py                # Deterministic Risk Engine & Position Sizing
├── execution/
│   ├── interfaces.py            # BrokerInterface
│   └── paper_broker.py          # Paper Broker con slippage y comisiones
├── portfolio/
│   └── monitor.py               # Monitor con Auto Break-Even (+1.0R)
├── journal/
│   └── trade_journal.py         # Registro inmutable por decision_id
├── orchestrator.py              # Orquestador end-to-end del pipeline
└── tests/                       # Suite de pruebas pytest (15/15 pasando)
```
