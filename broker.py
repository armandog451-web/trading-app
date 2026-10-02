import logging
from config import (
    BROKER, ALPACA_API_KEY, ALPACA_API_SECRET, ALPACA_BASE_URL,
    MOOMOO_HOST, MOOMOO_PORT, DEMO_CAPITAL
)
from database import log_event

logger = logging.getLogger(__name__)

# Simulated in-memory portfolio for Alpaca fallback if keys not provided
_sim_portfolio = {
    "cash": DEMO_CAPITAL,
    "equity": DEMO_CAPITAL,
    "positions": {}
}

class BrokerManager:
    def __init__(self):
        self.active_broker = BROKER
        self.alpaca_client = None
        self.moomoo_acc_id = 2837131  # Cuenta Demo / Simulate en Moomoo OpenD
        self._init_alpaca()

    def _init_alpaca(self):
        if ALPACA_API_KEY and ALPACA_API_SECRET and "<YOUR_" not in ALPACA_API_KEY:
            try:
                import alpaca_trade_api as tradeapi
                self.alpaca_client = tradeapi.REST(
                    ALPACA_API_KEY, ALPACA_API_SECRET, ALPACA_BASE_URL, api_version='v2'
                )
                logger.info("Cliente Alpaca Paper autenticado exitosamente.")
            except Exception as e:
                logger.warning(f"No se pudo conectar a Alpaca REST: {e}")
                self.alpaca_client = None

    def get_account_summary(self):
        """Retorna balance y estado de la cuenta según el broker activo."""
        # 1. MOOMOO OPEND EN VIVO
        if self.active_broker == "moomoo":
            try:
                import moomoo as ft
                trd_ctx = ft.OpenSecTradeContext(filter_trdmarket=ft.TrdMarket.US, host=MOOMOO_HOST, port=MOOMOO_PORT)
                ret, funds = trd_ctx.accinfo_query(trd_env=ft.TrdEnv.SIMULATE, acc_id=self.moomoo_acc_id)
                trd_ctx.close()
                if ret == 0 and not funds.empty:
                    row = funds.iloc[0]
                    return {
                        "broker": "Moomoo OpenD (Paper Account)",
                        "account_id": self.moomoo_acc_id,
                        "status": "Conectado en Vivo (127.0.0.1:11111)",
                        "cash": float(row["cash"]),
                        "equity": float(row["total_assets"]),
                        "buying_power": float(row["power"]),
                        "is_simulated": False
                    }
            except Exception as e:
                logger.warning(f"Error consultando Moomoo OpenD: {e}")

        # 2. ALPACA PAPER EN VIVO
        if self.active_broker == "alpaca" and self.alpaca_client:
            try:
                acc = self.alpaca_client.get_account()
                return {
                    "broker": "Alpaca Paper Trading",
                    "status": "Conectado en Vivo (API Real Paper)",
                    "cash": float(acc.cash),
                    "equity": float(acc.equity),
                    "buying_power": float(acc.buying_power),
                    "is_simulated": False
                }
            except Exception as e:
                logger.warning(f"Error obteniendo cuenta Alpaca: {e}")

        # 3. MOTOR DEMO SIMULADO (Fallback)
        return {
            "broker": "Alpaca Paper Demo" if self.active_broker == "alpaca" else "Moomoo OpenD Demo",
            "status": "Activo y Operativo (Demo Interno)",
            "cash": _sim_portfolio["cash"],
            "equity": _sim_portfolio["equity"],
            "buying_power": _sim_portfolio["cash"] * 2.0,
            "is_simulated": True
        }

    def get_positions(self):
        """Retorna lista de posiciones abiertas."""
        if self.active_broker == "moomoo":
            try:
                import moomoo as ft
                trd_ctx = ft.OpenSecTradeContext(filter_trdmarket=ft.TrdMarket.US, host=MOOMOO_HOST, port=MOOMOO_PORT)
                ret, pos = trd_ctx.position_list_query(trd_env=ft.TrdEnv.SIMULATE, acc_id=self.moomoo_acc_id)
                trd_ctx.close()
                if ret == 0 and not pos.empty:
                    res = []
                    for _, p in pos.iterrows():
                        res.append({
                            "symbol": p["code"].replace("US.", ""),
                            "qty": int(p["qty"]),
                            "side": "BUY" if p["qty"] > 0 else "SELL",
                            "avg_entry_price": float(p["cost_price"]),
                            "current_price": float(p["nominal_price"]),
                            "unrealized_pl": float(p["pl_val"]),
                            "unrealized_plpc": float(p["pl_ratio"]) * 100
                        })
                    return res
            except Exception as e:
                logger.warning(f"Error obteniendo posiciones Moomoo: {e}")

        if self.active_broker == "alpaca" and self.alpaca_client:
            try:
                positions = self.alpaca_client.list_positions()
                return [
                    {
                        "symbol": p.symbol,
                        "qty": int(p.qty),
                        "side": p.side,
                        "avg_entry_price": float(p.avg_entry_price),
                        "current_price": float(p.current_price),
                        "unrealized_pl": float(p.unrealized_pl),
                        "unrealized_plpc": float(p.unrealized_plpc) * 100
                    }
                    for p in positions
                ]
            except Exception:
                pass

        # Posiciones simuladas fallback
        res = []
        for sym, pos in _sim_portfolio["positions"].items():
            res.append({
                "symbol": sym,
                "qty": pos["qty"],
                "side": pos["side"],
                "avg_entry_price": pos["price"],
                "current_price": pos["price"] * 1.004,
                "unrealized_pl": (pos["price"] * 0.004) * pos["qty"],
                "unrealized_plpc": 0.40
            })
        return res

    def execute_order(self, symbol: str, side: str, qty: int, price: float, stop_loss: float = 0.0, take_profit: float = 0.0):
        """Ejecuta una orden de compra o venta en Moomoo OpenD, Alpaca o simulador."""
        # 1. MOOMOO OPEND EXECUTION
        if self.active_broker == "moomoo":
            try:
                import moomoo as ft
                trd_ctx = ft.OpenSecTradeContext(filter_trdmarket=ft.TrdMarket.US, host=MOOMOO_HOST, port=MOOMOO_PORT)
                trd_side = ft.TrdSide.BUY if side.upper() == "BUY" else ft.TrdSide.SELL
                ret, data = trd_ctx.place_order(
                    price=price,
                    qty=qty,
                    code=f"US.{symbol}",
                    trd_side=trd_side,
                    order_type=ft.OrderType.MARKET,
                    trd_env=ft.TrdEnv.SIMULATE,
                    acc_id=self.moomoo_acc_id
                )
                trd_ctx.close()
                if ret == 0:
                    order_id = str(data["order_id"].iloc[0])
                    log_event("SUCCESS", f"Orden Moomoo OpenD ejecutada: {side} {qty} {symbol} ID: {order_id}")
                    return {"success": True, "order_id": order_id, "broker": "Moomoo OpenD"}
                else:
                    logger.warning(f"Moomoo error: {data}")
            except Exception as e:
                logger.error(f"Error ejecutando en Moomoo OpenD: {e}")

        # 2. ALPACA EXECUTION
        if self.active_broker == "alpaca" and self.alpaca_client:
            try:
                order = self.alpaca_client.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side.lower(),
                    type="market",
                    time_in_force="day"
                )
                log_event("SUCCESS", f"Orden Alpaca ejecutada: {side} {qty} {symbol} ID: {order.id}")
                return {"success": True, "order_id": order.id, "broker": "Alpaca"}
            except Exception as e:
                log_event("ERROR", f"Fallo al enviar a Alpaca: {e}")

        # 3. SIMULADOR FALLBACK
        cost = qty * price
        if side.upper() == "BUY":
            _sim_portfolio["cash"] -= cost
            _sim_portfolio["positions"][symbol] = {
                "qty": _sim_portfolio["positions"].get(symbol, {}).get("qty", 0) + qty,
                "side": "BUY",
                "price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }
        else:
            _sim_portfolio["cash"] += cost
            if symbol in _sim_portfolio["positions"]:
                _sim_portfolio["positions"].pop(symbol, None)

        log_event("INFO", f"Orden Demo ejecutada en Simulador: {side} {qty} {symbol} @ ${price:.2f}")
        return {"success": True, "order_id": f"SIM-{symbol}-{side}", "broker": "Simulador Demo"}

    def close_position(self, symbol: str):
        """Cierra completamente una posición abierta (sincronización inmediata)."""
        positions = self.get_positions()
        for p in positions:
            if p["symbol"] == symbol:
                close_side = "SELL" if p["side"] == "BUY" else "BUY"
                qty = abs(p["qty"])
                result = self.execute_order(
                    symbol=symbol, side=close_side,
                    qty=qty, price=p["current_price"]
                )
                log_event("INFO", f"Posición {symbol} cerrada por sincronización: {close_side} {qty} @ ${p['current_price']:.2f}")
                return result
        return {"success": False, "message": f"No se encontró posición abierta para {symbol}"}

    def close_all_positions(self):
        """Cierra TODAS las posiciones abiertas (barrido forzoso intradía)."""
        positions = self.get_positions()
        results = []
        for p in positions:
            close_side = "SELL" if p["side"] == "BUY" else "BUY"
            res = self.execute_order(
                symbol=p["symbol"], side=close_side,
                qty=abs(p["qty"]), price=p["current_price"]
            )
            results.append({"symbol": p["symbol"], "result": res})
            log_event("WARNING", f"Auto-cierre forzoso: {close_side} {abs(p['qty'])} {p['symbol']} @ ${p['current_price']:.2f}")
        return results

    def get_total_unrealized_pnl(self):
        """Retorna P&L no realizado total de todas las posiciones."""
        positions = self.get_positions()
        return sum(p.get("unrealized_pl", 0.0) for p in positions)

    def has_open_position(self, symbol: str) -> bool:
        """Verifica si hay posición abierta para un símbolo (evita colisiones)."""
        positions = self.get_positions()
        return any(p["symbol"] == symbol for p in positions)

broker_manager = BrokerManager()
