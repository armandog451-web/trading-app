with open(r'C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\user_brief_full.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if l.startswith('#'):
        print(f"Line {i+1}: {l.strip()}")
