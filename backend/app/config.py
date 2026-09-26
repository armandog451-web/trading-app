import os
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class Settings(BaseSettings):
    # App basic
    APP_NAME: str = "TradePulse Quantitative Intraday Engine"
    ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Database
    DATABASE_URL: str = f"sqlite:///{os.path.join(BASE_DIR, 'trade_engine.db')}"

    # Broker selection
    ACTIVE_BROKER: str = "MOOMOO"
    AUTO_EXECUTE_TRADES: bool = False

    # Alpaca credentials
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_PAPER: bool = True
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"

    # Moomoo Open API credentials
    MOOMOO_HOST: str = "127.0.0.1"
    MOOMOO_PORT: int = 11111
    MOOMOO_TRADE_PWD: str = ""
    MOOMOO_PAPER: bool = True
    MOOMOO_ACC_ID: int = 0

    # Macro & Data APIs
    FRED_API_KEY: str = ""

    # Risk Management Defaults (percent values)
    MAX_DAILY_LOSS_PCT: float = 2.0   # 2% daily drawdown
    RISK_PER_TRADE_PCT: float = 1.0   # 1% per trade
    MIN_RR_RATIO: float = 2.0
    MAX_OPEN_POSITIONS: int = 3
    AUTO_SQUARE_OFF_TIME: str = "15:50"

    # Trading parameters (demo friendly)
    OPEN_MINUTES: int = 1
    VOLUME_MULTIPLIER: float = 1.5

    # Target universe
    CORE_SYMBOLS: list[str] = ["QQQ", "SPY", "TSLA", "AAPL", "MSFT"]
    MAX_SCREENED_STOCKS: int = 4

    # Notifications
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    DISCORD_WEBHOOK_URL: str = ""
    NOTIFY_MARKET_CLOSE: bool = False

    # Network / SSL
    SSL_VERIFY: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
