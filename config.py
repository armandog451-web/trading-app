import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Application Settings
APP_NAME = "AlgortimTrading Robot v2.0 PRO"
HOST = "127.0.0.1"
PORT = 8050
DEBUG = True

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8885408454:AAHJB3V7lM0foQX65sAzqvn-W6ydKKj6Jbk")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8887098910")

# Brokers Settings
BROKER = os.getenv("BROKER", "moomoo").lower()  # "moomoo" o "alpaca"
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET", "")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

MOOMOO_HOST = os.getenv("MOOMOO_HOST", "127.0.0.1")
MOOMOO_PORT = int(os.getenv("MOOMOO_PORT", "11111"))
MOOMOO_API_KEY = os.getenv("MOOMOO_API_KEY", "")
MOOMOO_API_SECRET = os.getenv("MOOMOO_API_SECRET", "")

# Risk Management & Protection Guardian ($1,000,000 USD Paper Profile)
DEMO_CAPITAL = float(os.getenv("DEMO_CAPITAL", "1000000.0"))
RISK_MAX_EXPOSURE = float(os.getenv("RISK_MAX_EXPOSURE", "0.0025"))  # 0.25% por trade ($2,500 USD)
MAX_PLANNED_RISK_PER_TRADE = float(os.getenv("MAX_PLANNED_RISK_PER_TRADE", "2500.0"))
MAX_AGGREGATE_OPEN_RISK = float(os.getenv("MAX_AGGREGATE_OPEN_RISK", "15000.0")) # $15,000 cap
MIN_RR_RATIO = float(os.getenv("MIN_RR_RATIO", "2.0"))             # R:R minimo 1:2
MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "1.0")) # Freno de emergencia diario -1.0% ($10,000 USD)
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "10000.0"))
AUTO_BREAK_EVEN = True                                             # Protección a +1R riesgo cero
AUTO_SQUARE_OFF_TIME = "15:55"                                     # Cierre obligatorio intradía EST
MARKET_TIMEZONE = "America/New_York"

# Universe: Alta liquidez y Beta institucional
WATCHLIST = ["QQQ", "SPY", "NVDA", "TSLA", "AMD", "AAPL", "MSFT"]

# Database
DB_PATH = BASE_DIR / "trading_robot.db"
