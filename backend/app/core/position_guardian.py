import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any, Optional

from app.database import SessionLocal
from app.models.db_models import Trade, BotLog
from app.core.notifier import notifier
from app.core.broker_manager import broker_manager

logger = logging.getLogger(__name__)

class PositionGuardian:
    """
    Guardián Automático de Posiciones (Stop Loss & Take Profit Engine).
    Monitorea de forma continua cada 3 segundos todas las posiciones abiertas
    en Moomoo (o Simulador). Si el precio toca o supera el Stop Loss o Take Profit,
    ejecuta la orden de cierre en el broker de forma 100% automática y envía
    la confirmación a Telegram.
    El usuario NO tiene que hacer nada manualmente.
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        # Registro en memoria de targets por símbolo: {symbol: {stop_loss, take_profit, qty, side, entry_price, asset_type}}
        self._targets: Dict[str, Dict[str, Any]] = {}
        self._last_prices: Dict[str, float] = {}

    def start(self):
        """Inicia el guardián en segundo plano."""
        if not self._running:
            self._running = True
            self._load_open_targets_from_db()
            self._task = asyncio.create_task(self._monitor_loop())
            logger.info("PositionGuardian iniciado: Monitoreo continuo de Stop Loss y Take Profit activo.")

    def stop(self):
        """Detiene el guardián."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
        logger.info("PositionGuardian detenido.")

    def register_target(
        self,
        symbol: str,
        stop_loss: float,
        take_profit: float,
        qty: float,
        side: str = "BUY",
        entry_price: float = 0.0,
        asset_type: str = "STOCK"
    ):
        """Registra o actualiza los niveles de SL y TP para supervisión automática."""
        clean_symbol = symbol.replace("US.", "").upper()
        raw_symbol = symbol.upper()
        target_data = {
            "symbol": clean_symbol,
            "raw_symbol": raw_symbol,
            "stop_loss": round(float(stop_loss), 2),
            "take_profit": round(float(take_profit), 2),
            "qty": float(qty),
            "side": side.upper(),
            "entry_price": round(float(entry_price), 2),
            "asset_type": asset_type.upper(),
            "created_at": datetime.utcnow()
        }
        self._targets[clean_symbol] = target_data
        self._targets[raw_symbol] = target_data
        self._last_prices[clean_symbol] = entry_price
        self._last_prices[raw_symbol] = entry_price
        logger.info(
            f"PositionGuardian target registrado para {clean_symbol}: "
            f"Entrada ${entry_price:.2f} | SL: ${stop_loss:.2f} | TP: ${take_profit:.2f} | Cant: {qty}"
        )

    def _load_open_targets_from_db(self):
        """Carga trades abiertos desde SQLite para que persistan ante reinicios del backend."""
        try:
            with SessionLocal() as db:
                open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()
                for t in open_trades:
                    sym = t.symbol.replace("US.", "").upper()
                    self._targets[sym] = {
                        "symbol": sym,
                        "stop_loss": t.stop_loss,
                        "take_profit": t.take_profit,
                        "qty": t.quantity,
                        "side": t.side,
                        "entry_price": t.entry_price,
                        "asset_type": "OPTION" if len(sym) > 10 else "STOCK",
                        "trade_id": t.id
                    }
                    self._last_prices[sym] = t.entry_price
                if open_trades:
                    logger.info(f"PositionGuardian: {len(open_trades)} trades abiertos cargados desde base de datos.")
        except Exception as e:
            logger.error(f"Error cargando trades abiertos en PositionGuardian: {e}")

    async def _monitor_loop(self):
        """Bucle asíncrono de verificación continua de precios vs SL/TP."""
        while self._running:
            try:
                positions = await broker_manager.get_positions()
                
                for pos in positions:
                    raw_sym = pos.get("symbol", "")
                    clean_sym = raw_sym.replace("US.", "").upper()
                    cur_price = float(pos.get("current_price", 0.0))
                    qty = abs(float(pos.get("qty", 1)))
                    side = pos.get("side", "BUY").upper()

                    # Si el broker no provee SL/TP en el objeto pos, buscar en targets registrados
                    target = self._targets.get(clean_sym) or self._targets.get(raw_sym)
                    
                    sl = float(pos.get("stop_loss") or (target.get("stop_loss") if target else 0.0) or 0.0)
                    tp = float(pos.get("take_profit") or (target.get("take_profit") if target else 0.0) or 0.0)
                    entry_p = float(pos.get("avg_entry_price") or (target.get("entry_price") if target else cur_price) or cur_price)
                    
                    if cur_price <= 0.0:
                        continue

                    # 1. Verificar Stop Loss (Para BUY: precio actual <= stop_loss)
                    if sl > 0.0 and side == "BUY" and cur_price <= sl:
                        await self._execute_exit(
                            symbol=raw_sym,
                            clean_symbol=clean_sym,
                            qty=qty,
                            side="SELL",
                            exit_price=cur_price,
                            target_price=sl,
                            entry_price=entry_p,
                            exit_reason="STOP_LOSS",
                            target=target
                        )
                        continue

                    # 2. Verificar Take Profit (Para BUY: precio actual >= take_profit)
                    if tp > 0.0 and side == "BUY" and cur_price >= tp:
                        await self._execute_exit(
                            symbol=raw_sym,
                            clean_symbol=clean_sym,
                            qty=qty,
                            side="SELL",
                            exit_price=cur_price,
                            target_price=tp,
                            entry_price=entry_p,
                            exit_reason="TAKE_PROFIT",
                            target=target
                        )
                        continue

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en PositionGuardian monitor_loop: {e}")

            await asyncio.sleep(3)

    async def _execute_exit(
        self,
        symbol: str,
        clean_symbol: str,
        qty: float,
        side: str,
        exit_price: float,
        target_price: float,
        entry_price: float,
        exit_reason: str,
        target: Optional[Dict[str, Any]]
    ):
        """Ejecuta el cierre automático en Moomoo, registra en BD y notifica a Telegram."""
        logger.warning(
            f"🚨 PositionGuardian DISPARADO: {exit_reason} en {clean_symbol}! "
            f"Precio actual ${exit_price:.2f} (Target: ${target_price:.2f})"
        )

        # 1. Enviar orden de venta de mercado a Moomoo
        close_res = await broker_manager.submit_bracket_order(
            symbol=symbol,
            qty=qty,
            side=side,
            entry_price=exit_price,
            stop_loss=0.0,
            take_profit=0.0,
            order_type="market"
        )

        broker_name = broker_manager.get_active_broker_name()
        order_id = close_res.get("order_id", "AUTO_CLOSE")

        # 2. Calcular PnL
        pnl_dollars = round((exit_price - entry_price) * qty, 2)
        pnl_pct = round(((exit_price - entry_price) / entry_price) * 100.0, 2) if entry_price > 0 else 0.0

        # 3. Actualizar registro en base de datos SQLite
        try:
            with SessionLocal() as db:
                trade = db.query(Trade).filter(
                    Trade.symbol.like(f"%{clean_symbol}%"),
                    Trade.status == "OPEN"
                ).first()

                if trade:
                    trade.status = "CLOSED"
                    trade.exit_price = exit_price
                    trade.exit_time = datetime.utcnow()
                    trade.exit_reason = exit_reason
                    trade.pnl = pnl_dollars
                    trade.pnl_pct = pnl_pct
                    db.commit()

                bot_log = BotLog(
                    level="TRADE",
                    module="position_guardian",
                    message=f"{exit_reason} ejecutado en {broker_name} para {clean_symbol} a ${exit_price:.2f} (PnL: ${pnl_dollars:+.2f} / {pnl_pct:+.1f}%)"
                )
                db.add(bot_log)
                db.commit()
        except Exception as db_err:
            logger.error(f"Error actualizando trade cerrado en DB: {db_err}")

        # 4. Limpiar del registro de monitoreo
        self._targets.pop(clean_symbol, None)
        self._targets.pop(symbol, None)

        # 5. Notificación institucional a Telegram
        is_tp = exit_reason == "TAKE_PROFIT"
        badge = "🎯 ¡TAKE PROFIT ALCANZADO!" if is_tp else "🛑 STOP LOSS EJECUTADO"
        pnl_sign = "+" if pnl_dollars >= 0 else ""
        icon = "🎉 Ganancia asegurada" if is_tp else "🛡️ Pérdida acotada y protegida"

        msg = (
            f"*{badge}* ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ *Activo:* `{clean_symbol}`\n"
            f"📥 *Precio Entrada:* `${entry_price:.2f}`\n"
            f"📤 *Precio Salida ({exit_reason}):* `${exit_price:.2f}`\n"
            f"💵 *Resultado P&L:* `{pnl_sign}${pnl_dollars:.2f}` ({pnl_sign}{pnl_pct:.1f}%)\n"
            f"📦 *Contratos/Acciones:* `{int(qty)}`\n"
            f"🏦 *Broker:* `{broker_name}` (Orden: `{order_id}`)\n"
            f"🤖 *Ejecución:* 100% Automática ({icon}).\n"
            f"⏰ *Hora:* `{datetime.utcnow().strftime('%H:%M:%S UTC')}`"
        )

        level = "INFO" if is_tp else "WARN"
        await notifier.send_alert(
            title=f"{badge} en {broker_name}",
            message=msg,
            level=level
        )

position_guardian = PositionGuardian()
