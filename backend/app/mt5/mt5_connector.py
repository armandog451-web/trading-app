# =====================================================================
# TRADEPULSE: CONECTOR OFICIAL METATRADER 5 (MetaTrader5 Python API)
# =====================================================================
import logging
import datetime
from typing import Optional, Dict, Any, List
import pandas as pd

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

logger = logging.getLogger(__name__)


class MetaTrader5Connector:
    """
    Cliente y Conector de Datos Históricos con MetaTrader 5 (MT5).
    Maneja la conexión al terminal local de MT5, extracción de velas en múltiples
    temporalidades (M1, M5, M15, H1, D1) y preparación de datasets para backtesting.
    """

    TIMEFRAMES_MAP = {
        "M1": 1 if not MT5_AVAILABLE else mt5.TIMEFRAME_M1,
        "M5": 5 if not MT5_AVAILABLE else mt5.TIMEFRAME_M5,
        "M15": 15 if not MT5_AVAILABLE else mt5.TIMEFRAME_M15,
        "M30": 30 if not MT5_AVAILABLE else mt5.TIMEFRAME_M30,
        "H1": 16385 if not MT5_AVAILABLE else mt5.TIMEFRAME_H1,
        "H4": 16388 if not MT5_AVAILABLE else mt5.TIMEFRAME_H4,
        "D1": 16408 if not MT5_AVAILABLE else mt5.TIMEFRAME_D1,
    }

    def __init__(self):
        self._connected = False
        self._terminal_info = None

    def initialize(self, path: Optional[str] = None) -> bool:
        """Inicializa la conexión con el terminal local de MT5."""
        if not MT5_AVAILABLE:
            logger.error("Librería oficial 'MetaTrader5' no disponible en el entorno Python.")
            return False

        try:
            if path:
                init_ok = mt5.initialize(path=path)
            else:
                init_ok = mt5.initialize()

            if not init_ok:
                err = mt5.last_error()
                logger.error(f"Fallo al conectar con MetaTrader 5. Código de error: {err}")
                self._connected = False
                return False

            self._connected = True
            info = mt5.terminal_info()
            if info:
                self._terminal_info = {
                    "connected": info.connected,
                    "build": info.build,
                    "name": info.name,
                    "company": info.company,
                    "path": info.path,
                    "data_path": info.data_path,
                    "ping_last": info.ping_last,
                    "maxbars": info.maxbars
                }
                logger.info(f"MetaTrader 5 Conectado: {info.name} Build {info.build} [{info.company}]")
            return True
        except Exception as e:
            logger.error(f"Excepción al inicializar MT5: {e}")
            self._connected = False
            return False

    def shutdown(self):
        """Cierra la conexión con MT5 de forma segura."""
        if MT5_AVAILABLE and self._connected:
            try:
                mt5.shutdown()
            except Exception:
                pass
            self._connected = False
            logger.info("Conexión con MetaTrader 5 finalizada de forma segura.")

    def is_connected(self) -> bool:
        """Verifica si la conexión con el terminal de MT5 sigue activa."""
        if not MT5_AVAILABLE:
            return False
        if not self._connected:
            return self.initialize()
        try:
            info = mt5.terminal_info()
            return bool(info and info.connected)
        except Exception:
            self._connected = False
            return False

    def get_terminal_status(self) -> Dict[str, Any]:
        """Devuelve el estado detallado del terminal de MT5."""
        active = self.is_connected()
        ver = mt5.version() if (MT5_AVAILABLE and active) else None
        return {
            "installed": MT5_AVAILABLE,
            "connected": active,
            "version": ver if ver else "N/A",
            "terminal_info": self._terminal_info or {},
            "default_symbols": ["EURUSD", "GBPUSD", "SPY", "QQQ", "AAPL", "TSLA", "US500", "USTEC"]
        }

    def get_historical_rates(
        self,
        symbol: str,
        timeframe: str = "M5",
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None,
        count: int = 1000
    ) -> Optional[pd.DataFrame]:
        """
        Extrae datos históricos de velas (Open, High, Low, Close, Volume, Spread)
        desde la base de datos local de MetaTrader 5.
        """
        if not self.is_connected():
            if not self.initialize():
                logger.error("No se pudo conectar a MT5 para extraer datos históricos.")
                return None

        # Resolver timeframe MT5
        tf_key = timeframe.upper()
        mt5_tf = self.TIMEFRAMES_MAP.get(tf_key, mt5.TIMEFRAME_M5)

        # Asegurar que el símbolo esté habilitado en MarketWatch
        sym_clean = symbol.upper().strip()
        mt5.symbol_select(sym_clean, True)

        rates = None
        try:
            # 1. Extracción por rango de fechas (desde fecha inicio hasta fin)
            if start_date is not None:
                end_dt = end_date or datetime.datetime.now()
                logger.info(f"Extrayendo datos MT5 para {sym_clean} ({tf_key}) desde {start_date} hasta {end_dt}")
                rates = mt5.copy_rates_range(sym_clean, mt5_tf, start_date, end_dt)

            # 2. Extracción por número de barras si no se define fecha o si copy_rates_range no retornó datos
            if rates is None or len(rates) == 0:
                logger.info(f"Extrayendo últimas {count} barras de MT5 para {sym_clean} ({tf_key})")
                rates = mt5.copy_rates_from_pos(sym_clean, mt5_tf, 0, count)

            if rates is None or len(rates) == 0:
                err = mt5.last_error()
                logger.warning(f"No se obtuvieron registros de MT5 para {sym_clean}. Error: {err}")
                return None

            # Convertir array estructurado de MT5 a pandas DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df['symbol'] = sym_clean
            df['timeframe'] = tf_key

            # Renombrar y seleccionar columnas clave
            # Columnas nativas de MT5: time, open, high, low, close, tick_volume, spread, real_volume
            return df
        except Exception as e:
            logger.error(f"Error extrayendo datos históricos de MT5: {e}")
            return None

    def get_available_symbols(self, search: Optional[str] = None) -> List[str]:
        """Obtiene la lista de símbolos disponibles en el terminal MT5."""
        if not self.is_connected():
            return []
        try:
            if search:
                symbols = mt5.symbols_get(f"*{search}*")
            else:
                symbols = mt5.symbols_get()
            if symbols:
                return [s.name for s in symbols]
            return []
        except Exception as e:
            logger.error(f"Error listando símbolos de MT5: {e}")
            return []


# Instancia singleton del conector
mt5_connector = MetaTrader5Connector()

if __name__ == "__main__":
    conn = MetaTrader5Connector()
    if conn.initialize():
        print("Estado MT5:", conn.get_terminal_status())
        df = conn.get_historical_rates("EURUSD", "M5", count=20)
        if df is not None:
            print("\nMuestra de velas extraídas (EURUSD M5):")
            print(df.tail(5)[['time', 'open', 'high', 'low', 'close', 'tick_volume']])
        conn.shutdown()
