import asyncio
from datetime import datetime
from app.core.broker_manager import broker_manager
from app.core.notifier import notifier

def format_balance_message(acc: dict, pos: list) -> str:
    equity = acc.get("equity", 0.0)
    cash = acc.get("cash", 0.0)
    market_val = acc.get("market_val", 0.0)
    buying_power = acc.get("buying_power", 0.0)
    margin_ratio = acc.get("margin_ratio", 2.0)
    maint_margin = acc.get("maintenance_margin", 0.0)
    daily_pnl = acc.get("daily_pnl", 0.0)
    daily_pnl_pct = acc.get("daily_pnl_pct", 0.0)
    mode = acc.get("mode", "MOOMOO")
    now_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    pnl_sign = "+" if daily_pnl > 0 else ""
    pnl_emoji = "🟢" if daily_pnl >= 0 else "🔴"
    status_label = "Ganando" if daily_pnl >= 0 else "Perdiendo"

    # Desglose de posiciones limpio con indicadores visuales
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
        f"⚡ *Poder de Compra (Margen {margin_ratio:.1f}x):* `${buying_power:,.2f}`\n"
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
    return msg

async def send_balance_telegram():
    acc = await broker_manager.get_account()
    pos = await broker_manager.get_positions()
    msg = format_balance_message(acc, pos)
    success = await notifier.send_alert("Estado de Cuenta y Posiciones Moomoo", msg, level="INFO")
    print(f"Despacho a Telegram exitoso: {success}")

if __name__ == "__main__":
    asyncio.run(send_balance_telegram())
