import asyncio
import logging
import httpx
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from database import get_connection, log_event
from broker import broker_manager
from latency_guardian import latency_guardian

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self._running = False
        self._task = None
        self._last_offset = 0

    def start(self):
        if not self._running and self.bot_token:
            self._running = True
            self._task = asyncio.create_task(self._poll_loop())
            logger.info('TelegramService: Polling iniciado...')
            log_event('INFO', 'Servicio Telegram conectado y escuchando comandos.')

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def send_balance_report(self, target_chat_id: int = None) -> bool:
        cid = target_chat_id or self.chat_id
        if not self.bot_token or not cid:
            return False
        try:
            acc = broker_manager.get_account_summary()
            positions = broker_manager.get_positions()
            equity = acc.get('equity', 0.0)
            cash = acc.get('cash', 0.0)
            buying_power = acc.get('buying_power', 0.0)
            broker_name = acc.get('broker', broker_manager.active_broker.upper())
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')
            if positions:
                pos_lines = []
                for p in positions:
                    sym = p.get('symbol', 'N/A')
                    qty = abs(p.get('qty', 0))
                    side = p.get('side', 'BUY')
                    entry = p.get('avg_entry_price', 0.0)
                    cur = p.get('current_price', 0.0)
                    pnl = p.get('unrealized_pl', 0.0)
                    pnl_pct = p.get('unrealized_plpc', 0.0)
                    emoji = '🟢' if pnl >= 0 else '🔴'
                    side_str = 'LONG' if side == 'BUY' else 'SHORT'
                    pos_lines.append(f'{emoji} *{sym}* - `{side_str}` ({qty} acciones)\n   • Entrada: `${entry:,.2f}` | Actual: `${cur:,.2f}`\n   • P&L: `{pnl:+,.2f} USD` ({pnl_pct:+.2f}%)')
                pos_text = '\n\n'.join(pos_lines)
            else:
                pos_text = '   _Sin posiciones abiertas actualmente._'
            msg = (
                f'💰 *ESTADO DE CUENTA Y SALDO EN VIVO* 💰\n'
                f'───────────────────────────────\n'
                f'🏦 *Broker:* `{broker_name}`\n'
                f'💵 *Capital Total (Equity):* `${equity:,.2f}`\n'
                f'💵 *Efectivo Disponible (Cash):* `${cash:,.2f}`\n'
                f'⚡ *Poder de Compra:* `${buying_power:,.2f}`\n'
                f'───────────────────────────────\n'
                f'📊 *POSICIONES ACTIVAS ({len(positions)}):*\n\n'
                f'{pos_text}\n'
                f'───────────────────────────────\n'
                f'🕒 *Actualizado:* `{now_str}`'
            )
            url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={'chat_id': cid, 'text': msg, 'parse_mode': 'Markdown'})
                return resp.status_code == 200
        except Exception as e:
            logger.error(f'Error enviando balance a Telegram: {e}')
            return False

    async def send_signal_alert(self, sig: dict) -> int:
        if not self.bot_token or not self.chat_id:
            return None
        total_investment = sig['price'] * sig['qty']
        risk_amount = abs(sig['price'] - sig['stop_loss']) * sig['qty']
        profit_amount = abs(sig['take_profit'] - sig['price']) * sig['qty']
        text = (
            f'⚡ *SEÑAL DE TRADING ALGORÍTMICO*\n\n'
            f'🎯 *Activo:* `{sig["symbol"]}`\n'
            f'📈 *Acción:* `{"COMPRA (LONG)" if sig["side"] == "BUY" else "VENTA (SHORT)"}`\n'
            f'💵 *Precio Unitario:* `${sig["price"]:.2f}` / acción\n'
            f'🔢 *Cantidad:* `{sig["qty"]} acciones`\n'
            f'💰 *Inversión Total:* `${total_investment:,.2f}`\n\n'
            f'🛑 *Stop Loss:* `${sig["stop_loss"]:.2f}` (Pérdida máx: `-${risk_amount:,.2f}`)\n'
            f'🎯 *Take Profit:* `${sig["take_profit"]:.2f}` (Ganancia est: `+${profit_amount:,.2f}`)\n'
            f'⚖️ *Riesgo/Beneficio:* `1 : {sig["rr_ratio"]:.1f}`\n\n'
            f'🤖 *Estrategia:* {sig["strategy"]}\n'
            f'💡 *Motivo Técnico:* {sig["rationale"]}\n'
            f'📊 *Confianza:* `{sig["confidence"]:.0f}%`\n\n'
            f'¿Deseas autorizar la ejecución en la cuenta Demo?'
        )
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '✅ Ejecutar Orden', 'callback_data': f'exec_{sig["id"]}'},
                    {'text': '❌ Descartar', 'callback_data': f'cancel_{sig["id"]}'}
                ]
            ]
        }
        url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
        payload = {'chat_id': self.chat_id, 'text': text, 'parse_mode': 'Markdown', 'reply_markup': keyboard}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    msg_id = data.get('result', {}).get('message_id')
                    logger.info(f'Señal enviada a Telegram con Message ID: {msg_id}')
                    return msg_id
                else:
                    logger.error(f'Error Telegram sendMessage: {resp.text}')
        except Exception as e:
            logger.error(f'Excepción enviando señal a Telegram: {e}')
        return None

    async def _handle_callback(self, callback_query: dict):
        cb_id = callback_query.get('id')
        data = callback_query.get('data', '')
        message = callback_query.get('message', {})
        message_id = message.get('message_id')
        chat_id = message.get('chat', {}).get('id')
        if data.startswith('exec_'):
            sig_id = int(data.split('_')[1])
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM signals WHERE id = ?', (sig_id,))
            row = cursor.fetchone()
            if row:
                if row['status'] != 'PENDIENTE':
                    await self._answer_callback(cb_id, f'Esta orden ya está {row["status"]}.')
                    conn.close()
                    return
                exec_res = broker_manager.execute_order(
                    symbol=row['symbol'], side=row['side'], qty=row['qty'],
                    price=row['price'], stop_loss=row['stop_loss'], take_profit=row['take_profit']
                )
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('UPDATE signals SET status = \'EJECUTADA\', executed_at = ? WHERE id = ?', (now, sig_id))
                conn.commit()
                conn.close()
                await self._answer_callback(cb_id, '✅ Orden ejecutada con éxito')
                edit_text = (
                    f'✅ *ORDEN EJECUTADA EN DEMO*\n\n'
                    f'• Activo: `{row["symbol"]}`\n'
                    f'• Lado: `{row["side"]}` | Cantidad: `{row["qty"]}`\n'
                    f'• Precio: `${row["price"]:.2f}`\n'
                    f'• Broker: `{exec_res.get("broker", "Demo")}`\n'
                    f'• Hora: `{now}`\n\n'
                    f'Monitoreando posición en el algoritmo...'
                )
                await self._edit_message(chat_id, message_id, edit_text)
                log_event('SUCCESS', f'Orden ID {sig_id} aprobada desde Telegram para {row["symbol"]}.')
        elif data.startswith('cancel_'):
            sig_id = int(data.split('_')[1])
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM signals WHERE id = ?', (sig_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute('UPDATE signals SET status = \'CANCELADA\' WHERE id = ?', (sig_id,))
                conn.commit()
                conn.close()
                await self._answer_callback(cb_id, '❌ Señal descartada')
                edit_text = f'❌ *SEÑAL DESCARTADA*\n\nLa recomendación para `{row["symbol"]}` fue cancelada por el usuario.'
                await self._edit_message(chat_id, message_id, edit_text)
                log_event('INFO', f'Señal ID {sig_id} cancelada desde Telegram.')

    async def _answer_callback(self, cb_id: str, text: str):
        url = f'https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery'
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                await client.post(url, json={'callback_query_id': cb_id, 'text': text})
        except Exception:
            pass

    async def _edit_message(self, chat_id: int, message_id: int, text: str):
        url = f'https://api.telegram.org/bot{self.bot_token}/editMessageText'
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                await client.post(url, json={'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': 'Markdown'})
        except Exception:
            pass

    async def _poll_loop(self):
        while self._running:
            if not self.bot_token:
                await asyncio.sleep(5)
                continue
            try:
                url = f'https://api.telegram.org/bot{self.bot_token}/getUpdates'
                params = {'offset': self._last_offset + 1, 'timeout': 15, 'allowed_updates': ['callback_query', 'message']}
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        updates = resp.json().get('result', [])
                        for u in updates:
                            self._last_offset = u.get('update_id', self._last_offset)
                            if 'callback_query' in u:
                                await self._handle_callback(u['callback_query'])
                            elif 'message' in u and 'text' in u['message']:
                                msg = u['message']
                                raw_text = msg.get('text', '').strip().lower()
                                chat = msg.get('chat', {}).get('id')
                                if raw_text in ['/saldo', '/balance', '/estado', '/posiciones']:
                                    await self.send_balance_report(chat)
                                elif raw_text in ['/latencia', '/latency', '/ping']:
                                    result = latency_guardian.check_and_optimize()
                                    await latency_guardian._send_latency_alert(result)
                                elif raw_text in ['/findesemana', '/weekend', '/backtest', '/optimizar', '/planlunes']:
                                    await client.post(
                                        f'https://api.telegram.org/bot{self.bot_token}/sendMessage',
                                        json={
                                            'chat_id': chat,
                                            'text': '⏳ *Iniciando Módulo de Fin de Semana...*\n\nDescargando datos históricos de la semana, ejecutando simulación multiestrategia y recalibrando pesos de Machine Learning. En breve recibirás el informe completo.',
                                            'parse_mode': 'Markdown'
                                        }
                                    )
                                    from weekend_engine import weekend_engine
                                    asyncio.create_task(weekend_engine.run_weekend_optimization(send_telegram=True))
                                elif raw_text in ['/start', '/ayuda']:
                                    reply = (
                                        '🤖 *Bienvenido a AlgortimTrading Robot v2.0*\n\n'
                                        'Estoy conectado a tu Dashboard de Trading.\n'
                                        '• Usa `/saldo` o `/balance` para ver tu capital y posiciones.\n'
                                        '• Usa `/findesemana` o `/backtest` para recalibrar el bot y ver el plan del lunes.\n'
                                        '• Usa `/latencia` o `/ping` para medir latencia de red.\n'
                                        '• Te enviaré aquí cada oportunidad cuantitativa para aprobarla con 1 clic.'
                                    )
                                    await client.post(
                                        f'https://api.telegram.org/bot{self.bot_token}/sendMessage',
                                        json={'chat_id': chat, 'text': reply, 'parse_mode': 'Markdown'}
                                    )
            except Exception as e:
                logger.debug(f'Telegram polling retry: {e}')
            await asyncio.sleep(1)

telegram_service = TelegramService()