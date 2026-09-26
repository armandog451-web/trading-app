import os
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from app.config import settings, BASE_DIR
from app.database import SessionLocal
from app.models.db_models import BotSetting
from app.core.notifier import notifier
from app.core.alpaca_client import alpaca_broker
from app.core.moomoo_client import moomoo_broker
from app.engines.risk_engine import risk_engine

logger = logging.getLogger(__name__)

ENV_FILE_PATH = Path(BASE_DIR) / ".env"

class SettingsManager:
    """
    Administrador de Persistencia Permanente de Credenciales y Configuración.
    Guarda y recupera todas las claves (Telegram, Moomoo, Alpaca, Riesgo)
    en la base de datos SQLite (tabla bot_settings) y en el archivo .env.
    """

    def save_setting(self, key: str, value: str, db: Session = None):
        """Guarda o actualiza una clave en SQLite y en el archivo .env."""
        val_str = str(value) if value is not None else ""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        try:
            setting = db.query(BotSetting).filter(BotSetting.key == key).first()
            if setting:
                setting.value = val_str
            else:
                setting = BotSetting(key=key, value=val_str)
                db.add(setting)
            db.commit()
        except Exception as e:
            logger.error(f"Error guardando setting {key} en SQLite: {e}")
            if db:
                db.rollback()
        finally:
            if should_close and db:
                db.close()

        # Actualizar archivo .env
        self._update_env_file(key, val_str)

    def save_settings_dict(self, data: dict):
        """Guarda un diccionario de configuraciones de forma masiva."""
        db = SessionLocal()
        try:
            for k, v in data.items():
                if v is not None:
                    self.save_setting(k, str(v), db=db)
        finally:
            db.close()

    def _update_env_file(self, key: str, value: str):
        """Escribe o actualiza la clave en el archivo .env del backend."""
        try:
            lines = []
            if ENV_FILE_PATH.exists():
                with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
                    lines = f.readlines()

            key_found = False
            new_lines = []
            for line in lines:
                if line.strip().startswith(f"{key}="):
                    new_lines.append(f"{key}={value}\n")
                    key_found = True
                else:
                    new_lines.append(line)

            if not key_found:
                new_lines.append(f"{key}={value}\n")

            with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

        except Exception as e:
            logger.error(f"Error escribiendo en archivo .env: {e}")

    def load_all_settings(self):
        """Carga e inyecta todas las configuraciones guardadas al iniciar el servidor."""
        db = SessionLocal()
        try:
            records = db.query(BotSetting).all()
            saved = {r.key: r.value for r in records}

            if not saved and ENV_FILE_PATH.exists():
                # Si SQLite está vacío pero .env existe, leer del .env
                with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line and not line.startswith("#"):
                            k, v = line.strip().split("=", 1)
                            saved[k] = v

            # 1. Telegram
            if "TELEGRAM_BOT_TOKEN" in saved:
                notifier.update_telegram_credentials(
                    token=saved["TELEGRAM_BOT_TOKEN"],
                    chat_id=saved.get("TELEGRAM_CHAT_ID", notifier.telegram_chat_id)
                )
            if "NOTIFY_MARKET_CLOSE" in saved:
                settings.NOTIFY_MARKET_CLOSE = str(saved["NOTIFY_MARKET_CLOSE"]).lower() in ("true", "1")

            # 2. Broker Activo
            if "ACTIVE_BROKER" in saved:
                settings.ACTIVE_BROKER = saved["ACTIVE_BROKER"].upper()

            if "AUTO_EXECUTE_TRADES" in saved:
                settings.AUTO_EXECUTE_TRADES = saved["AUTO_EXECUTE_TRADES"].lower() in ("true", "1")

            # 3. Alpaca
            if "ALPACA_API_KEY" in saved:
                settings.ALPACA_API_KEY = saved["ALPACA_API_KEY"]
                alpaca_broker.api_key = saved["ALPACA_API_KEY"]
            if "ALPACA_SECRET_KEY" in saved:
                settings.ALPACA_SECRET_KEY = saved["ALPACA_SECRET_KEY"]
                alpaca_broker.secret_key = saved["ALPACA_SECRET_KEY"]
            if "ALPACA_PAPER" in saved:
                is_paper = saved["ALPACA_PAPER"].lower() in ("true", "1")
                settings.ALPACA_PAPER = is_paper
                settings.ALPACA_BASE_URL = "https://paper-api.alpaca.markets" if is_paper else "https://api.alpaca.markets"
                alpaca_broker.base_url = settings.ALPACA_BASE_URL
                alpaca_broker.is_paper = is_paper

            # 4. Moomoo
            if "MOOMOO_HOST" in saved:
                settings.MOOMOO_HOST = saved["MOOMOO_HOST"]
                moomoo_broker.host = saved["MOOMOO_HOST"]
            if "MOOMOO_PORT" in saved:
                port_val = int(saved["MOOMOO_PORT"])
                settings.MOOMOO_PORT = port_val
                moomoo_broker.port = port_val
            if "MOOMOO_TRADE_PWD" in saved:
                settings.MOOMOO_TRADE_PWD = saved["MOOMOO_TRADE_PWD"]
                moomoo_broker.trade_pwd = saved["MOOMOO_TRADE_PWD"]
            if "MOOMOO_PAPER" in saved:
                is_m_paper = saved["MOOMOO_PAPER"].lower() in ("true", "1")
                settings.MOOMOO_PAPER = is_m_paper
                moomoo_broker.is_paper = is_m_paper
            if "MOOMOO_ACC_ID" in saved:
                acc_val = int(saved["MOOMOO_ACC_ID"])
                settings.MOOMOO_ACC_ID = acc_val
                moomoo_broker.acc_id = acc_val

            # 5. Riesgo
            if "MAX_DAILY_LOSS_PCT" in saved:
                val = float(saved["MAX_DAILY_LOSS_PCT"])
                risk_engine.max_daily_loss_pct = val
                settings.MAX_DAILY_LOSS_PCT = val
            if "RISK_PER_TRADE_PCT" in saved:
                val = float(saved["RISK_PER_TRADE_PCT"])
                risk_engine.risk_per_trade_pct = val
                settings.RISK_PER_TRADE_PCT = val
            if "MIN_RR_RATIO" in saved:
                val = float(saved["MIN_RR_RATIO"])
                risk_engine.min_rr_ratio = val
                settings.MIN_RR_RATIO = val
            if "AUTO_SQUARE_OFF_TIME" in saved:
                val = saved["AUTO_SQUARE_OFF_TIME"]
                risk_engine.auto_square_off_time = val
                settings.AUTO_SQUARE_OFF_TIME = val
            if "MAX_OPEN_POSITIONS" in saved:
                val = int(saved["MAX_OPEN_POSITIONS"])
                settings.MAX_OPEN_POSITIONS = val

            logger.info(f"SettingsManager: {len(saved)} configuraciones cargadas exitosamente desde persistencia.")

        except Exception as e:
            logger.error(f"Error cargando configuraciones desde persistencia: {e}")
        finally:
            db.close()

settings_manager = SettingsManager()
