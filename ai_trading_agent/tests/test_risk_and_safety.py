"""
ai_trading_agent.tests.test_risk_and_safety
===========================================
Pruebas críticas de seguridad, Risk Engine determinista y control estricto de ANALYSIS_ONLY.
"""

import pytest
from datetime import datetime
from ai_trading_agent.domain.enums import (
    SignalDirection, RiskDecision, TradingMode, OrderSide, OrderType, OrderStatus
)
from ai_trading_agent.domain.models import TradeProposal, PaperOrder, DecisionRecord, MarketRegime
from ai_trading_agent.risk.engine import DeterministicRiskEngine
from ai_trading_agent.execution.paper_broker import PaperBroker
from ai_trading_agent.journal.trade_journal import trade_journal


def test_risk_engine_valid_sizing():
    engine = DeterministicRiskEngine(risk_per_trade_pct=1.0, min_rr_ratio=2.0)
    proposal = TradeProposal(
        decision_id="dec_test_001",
        symbol="SPY",
        direction=SignalDirection.BUY,
        entry_price=500.0,
        stop_loss=495.0,  # $5 de riesgo por acción
        take_profit=510.0, # $10 de beneficio (R:R 2.0)
        rr_ratio=2.0,
        timestamp=datetime.utcnow(),
        rationale="Setup válido"
    )

    assessment = engine.assess_proposal(
        proposal=proposal,
        equity=100000.0,
        daily_pnl=0.0,
        open_positions=[]
    )

    assert assessment.decision == RiskDecision.APPROVED
    # 1% de 100k = $1000. Riesgo de $5 por acción -> 200 acciones
    # Max allocation = 15% de 100k = 15k / 500 = 30 acciones (limitado por capital por trade)
    assert assessment.approved_quantity == 30
    assert assessment.estimated_risk_dollars == 150.0  # 30 * $5


def test_risk_engine_rejects_insufficient_rr():
    engine = DeterministicRiskEngine(min_rr_ratio=2.0)
    proposal = TradeProposal(
        decision_id="dec_test_002",
        symbol="SPY",
        direction=SignalDirection.BUY,
        entry_price=500.0,
        stop_loss=495.0,  # $5 riesgo
        take_profit=505.0, # $5 beneficio (R:R 1.0 < 2.0)
        rr_ratio=1.0,
        timestamp=datetime.utcnow(),
        rationale="Setup con bajo R:R"
    )

    assessment = engine.assess_proposal(proposal, equity=100000.0, daily_pnl=0.0, open_positions=[])
    assert assessment.decision == RiskDecision.REJECTED
    assert any("RATIO R:R INSUFICIENTE" in r for r in assessment.reasons)


def test_risk_engine_circuit_breaker_daily_loss():
    engine = DeterministicRiskEngine(max_daily_loss_pct=2.0)
    proposal = TradeProposal(
        decision_id="dec_test_003",
        symbol="SPY",
        direction=SignalDirection.BUY,
        entry_price=500.0,
        stop_loss=495.0,
        take_profit=510.0,
        rr_ratio=2.0,
        timestamp=datetime.utcnow(),
        rationale="Test"
    )

    # -2.5% de pérdida acumulada hoy
    assessment = engine.assess_proposal(proposal, equity=100000.0, daily_pnl=-2500.0, open_positions=[])
    assert assessment.decision == RiskDecision.REJECTED
    assert assessment.circuit_breaker_active is True
    assert any("CIRCUIT BREAKER DIARIO" in r for r in assessment.reasons)


def test_analysis_only_mode_blocks_execution(paper_broker_instance):
    order = PaperOrder(
        order_id="ord_test_001",
        decision_id="dec_test_001",
        symbol="SPY",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
        requested_price=500.0,
        created_at=datetime.utcnow()
    )

    # En modo ANALYSIS_ONLY debe lanzar excepción de permiso obligatoriamente
    with pytest.raises(PermissionError) as exc_info:
        paper_broker_instance.submit_order(order, mode=TradingMode.ANALYSIS_ONLY)

    assert "EJECUCIÓN BLOQUEADA POR DISEÑO" in str(exc_info.value)
    assert paper_broker_instance.orders[order.order_id].status == OrderStatus.REJECTED


def test_paper_trading_execution_and_journal_trace(paper_broker_instance):
    order = PaperOrder(
        order_id="ord_test_002",
        decision_id="dec_trace_999",
        symbol="SPY",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
        requested_price=500.0,
        created_at=datetime.utcnow()
    )

    # En modo PAPER_TRADING sí debe ejecutar y actualizar balances
    filled = paper_broker_instance.submit_order(order, mode=TradingMode.PAPER_TRADING)
    assert filled.status == OrderStatus.FILLED
    assert filled.avg_fill_price > 0
    assert filled.commission > 0
    assert "SPY" in paper_broker_instance.positions

    # Trazabilidad inmutable en Journal
    record = DecisionRecord(
        decision_id="dec_trace_999",
        timestamp=datetime.utcnow(),
        symbol="SPY",
        market_regime=MarketRegime.BULL_TREND,
        signal_direction=SignalDirection.BUY,
        signal_score=78.0,
        reasons=["Tendencia confirmada"],
        risk_decision=RiskDecision.APPROVED,
        risk_reasons=["Aprobado por tamaño"],
        order_id=filled.order_id,
        order_status=filled.status,
        execution_price=filled.avg_fill_price
    )
    trade_journal.log_decision(record)

    # Reconstrucción exacta mediante decision_id
    retrieved = trade_journal.get_decision("dec_trace_999")
    assert retrieved is not None
    assert retrieved.decision_id == "dec_trace_999"
    assert retrieved.order_status == OrderStatus.FILLED
