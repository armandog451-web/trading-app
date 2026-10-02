import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class RiskGate:
    """Quantitative risk validation before any order is sent.

    Parameters
    ----------
    capital_provider: Callable[[], float]
        Function that returns the current total capital (equity) of the account.
    daily_drawdown_limit: float
        Maximum allowed daily loss as a fraction of capital (e.g., 0.02 for 2%).
    atr_provider: Callable[[str], float]
        Function that returns the latest ATR value for a symbol.
    max_risk_per_trade: float
        Upper bound of risk per trade as a fraction of capital (default 0.01 → 1%).
    """

    def __init__(
        self,
        capital_provider,
        daily_drawdown_limit: float = 0.02,
        atr_provider=None,
        max_risk_per_trade: float = 0.01,
    ) -> None:
        self.capital_provider = capital_provider
        self.daily_drawdown_limit = daily_drawdown_limit
        self.atr_provider = atr_provider
        self.max_risk_per_trade = max_risk_per_trade
        self._day_start = datetime.now().date()
        self._day_entry_loss = 0.0  # cumulative loss for the current day

    def _reset_daily_if_needed(self) -> None:
        today = datetime.now().date()
        if today != self._day_start:
            self._day_start = today
            self._day_entry_loss = 0.0

    def record_trade_result(self, pnl: float) -> None:
        """Update internal daily drawdown bookkeeping.
        Positive *pnl* reduces the loss, negative increases it.
        """
        self._reset_daily_if_needed()
        self._day_entry_loss -= pnl  # loss accumulates when pnl is negative

    def _daily_drawdown_exceeded(self) -> bool:
        capital = self.capital_provider()
        allowed_loss = capital * self.daily_drawdown_limit
        return self._day_entry_loss > allowed_loss

    def compute_position_size(self, entry_price: float, symbol: str, side: str) -> Optional[int]:
        """Return the integer number of contracts/shares to trade.

        * Uses 1% (or ``max_risk_per_trade``) of capital as risk.
        * Risk per contract = ATR * multiplier (default 1.0).
        * If daily drawdown already hit, returns ``None``.
        """
        self._reset_daily_if_needed()
        if self._daily_drawdown_exceeded():
            logger.warning("Daily drawdown limit reached – order blocked.")
            return None

        capital = self.capital_provider()
        risk_amount = capital * self.max_risk_per_trade
        atr = self.atr_provider(symbol) if self.atr_provider else None
        if atr is None or atr == 0:
            logger.warning("ATR not available for %s – cannot size position.", symbol)
            return None
        # Risk per contract = ATR (could be multiplied by a factor, e.g., 1.0)
        risk_per_contract = atr
        contracts = int(risk_amount / risk_per_contract)
        if contracts < 1:
            contracts = 1
        # Enforce the global rule of exactly ONE contract per order as requested.
        contracts = 1
        logger.info(
            "RiskGate: capital=%.2f, risk_amount=%.2f, atr=%.4f → contracts=%d",
            capital,
            risk_amount,
            atr,
            contracts,
        )
        return contracts

    def compute_stop_loss(self, entry_price: float, symbol: str, side: str) -> Optional[float]:
        """Calculate a dynamic stop‑loss using ATR.
        For LONG: entry_price - atr * 1.5 ; for SHORT: entry_price + atr * 1.5
        """
        if not self.atr_provider:
            return None
        atr = self.atr_provider(symbol)
        if atr is None:
            return None
        multiplier = 1.5
        if side.upper() == "LONG":
            return entry_price - atr * multiplier
        else:
            return entry_price + atr * multiplier

    async def validate_and_size(
        self, entry_price: float, symbol: str, side: str
    ) -> Optional[Dict[str, float]]:
        """Convenient async wrapper returning size and stop‑loss or ``None``.
        """
        size = self.compute_position_size(entry_price, symbol, side)
        if size is None:
            return None
        sl = self.compute_stop_loss(entry_price, symbol, side)
        return {"size": size, "stop_loss": sl}
