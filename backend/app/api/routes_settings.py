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
            "max_open_positions": settings.MAX_OPEN_POSITIONS,
            "max_option_cost_per_contract": getattr(settings, "MAX_OPTION_COST_PER_CONTRACT", 200.0)
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
            "discord_active": bool(settings.DISCORD_WEBHOOK_URL),
            "notify_market_close": getattr(settings, "NOTIFY_MARKET_CLOSE", False)
        }
    }

@router.post("/risk")
def update_risk_settings(cfg: RiskConfigUpdate):
    """Actualiza en caliente y guarda permanentemente los parámetros del Motor de Riesgo."""
    risk_engine.max_daily_loss_pct = cfg.max_daily_loss_pct
    risk_engine.risk_per_trade_pct = cfg.risk_per_trade_pct
    risk_engine.min_rr_ratio = cfg.min_rr_ratio
    risk_engine.auto_square_off_time = cfg.auto_square_off_time
    if cfg.max_option_cost_per_contract is not None:
        settings.MAX_OPTION_COST_PER_CONTRACT = float(cfg.max_option_cost_per_contract)

    settings_manager.save_settings_dict({
        "MAX_DAILY_LOSS_PCT": cfg.max_daily_loss_pct,
        "RISK_PER_TRADE_PCT": cfg.risk_per_trade_pct,
        "MIN_RR_RATIO": cfg.min_rr_ratio,
        "AUTO_SQUARE_OFF_TIME": cfg.auto_square_off_time,
        "MAX_OPEN_POSITIONS": cfg.max_open_positions,
        "MAX_OPTION_COST_PER_CONTRACT": getattr(settings, "MAX_OPTION_COST_PER_CONTRACT", 200.0)
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
    save_dict = {
        "TELEGRAM_BOT_TOKEN": cfg.telegram_bot_token,
        "TELEGRAM_CHAT_ID": cfg.telegram_chat_id
    }
    if cfg.notify_market_close is not None:
        settings.NOTIFY_MARKET_CLOSE = cfg.notify_market_close
        save_dict["NOTIFY_MARKET_CLOSE"] = cfg.notify_market_close

    settings_manager.save_settings_dict(save_dict)
    return {"success": True, "message": "Credenciales y preferencias de Telegram guardadas permanentemente"}


@router.post("/sync-github")
async def sync_github():
    """
    Sincroniza y sube todos los cambios locales al repositorio GitHub configurado.
    """
    import subprocess
    import os
    import datetime

    repo_dir = settings.BASE_DIR
    git_cmd = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe")
    if not os.path.exists(git_cmd):
        git_cmd = "git"

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}

    try:
        # git add .
        subprocess.run([git_cmd, "add", "."], cwd=repo_dir, capture_output=True, text=True, check=True)
        # git commit
        commit_res = subprocess.run([git_cmd, "commit", "-m", f"Auto-sync TradePulse: {now_str}"], cwd=repo_dir, capture_output=True, text=True)
        # git push
        push_res = subprocess.run([git_cmd, "push", "origin", "main"], cwd=repo_dir, capture_output=True, text=True, timeout=10, env=env)

        if push_res.returncode == 0:
            return {
                "success": True,
                "message": f"¡Sincronización exitosa con GitHub! [{now_str}]",
                "detail": push_res.stdout or commit_res.stdout
            }
        else:
            return {
                "success": False,
                "message": "Aviso: Git requiere autorización en GitHub. Haz doble clic en 'Sincronizar con GitHub' en tu Escritorio para iniciar sesión una sola vez.",
                "detail": push_res.stderr or push_res.stdout
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Git Credential Manager está esperando autorización. Haz doble clic en 'Sincronizar con GitHub' en el escritorio para iniciar sesión.",
            "detail": "Git push timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error ejecutando sincronización: {str(e)}",
            "detail": str(e)
        }


