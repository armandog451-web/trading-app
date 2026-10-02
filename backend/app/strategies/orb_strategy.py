import asyncio
import logging
from datetime import datetime, time, timedelta
from collections import defaultdict
from typing import Callable

logger = logging.getLogger(__name__)

class OpeningRangeBreakout:
    """Calculate opening range and generate breakout signals.

    Parameters
    ----------
    symbols: list[str]
        List of symbols to monitor.
    open_minutes: int
        Length of the opening window in minutes (default 15).
    volume_multiplier: float
        Minimum volume factor compared to the rolling average volume.
    """

from ..config import settings

    def __init__(self, symbols, open_minutes=None, volume_multiplier=None):
        # If not provided, use values from centralized Settings (demo-friendly)
        self.symbols = symbols
        self.open_minutes = open_minutes if open_minutes is not None else settings.OPEN_MINUTES
        self.volume_multiplier = volume_multiplier if volume_multiplier is not None else settings.VOLUME_MULTIPLIER
        # Store per‑symbol data: list of (price, volume, timestamp)
        self._ticks = defaultdict(list)
        # Cache opening range per day
        self._daily_range = {}
        self._session_start = None


    def _session_bounds(self) -> tuple[datetime, datetime]:
        """Compute NY session start/end for today (09:30‑16:00 EDT).
        For simplicity we use local time assuming the host runs in EDT.
        """
        now = datetime.now()
        start = datetime.combine(now.date(), time(9, 30))
        end = datetime.combine(now.date(), time(16, 0))
        return start, end

    def on_tick(self, tick: dict) -> None:
        """Consume a tick from the data feed.
        ``tick`` must contain at least ``symbol``, ``price`` (mid), ``volume`` and ``timestamp`` (datetime).
        """
        symbol = tick["symbol"]
        if symbol not in self.symbols:
            return
        ts = tick["timestamp"]
        self._ticks[symbol].append((tick["mid"], tick["volume"], ts))
        # Clean old entries (keep only today)
        today = datetime.now().date()
        self._ticks[symbol] = [(p, v, t) for p, v, t in self._ticks[symbol] if t.date() == today]
        self._maybe_update_open_range(symbol, ts)
        self._check_breakout(symbol)

    def _maybe_update_open_range(self, symbol, ts):
        start, _ = self._session_bounds()
        if self._session_start != start:
            # New trading day – reset caches
            self._daily_range.clear()
            self._session_start = start
        if ts < start + timedelta(minutes=self.open_minutes):
            # Within opening window – recompute high/low
            prices = [p for p, _, _ in self._ticks[symbol]]
            if not prices:
                return
            high = max(prices)
            low = min(prices)
            self._daily_range[symbol] = {"high": high, "low": low}

    def _average_volume(self, symbol) -> float:
        volumes = [v for _, v, _ in self._ticks[symbol]]
        return sum(volumes) / len(volumes) if volumes else 0.0

    def _check_breakout(self, symbol):
        if symbol not in self._daily_range:
            return
        start, _ = self._session_bounds()
        now = datetime.now()
        # Only consider signals after opening window
        if now < start + timedelta(minutes=self.open_minutes):
            return
        last_tick = self._ticks[symbol][-1]
        price = last_tick[0]
        vol = last_tick[1]
        avg_vol = self._average_volume(symbol)
        range_info = self._daily_range[symbol]
        # Breakout upward
        if price > range_info["high"] and vol >= self.volume_multiplier * avg_vol:
            self._emit_signal(symbol, "LONG", price)
        # Breakout downward
        elif price < range_info["low"] and vol >= self.volume_multiplier * avg_vol:
            self._emit_signal(symbol, "SHORT", price)

    def _emit_signal(self, symbol, side, price):
        logger.info("ORB signal %s %s @ %.2f", side, symbol, price)
        # In a full system this would call a callback or place the signal on a queue.
        # For now we just log – the Executor will subscribe to the logger or a shared queue.

    async def run(self, tick_source: Callable[[Callable], None]):
        """Convenient helper to plug a tick source that accepts a callback.
        ``tick_source`` receives ``self.on_tick`` as argument and pushes ticks.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, tick_source, self.on_tick)
