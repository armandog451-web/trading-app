"""
Módulo: shadow_logger.py (Auditoría SQLite y Notificación Telegram en Modo Espejo)
==================================================================================
Registra cada intento de trade evaluado por el Agente Interceptor en `agent_audit.db`
(usando `sqlite3`) y envía alertas a Telegram si las credenciales están configuradas.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_ENV_PATH = Path(__file__).resolve().parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH, override=False)
else:
    load_dotenv(override=False)

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "agent_audit.db"


class ShadowLogger:
    """
    Auditor SQLite (`agent_audit.db`) y notificador de Telegram para el
    Agente Interceptor de Noticias y Riesgo con IA.
    """

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self._init_db()

    def _init_db(self) -> None:
        """Crea la tabla `agent_audit_log` en `agent_audit.db` si no existe."""
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        strategy TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        entry_price REAL,
                        stop_loss REAL,
                        take_profit REAL,
                        approved INTEGER NOT NULL,
                        step_triggered TEXT NOT NULL,
                        reason TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
        except Exception as exc:
            logger.error("Error inicializando base de datos agent_audit.db: %s", exc)

    def log_decision(
        self,
        signal: Dict[str, Any],
        decision: Dict[str, Any],
        send_telegram: bool = True,
    ) -> Optional[int]:
        """
        Guarda la evaluación en `agent_audit.db` y envía alerta por Telegram si está configurado.

        Parámetros:
          - signal: dict con 'strategy', 'symbol', 'direction', 'entry_price', 'stop_loss'/'sl', 'take_profit'/'tp'
          - decision: dict devuelto por `TradingAgentJudge.evaluate_signal`
          - send_telegram: si True y existen credenciales en .env, envía notificación a Telegram
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        strategy = str(signal.get("strategy") or signal.get("strategy_id") or "ORACLE_STRATEGY")
        symbol = str(signal.get("symbol") or signal.get("ticker") or "UNKNOWN")
        direction = str(signal.get("direction") or signal.get("side") or "LONG").upper()

        def _to_float_or_none(val: Any) -> Optional[float]:
            if val is None or val == "":
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        entry_price = _to_float_or_none(
            signal.get("entry_price") if "entry_price" in signal else signal.get("price")
        )
        stop_loss = _to_float_or_none(
            signal.get("stop_loss") if "stop_loss" in signal else signal.get("sl")
        )
        take_profit = _to_float_or_none(
            signal.get("take_profit") if "take_profit" in signal else signal.get("tp")
        )

        allow_trade = bool(decision.get("allow_trade", True))
        approved_int = 1 if allow_trade else 0
        step_triggered = str(decision.get("step_triggered") or "UNKNOWN_STEP")
        reason = str(decision.get("reason") or "Sin motivo especificado")

        row_id: Optional[int] = None
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO agent_audit_log (
                        timestamp, strategy, symbol, direction,
                        entry_price, stop_loss, take_profit,
                        approved, step_triggered, reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        now_iso,
                        strategy,
                        symbol,
                        direction,
                        entry_price,
                        stop_loss,
                        take_profit,
                        approved_int,
                        step_triggered,
                        reason,
                    ),
                )
                row_id = cursor.lastrowid
                conn.commit()
        except Exception as exc:
            logger.error("Error registrando decisión en agent_audit.db: %s", exc)

        if send_telegram and self.telegram_token and self.telegram_chat_id:
            self._send_telegram_alert(
                timestamp=now_iso,
                strategy=strategy,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                allow_trade=allow_trade,
                step_triggered=step_triggered,
                reason=reason,
            )

        return row_id

    def _send_telegram_alert(
        self,
        *,
        timestamp: str,
        strategy: str,
        symbol: str,
        direction: str,
        entry_price: Optional[float],
        stop_loss: Optional[float],
        take_profit: Optional[float],
        allow_trade: bool,
        step_triggered: str,
        reason: str,
    ) -> bool:
        """Envía el reporte de intercepción a Telegram de forma no bloqueante (fail-safe)."""
        status_header = (
            "✅ APROBADA POR IA"
            if allow_trade
            else "🛑 FRENADA POR NOTICIAS (MODO ESPEJO)"
        )
        entry_str = f"${entry_price:,.2f}" if entry_price is not None else "MKT / N/A"
        sl_str = f"${stop_loss:,.2f}" if stop_loss is not None else "N/A"
        tp_str = f"${take_profit:,.2f}" if take_profit is not None else "N/A"

        text = (
            f"🤖 *ORACLE AI RISK & NEWS INTERCEPTOR*\n"
            f"Estado: *{status_header}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• *Estrategia:* `{strategy}`\n"
            f"• *Símbolo:* `{symbol}` ({direction})\n"
            f"• *Entrada Teórica:* `{entry_str}`\n"
            f"• *Stop Loss (SL):* `{sl_str}`\n"
            f"• *Take Profit (TP):* `{tp_str}`\n"
            f"• *Fase / Nivel:* `{step_triggered}`\n"
            f"• *Razón:* {reason}\n"
            f"• *Timestamp:* `{timestamp}`"
        )

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = json.dumps(
            {
                "chat_id": self.telegram_chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }
        ).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status == 200
        except Exception as exc:
            logger.warning("No se pudo enviar alerta de ShadowLogger a Telegram: %s", exc)
            return False

    @staticmethod
    def _fetch_current_price(symbol: str, quote_ctx: Any = None) -> Optional[float]:
        """
        Obtiene el precio actual del activo usando `quote_ctx.get_market_snapshot` de Moomoo
        si está disponible, o `yfinance` como respaldo.
        """
        raw_sym = str(symbol or "").strip().upper()
        moo_code = raw_sym if "." in raw_sym else f"US.{raw_sym}"
        clean_sym = raw_sym.split(".")[-1] if "." in raw_sym else raw_sym

        # 1. Intentar con quote_ctx de Moomoo si fue proporcionado
        if quote_ctx is not None:
            try:
                ret, data = quote_ctx.get_market_snapshot([moo_code])
                if ret == 0 and data is not None and not data.empty:
                    for col in ("last_price", "cur_price", "close_price"):
                        if col in data.columns:
                            val = float(data.iloc[0][col])
                            if val > 0:
                                return val
            except Exception as exc:
                logger.debug("Fallback desde Moomoo quote_ctx para %s: %s", moo_code, exc)

        # 2. Respaldo con yfinance
        try:
            import yfinance as yf

            ticker = yf.Ticker(clean_sym)
            try:
                last_px = float(ticker.fast_info.get("last_price") or 0.0)
                if last_px > 0:
                    return last_px
            except Exception:
                pass
            hist = ticker.history(period="1d", interval="1m")
            if hist is not None and not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception as exc:
            logger.warning("No se pudo obtener precio actual para %s: %s", clean_sym, exc)

        return None

    def generate_daily_audit_report(self, quote_ctx: Any = None) -> str:
        """
        Evalúa las decisiones registradas hoy en `agent_audit.db` y calcula el
        PnL teórico en modo espejo de las operaciones frenadas por la IA.
        """
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rows = []
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                rows = conn.execute(
                    """
                    SELECT id, timestamp, strategy, symbol, direction,
                           entry_price, stop_loss, take_profit,
                           approved, step_triggered, reason
                    FROM agent_audit_log
                    WHERE substr(timestamp, 1, 10) = ?
                    ORDER BY id ASC
                    """,
                    (today_utc,),
                ).fetchall()
        except Exception as exc:
            logger.error("Error leyendo agent_audit.db para auditoría diaria: %s", exc)
            return f"⚠️ *AUDITORÍA IA ({today_utc})*\nError leyendo `agent_audit.db`: `{exc}`"

        total_count = len(rows)
        approved_rows = [r for r in rows if int(r[8]) == 1]
        blocked_rows = [r for r in rows if int(r[8]) == 0]

        lines = [
            f"📊 *AUDITORÍA DIARIA DEL AGENTE IA ({today_utc} UTC)*",
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"• *Señales Evaluadas Hoy:* `{total_count}`",
            f"• ✅ *Aprobadas:* `{len(approved_rows)}`",
            f"• 🛑 *Frenadas por IA / Riesgo:* `{len(blocked_rows)}`",
        ]

        if not blocked_rows:
            lines.append("\n_No hubo operaciones frenadas en lo que va del día._")
            return "\n".join(lines)

        lines.append("\n🔍 *EVALUACIÓN MODO ESPEJO (OPERACIONES FRENADAS):*")
        net_saved_usd = 0.0
        evaluated_count = 0

        for r in blocked_rows:
            row_id, _ts, strategy, symbol, direction, entry, sl, tp, _app, step, reason = r
            current_price = self._fetch_current_price(symbol, quote_ctx=quote_ctx)

            if entry is None or current_price is None:
                lines.append(
                    f"\n• `#{row_id}` *{symbol}* (`{direction}` | `{strategy}`)\n"
                    f"  └ Fase: `{step}` | Precio actual o entrada N/D"
                )
                continue

            is_short = str(direction).upper() in ("SHORT", "SELL")
            theoretical_pnl = (entry - current_price) if is_short else (current_price - entry)
            pnl_pct = (theoretical_pnl / entry) * 100.0 if entry else 0.0
            evaluated_count += 1
            # Si el trade teórico hubiera perdido dinero (< 0), el bloqueo nos ahorró esa pérdida (> 0)
            net_saved_usd += -theoretical_pnl

            hit_note = ""
            if sl is not None and tp is not None:
                if (not is_short and current_price <= sl) or (is_short and current_price >= sl):
                    hit_note = " (Habría tocado Stop Loss)"
                elif (not is_short and current_price >= tp) or (is_short and current_price <= tp):
                    hit_note = " (Habría tocado Take Profit)"

            if theoretical_pnl < 0:
                verdict_str = (
                    f"🛡️ *Ahorró una pérdida* de `${abs(theoretical_pnl):,.2f}`/acc "
                    f"({pnl_pct:+.2f}%){hit_note}"
                )
            elif theoretical_pnl > 0:
                verdict_str = (
                    f"⚠️ *Frenó una ganancia* de `+${theoretical_pnl:,.2f}`/acc "
                    f"({pnl_pct:+.2f}%){hit_note}"
                )
            else:
                verdict_str = f"➖ *Neutral* (`$0.00`/acc){hit_note}"

            sl_txt = f"${sl:,.2f}" if sl is not None else "N/A"
            tp_txt = f"${tp:,.2f}" if tp is not None else "N/A"
            lines.append(
                f"\n• `#{row_id}` *{symbol}* (`{direction}` | `{strategy}`)\n"
                f"  ├ Entrada Teórica: `${entry:,.2f}` │ Actual: `${current_price:,.2f}`\n"
                f"  ├ SL: `{sl_txt}` │ TP: `{tp_txt}` │ Fase: `{step}`\n"
                f"  ├ Motivo: _{reason[:110]}_\n"
                f"  └ Resultado Espejo: {verdict_str}"
            )

        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━")
        if evaluated_count > 0:
            balance_emoji = "🟢" if net_saved_usd >= 0 else "🔴"
            balance_label = (
                "Ahorro neto gracias a bloqueos"
                if net_saved_usd >= 0
                else "Costo de oportunidad neto por bloqueos"
            )
            lines.append(
                f"{balance_emoji} *Balance Modo Espejo ({evaluated_count} ops/acc):* "
                f"`{net_saved_usd:+,.2f} USD` ({balance_label})"
            )
        else:
            lines.append("ℹ️ _Sin precios disponibles para calcular balance teórico._")

        return "\n".join(lines)

    def send_audit_report_to_telegram(
        self, quote_ctx: Any = None, chat_id: Optional[str | int] = None
    ) -> bool:
        """Genera y envía el reporte diario de auditoría IA a Telegram."""
        target_chat = str(chat_id or self.telegram_chat_id).strip()
        if not self.telegram_token or not target_chat:
            logger.warning("Telegram no configurado; no se puede enviar reporte de auditoría IA.")
            return False

        report_text = self.generate_daily_audit_report(quote_ctx=quote_ctx)
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = json.dumps(
            {
                "chat_id": target_chat,
                "text": report_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }
        ).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                return resp.status == 200
        except Exception as exc:
            logger.warning("Error enviando reporte /auditoria_ia a Telegram: %s", exc)
            return False
