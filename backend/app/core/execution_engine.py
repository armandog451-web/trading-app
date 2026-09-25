import asyncio
import structlog
from ..config import settings
from datetime import datetime
from typing import Callable, Any

from .real_time_connection import MoomooOpenDConnection
from .risk_gate import RiskGate
from ..strategies.orb_strategy import OpeningRangeBreakout
from ..core.moomoo_client import MoomooBroker
from ..core.alpaca_client import AlpacaBroker
from ..core.telegram_listener import TelegramNotifier
from ..repository.trade_repository import TradeRepository

logger = structlog.get_logger(__name__)

class ExecutionEngine:
    """Central orchestrator for TradingPulse.

    Responsibilities
    ----------------
    1. Maintain a live connection to Moomoo OpenD and receive ticks.
    2. Feed ticks to the ORB strategy.
    3. When the strategy emits a breakout signal, invoke the :class:`RiskGate`
       to compute position size and stop‑loss.
    4. Submit the order through :class:`MoomooBroker`.
    5. Notify the user via Telegram (order placed, execution result, etc.).
    """

    def __init__(
        self,
        symbols: list[str],
        broker: Any,  # MoomooBroker or AlpacaBroker
        telegram_notifier: TelegramNotifier,
        capital_provider: Callable[[], float],
        atr_provider: Callable[[str], float] | None = None,
    ) -> None:
        self.symbols = symbols
        self.broker = broker
        self.notifier = telegram_notifier
        self.trade_repo = TradeRepository()
        self.risk_gate = RiskGate(
            capital_provider=capital_provider,
            atr_provider=atr_provider,
            max_risk_per_trade=settings.RISK_PER_TRADE_PCT / 100 if hasattr(settings, "RISK_PER_TRADE_PCT") else 0.01,
            daily_drawdown_limit=settings.MAX_DAILY_LOSS_PCT / 100 if hasattr(settings, "MAX_DAILY_LOSS_PCT") else 0.02,
        )
        self.strategy = OpeningRangeBreakout(symbols=symbols)
        self.conn = MoomooOpenDConnection(
            host=settings.MOOMOO_HOST,
            port=settings.MOOMOO_PORT,
            subscription_symbols=symbols,
            on_tick=self._on_tick,
        )
        self._loop = asyncio.get_event_loop()
        self._running = False
        # Simple in‑memory queue for signals
        self._signal_queue: asyncio.Queue = asyncio.Queue()

    async def start(self) -> None:
        """Start the engine – launch the socket task and the signal processor."""
        self._running = True
        logger.info("Starting ExecutionEngine for %s", ", ".join(self.symbols))
        # Run the OpenD connection in background
        asyncio.create_task(self.conn.start())
        # Run the signal consumer
        asyncio.create_task(self._process_signals())
        # Wait until the connection is ready before proceeding
        await self.conn.wait_until_ready()
        logger.info("OpenD connection ready – engine fully operational")

    async def stop(self) -> None:
        """Gracefully shut down the engine."""
        self._running = False
        await self.conn.stop()
        logger.info("ExecutionEngine stopped")

    # ---------------------------------------------------------------------
    # Tick handling
    # ---------------------------------------------------------------------
    def _on_tick(self, tick: dict) -> None:
        """Callback from :class:`MoomooOpenDConnection`.
        The tick dict is transformed into the minimal format expected by the
        strategy (mid price, volume, timestamp).
        """
        # Convert OpenD tick to generic format
        try:
            mid_price = (tick["bid"] + tick["ask"]) / 2.0
            volume = tick["bidSize"] + tick["askSize"]
            generic_tick = {
                "symbol": tick["symbol"],
                "mid": mid_price,
                "volume": volume,
                "timestamp": datetime.utcnow(),
            }
            self.strategy.on_tick(generic_tick)
        except Exception as exc:
            logger.exception("Failed to translate OpenD tick %s: %s", tick, exc)

    # ---------------------------------------------------------------------
    # Signal handling – the strategy currently logs the signal. We'll intercept
    # by monkey‑patching the logger. For a clean design the strategy would expose
    # a callback; here we add one dynamically.
    # ---------------------------------------------------------------------
    async def _process_signals(self) -> None:
        """Consume breakout signals emitted by the strategy.
        In this implementation we listen to the logger of ``OpeningRangeBreakout``
        and push a tuple ``(symbol, side, price)`` onto the internal queue.
        """
        # Attach a custom logging handler to capture signals
        handler = _SignalLoggingHandler(self._signal_queue)
        logger_adapter = logging.getLogger("backend.app.strategies.orb_strategy")
        logger_adapter.addHandler(handler)
        logger_adapter.setLevel(logging.INFO)
        while self._running:
            try:
                signal = await asyncio.wait_for(self._signal_queue.get(), timeout=1.0)
                await self._handle_signal(*signal)
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.exception("Error processing signal: %s", exc)

    async def _handle_signal(self, symbol: str, side: str, price: float) -> None:
        """Validate risk, place order and notify via Telegram."""
        logger.info("Handling ORB signal %s %s @ %.4f", side, symbol, price)
        validation = await self.risk_gate.validate_and_size(entry_price=price, symbol=symbol, side=side)
        if validation is None:
            await self.notifier.send_message(
                f"⚠️ Trade blocked for {symbol} – risk limits exceeded or ATR missing."
            )
            return
        size = validation["size"]
        stop = validation["stop_loss"]
        # Build order payload – the broker client expects a dict; adjust as needed
        order = {
            "symbol": symbol,
            "price": price,
            "size": size,
            "side": side.lower(),  # "buy"/"sell" expected by Mo​mo​o API
            "stop_loss": stop,
            "take_profit": None,  # can be extended later
        }
        try:
            order_id = await self.broker.send_order(order)
            # Persist trade details
            self.trade_repo.save_trade(
                order_id=order_id,
                symbol=symbol,
                side=side.upper(),
                price=price,
                size=size,
                stop_loss=stop,
            )
            await self.notifier.send_message(
                f"📈 *Orden {side}* {symbol} @ {price:.2f}\n"
                f"Tamaño: {size} contrato(s)\n"
                f"Stop‑Loss: {stop:.2f if stop else 'N/A'}\n"
                f"ID: `{order_id}`"
            )
            # Record profit/loss later – broker will push execution updates that can be
            # hooked into `record_trade_result` of the risk gate.
        except Exception as exc:
            logger.exception("Order submission failed: %s", exc)
            await self.notifier.send_message(
                f"❌ Falló la orden {side} {symbol} @ {price:.2f}: {exc}"
            )

# -------------------------------------------------------------------------
# Helper logging handler to capture strategy signals
# -------------------------------------------------------------------------
class _SignalLoggingHandler(logging.Handler):
    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        # Expected message format from OpeningRangeBreakout: "ORB signal LONG AAPL @ 172.34"
        try:
            msg = record.getMessage()
            if not msg.startswith("ORB signal"):
                return
            parts = msg.split()
            # parts[2] = side, parts[3] = symbol, parts[5] = price
            side = parts[2]
            symbol = parts[3]
            price = float(parts[5])
            # Push to the queue; asyncio.Queue is thread‑safe for this scenario
            asyncio.get_event_loop().call_soon_threadsafe(self.queue.put_nowait, (symbol, side, price))
        except Exception:
            pass

# -------------------------------------------------------------------------
# Example entry‑point (can be used by `python -m trading_app.core.execution_engine`)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    # Minimal bootstrap – replace with your actual implementations
    from ..core.moomoo_client import MoomooBroker
    from ..core.telegram_listener import TelegramNotifier

    async def capital_provider() -> float:
        acc = await MoomooBroker().get_account()
        return acc.get("equity", 0.0)

    async def atr_provider(symbol: str) -> float:
        # Placeholder – you would calculate ATR from recent bars, perhaps via a\n        # historical data cache.
        return 0.5

    broker = MoomooBroker()
    notifier = TelegramNotifier()
    engine = ExecutionEngine(
        symbols=["QQQ", "SPY", "TSLA", "AAPL", "MSFT"],
        broker=broker,
        telegram_notifier=notifier,
        capital_provider=lambda: asyncio.run(capital_provider()),
        atr_provider=lambda s: asyncio.run(atr_provider(s)),
    )
    asyncio.run(engine.start())
    # Keep the process alive – in production you would have proper shutdown logic
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        asyncio.run(engine.stop())
