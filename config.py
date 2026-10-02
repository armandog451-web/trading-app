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

# Risk Management & Protection Guardian
DEMO_CAPITAL = float(os.getenv("DEMO_CAPITAL", "100000.0"))
RISK_MAX_EXPOSURE = float(os.getenv("RISK_MAX_EXPOSURE", "0.02"))  # 2% por trade
RISK_MAX_TOTAL = float(os.getenv("RISK_MAX_TOTAL", "0.10"))        # 10% max total
MIN_RR_RATIO = float(os.getenv("MIN_RR_RATIO", "2.0"))             # R:R minimo 1:2
MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "2.5")) # Freno de emergencia diario -2.5%
AUTO_BREAK_EVEN = True                                             # Protección a +1R riesgo cero
AUTO_SQUARE_OFF_TIME = "15:55"                                     # Cierre obligatorio intradía EST
ENFORCE_ENTRY_WINDOW = os.getenv("ENFORCE_ENTRY_WINDOW", "true").lower() in ("true", "1", "yes")
MARKET_TIMEZONE = "America/New_York"

# Universe: Alta liquidez y Beta institucional (<= $300 por unidad)
WATCHLIST = ["AMD", "PLTR", "SOXL"]

# Database
DB_PATH = BASE_DIR / "trading_robot.db"
