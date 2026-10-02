import asyncio
import logging
from datetime import datetime
import pytz

from config import (
    AUTO_BREAK_EVEN, AUTO_SQUARE_OFF_TIME, MARKET_TIMEZONE,
    MAX_DAILY_LOSS_PCT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    DEMO_CAPITAL
)
from database import get_connection, log_event
from broker import broker_manager
import httpx

logger = logging.getLogger(__name__)

# === CONSTANTES DE PROTECCION ===
MAX_SINGLE_POSITION_LOSS_PCT = 3.0   # Stop de emergencia por posicion individual
MAX_PORTFOLIO_DRAWDOWN_PCT = 5.0     # Circuit Breaker global de portafolio
SQUARE_OFF_START = "15:55"
SQUARE_OFF_HARD_DEADLINE = "16:05"

class PositionGuardian:
    def __init__(self):
        self.is_running = False
        self._task = None
        self.ny_tz = pytz.timezone(MARKET_TIMEZONE)
        self.break_even_positions = set()
        self.daily_loss_tripped = False
        self.circuit_breaker_active = False
        self.square_off_executed_today = False
        self._last_square_off_date = None
        self.session_start_equity = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._monitor_loop())
            logger.info("PositionGuardian iniciado...")
            log_event("INFO", "Guardian de Posiciones, Circuit Breaker y Auto-Cierre activado.")
            # Capturar equity al inicio de sesion
            try:
                acc = broker_manager.get_account_summary()
                self.session_start_equity = acc.get("equity", DEMO_CAPITAL)
            except Exception:
                self.session_start_equity = DEMO_CAPITAL

    def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _send_alert(self, text):
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                await client.post(url, json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": text,
                    "parse_mode": "Markdown"
                })
        except Exception as e:
            logger.debug(f"Error enviando alerta del Guardian: {e}")

    async def _monitor_loop(self):
        while self.is_running:
            try:
                await self._check_all_protections()
            except Exception as e:
                logger.error(f"Error en bucle del PositionGuardian: {e}")
            await asyncio.sleep(10)

    async def _check_all_protections(self):
        now_ny = datetime.now(self.ny_tz)
        current_time_str = now_ny.strftime("%H:%M")
        today_str = now_ny.strftime("%Y-%m-%d")

        # Reset diario del flag de square-off
        if self._last_square_off_date != today_str:
            self.square_off_executed_today = False
            self.daily_loss_tripped = False
            self.circuit_breaker_active = False
            self.break_even_positions.clear()
            try:
                acc = broker_manager.get_account_summary()
                self.session_start_equity = acc.get("equity", DEMO_CAPITAL)
            except Exception:
                pass

        # =============================================
        # FIX #3: AUTO-CIERRE INTRADIA REFORZADO
        # Barrido forzoso entre 15:55 y 16:05 EST
        # =============================================
        if SQUARE_OFF_START <= current_time_str <= SQUARE_OFF_HARD_DEADLINE:
            if not self.square_off_executed_today:
                positions = broker_manager.get_positions()
                if positions:
                    logger.warning(f"CAMPANA DE CIERRE {current_time_str} EST: Ejecutando barrido forzoso...")
                    results = broker_manager.close_all_positions()
                    closed_count = sum(1 for r in results if r["result"].get("success"))
                    self.square_off_executed_today = True
                    self._last_square_off_date = today_str
                    log_event("WARNING", f"Auto-cierre intradia: {closed_count}/{len(positions)} posiciones cerradas.")

                    symbols_closed = ", ".join([r["symbol"] for r in results])
                    await self._send_alert(
                        f"🔔 *AUTO-CIERRE INTRADÍA ({current_time_str} EST)*\n\n"
                        f"Se ejecutó barrido forzoso de todas las posiciones.\n"
                        f"📊 *Cerradas:* `{closed_count}/{len(positions)}`\n"
                        f"📋 *Símbolos:* `{symbols_closed}`\n\n"
                        f"Capital protegido para la sesión de mañana."
                    )

                    # Verificacion post-cierre (retry si quedan huerfanas)
                    await asyncio.sleep(3)
                    remaining = broker_manager.get_positions()
                    if remaining:
                        logger.warning(f"RETRY: {len(remaining)} posiciones huerfanas detectadas post-cierre.")
                        broker_manager.close_all_positions()
                        log_event("WARNING", f"Retry de cierre: {len(remaining)} posiciones huerfanas liquidadas.")
                else:
                    self.square_off_executed_today = True
                    self._last_square_off_date = today_str

        # =============================================
        # FIX #2: CIRCUIT BREAKER ESTRICTO
        # Stop de emergencia por drawdown del portafolio
        # =============================================
        if not self.circuit_breaker_active:
            acc = broker_manager.get_account_summary()
            current_equity = acc.get("equity", 0.0)
            cash = acc.get("cash", 0.0)

            # A) Circuit Breaker por Drawdown vs Equity Inicial de Sesion
            if self.session_start_equity and self.session_start_equity > 0:
                drawdown_pct = ((current_equity - self.session_start_equity) / self.session_start_equity) * 100.0
                if drawdown_pct <= -MAX_PORTFOLIO_DRAWDOWN_PCT:
                    await self._activate_circuit_breaker(
                        f"Drawdown de portafolio ({drawdown_pct:.2f}%) excede limite de -{MAX_PORTFOLIO_DRAWDOWN_PCT}%"
                    )
                    return

            # B) Circuit Breaker por perdida diaria vs cash
            if cash > 0:
                daily_loss_pct = ((current_equity - cash) / cash) * 100.0
                if daily_loss_pct <= -MAX_DAILY_LOSS_PCT and not self.daily_loss_tripped:
                    self.daily_loss_tripped = True
                    await self._activate_circuit_breaker(
                        f"Perdida diaria ({daily_loss_pct:.2f}%) alcanzo limite de -{MAX_DAILY_LOSS_PCT}%"
                    )
                    return

        # =============================================
        # FIX #2b: STOP DE EMERGENCIA POR POSICION INDIVIDUAL
        # Corta posiciones con perdida anomala > 3%
        # =============================================
        positions = broker_manager.get_positions()
        for pos in positions:
            pnl_pct = pos.get("unrealized_plpc", 0.0)
            if pnl_pct <= -MAX_SINGLE_POSITION_LOSS_PCT:
                symbol = pos["symbol"]
                logger.warning(f"STOP EMERGENCIA: {symbol} con P&L {pnl_pct:.2f}% (limite: -{MAX_SINGLE_POSITION_LOSS_PCT}%)")
                broker_manager.close_position(symbol)
                log_event("ERROR", f"Stop de emergencia activado para {symbol}: P&L {pnl_pct:.2f}%")
                await self._send_alert(
                    f"🛑 *STOP DE EMERGENCIA ACTIVADO*\n\n"
                    f"📉 *Activo:* `{symbol}`\n"
                    f"💀 *P&L:* `{pnl_pct:.2f}%` (Limite: `-{MAX_SINGLE_POSITION_LOSS_PCT}%`)\n\n"
                    f"Posicion cerrada automaticamente para evitar perdidas anomalas."
                )

        # =============================================
        # AUTO BREAK-EVEN (+1.0R = Riesgo Cero)
        # =============================================
        if AUTO_BREAK_EVEN:
            for pos in positions:
                sym = pos["symbol"]
                entry = pos["avg_entry_price"]
                curr = pos["current_price"]
                side = pos["side"]

                if sym in self.break_even_positions:
                    continue

                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT stop_loss FROM signals
                    WHERE symbol = ? AND status = 'EJECUTADA'
                    ORDER BY id DESC LIMIT 1
                """, (sym,))
                sig = cursor.fetchone()
                conn.close()

                if sig and sig["stop_loss"]:
                    sl = float(sig["stop_loss"])
                    risk_distance = abs(entry - sl)
                    if risk_distance > 0:
                        if side == "BUY" and (curr - entry) >= risk_distance:
                            self.break_even_positions.add(sym)
                            log_event("SUCCESS", f"Break-Even activado para {sym}: SL movido a ${entry:.2f}.")
                            await self._send_alert(
                                f"🛡️ *BREAK-EVEN ACTIVADO (RIESGO CERO)*\n\n"
                                f"🎯 *Activo:* `{sym}`\n"
                                f"📈 *Precio Actual:* `${curr:.2f}` (+1.0R)\n"
                                f"✅ *Nuevo Stop Loss:* `${entry:.2f}`"
                            )
                        elif side == "SELL" and (entry - curr) >= risk_distance:
                            self.break_even_positions.add(sym)
                            log_event("SUCCESS", f"Break-Even activado para Short {sym}: SL movido a ${entry:.2f}.")
                            await self._send_alert(
                                f"🛡️ *BREAK-EVEN ACTIVADO (RIESGO CERO)*\n\n"
                                f"🎯 *Activo:* `{sym} (SHORT)`\n"
                                f"📉 *Precio Actual:* `${curr:.2f}`\n"
                                f"✅ *Nuevo Stop Loss:* `${entry:.2f}`"
                            )

    async def _activate_circuit_breaker(self, reason):
        self.circuit_breaker_active = True
        from engine import strategy_engine
        strategy_engine.stop()

        # Cerrar todas las posiciones inmediatamente
        positions = broker_manager.get_positions()
        if positions:
            broker_manager.close_all_positions()
            log_event("ERROR", f"Circuit Breaker: {len(positions)} posiciones liquidadas de emergencia.")

        log_event("ERROR", f"CIRCUIT BREAKER ACTIVADO: {reason}")
        await self._send_alert(
            f"🚨 *CIRCUIT BREAKER ACTIVADO*\n\n"
            f"⛔ *Motivo:* {reason}\n\n"
            f"Se han cerrado TODAS las posiciones abiertas.\n"
            f"El robot ha sido pausado automaticamente.\n"
            f"Volvera a operar en la siguiente sesion."
        )

guardian = PositionGuardian()
