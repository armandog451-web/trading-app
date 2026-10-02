import sys, os
# Ensure project root is in PYTHONPATH for module imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
import structlog
from backend.app.core.execution_engine import ExecutionEngine
from backend.app.core.moomoo_client import MoomooBroker
from backend.app.core.alpaca_client import AlpacaBroker
from backend.app.core.telegram_listener import TelegramNotifier
from backend.app.config import settings

logger = structlog.get_logger(__name__)

notifier = TelegramNotifier()

# Simple providers (could be replaced by real account queries)
async def capital_provider() -> float:
    # Fixed capital for demo; in prod replace with account equity query
    return 100_000.0

async def atr_provider(symbol: str) -> float:
    # Placeholder constant ATR for any symbol
    return 0.5

async def main():
    engine = ExecutionEngine(
        symbols=["AAPL", "TSLA"],
        broker=AlpacaBroker() if settings.ACTIVE_BROKER.upper() == "ALPACA" else MoomooBroker(),
        telegram_notifier=notifier,
        capital_provider=capital_provider,
        atr_provider=atr_provider,
    )
    await engine.start()
    # Run long enough for the 1‑min opening window and a breakout
    await asyncio.sleep(30)
    await engine.stop()

if __name__ == "__main__":
    asyncio.run(main())
