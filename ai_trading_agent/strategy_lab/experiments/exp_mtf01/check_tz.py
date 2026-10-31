import os
import pandas as pd

data_dir = r"C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\data"

for tf in ["1d", "1h", "5m"]:
    df = pd.read_csv(os.path.join(data_dir, f"SPY_{tf}.csv"), index_col=0, parse_dates=True)
    print(f"SPY_{tf} index dtype: {df.index.dtype}, tz: {df.index.tz}")
