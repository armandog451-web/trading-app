"""
ai_trading_agent.notifications.telegram_service
===============================================
Servicio de mensajería y alertas a Telegram para el AI Trading Agent 1.0 (SuperRobot).
Emite notificaciones en vivo de señales aprobadas, estado de cuenta, ejecuciones de Paper Trading
y eventos de seguridad (Kill Switch y freno diario de pérdidas).
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from ai_trading_agent.config.settings import settings

logger = logging.getLogger(__name__)


class TelegramAlertService:
    """Emisor de alertas formateadas a Telegram para el SuperRobot."""

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id and settings.TELEGRAM_ENABLED)

    def send_message_sync(self, text: str) -> bool:
        """Envío síncrono para llamadas directas dentro de pipelines."""
        if not self.is_configured:
            return False
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, json=payload)
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Error enviando mensaje a Telegram: {e}")
            return False

    def send_message(self, text: str) -> bool:
        """Alias para envío síncrono de mensajes a Telegram."""
        return self.send_message_sync(text)

    async def send_message_async(self, text: str) -> bool:
        """Envío asíncrono para FastAPI."""
        if not self.is_configured:
            return False
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, json=payload)
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Error enviando mensaje asíncrono a Telegram: {e}")
            return False

    def send_signal_alert(self, pipeline_result: Dict[str, Any]) -> bool:
        """Emite una alerta formateada con la señal aprobada, riesgo y opción recomendada."""
        if not self.is_configured:
            return False

        sym = pipeline_result.get("symbol", "N/A")
        direction = pipeline_result.get("direction", "BUY")
        score = pipeline_result.get("score", 0.0)
        regime = pipeline_result.get("market_regime", "BULL_TREND")
        entry = pipeline_result.get("entry_price", 0.0)
        sl = pipeline_result.get("stop_loss", 0.0)
        tp = pipeline_result.get("take_profit", 0.0)
        qty = pipeline_result.get("quantity", 0)
        rr = pipeline_result.get("rr_ratio", 2.0)
        mode = pipeline_result.get("trading_mode", "ANALYSIS_ONLY")
        rationale = pipeline_result.get("rationale", "Setup técnico confirmado.")
        opt = pipeline_result.get("option_contract", {})

        opt_text = ""
        if opt:
            opt_type = opt.get("option_type", "CALL")
            strike = opt.get("strike_price", 0.0)
            exp = opt.get("expiration_date", "")
            cost = opt.get("total_contract_cost", 0.0)
            dte = opt.get("days_to_expiration", 21)
            opt_text = (
                f"\n🎟️ *CONTRATO DE OPCIONES (&le; $200 USD):*\n"
                f"   • Tipo: `{opt_type}` Strike `${strike:.2f}`\n"
                f"   • Vencimiento: `{exp}` ({dte} DTE)\n"
                f"   • Costo Estimado: `${cost:,.2f} USD`"
            )

        side_emoji = "🟢" if "BUY" in str(direction).upper() else "🔴"
        action_str = "COMPRA (LONG)" if "BUY" in str(direction).upper() else "VENTA (SHORT)"

        msg = (
            f"⚡ *SUPERROBOT — SEÑAL CUANTITATIVA*\n"
            f"───────────────────────────────\n"
            f"🎯 *Activo:* `{sym}`\n"
            f"{side_emoji} *Acción:* `{action_str}`\n"
            f"🤖 *Confluencia:* `{score:.1f} / 100` | *Régimen:* `{regime}`\n\n"
            f"💵 *Entrada Estimada:* `${entry:,.2f}`\n"
            f"🔢 *Cantidad Aprobada:* `{qty} acciones` (Riesgo exacto 1%)\n"
            f"🛑 *Stop Loss:* `${sl:,.2f}`\n"
            f"🎯 *Take Profit:* `${tp:,.2f}`\n"
            f"⚖️ *Ratio Riesgo/Beneficio:* `1 : {rr:.1f}`\n"
            f"{opt_text}\n"
            f"───────────────────────────────\n"
            f"🛡️ *Modo Operativo:* `{mode}`\n"
            f"💡 *Razón Técnica:* {rationale}\n"
            f"🕒 *Hora:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}`"
        )
        return self.send_message_sync(msg)

    def send_balance_alert(self, account_summary: Dict[str, Any], positions: List[Dict[str, Any]]) -> bool:
        """Emite reporte de saldo y posiciones en vivo."""
        if not self.is_configured:
            return False

        equity = account_summary.get("equity", 100000.0)
        cash = account_summary.get("cash", 100000.0)
        buying_power = account_summary.get("buying_power", cash * 2.0)
        broker_name = account_summary.get("broker", settings.ACTIVE_BROKER.upper())
        status = account_summary.get("status", "Operativo")

        pos_lines = []
        if positions:
            for p in positions:
                sym = p.get("symbol", "N/A")
                qty = p.get("quantity", p.get("qty", 0))
                side = p.get("side", "BUY")
                entry = p.get("avg_entry_price", 0.0)
                cur = p.get("current_price", 0.0)
                pnl = p.get("unrealized_pnl", p.get("unrealized_pl", 0.0))
                emoji = "🟢" if pnl >= 0 else "🔴"
                pos_lines.append(f"{emoji} *{sym}* ({side} {qty} acc.) @ ${cur:,.2f} | PnL: `${pnl:+,.2f}`")
            pos_text = "\n".join(pos_lines)
        else:
            pos_text = "   _Sin posiciones abiertas actualmente._"

        msg = (
            f"💰 *SUPERROBOT — ESTADO DE CUENTA Y SALDO*\n"
            f"───────────────────────────────\n"
            f"🏦 *Broker Activo:* `{broker_name}`\n"
            f"📶 *Estado de Conexión:* `{status}`\n"
            f"💵 *Capital Total (Equity):* `${equity:,.2f}`\n"
            f"💵 *Efectivo Disponible (Cash):* `${cash:,.2f}`\n"
            f"⚡ *Poder de Compra:* `${buying_power:,.2f}`\n"
            f"───────────────────────────────\n"
            f"📊 *POSICIONES ACTIVAS ({len(positions)}):*\n"
            f"{pos_text}\n"
            f"───────────────────────────────\n"
            f"🕒 *Actualizado:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}`"
        )
        return self.send_message_sync(msg)

    def send_kill_switch_alert(self, active: bool, reason: str) -> bool:
        """Emite alerta de cambio en el Kill Switch."""
        if not self.is_configured:
            return False

        if active:
            msg = (
                f"🚨 *ALERTA CRÍTICA: KILL SWITCH ACTIVADO*\n\n"
                f"El interruptor de emergencia del AI Trading Agent ha sido ACTIVADO.\n"
                f"• Motivo: {reason}\n"
                f"• Estado: Toda emisión o simulación de órdenes queda COMPLETAMENTE BLOQUEADA.\n"
                f"• Hora: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}`"
            )
        else:
            msg = (
                f"🛡️ *KILL SWITCH DESACTIVADO*\n\n"
                f"El sistema ha sido restaurado al modo operativo normal `{settings.TRADING_MODE}`.\n"
                f"• Motivo: {reason}\n"
                f"• Hora: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}`"
            )
        return self.send_message_sync(msg)


telegram_notifier = TelegramAlertService()
