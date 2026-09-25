import sqlite3
from pathlib import Path
from datetime import datetime

class TradeRepository:
    """Simple SQLite repository to persist trade records.
    The DB file lives in the project root under `trade_engine.db` (as defined in Settings).
    """

    def __init__(self, db_path: str | None = None):
        # Resolve DB path from Settings if not provided
        from ..config import settings
        self.db_path = db_path or settings.DATABASE_URL.replace('sqlite:///', '')
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self):
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT,
                    symbol TEXT,
                    side TEXT,
                    price REAL,
                    size INTEGER,
                    stop_loss REAL,
                    timestamp TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def save_trade(self, order_id: str, symbol: str, side: str, price: float, size: int, stop_loss: float | None):
        """Persist a trade record.
        Args:
            order_id: Identifier returned by the broker.
            symbol, side, price, size, stop_loss: Trade details.
        """
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO trades (order_id, symbol, side, price, size, stop_loss, timestamp) VALUES (?,?,?,?,?,?,?)",
                (
                    order_id,
                    symbol,
                    side,
                    price,
                    size,
                    stop_loss,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def list_trades(self, limit: int = 100):
        conn = self._connect()
        try:
            cur = conn.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            # Return list of dicts for convenience
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in rows]
        finally:
            conn.close()
