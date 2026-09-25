from fastapi import APIRouter
from app.config import settings
from app.models.schemas import RiskConfigUpdate, BrokerConfigUpdate, TelegramConfigUpdate, TestMoomooRequest
from app.engines.risk_engine import risk_engine
from app.core.alpaca_client import alpaca_broker
from app.core.moomoo_client import moomoo_broker
from app.core.notifier import notifier
from app.core.settings_manager import settings_manager

router = APIRouter(prefix="/api/settings", tags=["Configuraciones"])

@router.get("")
def get_current_settings():
    """Consulta la configuración activa del bot."""
    return {
        "risk": {
            "max_daily_loss_pct": risk_engine.max_daily_loss_pct,
            "risk_per_trade_pct": risk_engine.risk_per_trade_pct,
            "min_rr_ratio": risk_engine.min_rr_ratio,
            "auto_square_off_time": risk_engine.auto_square_off_time,
            "max_open_positions": settings.MAX_OPEN_POSITIONS
        },
        "broker": {
            "active_broker": settings.ACTIVE_BROKER,
            "auto_execute_trades": settings.AUTO_EXECUTE_TRADES,
            "has_alpaca_key": bool(settings.ALPACA_API_KEY),
            "alpaca_api_key": settings.ALPACA_API_KEY,
            "alpaca_paper": settings.ALPACA_PAPER,
            "base_url": settings.ALPACA_BASE_URL,
            "moomoo_host": settings.MOOMOO_HOST,
            "moomoo_port": settings.MOOMOO_PORT,
            "moomoo_paper": settings.MOOMOO_PAPER,
            "moomoo_acc_id": settings.MOOMOO_ACC_ID,
            "has_moomoo_pwd": bool(settings.MOOMOO_TRADE_PWD)
        },
        "macro": {
            "has_fred_key": bool(settings.FRED_API_KEY)
        },
        "notifications": {
            "telegram_active": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
            "telegram_bot_token": settings.TELEGRAM_BOT_TOKEN,
            "telegram_chat_id": settings.TELEGRAM_CHAT_ID,
            "discord_active": bool(settings.DISCORD_WEBHOOK_URL)
        }
    }

@router.post("/risk")
def update_risk_settings(cfg: RiskConfigUpdate):
    """Actualiza en caliente y guarda permanentemente los parámetros del Motor de Riesgo."""
    risk_engine.max_daily_loss_pct = cfg.max_daily_loss_pct
    risk_engine.risk_per_trade_pct = cfg.risk_per_trade_pct
    risk_engine.min_rr_ratio = cfg.min_rr_ratio
    risk_engine.auto_square_off_time = cfg.auto_square_off_time
    settings.MAX_OPEN_POSITIONS = cfg.max_open_positions

    settings_manager.save_settings_dict({
        "MAX_DAILY_LOSS_PCT": cfg.max_daily_loss_pct,
        "RISK_PER_TRADE_PCT": cfg.risk_per_trade_pct,
        "MIN_RR_RATIO": cfg.min_rr_ratio,
        "AUTO_SQUARE_OFF_TIME": cfg.auto_square_off_time,
        "MAX_OPEN_POSITIONS": cfg.max_open_positions
    })

    return {"success": True, "message": "Parámetros de riesgo guardados permanentemente"}

@router.post("/broker")
def update_broker_settings(cfg: BrokerConfigUpdate):
    """Actualiza y guarda permanentemente la selección de broker activo y las credenciales."""
    save_map = {}

    if cfg.active_broker:
        settings.ACTIVE_BROKER = cfg.active_broker.upper()
        save_map["ACTIVE_BROKER"] = settings.ACTIVE_BROKER
    if cfg.auto_execute_trades is not None:
        settings.AUTO_EXECUTE_TRADES = cfg.auto_execute_trades
        save_map["AUTO_EXECUTE_TRADES"] = cfg.auto_execute_trades

    if cfg.alpaca_api_key is not None:
        settings.ALPACA_API_KEY = cfg.alpaca_api_key
        alpaca_broker.api_key = cfg.alpaca_api_key
        save_map["ALPACA_API_KEY"] = cfg.alpaca_api_key
    if cfg.alpaca_secret_key is not None:
        settings.ALPACA_SECRET_KEY = cfg.alpaca_secret_key
        alpaca_broker.secret_key = cfg.alpaca_secret_key
        save_map["ALPACA_SECRET_KEY"] = cfg.alpaca_secret_key
    if cfg.alpaca_paper is not None:
        settings.ALPACA_PAPER = cfg.alpaca_paper
        settings.ALPACA_BASE_URL = "https://paper-api.alpaca.markets" if cfg.alpaca_paper else "https://api.alpaca.markets"
        alpaca_broker.base_url = settings.ALPACA_BASE_URL
        alpaca_broker.is_paper = cfg.alpaca_paper
        save_map["ALPACA_PAPER"] = cfg.alpaca_paper

    if cfg.moomoo_host is not None:
        settings.MOOMOO_HOST = cfg.moomoo_host
        moomoo_broker.host = cfg.moomoo_host
        save_map["MOOMOO_HOST"] = cfg.moomoo_host
    if cfg.moomoo_port is not None:
        settings.MOOMOO_PORT = cfg.moomoo_port
        moomoo_broker.port = cfg.moomoo_port
        save_map["MOOMOO_PORT"] = cfg.moomoo_port
    if cfg.moomoo_trade_pwd is not None:
        settings.MOOMOO_TRADE_PWD = cfg.moomoo_trade_pwd
        moomoo_broker.trade_pwd = cfg.moomoo_trade_pwd
        save_map["MOOMOO_TRADE_PWD"] = cfg.moomoo_trade_pwd
    if cfg.moomoo_paper is not None:
        settings.MOOMOO_PAPER = cfg.moomoo_paper
        moomoo_broker.is_paper = cfg.moomoo_paper
        save_map["MOOMOO_PAPER"] = cfg.moomoo_paper
    if cfg.moomoo_acc_id is not None:
        settings.MOOMOO_ACC_ID = cfg.moomoo_acc_id
        moomoo_broker.acc_id = cfg.moomoo_acc_id
        save_map["MOOMOO_ACC_ID"] = cfg.moomoo_acc_id

    settings_manager.save_settings_dict(save_map)

    return {
        "success": True,
        "message": f"Broker activo guardado permanentemente: {settings.ACTIVE_BROKER}."
    }

@router.post("/test-broker")
async def test_broker_credentials(cfg: BrokerConfigUpdate):
    """Verifica en tiempo real la conexión con Alpaca Markets."""
    res = await alpaca_broker.test_credentials(
        api_key=cfg.alpaca_api_key or settings.ALPACA_API_KEY,
        secret_key=cfg.alpaca_secret_key or settings.ALPACA_SECRET_KEY,
        is_paper=cfg.alpaca_paper if cfg.alpaca_paper is not None else settings.ALPACA_PAPER
    )
    return res

@router.post("/test-moomoo")
async def test_moomoo_credentials(cfg: TestMoomooRequest):
    """Verifica en tiempo real la conexión TCP con Moomoo OpenD y guarda las credenciales probadas."""
    res = await moomoo_broker.test_credentials(
        host=cfg.moomoo_host,
        port=cfg.moomoo_port,
        trade_pwd=cfg.moomoo_trade_pwd,
        is_paper=cfg.moomoo_paper,
        acc_id=cfg.moomoo_acc_id
    )
    if res.get("success"):
        settings_manager.save_settings_dict({
            "MOOMOO_HOST": cfg.moomoo_host,
            "MOOMOO_PORT": cfg.moomoo_port,
            "MOOMOO_TRADE_PWD": cfg.moomoo_trade_pwd,
            "MOOMOO_PAPER": cfg.moomoo_paper,
            "MOOMOO_ACC_ID": cfg.moomoo_acc_id
        })
    return res

@router.post("/telegram")
def update_telegram_settings(cfg: TelegramConfigUpdate):
    """Actualiza y guarda permanentemente las credenciales de Telegram Bot."""
    notifier.update_telegram_credentials(cfg.telegram_bot_token, cfg.telegram_chat_id)
    settings_manager.save_settings_dict({
        "TELEGRAM_BOT_TOKEN": cfg.telegram_bot_token,
        "TELEGRAM_CHAT_ID": cfg.telegram_chat_id
    })
    return {"success": True, "message": "Credenciales de Telegram guardadas permanentemente"}

