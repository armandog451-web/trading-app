import sys
import os
import pandas as pd

sys.path.insert(0, r"C:\Users\edsel\Documents\trading-app-repo")

from ai_trading_agent.strategy_lab.experiments.exp_mtf01.daily_context_engine import DailyContextEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.market_structure_engine import MarketStructureEngine
from ai_trading_agent.strategy_lab.experiments.exp_mtf01.fibonacci_confluence_engine import FibonacciConfluenceEngine

data_dir = r"C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\data"
symbols = ["SPY", "QQQ", "DIA", "IWM", "GLD", "TLT"]

d1_eng = DailyContextEngine()
h1_struct = MarketStructureEngine()
h1_fib = FibonacciConfluenceEngine()

print("=== DIAGNOSING D1 AND H1 SIGNALS (LAST 60 DAYS) ===")

for sym in symbols:
    df_d1 = pd.read_csv(os.path.join(data_dir, f"{sym}_1d.csv"), index_col=0, parse_dates=True)
    df_h1 = pd.read_csv(os.path.join(data_dir, f"{sym}_1h.csv"), index_col=0, parse_dates=True)
    df_m5 = pd.read_csv(os.path.join(data_dir, f"{sym}_5m.csv"), index_col=0, parse_dates=True)

    d1_feat = d1_eng.compute_daily_features(df_d1)
    # Filter to the M5 window (August 2026 to October 2026)
    m5_start = df_m5.index[0]
    d1_window = d1_feat[d1_feat.index >= m5_start]

    d1_bull_extremes = d1_window['Is_Lower_Extreme'].sum()
    d1_bear_extremes = d1_window['Is_Upper_Extreme'].sum()
    d1_bull_accel = d1_window['Accel_Down'].sum()
    d1_bear_accel = d1_window['Accel_Up'].sum()
    d1_bull_ctx = d1_window['D1_Bullish_Context'].sum()
    d1_bear_ctx = d1_window['D1_Bearish_Context'].sum()

    print(f"\n{sym} (M5 Window: {m5_start.strftime('%Y-%m-%d')} to {df_m5.index[-1].strftime('%Y-%m-%d')}):")
    print(f"  D1 Bars: {len(d1_window)}")
    print(f"  D1 Lower Extremes: {d1_bull_extremes}, Accel Down: {d1_bull_accel}, Bullish Context: {d1_bull_ctx}")
    print(f"  D1 Upper Extremes: {d1_bear_extremes}, Accel Up: {d1_bear_accel}, Bearish Context: {d1_bear_ctx}")

    h1_feat = h1_fib.compute_h1_indicators(df_h1)
    h1_feat = h1_struct.identify_swings_causally(h1_feat)
    h1_window = h1_feat[h1_feat.index >= m5_start]

    bos_bull = h1_window['BOS_Bullish'].sum()
    bos_bear = h1_window['BOS_Bearish'].sum()
    print(f"  H1 Bars: {len(h1_window)}, H1 Bullish BOS: {bos_bull}, H1 Bearish BOS: {bos_bear}")
