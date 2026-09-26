import logging
from datetime import datetime
import httpx
from app.config import settings
from app.database import SessionLocal
from app.models.db_models import SignalRecommendation

logger = logging.getLogger(__name__)

class Notifier:
    """
    Sistema de notificaciones multicanal para TradePulse:
    - Despacho de recomendaciones de compra en tiempo real para Acciones y Opciones.
    - Persistencia en base de datos SQLite para alimentar el Centro de Notificaciones en la App.
    - Envío directo a Telegram Bot con diseño institucional en Markdown.
    - Soporte para Discord Webhooks y comprobación de conectividad.
    """

    def __init__(self):
        self.telegram_token = settings.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = settings.TELEGRAM_CHAT_ID
        self.discord_webhook = settings.DISCORD_WEBHOOK_URL

    def _create_client(self, timeout: float = 6.0, verify: bool = None) -> httpx.AsyncClient:
        """Crea un cliente HTTP asíncrono con control de verificación SSL para evitar fallos de certificados auto-firmados."""
        v = settings.SSL_VERIFY if verify is None else verify
        return httpx.AsyncClient(timeout=timeout, verify=v)

    def update_telegram_credentials(self, token: str, chat_id: str):
        """Actualiza en caliente las credenciales de Telegram."""
        self.telegram_token = token.strip()
        self.telegram_chat_id = chat_id.strip()
        settings.TELEGRAM_BOT_TOKEN = self.telegram_token
        settings.TELEGRAM_CHAT_ID = self.telegram_chat_id

    async def send_alert(self, title: str, message: str, level: str = "INFO") -> bool:
        """Envía una alerta informativa genérica multicanal."""
        # Suprimir notificaciones de cierre de bolsa si están desactivadas por el usuario
        if not getattr(settings, "NOTIFY_MARKET_CLOSE", False):
            title_lower = title.lower()
            msg_lower = message.lower()
            if any(term in title_lower or term in msg_lower for term in ["cierre intraday", "cierre de bolsa", "cierre de mercado", "square off", "square-off"]):
                logger.info(f"Notificación de cierre de bolsa omitida según preferencia del usuario: {title}")
                return True

        formatted_msg = f"🔔 *{title}* [{level}]\n\n{message}"
        logger.info(f"ALERTA BOT [{level}]: {title} - {message}")

        success = True
        if self.telegram_token and self.telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                payload = {
                    "chat_id": self.telegram_chat_id,
                    "text": formatted_msg,
                    "parse_mode": "Markdown"
                }
                async with self._create_client(timeout=5.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code != 200:
                        logger.warning(f"Respuesta inesperada de Telegram ({resp.status_code}): {resp.text}")
                        success = False
            except Exception as e:
                logger.error(f"Fallo enviando alerta a Telegram: {e}")
                success = False

        if self.discord_webhook:
            try:
                payload = {"content": formatted_msg}
                async with self._create_client(timeout=5.0) as client:
                    await client.post(self.discord_webhook, json=payload)
            except Exception as e:
                logger.error(f"Fallo enviando alerta a Discord: {e}")
                success = False

        return success


    async def send_trade_recommendation(self, signal: dict, db=None) -> dict:
        """
        Registra una recomendación de compra en la base de datos (para la app)
        y la despacha a Telegram con formato estructurado de alta visibilidad.
        """
        asset_type = signal.get("asset_type", "STOCK").upper()
        symbol = signal.get("symbol", "SPY").upper()
        action = signal.get("action", "BUY_STOCK")
        current_price = float(signal.get("current_price", 0.0))
        entry_target = float(signal.get("entry_target", current_price))
        stop_loss = float(signal.get("stop_loss", current_price * 0.99))
        take_profit = float(signal.get("take_profit", current_price * 1.02))
        take_profit_2 = signal.get("take_profit_2")
        rr = float(signal.get("risk_reward", 2.0))
        confluence_score = int(signal.get("confluence_score", 85))
        rationale = signal.get("rationale", "Confluencia Top-Down detectada.")
        setup_type = signal.get("setup_type", "TopDown_Liquidity_VWAP")
        contracts_or_shares = int(signal.get("contracts_or_shares", signal.get("contracts", signal.get("shares", 1))))

        strike_price = signal.get("strike_price")
        option_type = signal.get("option_type")
        expiration_date = signal.get("expiration_date")
        premium_est = signal.get("premium_est")
        premium_sl = signal.get("premium_stop_loss")
        premium_tp = signal.get("premium_take_profit")

        # 1. Construir mensaje enriquecido para Telegram
        now_time = datetime.utcnow().strftime("%H:%M UTC")

        if asset_type == "OPTION":
            badge_icon = "🟢" if option_type == "CALL" else "🔴"
            costo_contrato = round((premium_est or 0.0) * 100.0, 2)
            tp2_val = signal.get("premium_take_profit_2", round((premium_est or 1.0) * 2.0, 2))

            tg_message = (
                f"{badge_icon} *ALERTA OPCIONES ({option_type})* ⚡\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏷️ *Subyacente:* `{symbol}` (${current_price:.2f})\n"
                f"🎯 *Strike:* `${strike_price:.2f}` ({option_type}) | 📅 `{expiration_date}`\n"
                f"💵 *Prima Est:* `${premium_est:.2f}` (${costo_contrato:.0f}/contrato)\n\n"
                f"🛑 *SL Prima:* `${premium_sl:.2f}` (-28%)\n"
                f"🎯 *TP1 Prima:* `${premium_tp:.2f}` (+50%)\n"
                f"🎯 *TP2 Prima:* `${tp2_val:.2f}` (+100%)\n\n"
                f"📦 *Contratos:* `{contracts_or_shares}` (Fijo: 1 contrato)\n"
                f"📊 *Confluencia:* `{confluence_score}%`\n"
                f"⏰ *Hora:* `{now_time}`"
            )
        else:
            tp2_line = f" | TP2: `${take_profit_2:.2f}`" if take_profit_2 else ""
            tg_message = (
                f"🟢 *ALERTA ACCIONES (BUY)* 📈\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 *Símbolo:* `{symbol}` (${current_price:.2f})\n"
                f"📥 *Entrada:* `${entry_target:.2f}`\n"
                f"🛑 *Stop Loss:* `${stop_loss:.2f}`\n"
                f"🎯 *Take Profit:* `${take_profit:.2f}`{tp2_line}\n"
                f"⚖️ *Ratio R:R:* `1:{rr}`\n"
                f"📦 *Tamaño:* `{contracts_or_shares}` acciones (1% riesgo)\n"
                f"📊 *Confluencia:* `{confluence_score}%`\n"
                f"⏰ *Hora:* `{now_time}`"
            )

        # 1. Guardar primero en la base de datos SQLite para obtener rec_id
        rec_id = None
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        db_record = None
        try:
            db_record = SignalRecommendation(
                asset_type=asset_type,
                symbol=symbol,
                action=action,
                current_price=current_price,
                entry_target=entry_target,
                stop_loss=stop_loss,
                take_profit=take_profit,
                take_profit_2=take_profit_2,
                risk_reward=rr,
                strike_price=strike_price,
                option_type=option_type,
                expiration_date=expiration_date,
                premium_est=premium_est,
                premium_stop_loss=premium_sl,
                premium_take_profit=premium_tp,
                contracts_or_shares=contracts_or_shares,
                confluence_score=confluence_score,
                setup_type=setup_type,
                rationale=rationale,
                is_read=False,
                sent_to_telegram=False,
                telegram_message_id=None
            )
            db.add(db_record)
            db.commit()
            db.refresh(db_record)
            rec_id = db_record.id
        except Exception as e:
            logger.error(f"Error guardando SignalRecommendation en SQLite: {e}")
            if db:
                db.rollback()

        # 2. Despachar a Telegram con Botones Interactivos (Inline Keyboard)
        sent_telegram = False
        tg_msg_id = None
        if self.telegram_token and self.telegram_chat_id:
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Aceptar y Ejecutar en Moomoo", "callback_data": f"exec_{rec_id or 0}"},
                        {"text": "❌ Cancelar Alerta", "callback_data": f"cancel_{rec_id or 0}"}
                    ]
                ]
            }

            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": tg_message,
                "parse_mode": "Markdown",
                "reply_markup": reply_markup
            }

            try:
                async with self._create_client(timeout=6.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        sent_telegram = True
                        tg_msg_id = str(resp.json().get("result", {}).get("message_id", ""))
                        logger.info(f"Recomendación con botones enviada exitosamente a Telegram para {symbol} [{asset_type}]")
                    else:
                        logger.warning(f"Telegram error {resp.status_code}: {resp.text}")
            except Exception as e:
                if "CERTIFICATE_VERIFY_FAILED" in str(e) or "SSL" in str(e):
                    try:
                        async with httpx.AsyncClient(timeout=6.0, verify=False) as client:
                            resp = await client.post(url, json=payload)
                            if resp.status_code == 200:
                                sent_telegram = True
                                tg_msg_id = str(resp.json().get("result", {}).get("message_id", ""))
                                logger.info(f"Recomendación enviada a Telegram con bypass SSL para {symbol}")
                    except Exception as retry_err:
                        logger.error(f"Error despachando a Telegram tras reintento SSL: {retry_err}")
                else:
                    logger.error(f"Error despachando recomendación a Telegram: {e}")

            if sent_telegram and db_record:
                try:
                    db_record.sent_to_telegram = True
                    db_record.telegram_message_id = tg_msg_id
                    db.commit()
                except Exception:
                    pass

        if should_close and db:
            db.close()

        return {
            "id": rec_id,
            "success": True,
            "asset_type": asset_type,
            "symbol": symbol,
            "action": action,
            "sent_to_telegram": sent_telegram,
            "telegram_message_id": tg_msg_id,
            "message": f"Recomendación para {symbol} ({asset_type}) procesada correctamente"
        }

    async def test_telegram_connection(self, token: str = None, chat_id: str = None, custom_msg: str = None) -> dict:
        """
        Verifica la conectividad con Telegram enviando un mensaje de prueba al chat del usuario.
        Soporta bypass SSL para entornos con inspección HTTPS de antivirus o proxies locales.
        """
        tok = (token or self.telegram_token or "").strip()
        cid = (chat_id or self.telegram_chat_id or "").strip()

        if not tok or not cid:
            return {
                "success": False,
                "error": "Debes especificar tanto el Telegram Bot Token como el Chat ID."
            }

        async def _execute_test(verify_ssl: bool):
            async with httpx.AsyncClient(timeout=8.0, verify=verify_ssl) as client:
                # 1. Comprobar identidad del bot
                me_resp = await client.get(f"https://api.telegram.org/bot{tok}/getMe")
                if me_resp.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Token de bot inválido ({me_resp.status_code}): {me_resp.json().get('description', 'Error')}"
                    }
                bot_info = me_resp.json().get("result", {})
                bot_name = bot_info.get("first_name", "Bot")
                bot_user = bot_info.get("username", "")

                # 2. Enviar mensaje de prueba al chat
                test_text = custom_msg or (
                    "🚀 *TradePulse Bot Conectado Exitosamente*\n\n"
                    "¡Tu canal de alertas está listo! A partir de ahora recibirás aquí todas las recomendaciones "
                    "cuantitativas de compra de *Acciones* y *Opciones Financieras* en tiempo real.\n\n"
                    f"🤖 *Bot:* @{bot_user}\n"
                    f"⏰ *Fecha:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                )

                send_resp = await client.post(
                    f"https://api.telegram.org/bot{tok}/sendMessage",
                    json={"chat_id": cid, "text": test_text, "parse_mode": "Markdown"}
                )

                if send_resp.status_code == 200:
                    return {
                        "success": True,
                        "bot_name": bot_name,
                        "bot_username": bot_user,
                        "message": f"Mensaje de prueba enviado con éxito a través de @{bot_user}"
                    }
                else:
                    raw_desc = send_resp.json().get('description', '')
                    if "chat not found" in raw_desc.lower():
                        friendly_err = (
                            f"Chat no encontrado. IMPORTANTE: Debes abrir Telegram, entrar al chat de tu bot (@{bot_user}) "
                            f"y presionar 'Iniciar' (/start). Además, confirma que tu Chat ID sean solo números (ej: 5829104812)."
                        )
                    else:
                        friendly_err = f"Fallo al enviar mensaje al Chat ID ({send_resp.status_code}): {raw_desc}"
                    return {
                        "success": False,
                        "bot_name": bot_name,
                        "bot_username": bot_user,
                        "error": friendly_err
                    }


        try:
            return await _execute_test(verify_ssl=settings.SSL_VERIFY)
        except Exception as e:
            # Si falla por verificación SSL (antivirus / proxy con certificado auto-firmado), reintentar automáticamente con verify=False
            err_str = str(e)
            if "CERTIFICATE_VERIFY_FAILED" in err_str or "SSL" in err_str:
                logger.warning("Fallo SSL en conexión con Telegram (proxy/antivirus detectado). Reintentando con verify=False...")
                try:
                    return await _execute_test(verify_ssl=False)
                except Exception as retry_err:
                    logger.error(f"Error verificando conexión de Telegram tras reintento SSL: {retry_err}")
                    return {"success": False, "error": f"Error tras reintento SSL: {str(retry_err)}"}

            logger.error(f"Error verificando conexión de Telegram: {e}")
            return {"success": False, "error": f"Error de conexión con la API de Telegram: {err_str}"}

notifier = Notifier()

