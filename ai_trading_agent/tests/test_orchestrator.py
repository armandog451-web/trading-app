"""
ai_trading_agent.tests.test_orchestrator
========================================
Pruebas de integración de extremo a extremo del pipeline orquestador.
"""

from ai_trading_agent.domain.enums import TradingMode, SignalDirection, OrderStatus
from ai_trading_agent.orchestrator import TradingPipelineOrchestrator
from ai_trading_agent.journal.trade_journal import trade_journal


def test_orchestrator_analysis_only_mode(bull_bars):
    trade_journal.clear()
    orch = TradingPipelineOrchestrator(mode=TradingMode.ANALYSIS_ONLY)
    result = orch.process_symbol("SPY", bull_bars)

    assert result["status"] in ("APPROVED", "NO_TRADE", "RISK_REJECTED")
    if result["status"] == "APPROVED":
        # En ANALYSIS_ONLY no debe existir orden enviada
        assert result["order_id"] is None
        assert result["order_status"] is None

        # Verificar que el Journal registró la decisión
        record = trade_journal.get_decision(result["decision_id"])
        assert record is not None
        assert record.decision_id == result["decision_id"]


def test_orchestrator_paper_trading_mode(bull_bars):
    trade_journal.clear()
    orch = TradingPipelineOrchestrator(mode=TradingMode.PAPER_TRADING)
    result = orch.process_symbol("SPY", bull_bars)

    assert result["status"] in ("APPROVED", "NO_TRADE", "RISK_REJECTED")
    if result["status"] == "APPROVED":
        # En PAPER_TRADING sí debe haberse ejecutado la orden
        assert result["order_id"] is not None
        assert result["order_status"] == OrderStatus.FILLED
        assert result["execution_price"] > 0

        # Verificar que el Journal registró la orden
        record = trade_journal.get_decision(result["decision_id"])
        assert record is not None
        assert record.order_id == result["order_id"]
        assert record.order_status == OrderStatus.FILLED
