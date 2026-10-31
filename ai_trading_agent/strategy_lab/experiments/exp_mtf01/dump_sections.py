with open(r'C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\user_brief_full.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect sections 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
import re

sections = re.split(r'\n(?=# \d+\. )', text)
for s in sections:
    header = s.strip().split('\n')[0]
    print("=" * 60)
    print(header)
    print("Length:", len(s))
    # print first 500 chars
    lines = s.strip().split('\n')
    print("\n".join(lines[:15]))
