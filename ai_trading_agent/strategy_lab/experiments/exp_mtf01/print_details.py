with open(r'C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\user_brief_full.txt', 'r', encoding='utf-8') as f:
    text = f.read()

import re
sections = re.split(r'\n(?=# \d+\. )', text)
for s in sections:
    header = s.strip().split('\n')[0]
    num = re.search(r'# (\d+)\.', header)
    if num and int(num.group(1)) in [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18]:
        print(f"=== {header} ===")
        print(s[:3500])
        print("\n" + "="*50 + "\n")
