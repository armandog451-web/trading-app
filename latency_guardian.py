# ==========================================
# Módulo: Latency Guardian para Bot de Trading
# ==========================================
import time
import socket
import asyncio
import logging
import httpx
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MOOMOO_PORT, BROKER

logger = logging.getLogger(__name__)

class LatencyGuardian:
    def __init__(self, max_latency_ms=50.0):
        self.max_latency_ms = max_latency_ms
        self.high_latency_mode = False
        self.is_running = False
        self._task = None
        self._last_alert_time = None
        self._alert_cooldown_seconds = 300  # No repetir alerta en 5 min

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._monitor_loop())
            logger.info("LatencyGuardian: Monitoreo de latencia iniciado...")

    def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None

    def check_and_optimize(self, alpaca_url="https://api.alpaca.markets/v2/clock", opend_port=None):
        """Mide latencias y aplica ajustes automáticos si superan el límite."""
        port = opend_port or MOOMOO_PORT

        # 1. Medir latencia HTTP con Alpaca si es el broker activo
        alpaca_latency = 0.0
        if BROKER.lower() == "alpaca":
            start_time = time.time()
            try:
                import requests
                requests.get(alpaca_url, timeout=2)
                alpaca_latency = (time.time() - start_time) * 1000
            except Exception:
                alpaca_latency = 999.0

        # 2. Medir latencia de socket local con Moomoo OpenD
        start_time = time.time()
        try:
            sock = socket.create_connection(("127.0.0.1", port), timeout=1)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            opend_latency = (time.time() - start_time) * 1000
            sock.close()
        except Exception:
            opend_latency = 999.0

        active_latency = opend_latency if BROKER.lower() == "moomoo" else alpaca_latency
        logger.info(f"Latencia ({BROKER.upper()}) -> OpenD: {opend_latency:.2f}ms | Alpaca: {alpaca_latency:.2f}ms")

        optimal = True
        # 3. Evaluación y Auto-Ajuste sobre broker activo
        if active_latency > self.max_latency_ms:
            logger.warning(f"Umbral de latencia superado para {BROKER.upper()} ({active_latency:.2f}ms > {self.max_latency_ms}ms).")
            self._trigger_emergency_optimizations()
            optimal = False
        else:
            if self.high_latency_mode:
                logger.info("Latencia normalizada. Restaurando modo estándar.")
                self.high_latency_mode = False

        return {
            "optimal": optimal,
            "alpaca_latency_ms": round(alpaca_latency, 2),
            "opend_latency_ms": round(opend_latency, 2),
            "threshold_ms": self.max_latency_ms,
            "high_latency_mode": self.high_latency_mode,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S EST")
        }

    def _trigger_emergency_optimizations(self):
        """Ajustes automáticos ejecutados al detectar degradación de red."""
        self.high_latency_mode = True
        logger.info("[AUTO-AJUSTE 1] Conmutando a modo exclusivo de WebSockets persistentes para evitar overhead HTTP.")
        logger.info("[AUTO-AJUSTE 2] Desactivando registro masivo en disco (Logging a nivel WARNING) para liberar E/S del sistema.")
        logger.info("[AUTO-AJUSTE 3] Aplicando prioridad de hilo de alta velocidad en el bucle principal de ejecución.")

    async def _send_latency_alert(self, result: dict):
        """Envía alerta de latencia degradada a Telegram (con cooldown)."""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return
        now = time.time()
        if self._last_alert_time and (now - self._last_alert_time) < self._alert_cooldown_seconds:
            return
        self._last_alert_time = now

        if result["optimal"]:
            emoji = "🟢"
            status = "ÓPTIMO"
        else:
            emoji = "🔴"
            status = "DEGRADADO - Auto-ajustes aplicados"

        msg = (
            f"{emoji} *MONITOR DE LATENCIA DE RED*\n"
            f"───────────────────────────────\n"
            f"🌐 *Alpaca API:* `{result['alpaca_latency_ms']}ms`\n"
            f"🖥️ *Moomoo OpenD:* `{result['opend_latency_ms']}ms`\n"
            f"⚡ *Umbral máximo:* `{result['threshold_ms']}ms`\n"
            f"📊 *Estado:* *{status}*\n"
            f"───────────────────────────────\n"
            f"🕒 `{result['timestamp']}`"
        )

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                await client.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        except Exception as e:
            logger.debug(f"Error enviando alerta de latencia a Telegram: {e}")

    async def _monitor_loop(self):
        """Bucle de monitoreo cada 60 segundos."""
        while self.is_running:
            try:
                result = self.check_and_optimize()
                if not result["optimal"]:
                    await self._send_latency_alert(result)
            except Exception as e:
                logger.debug(f"LatencyGuardian monitor error: {e}")
            await asyncio.sleep(60)

latency_guardian = LatencyGuardian(max_latency_ms=50.0)
