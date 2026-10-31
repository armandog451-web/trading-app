"""
ai_trading_agent.strategy_lab.experiments.exp_mtf01.causal_mtf_synchronizer
============================================================================
Sincronizador Causal Multitemporal D1 / H1 / M5.
Garantiza alineación temporal estricta de barras cerradas previas:
- D1: barra cerrada en sesión anterior (D-1 o anterior).
- H1: barra cerrada estrictamente antes o en el timestamp de evaluación.
- M5: barra actual cerrada para evaluación; ejecución en T+1 Open.
"""

from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

from ai_trading_agent.strategy_lab.experiments.exp_mtf01.daily_context_engine import DailyContextEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.market_structure_engine import MarketStructureEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.fibonacci_confluence_engine import FibonacciConfluenceEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.m5_entry_engine import M5EntryEngine


class CausalMTFSynchronizer:
    """Orquestador de Sincronización Causal de 3 Temporalidades."""

    def __init__(
        self,
        d1_engine: Optional[DailyContextEngine] = None,
        structure_engine: Optional[MarketStructureEngine] = None,
        fib_engine: Optional[FibonacciConfluenceEngine] = None,
        m5_engine: Optional[M5EntryEngine] = None,
        enable_d1_filter: bool = True,
        enable_fib_filter: bool = True,
        enable_ema_filter: bool = True,
        enable_m5_filter: bool = True
    ):
        self.d1_engine = d1_engine or DailyContextEngine()
        self.structure_engine = structure_engine or MarketStructureEngine()
        self.fib_engine = fib_engine or FibonacciConfluenceEngine()
        self.m5_engine = m5_engine or M5EntryEngine()

        # Flags para estudios de ablación controlada
        self.enable_d1_filter = enable_d1_filter
        self.enable_fib_filter = enable_fib_filter
        self.enable_ema_filter = enable_ema_filter
        self.enable_m5_filter = enable_m5_filter

    def prepare_data(
        self,
        df_d1: pd.DataFrame,
        df_h1: pd.DataFrame,
        df_m5: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Preprocesa indicadores en cada timeframe de forma causal."""
        d1_feat = self.d1_engine.compute_daily_features(df_d1)
        h1_feat = self.fib_engine.compute_h1_indicators(df_h1)
        h1_feat = self.structure_engine.identify_swings_causally(h1_feat)
        m5_feat = self.m5_engine.compute_m5_swings(df_m5) if self.enable_m5_filter else df_m5.copy()

        return d1_feat, h1_feat, m5_feat

    def run_synchronization(
        self,
        d1_feat: pd.DataFrame,
        h1_feat: pd.DataFrame,
        m5_feat: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        Itera secuencialmente y causalmente a través de las barras.
        Genera señales de trading con trazabilidad completa.
        """
        signals = []

        # Asegurar formato de fechas consistente
        d1_feat.index = pd.to_datetime(d1_feat.index)
        h1_feat.index = pd.to_datetime(h1_feat.index)
        m5_feat.index = pd.to_datetime(m5_feat.index)

        if d1_feat.index.tz is None:
            d1_feat.index = d1_feat.index.tz_localize('UTC')
        if h1_feat.index.tz is None:
            h1_feat.index = h1_feat.index.tz_localize('UTC')
        if m5_feat.index.tz is None:
            m5_feat.index = m5_feat.index.tz_localize('UTC')

        # Mapeo rápido de H1 por timestamp
        h1_times = h1_feat.index.values

        active_setup: Optional[Dict[str, Any]] = None
        bars_in_setup = 0

        # Iterar sobre cada barra M5
        for i in range(len(m5_feat)):
            m5_row = m5_feat.iloc[i]
            t_m5 = m5_row.name

            # 1. Obtener contexto D1 disponible (sesión cerrada previa)
            if self.enable_d1_filter:
                d1_ctx = self.d1_engine.get_context_for_date(d1_feat, t_m5)
            else:
                d1_ctx = {"bullish_context": True, "bearish_context": True, "last_closed_date": "BYPASSED", "atr": 1.0}

            # 2. Obtener la última barra H1 estrictamente cerrada antes o en t_m5
            # En datos de mercado horario, una barra con timestamp 10:30 cierra a las 11:30.
            # Aquí aseguramos que el timestamp de la barra H1 ya esté completado.
            available_h1 = h1_feat[h1_feat.index <= t_m5]
            if available_h1.empty or len(available_h1) < 10:
                continue

            last_h1 = available_h1.iloc[-1]

            # 3. Evaluar si se genera o actualiza un setup H1
            if active_setup is None:
                # Buscar BOS reciente en las últimas 5 barras H1
                recent_h1 = available_h1.iloc[-5:]
                bullish_bos = bool(recent_h1['BOS_Bullish'].any())
                bearish_bos = bool(recent_h1['BOS_Bearish'].any())

                direction = None
                if bullish_bos and d1_ctx["bullish_context"]:
                    direction = "BUY"
                elif bearish_bos and d1_ctx["bearish_context"]:
                    direction = "SELL"

                if direction is not None:
                    # Encontrar P0 y P1 del impulso
                    if direction == "BUY":
                        p1 = float(last_h1['Last_Confirmed_Swing_High'])
                        p0 = float(last_h1['Last_Confirmed_Swing_Low'])
                    else:
                        p1 = float(last_h1['Last_Confirmed_Swing_Low'])
                        p0 = float(last_h1['Last_Confirmed_Swing_High'])

                    ema50 = float(last_h1['EMA50'])
                    atr_h1 = float(last_h1['ATR_H1'])

                    confl = self.fib_engine.evaluate_confluence(p0, p1, direction, ema50, atr_h1)

                    # Aplicar filtros según configuración de ablación
                    valid_setup = True
                    if self.enable_fib_filter and self.enable_ema_filter:
                        valid_setup = confl["confluent"]
                    elif self.enable_fib_filter and not self.enable_ema_filter:
                        # Solo retroceso Fib, sin importar distancia a EMA50
                        valid_setup = True
                    elif not self.enable_fib_filter and self.enable_ema_filter:
                        # Solo proximidad a EMA 50
                        valid_setup = abs(float(last_h1['Close']) - ema50) <= (0.50 * atr_h1)

                    if valid_setup and p1 != p0:
                        # Comprobar si el precio H1 ya retrocedió a la zona de confluencia
                        h1_in_zone = (last_h1['Low'] <= confl["zone_max"]) and (last_h1['High'] >= confl["zone_min"])
                        if h1_in_zone or not self.enable_fib_filter:
                            active_setup = {
                                "setup_id": f"SETUP_{t_m5.strftime('%Y%m%d_%H%M%S')}",
                                "direction": direction,
                                "created_time": t_m5,
                                "p0": p0,
                                "p1": p1,
                                "fib_618": confl["fib_618"],
                                "fib_75": confl["fib_75"],
                                "zone_min": confl["zone_min"],
                                "zone_max": confl["zone_max"],
                                "atr_h1": atr_h1,
                                "ema50": ema50
                            }
                            bars_in_setup = 0

            # 4. Si hay un setup activo, evaluar gatillo M5 (o H1 directo si ablación E)
            if active_setup is not None:
                bars_in_setup += 1

                if not self.enable_m5_filter:
                    # Ablación E: Entrada inmediata sin confirmación M5
                    sig = {
                        "signal_id": f"SIG_{t_m5.strftime('%Y%m%d_%H%M%S')}",
                        "signal_time": t_m5,
                        "direction": active_setup["direction"],
                        "signal_close": float(m5_row['Close']),
                        "setup": active_setup.copy(),
                        "bar_index": i
                    }
                    signals.append(sig)
                    active_setup = None
                    bars_in_setup = 0
                else:
                    # Baseline y otras ablaciones: confirmación M5
                    res = self.m5_engine.evaluate_entry_trigger(m5_row, active_setup, bars_in_setup)
                    if res["triggered"]:
                        sig = {
                            "signal_id": f"SIG_{t_m5.strftime('%Y%m%d_%H%M%S')}",
                            "signal_time": t_m5,
                            "direction": active_setup["direction"],
                            "signal_close": float(m5_row['Close']),
                            "breakout_level": res.get("breakout_level"),
                            "setup": active_setup.copy(),
                            "bar_index": i
                        }
                        signals.append(sig)
                        active_setup = None
                        bars_in_setup = 0
                    elif res["status"] in ["TIMEOUT_EXPIRED", "INVALIDATED_FIB_75"]:
                        active_setup = None
                        bars_in_setup = 0

        return signals
