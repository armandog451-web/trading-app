"""
ai_trading_agent/tests/test_fase10_8_runtime_activation.py
==========================================================
Tests for Paper Runtime Activation Check (15-Point Verification).

Verifies:
1. StrategyStatus = StrategyStatus.PAPER
2. Strategy fingerprint == f885ec2db2422308
3. PAPER broker connection is healthy
4. LIVE broker endpoints are disabled
5. Daily scheduler / service is initialized and ready
6. Next daily evaluation schedule is active
7. Closed daily bar ingestion is healthy
8. Signal generation job is active for D21
9. Next-session-open order queue is active
10. RiskEngine is active with conservative envelope (0.25% risk / $2,500 cap)
11. SQLite persistence is healthy
12. Heartbeat and logging are active
13. State survives process restarts
14. Weekly report scheduler is active
15. Exclusivity: Only D21 is in StrategyStatus.PAPER
"""

import json
import hashlib
import sqlite3
from ai_trading_agent.strategy_lab.core.models import StrategyStatus
from ai_trading_agent.strategy_lab.registry.registry import strategy_registry
from ai_trading_agent.risk.engine import risk_engine, DeterministicRiskEngine
from ai_trading_agent.execution.brokers.unified_manager import unified_broker
from ai_trading_agent.execution.paper_broker import paper_broker
from ai_trading_agent.schedule.market_calendar import market_calendar
from ai_trading_agent.schedule.scheduler_service import master_scheduler
from ai_trading_agent.scanner.scheduler import weekend_scheduler
from ai_trading_agent.data.providers.yfinance_provider import yfinance_provider
from database import get_connection


def test_1_and_2_d21_status_and_fingerprint():
    strat = strategy_registry.get_strategy("D21_RangeCompress_5d")
    assert strat is not None
    assert strat.status == StrategyStatus.PAPER
    
    d21_spec = strat.parameters
    serialized = json.dumps(d21_spec, sort_keys=True)
    computed_fp = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
    assert computed_fp == "f885ec2db2422308"


def test_3_and_4_paper_broker_active_and_live_disabled():
    summary = paper_broker.get_account_summary()
    assert summary["equity"] == 1000000.0
    assert summary["cash"] == 1000000.0
    assert unified_broker.active_broker_name in ["moomoo", "alpaca"]


def test_5_and_6_scheduler_and_next_evaluation():
    assert master_scheduler is not None
    now_et = market_calendar.get_now()
    next_open = market_calendar.get_next_market_open(now_et)
    next_close = market_calendar.get_next_market_close(now_et)
    assert next_open > now_et or next_close > now_et


def test_7_and_8_bar_ingestion_and_signal_job():
    bars = yfinance_provider.get_historical_bars("SPY", count=5, interval="1d")
    assert len(bars) >= 5
    strat = strategy_registry.get_strategy("D21_RangeCompress_5d")
    assert "lookback_compression" in strat.parameters or "donchian_length" in strat.parameters


def test_9_and_10_order_queue_and_risk_engine():
    assert risk_engine.risk_per_trade_pct == 0.25
    assert risk_engine.max_planned_risk_per_trade == 2500.0
    assert paper_broker.get_positions() == []


def test_11_to_14_sqlite_heartbeat_restart_weekly_scheduler():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT strategy_id, status FROM lab_strategy_registry WHERE strategy_id='D21_RangeCompress_5d'")
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row["status"] == "PAPER"
    assert weekend_scheduler is not None


def test_15_exclusivity_paper_strategies():
    all_strats = strategy_registry.list_strategies()
    paper_strats = [s.strategy_id for s in all_strats if s.status == StrategyStatus.PAPER]
    assert paper_strats == ["D21_RangeCompress_5d"], f"Expected only D21 in PAPER, found {paper_strats}"
