# data_feeds.py
import asyncio
import json
import logging
import ssl
from datetime import datetime, timezone

import backtrader as bt
import websockets

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Alpaca live data feed (WebSocket → Backtrader)
# ----------------------------------------------------------------------
class AlpacaLiveDataFeed(bt.feed.DataBase):
    """
    Backtrader data feed that receives live 1‑minute bars from Alpaca
    via its WebSocket API.
    --------------------------------------------------------------------
    Parameters
    --------------------------------------------------------------------
    api_key          – Alpaca API key (paper)
    api_secret       – Alpaca API secret (paper)
    base_url         – ``https://paper-api.alpaca.markets`` (default)
    symbols          – list of ticker symbols, e.g. ["AAPL","MSFT"]
    timeframe        – ``bt.TimeFrame.Minutes`` (fixed to 1‑min bars)
    --------------------------------------------------------------------
    Usage
    --------------------------------------------------------------------
    feed = AlpacaLiveDataFeed(
        api_key=ALPACA_API_KEY,
        api_secret=ALPACA_API_SECRET,
        base_url=ALPACA_BASE_URL,
        symbols=["AAPL", "MSFT", "SPY"]
    )
    cerebro.adddata(feed)
    """
    params = (
        ("api_key", None),
        ("api_secret", None),
        ("base_url", "https://paper-api.alpaca.markets"),
        ("symbols", []),
        ("timeframe", bt.TimeFrame.Minutes),   # 1‑minute bars
        ("compression", 1),
    )

    def __init__(self):
        super().__init__()
        self._loop = asyncio.get_event_loop()
        self._ws = None
        self._connected = False
        self._queue = asyncio.Queue()
        self._task = None

    # --------------------------------------------------------------
    # Backtrader required methods
    # --------------------------------------------------------------
    def start(self):
        """Called by Backtrader when the engine starts."""
        self._task = self._loop.create_task(self._run())
        logger.info("AlpacaLiveDataFeed started – connecting to websocket…")

    def stop(self):
        """Called by Backtrader when the engine stops."""
        if self._task:
            self._task.cancel()
        logger.info("AlpacaLiveDataFeed stopped")

    def _load(self):
        """Backtrader calls ``_load`` each time it needs the next bar.
        We block (with a short timeout) until a bar is available in the queue.
        """
        try:
            bar = self._loop.run_until_complete(
                asyncio.wait_for(self._queue.get(), timeout=5.0)
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            return False

        self.datetime[0] = bar["datetime"]
        self.open[0] = bar["open"]
        self.high[0] = bar["high"]
        self.low[0] = bar["low"]
        self.close[0] = bar["close"]
        self.volume[0] = bar["volume"]
        self.openinterest[0] = 0
        return True

    # --------------------------------------------------------------
    # Async websocket handling
    # --------------------------------------------------------------
    async def _run(self):
        endpoint = "wss://stream.data.alpaca.markets/v2/iex"
        auth_msg = {
            "action": "authenticate",
            "data": {"key_id": self.p.api_key, "secret_key": self.p.api_secret},
        }
        subscribe_msg = {
            "action": "listen",
            "data": {"streams": [f"T.{sym}" for sym in self.p.symbols]},
        }

        while True:
            try:
                async with websockets.connect(
                    endpoint, ssl=ssl.SSLContext(), ping_interval=20, max_size=2 ** 20
                ) as ws:
                    self._ws = ws
                    await ws.send(json.dumps(auth_msg))
                    auth_resp = json.loads(await ws.recv())
                    if auth_resp.get("error"):
                        logger.error(f"Alpaca auth error: {auth_resp['error']}")
                        return
                    logger.info("Alpaca websocket authenticated")

                    await ws.send(json.dumps(subscribe_msg))
                    sub_resp = json.loads(await ws.recv())
                    if sub_resp.get("error"):
                        logger.error(f"Alpaca subscribe error: {sub_resp['error']}")
                        return
                    logger.info(f"Subscribed to: {self.p.symbols}")

                    async for message in ws:
                        data = json.loads(message)
                        for bar in data.get("data", []):
                            ts = int(bar["t"]) / 1_000_000_000
                            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                            bar_dict = {
                                "datetime": bt.date2num(dt),
                                "open": float(bar["o"]),
                                "high": float(bar["h"]),
                                "low": float(bar["l"]),
                                "close": float(bar["c"]),
                                "volume": float(bar["v"]),
                            }
                            await self._queue.put(bar_dict)

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(
                    f"Alpaca websocket closed ({e.code}): {e.reason}. Reconnecting in 5 s…"
                )
                await asyncio.sleep(5)
                continue
            except Exception as exc:
                logger.exception(f"Unexpected error in AlpacaLiveDataFeed: {exc}")
                await asyncio.sleep(5)
                continue

# ----------------------------------------------------------------------
# Moomoo live data feed – placeholder (to be completed when SDK is ready)
# ----------------------------------------------------------------------
class MoomooLiveDataFeed(bt.feed.DataBase):
    """Stub for Moomoo live data. Replace with real SDK calls when available.
    The public interface (attributes set in ``_load``) must be identical to
    ``AlpacaLiveDataFeed``.
    """
    params = (
        ("api_key", None),
        ("api_secret", None),
        ("symbols", []),
        ("timeframe", bt.TimeFrame.Minutes),
        ("compression", 1),
    )

    def start(self):
        raise NotImplementedError(
            "MoomooLiveDataFeed not implemented – install the Moomoo SDK and "
            "replace this class with a real implementation."
        )
