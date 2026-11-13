"""
Script CLI: audit_report.py
===========================
Genera el reporte diario de auditoría del Agente Interceptor de Noticias y Riesgo IA
(evaluando en modo espejo las operaciones frenadas) y opcionalmente lo envía a Telegram.

Uso:
  python audit_report.py
  python audit_report.py --telegram
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv(override=False)

from shadow_logger import ShadowLogger


def _try_open_moomoo_quote_ctx():
    """Intenta abrir un OpenQuoteContext de Moomoo OpenD si está escuchando."""
    try:
        import socket
        import moomoo as ft

        host = os.getenv("MOOMOO_HOST", "127.0.0.1")
        port = int(os.getenv("MOOMOO_PORT", "11111"))
        with socket.create_connection((host, port), timeout=0.5):
            pass
        return ft.OpenQuoteContext(host=host, port=port)
    except Exception:
        return None


def main() -> None:
    send_tg = "--telegram" in sys.argv
    shadow = ShadowLogger()
    quote_ctx = _try_open_moomoo_quote_ctx()
    try:
        report = shadow.generate_daily_audit_report(quote_ctx=quote_ctx)
        print(report)
        if send_tg:
            ok = shadow.send_audit_report_to_telegram(quote_ctx=quote_ctx)
            print(f"\n[Telegram] Envío de /auditoria_ia: {'OK ✅' if ok else 'FALLÓ ❌'}")
    finally:
        if quote_ctx is not None:
            try:
                quote_ctx.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
