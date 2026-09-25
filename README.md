# TradingPulse Demo

## Overview

**TradingPulse** is a simple algorithmic trading engine built in pure Python. It demonstrates:

- Real‑time market data ingestion via a mock **Moomoo OpenD** TCP server.
- An **Opening Range Breakout (ORB)** strategy with configurable opening window (`OPEN_MINUTES`).
- Centralised configuration using a `Settings` class (environment variables via `.env`).
- Structured JSON logging with **structlog**.
- Trade persistence to a local SQLite database.
- Optional Telegram notifications (place‑holder implementation).
- Docker container support for easy reproducibility.

The demo runs for a short period (30 s) to allow the 1‑minute opening window to complete and potentially generate a breakout signal.

---

## Prerequisites

- **Windows** (the project is set up for Windows paths).
- Python **3.11** installed and accessible as `python` (or adjust the Dockerfile for another interpreter).
- (Optional) Docker installed if you want to run the demo in a container.

---

## Quick Start (local)

1. **Clone the repository** (or copy the project folder) to a location on your machine.
2. **Create a `.env` file** – copy the example provided:
   ```
   cp .env.example .env   # or manually create .env in the project root
   ```
   Fill in any real credentials you wish to use (Telegram bot token, Alpaca keys, etc.). For the demo you can leave them empty.
3. **Install dependencies**:
   ```
   pip install structlog pydantic pydantic-settings httpx
   ```
   (If you add a `requirements.txt` you can `pip install -r requirements.txt`.)
4. **Start the mock OpenD server** (runs in the background):
   ```
   python backend/mock_opend_server.py
   ```
   The server will emit a synthetic tick for each symbol every second.
5. **Run the engine**:
   ```
   python backend/run_test_engine.py
   ```
   You should see JSON logs indicating the connection, opening‑range calculation, any breakout signals, order placement, and trade persistence.
6. **Inspect persisted trades** (optional):
   ```
   sqlite3 backend/trade_engine.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"
   ```
   You will see rows with `symbol`, `side`, `price`, `size`, `stop_loss`, and timestamps.

---

## Docker

A minimal Docker image is provided. To build and run:
```bash
# Build the image
docker build -t tradingpulse .

# Run the container (the mock server is started automatically as a daemon in the background)
docker run --rm tradingpulse
```
The container executes `backend/run_test_engine.py` by default.

---

## Configuration

All configurable values are defined in `backend/app/config.py` and can be overridden via the `.env` file:

| Variable | Description |
|---|---|
| `MOOMOO_HOST` / `MOOMOO_PORT` | Host/port of the mock OpenD server (default `127.0.0.1:11111`). |
| `OPEN_MINUTES` | Length of the opening‑range window (default **1** minute). |
| `VOLUME_MULTIPLIER` | Volume multiplier used by the ORB strategy. |
| `RISK_PER_TRADE_PCT` | Percentage of capital risked per trade (default **1%**). |
| `MAX_DAILY_LOSS_PCT` | Maximum daily draw‑down as a percent of capital (default **2%**). |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Telegram credentials for notifications. |
| `DATABASE_URL` | SQLite DB path (default points to `backend/trade_engine.db`). |

---

## Extending the Demo

- **Real broker integration** – replace `MoomooBroker` with a concrete broker wrapper (Alpaca, Interactive Brokers, etc.).
- **Additional strategies** – implement new strategy classes in `backend/app/strategies/` and register them in `ExecutionEngine`. 
- **Metrics** – uncomment the optional Prometheus metrics in `run_test_engine.py` to expose `/metrics` on port 8001.

---

## License

This demo code is provided for educational purposes and is not intended for production trading without thorough testing and risk assessment.
