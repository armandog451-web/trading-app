import socket
import asyncio
import logging
from typing import List, Dict, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class MoomooOpenDConnection:
    """Manage a persistent TCP connection to Moomoo OpenD.

    Parameters
    ----------
    host: str
        Hostname or IP of the OpenD server (default ``127.0.0.1``).
    port: int
        TCP port (default ``11111``).
    subscription_symbols: List[str]
        Symbols to subscribe for Level‑1/Level‑2 data.
    reconnection_interval: int
        Seconds to wait before attempting reconnection after a failure.
    on_tick: Callable[[dict], None]
        Callback invoked for each received tick/message.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11111,
        subscription_symbols: List[str] | None = None,
        reconnection_interval: int = 5,
        on_tick: Callable[[dict], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.subscription_symbols = subscription_symbols or []
        self.reconnection_interval = reconnection_interval
        self.on_tick = on_tick or (lambda msg: None)
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = asyncio.Event()
        self._stop = False

    async def start(self) -> None:
        """Entry point for the background task.

        It continuously tries to keep the socket alive, reconnecting as needed.
        """
        while not self._stop:
            try:
                logger.info("Connecting to Moomoo OpenD %s:%s", self.host, self.port)
                self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
                self._connected.set()
                logger.info("Connected to OpenD – subscribing symbols")
                await self._subscribe_symbols()
                await self._receive_loop()
            except (ConnectionError, OSError) as exc:
                logger.warning("OpenD connection lost: %s – retry in %s s", exc, self.reconnection_interval)
                self._connected.clear()
                await asyncio.sleep(self.reconnection_interval)
            finally:
                await self._close()

    async def stop(self) -> None:
        """Gracefully stop the connection task."""
        self._stop = True
        await self._close()
        self._connected.clear()

    async def _close(self) -> None:
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
        self._reader = None

    async def _subscribe_symbols(self) -> None:
        """Send a simple subscription protocol to OpenD.

        The real OpenD protocol is binary; here we emit a JSON‑like line for the
        sake of illustration. Replace with the official request format if
        available.
        """
        for symbol in self.subscription_symbols:
            msg = f"SUBSCRIBE|{symbol}\n".encode("utf-8")
            self._writer.write(msg)
        await self._writer.drain()

    async def _receive_loop(self) -> None:
        """Read messages from OpenD and forward them to ``on_tick``.

        The implementation assumes a newline‑delimited JSON payload. Adjust the
        parsing logic to match the actual binary protocol.
        """
        while not self._stop:
            line = await self._reader.readline()
            if not line:
                raise ConnectionError("Socket closed by peer")
            try:
                # Very light‑weight parsing – replace with proper protobuf/flatbuffer
                payload = line.decode("utf-8").strip()
                # Expected format: "TICK|SYMBOL|bid|ask|bidSize|askSize|..."
                parts = payload.split("|")
                if parts[0] == "TICK":
                    tick = {
                        "symbol": parts[1],
                        "bid": float(parts[2]),
                        "ask": float(parts[3]),
                        "bidSize": int(parts[4]),
                        "askSize": int(parts[5]),
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                    self.on_tick(tick)
            except Exception as exc:
                logger.exception("Failed to parse OpenD message %s: %s", line, exc)

    async def wait_until_ready(self) -> None:
        """Block until the socket is connected and subscribed."""
        await self._connected.wait()

    # Helper for external callers -------------------------------------------------
    async def get_latest_snapshot(self, symbol: str) -> dict | None:
        """Return the most recent tick for *symbol* if cached.

        Sub‑classes may implement an internal LRU cache. For brevity we expose the
        callback‑only interface; callers can keep their own state.
        """
        return None  # placeholder – extend as needed
