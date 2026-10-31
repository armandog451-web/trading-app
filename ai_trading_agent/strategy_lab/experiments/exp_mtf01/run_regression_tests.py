import sys
import os
import pytest

repo_root = r"C:\Users\edsel\Documents\trading-app-repo"
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

tests = [
    os.path.join(repo_root, "ai_trading_agent", "tests", "test_exp_mtf01_extreme_reversal.py"),
    os.path.join(repo_root, "ai_trading_agent", "tests", "test_exp_st01_supertrend.py"),
    os.path.join(repo_root, "ai_trading_agent", "tests", "test_exp_st02_audit_and_shadow.py"),
]
ret = pytest.main(["-v"] + tests)
print(f"Regression tests return code: {ret}")
sys.exit(ret)
