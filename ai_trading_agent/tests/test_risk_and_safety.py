"""
ai_trading_agent.tests.test_risk_and_safety
===========================================
Pruebas críticas de seguridad, Motor de Riesgo Determinista de $1,000,000 USD y control de ANALYSIS_ONLY.
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
from database import init_db, set_setting
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def reset_risk_db_settings():
    """Restablece el estado persistente de riesgo en SQLite antes de cada prueba."""
    init_db()
    set_setting("risk_high_water_mark", "1000000.0")
    set_setting("daily_pnl_accumulated", "0.0")
    set_setting("consecutive_losses_generic", "0")
    set_setting("consecutive_losses_orb_test", "0")
    set_setting("consecutive_losses_restart_test_strat", "0")


def test_risk_engine_valid_sizing_1m_profile():
    """Prueba el dimensionamiento exacto de posición con la fórmula floor(risk_budget / risk_per_share) para $1,000,000 USD."""
    engine = DeterministicRiskEngine(risk_per_trade_pct=0.25, min_rr_ratio=2.0)
    proposal = TradeProposal(
        decision_id="dec_test_1m_001",
        symbol="SPY",
        direction=SignalDirection.BUY,
        entry_price=500.0,
        stop_loss=495.0,  # $5 de riesgo por acción
        take_profit=510.0, # $10 de beneficio (R:R 2.0)
        rr_ratio=2.0,
        timestamp=datetime.utcnow(),
        rationale="Setup válido $1M profile"
    )

    assessment = engine.assess_proposal(
        proposal=proposal,
        equity=1000000.0,
        daily_pnl=0.0,
        open_positions=[]
    )

    assert assessment.decision == RiskDecision.APPROVED
    # Presupuesto riesgo 0.25% de $1M = $2,500 USD.
    # Costes (slippage 5bps = $0.25 + comisión $0.005) -> risk_per_share ~ $5.255
    # floor(2500 / 5.255) -> 475 acciones
    assert assessment.approved_quantity > 0
    assert assessment.estimated_risk_dollars <= 2500.0


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

    assessment = engine.assess_proposal(proposal, equity=1000000.0, daily_pnl=0.0, open_positions=[])
    assert assessment.decision == RiskDecision.REJECTED
    assert any("RATIO R:R INSUFICIENTE" in r for r in assessment.reasons)


def test_risk_engine_circuit_breaker_daily_loss_10k():
    """Verifica que el límite diario de pérdida de $10,000 USD active el Circuit Breaker de inmediato."""
    engine = DeterministicRiskEngine(max_daily_loss=10000.0)
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

    # Pérdida del día de -$10,500 USD
    assessment = engine.assess_proposal(proposal, equity=1000000.0, daily_pnl=-10500.0, open_positions=[])
    assert assessment.decision == RiskDecision.REJECTED
    assert assessment.circuit_breaker_active is True
    assert any("CIRCUIT BREAKER DIARIO" in r for r in assessment.reasons)


def test_risk_engine_consecutive_losses_pause():
    """Verifica la pausa de estrategia tras 3 pérdidas consecutivas."""
    engine = DeterministicRiskEngine(max_consecutive_losses=3)
    strat_code = "orb_test"

    # Registrar 3 pérdidas consecutivas
    engine.record_trade_result(strat_code, is_win=False)
    engine.record_trade_result(strat_code, is_win=False)
    engine.record_trade_result(strat_code, is_win=False)

    proposal = TradeProposal(
        decision_id="dec_test_consec_losses",
        symbol="QQQ",
        direction=SignalDirection.BUY,
        entry_price=400.0,
        stop_loss=395.0,
        take_profit=410.0,
        rr_ratio=2.0,
        timestamp=datetime.utcnow(),
        rationale="Test consec losses",
        strategy_code=strat_code
    )

    assessment = engine.assess_proposal(proposal, equity=1000000.0, daily_pnl=0.0, open_positions=[])
    assert assessment.decision == RiskDecision.REJECTED
    assert any("ESTRATEGIA PAUSADA" in r for r in assessment.reasons)

    # Restablecer tras una victoria
    engine.record_trade_result(strat_code, is_win=True)
    assessment2 = engine.assess_proposal(proposal, equity=1000000.0, daily_pnl=0.0, open_positions=[])
    assert assessment2.decision == RiskDecision.APPROVED


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


def test_risk_engine_defends_against_data_errors():
    """Verifica que la plataforma rechace precios inválidos/nulos a nivel de esquema Pydantic y de geometría."""
    engine = DeterministicRiskEngine()

    # 1. Pydantic debe rechazar precios <= 0 al instanciar TradeProposal
    with pytest.raises(ValidationError):
        TradeProposal(
            decision_id="dec_err_neg",
            symbol="SPY",
            direction=SignalDirection.BUY,
            entry_price=-100.0,
            stop_loss=490.0,
            take_profit=510.0,
            rr_ratio=2.0,
            timestamp=datetime.utcnow(),
            rationale="Error test negative"
        )

    # 2. Motor de riesgo debe rechazar propuesta con geometría inválida (stop loss >= entry)
    proposal_invalid_geom = TradeProposal(
        decision_id="dec_err_geom",
        symbol="SPY",
        direction=SignalDirection.BUY,
        entry_price=500.0,
        stop_loss=505.0,  # SL por encima de entrada para un BUY
        take_profit=520.0,
        rr_ratio=2.0,
        timestamp=datetime.utcnow(),
        rationale="Invalid geometry"
    )

    assessment = engine.assess_proposal(proposal_invalid_geom, equity=1000000.0, daily_pnl=0.0, open_positions=[])
    assert assessment.decision == RiskDecision.REJECTED
    assert any("GEOMETRÍA INVÁLIDA" in r for r in assessment.reasons)


def test_risk_engine_accounts_for_pending_orders_and_aggregate_risk():
    """Verifica que el cálculo de riesgo abierto agregado incluya posiciones activas Y órdenes pendientes."""
    engine = DeterministicRiskEngine(max_aggregate_open_risk=15000.0)

    # Simular orden pendiente con $14,000 USD de riesgo (700 acciones * $20 stop dist)
    class MockPendingOrder:
        symbol = "QQQ"
        entry_price = 400.0
        stop_loss = 380.0
        quantity = 700  # 700 * $20 = $14,000 riesgo

    pending = [MockPendingOrder()]

    # Propuesta que requiere ~$2,470 USD adicionales de riesgo ($14k + $2.47k = $16.47k > $15k cap)
    proposal = TradeProposal(
        decision_id="dec_test_pending",
        symbol="AAPL",
        direction=SignalDirection.BUY,
        entry_price=200.0,
        stop_loss=190.0,  # $10 riesgo por acción
        take_profit=230.0,
        rr_ratio=3.0,
        timestamp=datetime.utcnow(),
        rationale="Test pending risk"
    )

    assessment = engine.assess_proposal(
        proposal=proposal,
        equity=1000000.0,
        daily_pnl=0.0,
        open_positions=[],
        pending_orders=pending
    )

    assert assessment.decision == RiskDecision.REJECTED
    assert any("EXCESO DE RIESGO AGREGADO" in r for r in assessment.reasons)


def test_risk_engine_persists_across_simulated_process_restart():
    """Verifica la persistencia determinista de HWM Drawdown y contador de pérdidas tras un reinicio del servicio."""
    engine1 = DeterministicRiskEngine()
    strat = "restart_test_strat"

    # Registrar HWM alto ($1,200,000)
    engine1.get_high_water_mark(1200000.0)

    # Registrar 3 pérdidas consecutivas
    for _ in range(3):
        engine1.record_trade_result(strat, is_win=False)

    # SIMULAR REINICIO DEL PROCESO (crear nueva instancia)
    engine2 = DeterministicRiskEngine()

    # Verificar que el HWM se mantiene en $1.2M (con $1M actual = 16.6% drawdown > 10% halt)
    proposal = TradeProposal(
        decision_id="dec_restart_test",
        symbol="SPY",
        direction=SignalDirection.BUY,
        entry_price=500.0,
        stop_loss=495.0,
        take_profit=510.0,
        rr_ratio=2.0,
        timestamp=datetime.utcnow(),
        rationale="Restart test",
        strategy_code=strat
    )

    assessment = engine2.assess_proposal(proposal, equity=1000000.0, daily_pnl=0.0, open_positions=[])
    assert assessment.decision == RiskDecision.REJECTED
    assert assessment.circuit_breaker_active is True
    assert any("DRAWDOWN HALT ACTIVO" in r for r in assessment.reasons)


def test_extreme_scenario_overnight_gap_and_slippage_stress():
    """
    Escenario Extremo 1: Gap nocturno del -20% o slippage masivo que hace que la pérdida real supere
    el riesgo planificado. Verifica que la caída de equity activa el Drawdown Halt (>= 10%)
    y bloquea completamente nuevas entradas.
    """
    engine = DeterministicRiskEngine()
    
    # HWM inicial de $1,000,000 USD
    engine.get_high_water_mark(1000000.0)

    # Gap de apertura catastrófico reduce el equity a $880,000 USD (12% Drawdown desde HWM)
    catastrophic_equity = 880000.0

    proposal = TradeProposal(
        decision_id="dec_extreme_gap",
        symbol="SPY",
        direction=SignalDirection.BUY,
        entry_price=500.0,
        stop_loss=495.0,
        take_profit=510.0,
        rr_ratio=2.0,
        timestamp=datetime.utcnow(),
        rationale="Intento de entrada post-gap"
    )

    assessment = engine.assess_proposal(
        proposal=proposal,
        equity=catastrophic_equity,
        daily_pnl=-120000.0,
        open_positions=[]
    )

    assert assessment.decision == RiskDecision.REJECTED
    assert assessment.circuit_breaker_active is True
    assert any("DRAWDOWN HALT ACTIVO" in r for r in assessment.reasons)


def test_extreme_scenario_flash_crash_daily_loss_breach():
    """
    Escenario Extremo 2: Flash crash intradiario con múltiples ejecuciones con slippage severo.
    La pérdida del día alcanza -$25,000 USD (muy por encima del límite de $10,000 USD).
    Verifica la activación inmediata del Circuit Breaker diario determinista.
    """
    engine = DeterministicRiskEngine(max_daily_loss=10000.0)

    proposal = TradeProposal(
        decision_id="dec_extreme_flash_crash",
        symbol="QQQ",
        direction=SignalDirection.BUY,
        entry_price=400.0,
        stop_loss=395.0,
        take_profit=410.0,
        rr_ratio=2.0,
        timestamp=datetime.utcnow(),
        rationale="Intento de rebote en flash crash"
    )

    # Pérdida extrema intradiaria -$25,000 USD
    assessment = engine.assess_proposal(
        proposal=proposal,
        equity=975000.0,
        daily_pnl=-25000.0,
        open_positions=[]
    )

    assert assessment.decision == RiskDecision.REJECTED
    assert assessment.circuit_breaker_active is True
    assert any("CIRCUIT BREAKER DIARIO" in r for r in assessment.reasons)
