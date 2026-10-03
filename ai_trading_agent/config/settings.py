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

    # Parámetros Deterministas de Gestión de Riesgo ($1,000,000 USD Paper Profile)
    PAPER_INITIAL_CAPITAL: float = 1000000.0
    RISK_PER_TRADE_PCT: float = 0.25           # 0.25% de riesgo por trade ($2,500 USD cap)
    MAX_PLANNED_RISK_PER_TRADE: float = 2500.0 # $2,500 USD máx por trade
    MAX_AGGREGATE_OPEN_RISK_PCT: float = 1.50  # 1.50% de riesgo abierto agregado ($15,000 USD cap)
    MAX_AGGREGATE_OPEN_RISK: float = 15000.0
    MAX_DAILY_LOSS_PCT: float = 1.00           # Freno de emergencia diario 1.00% ($10,000 USD cap)
    MAX_DAILY_LOSS: float = 10000.0
    MAX_CONSECUTIVE_LOSSES: int = 3            # Pausar estrategia tras 3 pérdidas consecutivas
    DRAWDOWN_WARNING_PCT: float = 5.0          # Alerta y reducción de riesgo al 5.0%
    DRAWDOWN_HALT_PCT: float = 10.0            # Detención total y autorización al 10.0%
    MAX_GROSS_EXPOSURE_PCT: float = 50.0       # Máximo 50% de exposición bruta ($500,000 USD)
    MAX_SINGLE_STOCK_EXPOSURE_PCT: float = 10.0 # Máximo 10% por activo ($100,000 USD)
    MAX_SECTOR_EXPOSURE_PCT: float = 20.0       # Máximo 20% por sector ($200,000 USD)
    MIN_RR_RATIO: float = 2.0                  # Ratio mínimo Riesgo:Beneficio 1:2
    MAX_OPEN_POSITIONS: int = 5                # Máximo 5 posiciones simultáneas
    MAX_CAPITAL_ALLOCATION_PCT: float = 10.0    # Máximo 10% del capital por activo

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
