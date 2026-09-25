import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import pandas as pd
import numpy as np

from app.engines.options_engine import options_engine
from app.core.notifier import notifier

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "orb_config.json"

class ORBStrategy:
    """
    Estrategia Cuantitativa ORB (Opening Range Breakout) con Filtro de Volumen Estricto.
    
    Reglas Operativas:
    1. Define el rango de apertura (09:30 a 09:45 EST o según configuración).
    2. Identifica Techo (OR High) y Piso (OR Low) del rango.
    3. Detecta rupturas en velas de 1 minuto:
       - Ruptura alcista: Close > OR High -> Recomendación CALL.
       - Ruptura bajista: Close < OR Low -> Recomendación PUT.
    4. Filtro de Volumen Estricto:
       - El volumen de la vela de ruptura DEBE ser >= N veces el promedio móvil de volumen (ej. 1.5x de SMA 20).
       - Si no supera el umbral, se descarta la señal por riesgo de ruptura falsa (Fakeout).
    5. Gestión de Riesgo Global:
       - 1 solo contrato fijo de opciones para todas las operaciones (14-30 DTE, SL -28%, TP1 +50%, TP2 +100%).
    """

    def __init__(self, config_file: Optional[Path] = None):
        self.config_path = config_file or CONFIG_PATH
        self.config = self._load_config()
        self.detected_breakouts: Dict[str, Dict[str, Any]] = {}

    def _load_config(self) -> Dict[str, Any]:
        default_config = {
            "strategy_name": "Opening Range Breakout (ORB) con Filtro de Volumen",
            "enabled": True,
            "opening_range_minutes": 15,
            "market_open_time": "09:30",
            "range_close_time": "09:45",
            "end_trading_time": "15:45",
            "timeframe": "1m",
            "volume_multiplier": 1.5,
            "volume_ma_period": 20,
            "tickers": ["QQQ", "SPY", "TSLA", "AAPL", "MSFT"],
            "fixed_contracts": 1,
            "stop_loss_pct": -28.0,
            "take_profit_1_pct": 50.0,
            "take_profit_2_pct": 100.0,
            "auto_dispatch_telegram": True,
            "auto_register_guardian": True
        }

        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                    default_config.update(user_cfg)
            except Exception as e:
                logger.error(f"Error cargando {self.config_path}, usando valores por defecto: {e}")

        return default_config

    def reload_config(self):
        """Recarga la configuración desde el archivo JSON en caliente."""
        self.config = self._load_config()
        logger.info("Configuración de ORB recargada correctamente.")

    def compute_opening_range(self, df: pd.DataFrame) -> Tuple[Optional[float], Optional[float], bool]:
        """
        Calcula el Techo (OR High) y Piso (OR Low) del rango de apertura.
        Espera un DataFrame con índice de datetime o columna 'time'/'timestamp'
        y columnas ['high', 'low', 'close', 'volume'].
        """
        if df.empty:
            return None, None, False

        # Asegurar formato datetime en índice
        work_df = df.copy()
        if not isinstance(work_df.index, pd.DatetimeIndex):
            if "time" in work_df.columns:
                work_df["datetime"] = pd.to_datetime(work_df["time"])
                work_df.set_index("datetime", inplace=True)
            elif "timestamp" in work_df.columns:
                work_df["datetime"] = pd.to_datetime(work_df["timestamp"])
                work_df.set_index("datetime", inplace=True)
            else:
                base_dt = datetime.utcnow().replace(hour=9, minute=30, second=0, microsecond=0)
                work_df.index = pd.DatetimeIndex([base_dt + pd.Timedelta(minutes=i) for i in range(len(work_df))])

        # Parsear tiempos de apertura y cierre del rango
        open_h, open_m = map(int, self.config.get("market_open_time", "09:30").split(":"))
        close_h, close_m = map(int, self.config.get("range_close_time", "09:45").split(":"))

        t_open = time(open_h, open_m)
        t_close = time(close_h, close_m)

        # Filtrar velas dentro de la ventana de apertura
        mask_range = (work_df.index.time >= t_open) & (work_df.index.time < t_close)
        range_bars = work_df.loc[mask_range]

        if len(range_bars) < 3:
            # Muy pocos datos para un rango consistente
            return None, None, False

        or_high = float(range_bars["high"].max())
        or_low = float(range_bars["low"].min())
        is_completed = work_df.index.max().time() >= t_close

        return or_high, or_low, is_completed

    def evaluate_breakout(
        self,
        symbol: str,
        df: pd.DataFrame,
        or_high: float,
        or_low: float
    ) -> Optional[Dict[str, Any]]:
        """
        Evalúa si la vela más reciente rompe el rango con confirmación estricta de volumen.
        Retorna diccionario con detalles de la ruptura o None si no hay señal válida.
        """
        if df.empty or or_high is None or or_low is None:
            return None

        work_df = df.copy()
        if not isinstance(work_df.index, pd.DatetimeIndex):
            if "time" in work_df.columns:
                work_df["datetime"] = pd.to_datetime(work_df["time"])
                work_df.set_index("datetime", inplace=True)
            elif "timestamp" in work_df.columns:
                work_df["datetime"] = pd.to_datetime(work_df["timestamp"])
                work_df.set_index("datetime", inplace=True)
            else:
                base_dt = datetime.utcnow().replace(hour=9, minute=30, second=0, microsecond=0)
                work_df.index = pd.DatetimeIndex([base_dt + pd.Timedelta(minutes=i) for i in range(len(work_df))])

        # Calcular media móvil de volumen previo (SMA 20)
        vol_period = int(self.config.get("volume_ma_period", 20))
        vol_multiplier = float(self.config.get("volume_multiplier", 1.5))
        
        work_df["volume_sma"] = work_df["volume"].rolling(vol_period, min_periods=5).mean()

        # Tomar la última vela cerrada / actual
        last_bar = work_df.iloc[-1]
        close_price = float(last_bar["close"])
        candle_vol = float(last_bar["volume"])
        avg_vol = float(last_bar["volume_sma"]) if not np.isnan(last_bar["volume_sma"]) else candle_vol
        
        vol_ratio = round(candle_vol / avg_vol, 2) if avg_vol > 0 else 1.0

        # Rango de tiempo operativo (después de 09:45 y antes de 15:45)
        close_h, close_m = map(int, self.config.get("range_close_time", "09:45").split(":"))
        end_h, end_m = map(int, self.config.get("end_trading_time", "15:45").split(":"))
        
        bar_time = last_bar.name.time() if hasattr(last_bar.name, "time") else datetime.utcnow().time()
        
        if not (time(close_h, close_m) <= bar_time <= time(end_h, end_m)):
            return None

        # 1. EVALUAR RUPTURA ALCISTA (LONG / CALL)
        if close_price > or_high:
            if vol_ratio >= vol_multiplier:
                logger.info(
                    f"🚀 [ORB LONG CONFIRMADO] {symbol}: Cierre ${close_price:.2f} > Techo ${or_high:.2f} "
                    f"| Volumen: {vol_ratio}x (Requerido: {vol_multiplier}x)"
                )
                return {
                    "symbol": symbol,
                    "direction": "LONG",
                    "bias": "BULLISH",
                    "option_type": "CALL",
                    "breakout_price": close_price,
                    "or_high": or_high,
                    "or_low": or_low,
                    "candle_volume": candle_vol,
                    "avg_volume": avg_vol,
                    "volume_ratio": vol_ratio,
                    "volume_filter_passed": True,
                    "timestamp": last_bar.name if hasattr(last_bar.name, "isoformat") else str(last_bar.name)
                }
            else:
                logger.info(
                    f"⚠️ [ORB FAKEOUT ALCISTA DESCARTADO] {symbol}: Cierre ${close_price:.2f} > Techo ${or_high:.2f} "
                    f"pero volumen débil ({vol_ratio}x < {vol_multiplier}x). Señal descartada."
                )
                return None

        # 2. EVALUAR RUPTURA BAJISTA (SHORT / PUT)
        elif close_price < or_low:
            if vol_ratio >= vol_multiplier:
                logger.info(
                    f"🩸 [ORB SHORT CONFIRMADO] {symbol}: Cierre ${close_price:.2f} < Piso ${or_low:.2f} "
                    f"| Volumen: {vol_ratio}x (Requerido: {vol_multiplier}x)"
                )
                return {
                    "symbol": symbol,
                    "direction": "SHORT",
                    "bias": "BEARISH",
                    "option_type": "PUT",
                    "breakout_price": close_price,
                    "or_high": or_high,
                    "or_low": or_low,
                    "candle_volume": candle_vol,
                    "avg_volume": avg_vol,
                    "volume_ratio": vol_ratio,
                    "volume_filter_passed": True,
                    "timestamp": last_bar.name if hasattr(last_bar.name, "isoformat") else str(last_bar.name)
                }
            else:
                logger.info(
                    f"⚠️ [ORB FAKEOUT BAJISTA DESCARTADO] {symbol}: Cierre ${close_price:.2f} < Piso ${or_low:.2f} "
                    f"pero volumen débil ({vol_ratio}x < {vol_multiplier}x). Señal descartada."
                )
                return None

        return None

    def generate_signal_payload(self, breakout_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforma la ruptura ORB confirmada en una recomendación ejecutable de OPCIONES
        con vencimiento de 14 a 30 días, Stop Loss -28%, Take Profit +50% y tamaño FIJO de 1 contrato.
        """
        symbol = breakout_data["symbol"]
        price = breakout_data["breakout_price"]
        bias = breakout_data["bias"]
        vol_ratio = breakout_data["volume_ratio"]
        or_high = breakout_data["or_high"]
        or_low = breakout_data["or_low"]

        # Generar estructura de contrato de opción con options_engine
        opt = options_engine.calculate_option_contract(
            symbol=symbol,
            current_price=price,
            bias=bias,
            equity=100000.0,
            risk_pct=1.0
        )

        direction_label = "ALCISTA (Breakout Techo)" if bias == "BULLISH" else "BAJISTA (Breakdown Piso)"
        or_level_text = f"Techo ${or_high:.2f}" if bias == "BULLISH" else f"Piso ${or_low:.2f}"

        rationale = (
            f"Estrategia ORB {direction_label} sobre {symbol}. "
            f"Vela de 1m rompió {or_level_text} a ${price:.2f} con fuerte confirmación institucional "
            f"de volumen ({vol_ratio:.1f}x sobre SMA20). "
            f"Rango de apertura 15m: [${or_low:.2f} - ${or_high:.2f}]. "
            f"Contrato {opt['option_type']} Strike ${opt['strike_price']} Exp {opt['expiration_date']}. "
            f"Gestión de riesgo: SL en prima al -28% (${opt['premium_stop_loss']:.2f}) y TP al +50% (${opt['premium_take_profit']:.2f})."
        )

        # Retornar estructura idéntica a las recomendaciones del sistema con 1 contrato estricto
        return {
            "asset_type": "OPTION",
            "symbol": symbol,
            "action": "BUY_CALL" if bias == "BULLISH" else "BUY_PUT",
            "option_type": opt["option_type"],
            "strike_price": opt["strike_price"],
            "expiration_date": opt["expiration_date"],
            "current_price": price,
            "entry_target": price,
            "premium_est": opt["premium_est"],
            "premium_stop_loss": opt["premium_stop_loss"],
            "premium_take_profit": opt["premium_take_profit"],
            "premium_take_profit_2": opt["premium_take_profit_2"],
            "stop_loss": opt["stop_loss"],
            "take_profit": opt["take_profit"],
            "risk_reward": opt["risk_reward"],
            "contracts_or_shares": 1,  # ESTRICTAMENTE 1 CONTRATO FIJO
            "contracts": 1,
            "confluence_score": 92,
            "setup_type": "ORB_Volume_Breakout_15m",
            "rationale": rationale,
            "orb_details": {
                "or_high": or_high,
                "or_low": or_low,
                "or_range": round(or_high - or_low, 2),
                "volume_ratio": vol_ratio,
                "breakout_direction": breakout_data["direction"]
            }
        }

    async def scan_and_dispatch(self, symbol: str, df: pd.DataFrame, db=None) -> Optional[Dict[str, Any]]:
        """
        Escanea un símbolo, calcula rango de apertura, valida ruptura de volumen
        y despacha la alerta automática a Telegram y la base de datos si aplica.
        """
        or_high, or_low, is_completed = self.compute_opening_range(df)
        if or_high is None or or_low is None:
            return None

        breakout = self.evaluate_breakout(symbol, df, or_high, or_low)
        if not breakout:
            return None

        # Evitar re-disparar la misma ruptura si ya fue detectada en esta sesión
        cache_key = f"{symbol}_{breakout['direction']}"
        if cache_key in self.detected_breakouts:
            return None

        self.detected_breakouts[cache_key] = breakout

        # Generar señal estructurada con 1 contrato fijo
        signal_payload = self.generate_signal_payload(breakout)

        # Despachar automáticamente a Telegram y Guardar en SQLite
        if self.config.get("auto_dispatch_telegram", True):
            await notifier.send_trade_recommendation(signal_payload, db=db)
            logger.info(f"✅ Alerta ORB despachada exitosamente para {symbol} ({breakout['direction']})")

        return signal_payload

orb_strategy = ORBStrategy()
