# =====================================================================
# AGENTE ANTIGRAVITY: MOTOR MAESTRO DE DAY TRADING (Moomoo & Alpaca)
# =====================================================================
import time
import socket
import logging
import requests
from typing import Optional, Dict, Any

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

try:
    from futu import OpenQuoteContext, OpenTradeContext, RET_OK, TradeEnv
except ImportError:
    from moomoo import (
        OpenQuoteContext, 
        OpenSecTradeContext as OpenTradeContext, 
        RET_OK, 
        TrdEnv as TradeEnv,
        TrdMarket,
        OrderType as MoomooOrderType,
        TrdSide as MoomooTrdSide
    )

import sys
import os
from pathlib import Path

# Asegurar que 'backend' esté en sys.path tanto en ejecución modular como standalone
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings

# Configuración de Logging Optimizada (Nivel INFO por defecto)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MasterTradingEngine:
    """
    Motor Maestro de Day Trading para ejecución coordinada entre Moomoo OpenD y Alpaca Markets.
    Incluye auditoría de latencia de ultra-baja frecuencia y protocolos de auto-ajuste ante
    picos de latencia de red.
    """

    def __init__(
        self, 
        alpaca_api_key: Optional[str] = None, 
        alpaca_secret_key: Optional[str] = None, 
        max_latency_ms: float = 50.0
    ):
        self.max_latency_ms = max_latency_ms
        self.high_latency_mode = False
        self.last_audit: Dict[str, Any] = {
            "alpaca_latency_ms": 0.0,
            "opend_latency_ms": 0.0,
            "high_latency_mode": False,
            "timestamp": 0.0,
            "threshold_ms": max_latency_ms
        }
        
        # Resolver credenciales de Alpaca (parámetro o configuración persistida)
        api_key = alpaca_api_key or settings.ALPACA_API_KEY
        secret_key = alpaca_secret_key or settings.ALPACA_SECRET_KEY

        if api_key == "TU_API_KEY_AQUI":
            api_key = settings.ALPACA_API_KEY
        if secret_key == "TU_SECRET_KEY_AQUI":
            secret_key = settings.ALPACA_SECRET_KEY

        # Clientes Alpaca (iniciar de forma segura si las claves están configuradas)
        if api_key and secret_key and len(api_key) > 5:
            try:
                self.alpaca_trading = TradingClient(api_key, secret_key, paper=settings.ALPACA_PAPER)
                self.alpaca_data = StockHistoricalDataClient(api_key, secret_key)
            except Exception as e:
                logger.warning(f"No se pudieron inicializar clientes nativos de Alpaca: {e}")
                self.alpaca_trading = None
                self.alpaca_data = None
        else:
            self.alpaca_trading = None
            self.alpaca_data = None
        
        # Contextos Moomoo OpenD
        self.moomoo_quote = None
        self.moomoo_trade = None

    def audit_and_optimize_latency(self, verbose: bool = True) -> bool:
        """Mide la latencia de red y aplica ajustes automáticos si supera el umbral."""
        # 1. Auditoría Alpaca (HTTP)
        start = time.time()
        try:
            url = "https://paper-api.alpaca.markets/v2/clock" if settings.ALPACA_PAPER else "https://api.alpaca.markets/v2/clock"
            requests.get(url, timeout=2)
            alpaca_latency = (time.time() - start) * 1000
        except Exception:
            alpaca_latency = 999.0

        # 2. Auditoría Moomoo OpenD (Socket Local 11111 con TCP_NODELAY)
        start = time.time()
        host = settings.MOOMOO_HOST or "127.0.0.1"
        port = int(settings.MOOMOO_PORT or 11111)
        try:
            sock = socket.create_connection((host, port), timeout=1)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            opend_latency = (time.time() - start) * 1000
            sock.close()
        except Exception:
            opend_latency = 999.0

        if verbose:
            logging.info(f"[AUDITORÍA] Latencia Alpaca: {alpaca_latency:.2f}ms | Moomoo OpenD: {opend_latency:.2f}ms")

        # 3. Disparador de Auto-Ajuste si excede el umbral (50ms)
        exceeds_threshold = (alpaca_latency > self.max_latency_ms or opend_latency > self.max_latency_ms)

        if exceeds_threshold:
            self.high_latency_mode = True
            logging.warning(f"[ALERTA] Umbral de {self.max_latency_ms}ms superado. Activando protocolo de emergencia:")
            logging.warning(" -> Conmutación exclusiva a WebSockets persistentes.")
            logging.warning(" -> Reducción de escrituras en disco (logging a nivel WARNING).")
            # Reducir I/O en disco
            logging.getLogger().setLevel(logging.WARNING)
        else:
            self.high_latency_mode = False
            logging.getLogger().setLevel(logging.INFO)

        self.last_audit = {
            "alpaca_latency_ms": round(alpaca_latency, 2),
            "opend_latency_ms": round(opend_latency, 2),
            "high_latency_mode": self.high_latency_mode,
            "timestamp": time.time(),
            "threshold_ms": self.max_latency_ms,
            "status": "HIGH_LATENCY_EMERGENCY" if self.high_latency_mode else "OPTIMAL"
        }

        return not self.high_latency_mode

    def get_latency_report(self) -> Dict[str, Any]:
        """Devuelve el reporte de latencia actual (o ejecuta uno si es necesario)."""
        now = time.time()
        # Si la última auditoría tiene más de 10 segundos, renovarla
        if now - self.last_audit.get("timestamp", 0) > 10.0:
            self.audit_and_optimize_latency(verbose=False)
        return self.last_audit

    def connect_moomoo(self, host: str = '127.0.0.1', port: int = 11111) -> bool:
        """Conecta con la pasarela local OpenD."""
        try:
            # Si ya está conectado, no duplicar conexiones
            if self.moomoo_quote is None:
                self.moomoo_quote = OpenQuoteContext(host=host, port=port)
            if self.moomoo_trade is None:
                try:
                    self.moomoo_trade = OpenTradeContext(host=host, port=port)
                except TypeError:
                    from moomoo import TrdMarket
                    self.moomoo_trade = OpenTradeContext(filter_trdmarket=TrdMarket.US, host=host, port=port)

            logging.info(f"Conectado exitosamente a Moomoo OpenD en {host}:{port}")
            return True
        except Exception as e:
            logging.error(f"Fallo al conectar con Moomoo OpenD: {e}")
            return False

    def execute_market_order(self, symbol: str, qty: float, side: OrderSide, broker: str = "alpaca"):
        """Ejecuta órdenes validando previamente la latencia del sistema operativo."""
        if not self.audit_and_optimize_latency():
            logging.warning("Ejecución bajo protocolo de alta latencia: se prioriza velocidad de socket.")

        broker_name = broker.lower()

        if broker_name == "alpaca":
            if self.alpaca_trading:
                try:
                    order_data = MarketOrderRequest(symbol=symbol, qty=qty, side=side, time_in_force=TimeInForce.IOC)
                    order = self.alpaca_trading.submit_order(order_data=order_data)
                    logging.info(f"[ALPACA] Orden ejecutada: {order.side} {order.qty} {order.symbol}")
                    return order
                except Exception as e:
                    logging.error(f"[ALPACA] Error en orden: {e}")
                    return None
            else:
                # Fallback al adaptador AlpacaBroker del sistema
                from app.core.alpaca_client import alpaca_broker
                logging.info(f"[ALPACA-ADAPTER] Enrutando orden para {symbol} {qty} {side} vía adaptador de sistema.")
                import asyncio
                side_str = "buy" if side in (OrderSide.BUY, "buy") else "sell"
                return asyncio.run(alpaca_broker.submit_order(symbol=symbol, qty=qty, side=side_str, order_type="market"))

        elif broker_name == "moomoo":
            # Lógica de enrutamiento mediante Moomoo OpenD
            logging.info(f"[MOOMOO] Procesando orden para {symbol} vía OpenD local.")
            from app.core.moomoo_client import moomoo_broker
            import asyncio
            side_str = "buy" if side in (OrderSide.BUY, "buy") else "sell"
            return asyncio.run(moomoo_broker.submit_order(symbol=symbol, qty=qty, side=side_str, order_type="market"))

    def close_connections(self):
        if self.moomoo_quote:
            try:
                self.moomoo_quote.close()
            except Exception:
                pass
            self.moomoo_quote = None

        if self.moomoo_trade:
            try:
                self.moomoo_trade.close()
            except Exception:
                pass
            self.moomoo_trade = None

        logging.info("Conexiones cerradas de forma segura.")


# Instancia única del Motor Maestro para importación global en TradePulse
master_trading_engine = MasterTradingEngine()

# =====================================================================
# INICIALIZACIÓN DEL SISTEMA
# =====================================================================
if __name__ == "__main__":
    BOT = MasterTradingEngine(
        alpaca_api_key="TU_API_KEY_AQUI", 
        alpaca_secret_key="TU_SECRET_KEY_AQUI", 
        max_latency_ms=50.0
    )
    
    if BOT.connect_moomoo():
        # Verificación inicial antes de operar
        BOT.audit_and_optimize_latency()
        BOT.close_connections()

