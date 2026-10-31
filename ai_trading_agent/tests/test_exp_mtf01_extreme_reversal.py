"""
ai_trading_agent.tests.test_exp_mtf01_extreme_reversal
======================================================
Suite completa de pruebas de regresión e integridad causal para EXP-MTF01.
Cubre Groups A-G: Contexto D1, Estructura H1, Confluencia Fib/EMA, Gatillo M5,
Sincronización Causal, Backtesting con Fricción, y Aislamiento Institucional.
"""

import os
import json
import pytest
import pandas as pd
import numpy as np

from ai_trading_agent.strategy_lab.experiments.exp_mtf01.daily_context_engine import DailyContextEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.market_structure_engine import MarketStructureEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.fibonacci_confluence_engine import FibonacciConfluenceEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.m5_entry_engine import M5EntryEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.causal_mtf_synchronizer import CausalMTFSynchronizer
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.mtf_backtester import MTFBacktester


class TestGroupA_DailyContext:
    """Pruebas del motor de contexto diario D1."""

    def test_daily_features_computation(self):
        dates = pd.date_range("2026-01-01", periods=80, freq="D", tz="UTC")
        df_d1 = pd.DataFrame({
            "Open": np.linspace(100, 70, 80),
            "High": np.linspace(102, 72, 80),
            "Low": np.linspace(99, 69, 80),
            "Close": np.linspace(100, 70, 80),
            "Volume": 1000
        }, index=dates)

        eng = DailyContextEngine(extreme_lookback=60, accel_lookback=5)
        res = eng.compute_daily_features(df_d1)

        assert "ATR" in res.columns
        assert "Min_Low_60" in res.columns
        assert "Is_Lower_Extreme" in res.columns
        assert "Accel_Down" in res.columns
        assert not res["ATR"].dropna().empty

    def test_daily_context_strict_closed_bar_access(self):
        dates = pd.date_range("2026-01-01", periods=80, freq="D", tz="UTC")
        df_d1 = pd.DataFrame({
            "Open": np.linspace(100, 70, 80),
            "High": np.linspace(102, 72, 80),
            "Low": np.linspace(99, 69, 80),
            "Close": np.linspace(100, 70, 80),
            "Volume": 1000
        }, index=dates)

        eng = DailyContextEngine(extreme_lookback=60)
        res = eng.compute_daily_features(df_d1)

        # Evaluar para el día 50 a las 11:30 AM
        eval_time = dates[50] + pd.Timedelta(hours=11, minutes=30)
        ctx = eng.get_context_for_date(res, eval_time)

        # La última fecha cerrada debe ser el día 49
        expected_date = dates[49].strftime("%Y-%m-%d")
        assert ctx["last_closed_date"] == expected_date


class TestGroupB_MarketStructure:
    """Pruebas de swings causales y Break of Structure."""

    def test_swing_confirmation_delay(self):
        # Crear un pico en k=5 con L=3, R=3
        dates = pd.date_range("2026-01-01", periods=15, freq="h", tz="UTC")
        highs = [10, 11, 12, 13, 14, 20, 14, 13, 12, 11, 10, 9, 8, 7, 6]
        lows = [h - 2 for h in highs]
        closes = [h - 1 for h in highs]
        opens = [h - 1.5 for h in highs]

        df_h1 = pd.DataFrame({
            "Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": 500
        }, index=dates)

        eng = MarketStructureEngine(swing_left=3, swing_right=3)
        res = eng.identify_swings_causally(df_h1)

        # El swing está en k=5 (precio 20), pero solo se confirma en k=5+3 = 8
        assert res.iloc[5]["Is_Swing_High"] == True
        assert np.isnan(res.iloc[5]["Confirmed_Swing_High_Price"])
        assert res.iloc[8]["Confirmed_Swing_High_Price"] == 20.0


class TestGroupC_FibonacciConfluence:
    """Pruebas de retroceso de Fibonacci y confluencia con EMA 50."""

    def test_fibonacci_confluence_metrics(self):
        eng = FibonacciConfluenceEngine(ema_period=50, fib_retracement=0.618, fib_stop_reference=0.75)
        p0 = 100.0  # Swing Low
        p1 = 200.0  # Swing High
        # Range = 100. Fib 0.618 = 200 - 61.8 = 138.2. Fib 0.75 = 200 - 75 = 125.0
        ema50 = 139.0
        atr = 5.0  # tol = 0.25 * 5 = 1.25. Dist = |138.2 - 139| = 0.8 <= 1.25 (Confluente)

        res = eng.evaluate_confluence(p0, p1, "BUY", ema50, atr)
        assert res["confluent"] == True
        assert res["fib_618"] == 138.2
        assert res["fib_75"] == 125.0

    def test_fibonacci_non_confluent(self):
        eng = FibonacciConfluenceEngine(ema_period=50)
        p0 = 100.0
        p1 = 200.0
        ema50 = 160.0  # Dist = 21.8 >> tol
        atr = 5.0
        res = eng.evaluate_confluence(p0, p1, "BUY", ema50, atr)
        assert res["confluent"] == False


class TestGroupD_M5Entry:
    """Pruebas de gatillo intradía M5, timeout e invalidación."""

    def test_m5_breakout_confirmed(self):
        eng = M5EntryEngine(timeout_bars=24)
        setup = {"direction": "BUY", "fib_75": 125.0}
        bar = pd.Series({
            "Close": 142.0, "Low": 139.0, "High": 143.0, "Last_M5_Swing_High": 140.0
        }, name=pd.Timestamp("2026-01-01 10:00:00", tz="UTC"))

        res = eng.evaluate_entry_trigger(bar, setup, bars_since_setup=5)
        assert res["triggered"] == True
        assert res["status"] == "CONFIRMED_BREAKOUT"

    def test_m5_timeout_and_invalidation(self):
        eng = M5EntryEngine(timeout_bars=24)
        setup = {"direction": "BUY", "fib_75": 125.0}

        # Test timeout
        bar = pd.Series({"Close": 135.0, "Low": 134.0, "High": 136.0}, name=pd.Timestamp("2026-01-01 10:00:00", tz="UTC"))
        res_timeout = eng.evaluate_entry_trigger(bar, setup, bars_since_setup=25)
        assert res_timeout["triggered"] == False
        assert res_timeout["status"] == "TIMEOUT_EXPIRED"

        # Test invalidation
        bar_inv = pd.Series({"Close": 124.0, "Low": 123.0, "High": 126.0}, name=pd.Timestamp("2026-01-01 10:00:00", tz="UTC"))
        res_inv = eng.evaluate_entry_trigger(bar_inv, setup, bars_since_setup=10)
        assert res_inv["triggered"] == False
        assert res_inv["status"] == "INVALIDATED_FIB_75"


class TestGroupE_BacktesterMicrostructure:
    """Pruebas de simulación de ejecución, slippage y colisión conservadora."""

    def test_conservative_collision_resolution(self):
        # Cuando en la misma barra se tocan SL y TP, el SL debe ganar
        dates = pd.date_range("2026-01-01", periods=10, freq="5min", tz="UTC")
        df_m5 = pd.DataFrame({
            "Open": [100.0] * 10,
            "High": [100.0] * 5 + [120.0] + [100.0] * 4,
            "Low": [100.0] * 5 + [80.0] + [100.0] * 4,
            "Close": [100.0] * 10,
            "Volume": 1000
        }, index=dates)

        bt = MTFBacktester()
        sig = [{
            "signal_id": "SIG_TEST",
            "bar_index": 3,
            "direction": "BUY",
            "setup": {
                "fib_75": 90.0,
                "atr_h1": 5.0,
                "p1": 115.0
            }
        }]

        # Fill at bar 4 (Open 100). SL = 90 - 0.5 = 89.5. TP V1A = 115.0.
        # At bar 5, High=120 (>= TP) and Low=80 (<= SL). Both hit!
        res = bt.run_simulation(sig, df_m5, tp_variant="V1A")
        assert res["total_trades"] == 1
        trade = res["trades"][0]
        assert trade["exit_reason"] == "SL_COLLISION_CONSERVATIVE"
        assert trade["net_pnl"] < 0  # Pérdida asignada conservadoramente


class TestGroupF_InstitutionalIsolation:
    """Verificación de aislamiento y preservación del sistema principal."""

    def test_live_trading_disabled(self):
        from ai_trading_agent.config.settings import settings
        from ai_trading_agent.domain.enums import TradingMode
        assert settings.TRADING_MODE != "LIVE"
        assert settings.ENVIRONMENT == "local_simulation"

    def test_protected_manifests_intact(self):
        p1 = r"C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\EXP_MTF01_PARAMETER_MANIFEST.json"
        assert os.path.exists(p1)
        with open(p1, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["isolation_guards"]["live_trading_enabled"] is False
        assert data["isolation_guards"]["paper_broker_enabled"] is False
