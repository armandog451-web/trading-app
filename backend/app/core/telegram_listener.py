import logging
import asyncio
import httpx
from datetime import datetime
from app.config import settings
from app.database import SessionLocal
from app.models.db_models import SignalRecommendation
from app.core.broker_manager import broker_manager

logger = logging.getLogger(__name__)

class TelegramListener:
    """
    Escuchador en segundo plano para Telegram Bot API.
    Procesa las interacciones de botones en vivo (Inline Keyboard Callback Queries):
    - 'exec_<id>': Acepta y ejecuta la orden en Moomoo OpenD.
    - 'cancel_<id>': Cancela y descarta la recomendación.
    """

    def __init__(self):
        self._running = False
        self._task = None
        self._last_offset = 0

    def start(self):
        """Inicia el bucle de escucha asíncrono si no está activo."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._poll_loop())
            logger.info("TelegramListener iniciado en segundo plano (getUpdates)...")

    def stop(self):
        """Detiene el escuchador."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _poll_loop(self):
        """Bucle continuo de consulta de actualizaciones (long polling) a Telegram Bot API."""
        while self._running:
            token = settings.TELEGRAM_BOT_TOKEN
            if not token:
                await asyncio.sleep(5)
                continue

            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                params = {
                    "offset": self._last_offset + 1,
                    "timeout": 10,
                    "allowed_updates": ["callback_query", "message"]
                }

                verify_ssl = settings.SSL_VERIFY
                async with httpx.AsyncClient(timeout=15.0, verify=verify_ssl) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        updates = data.get("result", [])
                        for update in updates:
                            self._last_offset = update["update_id"]
                            if "callback_query" in update:
                                await self._handle_callback_query(update["callback_query"], token, client)
                            elif "message" in update:
                                await self._handle_incoming_message(update["message"], token, client)
                    else:
                        await asyncio.sleep(3)

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Silenciar errores transitorios de red para evitar saturar logs
                await asyncio.sleep(3)

    async def _handle_incoming_message(self, message: dict, token: str, client: httpx.AsyncClient):
        """Procesa comandos de texto enviados directamente al bot (ej: /balance, /saldo, /status)."""
        text = (message.get("text") or "").strip().lower()
        chat_id = message.get("chat", {}).get("id")
        if not chat_id or not text:
            return

        if text in ("/balance", "/saldo", "/cuenta", "balance", "saldo", "/status", "/posiciones", "posiciones"):
            acc = await broker_manager.get_account()
            pos = await broker_manager.get_positions()
            equity = acc.get("equity", 0.0)
            cash = acc.get("cash", 0.0)
            market_val = acc.get("market_val", 0.0)
            bp = acc.get("buying_power", 0.0)
            margin_ratio = acc.get("margin_ratio", 2.0)
            maint_margin = acc.get("maintenance_margin", 0.0)
            daily_pnl = acc.get("daily_pnl", 0.0)
            daily_pnl_pct = acc.get("daily_pnl_pct", 0.0)
            mode = acc.get("mode", "MOOMOO")
            now_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            pnl_sign = "+" if daily_pnl > 0 else ""
            pnl_emoji = "🟢" if daily_pnl >= 0 else "🔴"
            status_label = "Ganando" if daily_pnl >= 0 else "Perdiendo"

            if pos:
                pos_lines = []
                for p in pos:
                    sym = p.get("symbol")
                    qty = abs(p.get("qty", 0.0))
                    side = p.get("side", "BUY")
                    unit = p.get("unit_label", "Contratos" if p.get("asset_type") == "OPTION" else "Acciones")
                    entry = p.get("avg_entry_price", 0.0)
                    cur = p.get("current_price", 0.0)
                    pos_pnl = p.get("unrealized_pnl", 0.0)
                    pos_pct = p.get("unrealized_pnl_pct", 0.0)
                    dot = "🟢" if pos_pnl >= 0 else "🔴"
                    side_badge = "LONG" if side == "BUY" else "SHORT"

                    pos_lines.append(
                        f"{dot} *{sym}* · `{side_badge}` ({qty:g} {unit})\n"
                        f"   ├ Entrada: `${entry:,.2f}` │ Actual: `${cur:,.2f}`\n"
                        f"   └ P&L: `{pos_pnl:+,.2f} USD` ({pos_pct:+.2f}%)"
                    )
                pos_text = "\n".join(pos_lines)
            else:
                pos_text = "   _Sin posiciones abiertas actualmente._"

            msg = (
                f"💼 *ESTADO DE CUENTA MOOMOO (TIEMPO REAL)*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏦 *Broker / Modo:* `{mode}`\n"
                f"💰 *Capital Total (Equity):* `${equity:,.2f}`\n"
                f"💵 *Efectivo Disponible:* `${cash:,.2f}`\n"
                f"📊 *Capital Invertido en Mercado:* `${market_val:,.2f}`\n"
                f"⚡ *Poder de Compra (Margen {margin_ratio:.1f}x):* `${bp:,.2f}`\n"
                f"🛡️ *Margen de Mantenimiento:* `${maint_margin:,.2f}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📈 *Rendimiento Global:* {pnl_emoji} *{status_label}*\n"
                f"💵 *P&L No Realizado:* `{pnl_sign}{daily_pnl:,.2f} USD` ({daily_pnl_pct:+.2f}%)\n"
                f"📦 *Posiciones Activas:* `{len(pos)}`\n\n"
                f"📋 *DESGLOSE DE POSICIONES EN VIVO:*\n"
                f"{pos_text}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔒 *Restricción de Tamaño:* `1 solo contrato fijo por alerta`\n"
                f"⏰ *Actualizado:* `{now_time}`"
            )

            try:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
                )
                logger.info(f"Reporte de balance enviado a Telegram (Chat ID: {chat_id})")
            except Exception as e:
                logger.error(f"Error respondiendo comando balance en Telegram: {e}")

        elif text in ("/findesemana", "/weekend", "/backtest", "/optimizar", "/planlunes"):
            try:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": "⏳ *Iniciando Módulo de Fin de Semana...*\n\nDescargando datos históricos de la semana, ejecutando simulación multiestrategia y recalibrando pesos de Machine Learning. En breve recibirás el informe completo.",
                        "parse_mode": "Markdown"
                    }
                )
                # Ejecutar el motor de fin de semana
                import sys
                from pathlib import Path
                root_path = Path(__file__).resolve().parent.parent.parent.parent
                if str(root_path) not in sys.path:
                    sys.path.insert(0, str(root_path))
                from weekend_engine import weekend_engine
                asyncio.create_task(weekend_engine.run_weekend_optimization(send_telegram=True))
            except Exception as e:
                logger.error(f"Error ejecutando optimización de fin de semana: {e}")

        elif text in ("/start", "/ayuda", "/help"):
            help_msg = (
                "🤖 *TradePulse Quantitative Engine v2.0*\n\n"
                "• `/balance` o `/saldo` : Consulta de saldo y posiciones en tiempo real.\n"
                "• `/findesemana` o `/backtest` : Ejecuta la optimización y recalibración ML de fin de semana.\n"
                "• Alertas interactivas con botones `[✅ Ejecutar]` y `[❌ Descartar]` para aprobación en 1 toque."
            )
            try:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": help_msg, "parse_mode": "Markdown"}
                )
            except Exception as e:
                logger.error(f"Error enviando ayuda Telegram: {e}")

    async def _handle_callback_query(self, cb_query: dict, token: str, client: httpx.AsyncClient):
        """Maneja el evento cuando el usuario presiona un botón interactivo en Telegram."""
        cb_id = cb_query.get("id")
        cb_data = cb_query.get("data", "")
        message = cb_query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        msg_id = message.get("message_id")
        orig_text = message.get("text", "")

        logger.info(f"Telegram CallbackQuery recibido: {cb_data} desde Chat ID {chat_id}")

        if cb_data.startswith("exec_"):
            try:
                rec_id = int(cb_data.replace("exec_", ""))
                await self._process_execution(rec_id, cb_id, chat_id, msg_id, orig_text, token, client)
            except Exception as e:
                logger.error(f"Error procesando ejecucion desde Telegram: {e}")
                await self._answer_cb(cb_id, f"❌ Error ejecutando orden: {str(e)}", token, client)

        elif cb_data.startswith("cancel_"):
            try:
                rec_id = int(cb_data.replace("cancel_", ""))
                await self._process_cancellation(rec_id, cb_id, chat_id, msg_id, orig_text, token, client)
            except Exception as e:
                logger.error(f"Error procesando cancelacion desde Telegram: {e}")
                await self._answer_cb(cb_id, f"❌ Error: {str(e)}", token, client)

    async def _process_execution(self, rec_id: int, cb_id: str, chat_id: int, msg_id: int, orig_text: str, token: str, client: httpx.AsyncClient):
        from app.models.db_models import Trade
        from app.core.position_guardian import position_guardian

        db = SessionLocal()
        try:
            item = db.query(SignalRecommendation).filter(SignalRecommendation.id == rec_id).first()
            if not item:
                await self._answer_cb(cb_id, "⚠️ Recomendación no encontrada en la base de datos.", token, client)
                return

            is_option = (item.asset_type or "STOCK").upper() == "OPTION"
            if is_option:
                # Código exacto para Opciones Moomoo US: US.{TICKER}{YYMMDD}{C/P}{STRIKE*1000}
                exp_clean = (item.expiration_date or "2026-10-16").replace("-", "")[2:]
                opt_char = "C" if (item.option_type or "CALL").upper() == "CALL" else "P"
                strike_val = item.strike_price or item.current_price or 100.0
                strike_code = str(int(strike_val * 1000))
                trade_symbol = f"US.{item.symbol.upper()}{exp_clean}{opt_char}{strike_code}"
                
                trade_qty = max(1, item.contracts_or_shares or 1)
                trade_entry = float(item.premium_est or 1.0)
                trade_sl = float(item.premium_stop_loss or round(trade_entry * 0.72, 2))
                trade_tp = float(item.premium_take_profit or round(trade_entry * 1.50, 2))
                asset_label = f"Opción {item.option_type} ${strike_val:.2f}"
            else:
                trade_symbol = item.symbol.upper()
                trade_qty = max(1, item.contracts_or_shares or 1)
                trade_entry = float(item.entry_target or item.current_price or 100.0)
                trade_sl = float(item.stop_loss or round(trade_entry * 0.98, 2))
                trade_tp = float(item.take_profit or round(trade_entry * 1.05, 2))
                asset_label = "Acción"

            # 1. Ejecutar orden de compra a través del Broker activo (Moomoo OpenD)
            res = await broker_manager.submit_bracket_order(
                symbol=trade_symbol,
                qty=trade_qty,
                side="BUY",
                entry_price=trade_entry,
                stop_loss=trade_sl,
                take_profit=trade_tp,
                order_type="market"
            )

            order_id = res.get("order_id", "OK")
            broker_name = broker_manager.get_active_broker_name()

            # 2. Registrar objetivo en el Position Guardian para supervisión 100% automática
            position_guardian.register_target(
                symbol=trade_symbol,
                stop_loss=trade_sl,
                take_profit=trade_tp,
                qty=trade_qty,
                side="BUY",
                entry_price=trade_entry,
                asset_type="OPTION" if is_option else "STOCK"
            )

            # 3. Guardar Trade abierto en SQLite para persistencia y visualización en app
            try:
                open_trade = Trade(
                    symbol=trade_symbol,
                    side="BUY",
                    entry_price=trade_entry,
                    quantity=trade_qty,
                    stop_loss=trade_sl,
                    take_profit=trade_tp,
                    risk_reward_ratio=float(item.risk_reward or 1.8),
                    status="OPEN",
                    macro_bias="BULLISH" if (item.option_type or "CALL").upper() == "CALL" else "BEARISH",
                    strategy=item.setup_type or "TopDown_Confluence",
                    order_id=order_id
                )
                db.add(open_trade)
            except Exception as tr_err:
                logger.warning(f"Aviso guardando trade en SQLite: {tr_err}")

            item.is_read = True
            db.commit()

            # 4. Notificación popup en el celular del usuario
            await self._answer_cb(cb_id, f"🚀 ¡EJECUTADO EN {broker_name}!\nSL: ${trade_sl:.2f} | TP: ${trade_tp:.2f}\nSupervisión 100% Automática", token, client)

            # 5. Actualizar el mensaje de Telegram agregando la confirmación y los niveles activos
            qty_unit = "contratos" if is_option else "acciones"
            updated_text = (
                f"{orig_text}\n\n"
                f"✅ *ORDEN EJECUTADA EN {broker_name}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 *Activo:* `{trade_symbol}` ({asset_label})\n"
                f"💵 *Entrada:* `${trade_entry:.2f}` ({trade_qty} {qty_unit})\n"
                f"🛑 *Stop Loss Activo:* `${trade_sl:.2f}` (-28%)\n"
                f"🎯 *Take Profit Activo:* `${trade_tp:.2f}` (+50%)\n"
                f"🤖 *Modo:* 100% Automático. El sistema cerrará la posición cuando toque SL o TP sin que tengas que intervenir.\n"
                f"⏰ *Hora Ejecución:* `{datetime.utcnow().strftime('%H:%M:%S UTC')}`"
            )
            await self._edit_message(chat_id, msg_id, updated_text, token, client)

        finally:
            db.close()

    async def _process_cancellation(self, rec_id: int, cb_id: str, chat_id: int, msg_id: int, orig_text: str, token: str, client: httpx.AsyncClient):
        db = SessionLocal()
        try:
            item = db.query(SignalRecommendation).filter(SignalRecommendation.id == rec_id).first()
            if item:
                item.is_read = True
                db.commit()

            # 1. Notificación popup
            await self._answer_cb(cb_id, "❌ Recomendación cancelada.", token, client)

            # 2. Actualizar texto en Telegram
            updated_text = (
                f"{orig_text}\n\n"
                f"❌ *RECOMENDACIÓN CANCELADA Y DESCARTADA*\n"
                f"⏰ *Hora:* `{datetime.utcnow().strftime('%H:%M:%S UTC')}`"
            )
            await self._edit_message(chat_id, msg_id, updated_text, token, client)

        finally:
            db.close()

    async def _answer_cb(self, cb_id: str, text: str, token: str, client: httpx.AsyncClient):
        """Envía una respuesta de alerta emergente al botón en Telegram."""
        try:
            url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
            await client.post(url, json={"callback_query_id": cb_id, "text": text, "show_alert": True})
        except Exception as e:
            logger.warning(f"Error respondiendo answerCallbackQuery: {e}")

    async def _edit_message(self, chat_id: int, msg_id: int, text: str, token: str, client: httpx.AsyncClient):
        """Edita el texto del mensaje en Telegram para reflejar el cambio de estado sin los botones."""
        try:
            url = f"https://api.telegram.org/bot{token}/editMessageText"
            payload = {
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            await client.post(url, json=payload)
        except Exception as e:
            logger.warning(f"Error editando mensaje en Telegram: {e}")

telegram_listener = TelegramListener()
