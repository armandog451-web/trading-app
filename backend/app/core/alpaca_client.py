import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class AlpacaBroker:
    """
    Adaptador de ejecución para Alpaca Markets (Paper y Live).
    Soporta Bracket Orders nativas (Entrada + Stop Loss + Take Profit como OCO),
    consulta de posiciones, buying power y botón de pánico de emergencia (close_all).
    Incluye emulación local inteligente si las claves no se han configurado aún.
    """

    def __init__(self):
        self.api_key = settings.ALPACA_API_KEY
        self.secret_key = settings.ALPACA_SECRET_KEY
        self.base_url = settings.ALPACA_BASE_URL
        self.is_paper = settings.ALPACA_PAPER
        
        # Estado simulado para pruebas iniciales o modo offline
        self._sim_equity = 100000.0
        self._sim_cash = 100000.0
        self._sim_positions = {}
        self._sim_orders = []

    @property
    def has_real_credentials(self) -> bool:
        return bool(self.api_key and self.secret_key and len(self.api_key) > 5)

    def _get_headers(self) -> dict:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        }

    def _get_client(self, timeout: float = 6.0) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout, verify=settings.SSL_VERIFY)

    async def test_credentials(self, api_key: str, secret_key: str, is_paper: bool = True) -> dict:
        """Prueba las credenciales API enviando un GET /v2/account directamente a Alpaca."""
        api_key = api_key.strip()
        secret_key = secret_key.strip()

        if not api_key or not secret_key:
            return {"success": False, "error": "Ingresa tu API Key ID y Secret Key de Alpaca."}

        base_url = "https://paper-api.alpaca.markets" if is_paper else "https://api.alpaca.markets"
        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "Content-Type": "application/json"
        }
        try:
            async with self._get_client(timeout=6.0) as client:
                resp = await client.get(f"{base_url}/v2/account", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    eq = float(data.get("equity", 0.0))
                    bp = float(data.get("buying_power", 0.0))
                    status_str = data.get("status", "ACTIVE")
                    mode_str = "Paper Trading" if is_paper else "Real (Live)"
                    return {
                        "success": True,
                        "equity": eq,
                        "buying_power": bp,
                        "status": status_str,
                        "mode": mode_str,
                        "message": f"¡Cuenta Alpaca ({mode_str}) verificada! Equity: ${eq:,.2f} | Buying Power: ${bp:,.2f}"
                    }
                else:
                    err_detail = resp.json().get("message", resp.text) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                    return {
                        "success": False,
                        "error": f"Error de autenticación en Alpaca ({resp.status_code}): {err_detail}. Verifica si elegiste el modo correcto (Paper vs Live)."
                    }
        except Exception as e:
            return {"success": False, "error": f"Error de conexión con Alpaca: {str(e)}"}

    async def get_account(self) -> dict:

        """Obtiene información de la cuenta, balance, equity y poder de compra."""
        if self.has_real_credentials:
            try:
                async with self._get_client(timeout=5.0) as client:

                    resp = await client.get(f"{self.base_url}/v2/account", headers=self._get_headers())
                    if resp.status_code == 200:
                        data = resp.json()
                        equity = float(data.get("equity", 100000.0))
                        last_equity = float(data.get("last_equity", equity))
                        daily_pnl = equity - last_equity
                        return {
                            "equity": equity,
                            "cash": float(data.get("cash", equity)),
                            "buying_power": float(data.get("buying_power", equity * 2)),
                            "daily_pnl": round(daily_pnl, 2),
                            "daily_pnl_pct": round((daily_pnl / last_equity) * 100.0 if last_equity > 0 else 0.0, 2),
                            "mode": "PAPER" if self.is_paper else "LIVE",
                            "status": data.get("status", "ACTIVE")
                        }
            except Exception as e:
                logger.error(f"Error consultando cuenta en Alpaca: {e}")

        # Fallback a cuenta simulada
        unrealized = sum(p["unrealized_pnl"] for p in self._sim_positions.values())
        return {
            "equity": round(self._sim_cash + unrealized, 2),
            "cash": round(self._sim_cash, 2),
            "buying_power": round(self._sim_cash * 2.0, 2),
            "daily_pnl": round(unrealized, 2),
            "daily_pnl_pct": round((unrealized / self._sim_equity) * 100.0, 2),
            "mode": "PAPER (Simulado)" if not self.has_real_credentials else ("PAPER" if self.is_paper else "LIVE"),
            "status": "ACTIVE"
        }

    async def get_positions(self) -> list[dict]:
        """Obtiene las posiciones abiertas actualmente."""
        if self.has_real_credentials:
            try:
                async with self._get_client(timeout=5.0) as client:
                    resp = await client.get(f"{self.base_url}/v2/positions", headers=self._get_headers())
                    if resp.status_code == 200:
                        positions = []
                        for p in resp.json():
                            positions.append({
                                "symbol": p["symbol"],
                                "qty": float(p["qty"]),
                                "side": p["side"].upper(),
                                "avg_entry_price": float(p["avg_entry_price"]),
                                "current_price": float(p["current_price"]),
                                "unrealized_pnl": round(float(p["unrealized_pl"]), 2),
                                "unrealized_pnl_pct": round(float(p["unrealized_plpc"]) * 100.0, 2)
                            })
                        return positions
            except Exception as e:
                logger.error(f"Error consultando posiciones en Alpaca: {e}")

        return list(self._sim_positions.values())

    async def submit_bracket_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        order_type: str = "market"
    ) -> dict:
        """
        Envía una Bracket Order institucional:
        Orden de entrada con Stop-Loss y Take-Profit automáticos OCO gestionados por el broker.
        """
        side_lower = side.lower()
        payload = {
            "symbol": symbol.upper(),
            "qty": str(qty),
            "side": side_lower,
            "type": order_type,
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit": {
                "limit_price": str(round(take_profit, 2))
            },
            "stop_loss": {
                "stop_price": str(round(stop_loss, 2))
            }
        }

        if order_type == "limit":
            payload["limit_price"] = str(round(entry_price, 2))

        if self.has_real_credentials:
            try:
                async with self._get_client(timeout=6.0) as client:
                    resp = await client.post(f"{self.base_url}/v2/orders", json=payload, headers=self._get_headers())
                    if resp.status_code in (200, 201):
                        order_data = resp.json()
                        logger.info(f"Bracket order ejecutada en Alpaca: {order_data.get('id')}")
                        return {
                            "success": True,
                            "order_id": order_data.get("id"),
                            "symbol": symbol,
                            "qty": qty,
                            "status": order_data.get("status", "SUBMITTED"),
                            "data": order_data
                        }
                    else:
                        error_msg = resp.text
                        logger.error(f"Error de Alpaca al enviar orden: {error_msg}")
                        return {"success": False, "error": error_msg}
            except Exception as e:
                logger.error(f"Fallo de conexión enviando orden a Alpaca: {e}")
                return {"success": False, "error": str(e)}

        # Registro simulado
        sim_id = f"sim_ord_{len(self._sim_orders) + 1}"
        self._sim_positions[symbol] = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "avg_entry_price": entry_price,
            "current_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0
        }
        self._sim_cash -= (qty * entry_price)
        self._sim_orders.append({"id": sim_id, "symbol": symbol, "qty": qty, "side": side})

        return {
            "success": True,
            "order_id": sim_id,
            "symbol": symbol,
            "qty": qty,
            "status": "FILLED_SIMULATED",
            "message": "Bracket order simulada exitosa"
        }

    async def close_all_positions(self) -> dict:
        """
        BOTÓN DE PÁNICO:
        Cancela todas las órdenes activas y cierra inmediatamente todas las posiciones a mercado.
        """
        logger.warning("BOTÓN DE PÁNICO ACTIVADO: Cerrando todas las posiciones y cancelando órdenes.")
        if self.has_real_credentials:
            try:
                async with self._get_client(timeout=8.0) as client:
                    # 1. Cancelar todas las órdenes
                    await client.delete(f"{self.base_url}/v2/orders", headers=self._get_headers())
                    # 2. Cerrar todas las posiciones a mercado
                    resp = await client.delete(f"{self.base_url}/v2/positions?cancel_orders=true", headers=self._get_headers())
                    return {"success": True, "message": "Todas las posiciones cerradas en Alpaca", "raw": resp.json()}
            except Exception as e:
                logger.error(f"Error en cierre de pánico Alpaca: {e}")
                return {"success": False, "error": str(e)}


        # Cierre en simulador
        closed_count = len(self._sim_positions)
        for pos in self._sim_positions.values():
            self._sim_cash += (pos["qty"] * pos["current_price"])
        self._sim_positions.clear()
        return {"success": True, "message": f"Simulador: {closed_count} posiciones cerradas de emergencia"}

alpaca_broker = AlpacaBroker()
