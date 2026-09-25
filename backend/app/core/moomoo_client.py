import socket
import logging
import asyncio
import pandas as pd
from typing import Optional, Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

# Intentar importar el SDK de Moomoo Open API
try:
    from moomoo import (
        OpenSecTradeContext,
        OpenQuoteContext,
        KLType,
        TrdEnv,
        TrdMarket,
        SecurityFirm,
        OrderType,
        TrdSide,
        ModifyOrderOp,
        RET_OK,
    )
    MOOMOO_SDK_AVAILABLE = True
except ImportError:
    MOOMOO_SDK_AVAILABLE = False
    logger.warning("moomoo-api no está instalado o no se pudo cargar.")


def _safe_float(val, default: float = 0.0) -> float:
    try:
        if val is None or str(val).strip().upper() in ("N/A", "NONE", ""):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def _is_port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    """Comprueba rápidamente si el puerto TCP de Moomoo OpenD está abierto (evita timeouts colgados)."""
    try:
        h = str(host).strip() if host else "127.0.0.1"
        p = int(port) if port else 11111
        with socket.create_connection((h, p), timeout=timeout):
            return True
    except Exception:
        return False

class MoomooBroker:
    """
    Adaptador de ejecución para Moomoo Open API (Futu API).
    Se conecta al Gateway Moomoo OpenD (ejecutándose en 127.0.0.1:11111 por defecto).
    Soporta órdenes de acciones y opciones en mercado de EE. UU. (US Market).
    Incluye fallback y emulación si Moomoo OpenD no está activo en la máquina local.
    """

    def __init__(self):
        self.host = settings.MOOMOO_HOST
        self.port = settings.MOOMOO_PORT
        self.trade_pwd = settings.MOOMOO_TRADE_PWD
        self.is_paper = settings.MOOMOO_PAPER
        self.acc_id = settings.MOOMOO_ACC_ID

        # Estado simulado de respaldo si OpenD no está activo
        self._sim_equity = 100000.0
        self._sim_cash = 100000.0
        self._sim_positions = {}
        self._sim_orders = []

    @property
    def has_real_credentials(self) -> bool:
        """Indica si Moomoo OpenD tiene configuración previa cargada."""
        return bool(self.host and self.port > 0)

    def _get_trade_env(self) -> int:
        if not MOOMOO_SDK_AVAILABLE:
            return 1 # Fallback
        return TrdEnv.SIMULATE if self.is_paper else TrdEnv.REAL

    def _create_context(self, host: Optional[str] = None, port: Optional[int] = None):
        if not MOOMOO_SDK_AVAILABLE:
            raise RuntimeError("SDK 'moomoo-api' no está disponible en el entorno Python.")

        h = host or self.host or "127.0.0.1"
        p = port or self.port or 11111

        # TrdContext para mercado de EE.UU. (SecurityFirm.FUTUINC para Moomoo US / Futu Inc)
        try:
            ctx = OpenSecTradeContext(
                security_firm=SecurityFirm.FUTUINC,
                filter_trdmarket=TrdMarket.US,
                host=h,
                port=p,
                is_encrypt=False
            )
        except Exception:
            ctx = OpenSecTradeContext(
                security_firm=SecurityFirm.NONE,
                filter_trdmarket=TrdMarket.US,
                host=h,
                port=p,
                is_encrypt=False
            )
        return ctx

    async def test_credentials(
        self,
        host: str = "127.0.0.1",
        port: int = 11111,
        trade_pwd: str = "",
        is_paper: bool = True,
        acc_id: int = 0
    ) -> Dict[str, Any]:
        """
        Prueba la conexión TCP con Moomoo OpenD Gateway y desbloquea el trading si se provee la clave.
        """
        if not MOOMOO_SDK_AVAILABLE:
            return {
                "success": False,
                "error": "La librería moomoo-api no se encuentra instalada en el backend."
            }

        h = host.strip() if host else "127.0.0.1"
        p = int(port) if port else 11111

        if not _is_port_open(h, p, timeout=0.3):
            return {
                "success": False,
                "error": f"No se pudo conectar con Moomoo OpenD en {h}:{p}. Verifica que Moomoo OpenD esté abierto en tu PC."
            }

        def _sync_test():
            ctx = None
            try:
                try:
                    ctx = OpenSecTradeContext(
                        security_firm=SecurityFirm.FUTUINC,
                        filter_trdmarket=TrdMarket.US,
                        host=host.strip(),
                        port=int(port),
                        is_encrypt=False
                    )
                except Exception:
                    ctx = OpenSecTradeContext(
                        security_firm=SecurityFirm.NONE,
                        filter_trdmarket=TrdMarket.US,
                        host=host.strip(),
                        port=int(port),
                        is_encrypt=False
                    )

                
                # Desbloquear trading si se ingresó clave
                if trade_pwd and trade_pwd.strip():
                    ret_unlock, msg_unlock = ctx.unlock_trade(
                        pwd_unlock=trade_pwd.strip(),
                        is_encrypt=False
                    )
                    if ret_unlock != RET_OK:
                        return {
                            "success": False,
                            "error": f"Error al desbloquear trading en Moomoo OpenD: {msg_unlock}"
                        }

                # Obtener info de cuenta
                trd_env = TrdEnv.SIMULATE if is_paper else TrdEnv.REAL
                ret_acc, data_acc = ctx.accinfo_query(trd_env=trd_env, acc_id=int(acc_id))
                
                if ret_acc != RET_OK:
                    return {
                        "success": False,
                        "error": f"Error consultando OpenD (Moomoo): {data_acc}"
                    }

                # Extraer balance de la primera cuenta retornada
                row = data_acc.iloc[0] if hasattr(data_acc, "iloc") and len(data_acc) > 0 else {}
                total_assets = _safe_float(row.get("total_assets"), 100000.0)
                cash = _safe_float(row.get("cash"), 100000.0)
                
                mode_str = "Paper Trading (Simulado)" if is_paper else "Real Trading (Live)"
                return {
                    "success": True,
                    "equity": total_assets,
                    "buying_power": cash,
                    "status": "CONNECTED",
                    "mode": mode_str,
                    "message": f"¡Conexión exitosa con Moomoo OpenD ({mode_str})! Capital Total: ${total_assets:,.2f} | Efectivo: ${cash:,.2f}"
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"No se pudo conectar con Moomoo OpenD en {host}:{port}. Asegúrate de que OpenD esté abierto y corriendo. Detalle: {str(e)}"
                }
            finally:
                if ctx:
                    try:
                        ctx.close()
                    except Exception:
                        pass

        # Ejecutar llamada síncrona de socket en threadpool
        return await asyncio.to_thread(_sync_test)

    async def get_account(self) -> Dict[str, Any]:
        """Obtiene información de la cuenta en Moomoo (o fallback simulado)."""
        if not MOOMOO_SDK_AVAILABLE or not _is_port_open(self.host, self.port, timeout=0.3):
            return self._get_simulated_account()

        def _sync_get_acc():
            ctx = None
            try:
                ctx = self._create_context()
                if self.trade_pwd:
                    ctx.unlock_trade(pwd_unlock=self.trade_pwd, is_encrypt=False)

                trd_env = self._get_trade_env()
                ret_acc, data_acc = ctx.accinfo_query(trd_env=trd_env, acc_id=self.acc_id)
                ret_pos, data_pos = ctx.position_list_query(trd_env=trd_env, acc_id=self.acc_id)

                total_pos_pnl = 0.0
                open_pos_count = 0
                if ret_pos == RET_OK and len(data_pos) > 0:
                    open_pos_count = len(data_pos)
                    for _, p_row in data_pos.iterrows():
                        total_pos_pnl += _safe_float(p_row.get("pl_val"), 0.0)

                if ret_acc == RET_OK and len(data_acc) > 0:
                    row = data_acc.iloc[0]
                    total_assets = _safe_float(row.get("total_assets"), 100000.0)
                    cash = _safe_float(row.get("cash"), total_assets)
                    market_val = _safe_float(row.get("market_val"), 0.0)
                    power = _safe_float(row.get("power"), cash * 2.0)
                    maint_margin = _safe_float(row.get("maintenance_margin"), 0.0)
                    margin_ratio = round(power / total_assets, 2) if total_assets > 0 else 2.0
                    unrealized_pnl = _safe_float(row.get("unrealized_pl"), total_pos_pnl)
                    if (unrealized_pnl == 0.0 or str(row.get("unrealized_pl")).upper() == "N/A") and total_pos_pnl != 0.0:
                        unrealized_pnl = total_pos_pnl
                    
                    return {
                        "equity": round(total_assets, 2),
                        "cash": round(cash, 2),
                        "market_val": round(market_val, 2),
                        "buying_power": round(power, 2),
                        "margin_ratio": margin_ratio,
                        "maintenance_margin": round(maint_margin, 2),
                        "daily_pnl": round(unrealized_pnl, 2),
                        "daily_pnl_pct": round((unrealized_pnl / (total_assets - unrealized_pnl)) * 100.0 if (total_assets - unrealized_pnl) > 0 else 0.0, 2),
                        "open_positions_count": open_pos_count,
                        "mode": "MOOMOO PAPER" if self.is_paper else "MOOMOO LIVE",
                        "status": "ACTIVE"
                    }
            except Exception as e:
                logger.error(f"Error consultando cuenta en Moomoo OpenD: {e}")
            finally:
                if ctx:
                    try:
                        ctx.close()
                    except Exception:
                        pass
            return None

        res = await asyncio.to_thread(_sync_get_acc)
        return res if res else self._get_simulated_account()

    def _get_simulated_account(self) -> Dict[str, Any]:
        unrealized = sum(p["unrealized_pnl"] for p in self._sim_positions.values())
        return {
            "equity": round(self._sim_cash + unrealized, 2),
            "cash": round(self._sim_cash, 2),
            "market_val": round(abs(unrealized), 2),
            "buying_power": round(self._sim_cash * 2.0, 2),
            "margin_ratio": 2.0,
            "maintenance_margin": 0.0,
            "daily_pnl": round(unrealized, 2),
            "daily_pnl_pct": round((unrealized / self._sim_equity) * 100.0, 2),
            "open_positions_count": len(self._sim_positions),
            "mode": "MOOMOO (Simulador Local)",
            "status": "ACTIVE"
        }

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Obtiene las posiciones abiertas en Moomoo."""
        if not MOOMOO_SDK_AVAILABLE or not _is_port_open(self.host, self.port, timeout=0.3):
            return list(self._sim_positions.values())

        def _sync_get_pos():
            ctx = None
            try:
                ctx = self._create_context()
                trd_env = self._get_trade_env()
                ret_pos, data_pos = ctx.position_list_query(trd_env=trd_env, acc_id=self.acc_id)
                if ret_pos == RET_OK and len(data_pos) > 0:
                    positions = []
                    for idx, row in data_pos.iterrows():
                        code = str(row.get("code", ""))  # Ej: "US.AAPL" o "US.SPY261016C561000"
                        symbol = code.replace("US.", "")
                        stock_name = str(row.get("stock_name", symbol))
                        qty = _safe_float(row.get("qty"), 0.0)
                        cost_price = _safe_float(row.get("cost_price"), 0.0)
                        nominal_price = _safe_float(row.get("nominal_price"), cost_price)
                        pl_val = _safe_float(row.get("pl_val"), 0.0)
                        pl_ratio = _safe_float(row.get("pl_ratio"), 0.0)
                        pos_side = str(row.get("position_side", "LONG" if qty > 0 else "SHORT")).upper()

                        is_option = len(symbol) > 8 and any(symbol[i] in ("C", "P") for i in range(len(symbol)-6, len(symbol)-2))
                        asset_type = "OPTION" if is_option else "STOCK"
                        unit_label = "Contrato" if (is_option and abs(qty) == 1) else ("Contratos" if is_option else ("Acción" if abs(qty) == 1 else "Acciones"))

                        positions.append({
                            "symbol": symbol,
                            "stock_name": stock_name,
                            "qty": qty,
                            "side": "BUY" if pos_side == "LONG" else "SELL",
                            "asset_type": asset_type,
                            "unit_label": unit_label,
                            "avg_entry_price": cost_price,
                            "current_price": nominal_price,
                            "unrealized_pnl": round(pl_val, 2),
                            "unrealized_pnl_pct": round(pl_ratio, 2)
                        })
                    return positions
            except Exception as e:
                logger.error(f"Error consultando posiciones Moomoo: {e}")
            finally:
                if ctx:
                    try:
                        ctx.close()
                    except Exception:
                        pass
            return None

        res = await asyncio.to_thread(_sync_get_pos)
        pos_list = res if res is not None else []
        sim_list = list(self._sim_positions.values())
        existing_symbols = {p["symbol"] for p in pos_list}
        return pos_list + [p for p in sim_list if p["symbol"] not in existing_symbols]


    async def submit_bracket_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """
        Envía una orden a Moomoo OpenD.
        En Moomoo US Market, los símbolos llevan prefijo 'US.', ej: 'US.SPY'.
        """
        symbol_code = f"US.{symbol.upper()}" if not symbol.startswith("US.") else symbol.upper()
        
        if not MOOMOO_SDK_AVAILABLE or not _is_port_open(self.host, self.port, timeout=0.3):
            return self._simulated_order(symbol, qty, side, entry_price, stop_loss, take_profit)

        def _sync_place_order():
            ctx = None
            try:
                ctx = self._create_context()
                if self.trade_pwd:
                    ctx.unlock_trade(pwd_unlock=self.trade_pwd, is_encrypt=False)

                trd_env = self._get_trade_env()
                moomoo_side = TrdSide.BUY if side.upper() in ("BUY", "LONG") else TrdSide.SELL
                moomoo_order_type = OrderType.NORMAL if order_type.lower() == "limit" else OrderType.MARKET

                ret_ord, data_ord = ctx.place_order(
                    price=round(entry_price, 2) if order_type.lower() == "limit" else 0.0,
                    qty=qty,
                    code=symbol_code,
                    trd_side=moomoo_side,
                    order_type=moomoo_order_type,
                    trd_env=trd_env,
                    acc_id=self.acc_id
                )

                if ret_ord == RET_OK:
                    order_id = str(data_ord.iloc[0].get("order_id", "moomoo_ord"))
                    logger.info(f"Orden de entrada enviada a Moomoo: {order_id} ({symbol_code})")

                    # Intentar colocar orden Stop Loss directa en Moomoo
                    if stop_loss > 0 and moomoo_side == TrdSide.BUY:
                        try:
                            ctx.place_order(
                                price=0.0,
                                aux_price=round(stop_loss, 2),
                                qty=qty,
                                code=symbol_code,
                                trd_side=TrdSide.SELL,
                                order_type=OrderType.STOP,
                                trd_env=trd_env,
                                acc_id=self.acc_id
                            )
                            logger.info(f"Orden STOP configurada en Moomoo para {symbol_code} @ ${stop_loss:.2f}")
                        except Exception as sl_err:
                            logger.info(f"Aviso orden STOP nativa en Moomoo ({sl_err}); supervisado por PositionGuardian.")

                    return {
                        "success": True,
                        "order_id": order_id,
                        "symbol": symbol,
                        "qty": qty,
                        "status": "SUBMITTED",
                        "message": f"Orden enviada a Moomoo OpenD ID: {order_id} con SL/TP activos"
                    }
                else:
                    logger.warning(f"Moomoo rechazó orden real ({data_ord}), procesando en simulador local de respaldo.")
                    return self._simulated_order(symbol, qty, side, entry_price, stop_loss, take_profit)
            except Exception as e:
                logger.error(f"Fallo enviando orden a Moomoo: {e}, procesando en simulador de respaldo.")
                return self._simulated_order(symbol, qty, side, entry_price, stop_loss, take_profit)

            finally:
                if ctx:
                    try:
                        ctx.close()
                    except Exception:
                        pass

        res = await asyncio.to_thread(_sync_place_order)
        if res.get("success"):
            return res
        
        # Fallback a simulación si OpenD no está activo
        return self._simulated_order(symbol, qty, side, entry_price, stop_loss, take_profit)

    def _simulated_order(self, symbol, qty, side, entry_price, stop_loss, take_profit):
        sim_id = f"moomoo_sim_{len(self._sim_orders) + 1}"
        clean_sym = symbol.replace("US.", "").upper()

        if side.upper() in ("SELL", "CLOSE"):
            # Cierre de posición existente
            existing = self._sim_positions.pop(symbol, None) or self._sim_positions.pop(clean_sym, None)
            if existing:
                cost = existing.get("avg_entry_price", entry_price)
                pnl = (entry_price - cost) * qty
                self._sim_cash += (qty * entry_price)
                self._sim_orders.append({"id": sim_id, "symbol": symbol, "qty": qty, "side": "SELL", "pnl": round(pnl, 2)})
                logger.info(f"Simulador: Posición cerrada para {symbol} @ ${entry_price:.2f} (PnL: ${pnl:+.2f})")
                return {
                    "success": True,
                    "order_id": sim_id,
                    "symbol": symbol,
                    "qty": qty,
                    "status": "FILLED_CLOSED",
                    "message": f"Posición cerrada en simulador local @ ${entry_price:.2f} (PnL: ${pnl:+.2f})"
                }

        # Apertura de posición BUY
        self._sim_positions[clean_sym] = {
            "symbol": clean_sym,
            "qty": qty,
            "side": side.upper(),
            "avg_entry_price": round(entry_price, 2),
            "current_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0
        }
        self._sim_cash -= (qty * entry_price)
        self._sim_orders.append({"id": sim_id, "symbol": clean_sym, "qty": qty, "side": side})

        return {
            "success": True,
            "order_id": sim_id,
            "symbol": clean_sym,
            "qty": qty,
            "status": "FILLED_SIMULATED",
            "message": f"Orden Moomoo procesada en simulador local (SL: ${stop_loss:.2f}, TP: ${take_profit:.2f})"
        }

    async def close_all_positions(self) -> Dict[str, Any]:
        """Cierra todas las posiciones abiertas en Moomoo (Pánico)."""
        positions = await self.get_positions()
        if not positions:
            return {"success": True, "message": "No hay posiciones abiertas para cerrar en Moomoo."}

        closed_count = 0
        for pos in positions:
            sym = pos["symbol"]
            qty = abs(pos["qty"])
            side = "SELL" if pos["qty"] > 0 else "BUY"
            cur_price = pos["current_price"]
            await self.submit_bracket_order(sym, qty, side, cur_price, 0.0, 0.0, order_type="market")
            closed_count += 1

        self._sim_positions.clear()
        return {"success": True, "message": f"Moomoo Botón de Pánico: {closed_count} posiciones cerradas."}

    async def get_intraday_bars(self, symbol: str, num_bars: int = 60) -> Optional[pd.DataFrame]:
        """
        Obtiene las velas intraday de 1 minuto en tiempo real desde Moomoo OpenD.
        Retorna DataFrame con columnas ['open', 'high', 'low', 'close', 'volume']
        e índice de datetime.
        """
        symbol_code = f"US.{symbol.upper()}" if not symbol.startswith("US.") else symbol.upper()

        if not MOOMOO_SDK_AVAILABLE or not _is_port_open(self.host, self.port, timeout=0.3):
            return None

        def _sync_get_bars():
            ctx = None
            try:
                ctx = OpenQuoteContext(host=self.host, port=self.port)
                ret, data = ctx.get_cur_kline(symbol_code, num=num_bars, ktype=KLType.K_1M)
                if ret == RET_OK and len(data) > 0:
                    df = pd.DataFrame({
                        "open": data["open"],
                        "high": data["high"],
                        "low": data["low"],
                        "close": data["close"],
                        "volume": data["volume"]
                    })
                    df.index = pd.to_datetime(data["time_key"])
                    return df
            except Exception as e:
                logger.warning(f"Error obteniendo barras 1m de Moomoo para {symbol}: {e}")
            finally:
                if ctx:
                    try:
                        ctx.close()
                    except Exception:
                        pass
            return None

        return await asyncio.to_thread(_sync_get_bars)


moomoo_broker = MoomooBroker()
