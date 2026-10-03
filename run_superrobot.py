"""
run_superrobot.py
=================
Lanzador del servidor FastAPI para AI Trading Agent 1.0 (SuperRobot).
Servidor central en http://localhost:8090
"""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print(" INICIANDO AI TRADING AGENT 1.0 — SUPERROBOT CORE")
    print(" Modo: ANALYSIS_ONLY (100% auditable y determinista)")
    print(" Panel: http://localhost:8090")
    print("=" * 70)
    uvicorn.run("ai_trading_agent.api.app:app", host="127.0.0.1", port=8090, log_level="info", reload=True)
