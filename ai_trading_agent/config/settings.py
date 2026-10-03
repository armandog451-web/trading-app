"""
ai_trading_agent.config.settings
================================
Configuración determinista y validada con Pydantic Settings.
Sin credenciales externas obligatorias para operar en Fase 1.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from ai_trading_agent.domain.enums import TradingMode


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Identificación
    APP_NAME: str = "AI Trading Agent 1.0 (SuperRobot)"
    VERSION: str = "1.0.0-alpha"
    ENVIRONMENT: str = "local_simulation"

    # Modo Operativo Inicial OBLIGATORIO (Instrucción 14)
    # Por defecto ANALYSIS_ONLY: Imposibilidad técnica absoluta de enviar órdenes
    TRADING_MODE: TradingMode = TradingMode.ANALYSIS_ONLY

    # Kill Switch de Emergencia Global
    KILL_SWITCH_ACTIVE: bool = False

    # Parámetros Deterministas de Gestión de Riesgo (Instrucción 12)
    PAPER_INITIAL_CAPITAL: float = 100000.0
    RISK_PER_TRADE_PCT: float = 1.0        # Máximo 1.0% de riesgo por trade
    MAX_DAILY_LOSS_PCT: float = 2.0        # Freno de emergencia diario -2.0%
    MAX_DRAWDOWN_PCT: float = 5.0          # Límite de drawdown de cartera -5.0%
    MIN_RR_RATIO: float = 2.0              # Ratio mínimo Riesgo:Beneficio 1:2
    MAX_OPEN_POSITIONS: int = 3            # Máximo 3 posiciones simultáneas
    MAX_CAPITAL_ALLOCATION_PCT: float = 15.0 # Máximo 15% del capital total por activo

    # Parámetros de Simulación de Ejecución (Paper Broker)
    ESTIMATED_COMMISSION_PER_SHARE: float = 0.005  # $0.005 por acción
    ESTIMATED_SLIPPAGE_BPS: float = 5.0            # 5 puntos básicos (0.05%)
    MAX_ALLOWED_SPREAD_PCT: float = 0.002          # Máximo 0.2% de spread aceptable

    # Universo de Análisis Inicial
    CORE_SYMBOLS: List[str] = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA"]

    # Base de Datos Local
    DATABASE_URL: str = "sqlite:///ai_trading_agent.db"

    # Integración con Telegram
    TELEGRAM_BOT_TOKEN: str = "8885408454:AAHJB3V7lM0foQX65sAzqvn-W6ydKKj6Jbk"
    TELEGRAM_CHAT_ID: str = "8887098910"
    TELEGRAM_ENABLED: bool = True

    # Broker Activo ("moomoo", "alpaca" o "paper")
    ACTIVE_BROKER: str = "moomoo"

    # Conexión Moomoo OpenD
    MOOMOO_HOST: str = "127.0.0.1"
    MOOMOO_PORT: int = 11111
    MOOMOO_ACC_ID: int = 2837131

    # Conexión Alpaca Paper
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"


settings = AgentSettings()
