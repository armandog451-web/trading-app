import json

with open(r'C:\Users\edsel\.gemini\antigravity\brain\e7736a35-e8b4-4ce9-b42c-0d2570d46731\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        if obj.get('type') == 'USER_INPUT':
            content = obj.get('content', '')
            if 'EXP-MTF01' in content:
                print("FOUND USER INPUT EXP-MTF01, length:", len(content))
                with open(r'C:\Users\edsel\Documents\trading-app-repo\ai_trading_agent\strategy_lab\experiments\exp_mtf01\user_brief_full.txt', 'w', encoding='utf-8') as out:
                    out.write(content)
                print("Written to user_brief_full.txt")
