import sys
import os
import pytest

repo_root = r"C:\Users\edsel\Documents\trading-app-repo"
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

test_path = os.path.join(repo_root, "ai_trading_agent", "tests", "test_exp_mtf01_extreme_reversal.py")
ret = pytest.main(["-v", test_path])
print(f"Pytest return code: {ret}")
sys.exit(ret)
