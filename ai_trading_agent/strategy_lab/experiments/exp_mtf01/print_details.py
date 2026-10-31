import sys, io, re

with open(r'C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\user_brief_full.txt', 'r', encoding='utf-8') as f:
    text = f.read()

sections = re.split(r'\n(?=# \d+\. )', text)
with open(r'C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\sections_extracted_utf8.txt', 'w', encoding='utf-8') as out:
    for s in sections:
        header = s.strip().split('\n')[0]
        num = re.search(r'# (\d+)\.', header)
        if num and int(num.group(1)) in [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18]:
            out.write(f"=== {header} ===\n")
            out.write(s)
            out.write("\n" + "="*50 + "\n\n")
print("Done writing utf-8 extracted sections")
