import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "TradePulse Quantitative Intraday Engine"
    ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'trade_engine.db'}"

    # Active Broker Selector: "ALPACA", "MOOMOO", "SIMULATOR"
    ACTIVE_BROKER: str = "MOOMOO"
    AUTO_EXECUTE_TRADES: bool = False  # False = Modo Solo Señales/Notificaciones (no ejecuta orden en broker)


    # Alpaca Broker Credentials
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_PAPER: bool = True
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"

    # Moomoo Open API Credentials
    MOOMOO_HOST: str = "127.0.0.1"
    MOOMOO_PORT: int = 11111
    MOOMOO_TRADE_PWD: str = ""
    MOOMOO_PAPER: bool = True
    MOOMOO_ACC_ID: int = 0

    # Macro & Data APIs

    FRED_API_KEY: str = ""  # Free key from St. Louis Fed

    # Risk Management Defaults
    MAX_DAILY_LOSS_PCT: float = 2.0       # Circuit Breaker: 2% max drawdown per day
    RISK_PER_TRADE_PCT: float = 1.0       # 1% equity risked per trade
    MIN_RR_RATIO: float = 2.0             # Minimum 1:2 Risk/Reward required
    MAX_OPEN_POSITIONS: int = 3           # Max concurrent positions
    AUTO_SQUARE_OFF_TIME: str = "15:50"   # EST time to close all intraday trades

    # Target Universe - High Performance Intraday / Scalping Assets
    CORE_SYMBOLS: list[str] = ["QQQ", "SPY", "TSLA", "AAPL", "MSFT"]
    MAX_SCREENED_STOCKS: int = 4

    # Notifications
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    DISCORD_WEBHOOK_URL: str = ""

    # Network / SSL
    SSL_VERIFY: bool = False  # False avoids SSL: CERTIFICATE_VERIFY_FAILED with Windows Antivirus/Proxy SSL inspection

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
