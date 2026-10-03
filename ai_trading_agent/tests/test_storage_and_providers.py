"""
ai_trading_agent.tests.test_storage_and_providers
=================================================
Pruebas unitarias de:
1. Proveedores de datos de mercado (Synthetic & YFinance fallback)
2. Persistencia relacional de auditoría con SQLAlchemy (SQLite)
3. Endpoint del panel de control web institucional (Dashboard HTML)
"""

import pytest
from datetime import datetime
from starlette.testclient import TestClient

from ai_trading_agent.api.app import app
from ai_trading_agent.domain.enums import MarketRegime, SignalDirection, RiskDecision, OrderSide, OrderType, OrderStatus
from ai_trading_agent.domain.models import DecisionRecord, PaperOrder
from ai_trading_agent.data.providers.synthetic_provider import synthetic_provider
from ai_trading_agent.data.providers.yfinance_provider import yfinance_provider
from ai_trading_agent.data.storage.repository import audit_repo


client = TestClient(app)


class TestStorageAndProviders:

    def test_synthetic_provider_bars_and_quote(self):
        """Verifica que el proveedor sintético genere barras y cotizaciones válidas."""
        bars = synthetic_provider.get_historical_bars("SPY", count=50)
        assert len(bars) == 50
        assert bars[0].symbol == "SPY"

        quote = synthetic_provider.get_quote("SPY")
        assert quote is not None
        assert quote.symbol == "SPY"
        assert quote.ask >= quote.bid
        assert quote.spread > 0

    def test_yfinance_provider_resilience(self):
        """Verifica que el proveedor yfinance responda o active fallback sin arrojar excepciones."""
        # Consulta de barras (con fallback automático habilitado)
        bars = yfinance_provider.get_historical_bars("AAPL", count=20)
        assert len(bars) > 0

        # Consulta de cotización
        quote = yfinance_provider.get_quote("AAPL")
        assert quote is not None
        assert quote.symbol == "AAPL"

        # Consulta de calendario
        cal = yfinance_provider.get_event_calendar("AAPL")
        assert "has_earnings_today" in cal

    def test_audit_repository_sqlite_persistence(self):
        """Verifica el guardado y consulta de decisiones y órdenes en SQLite."""
        dec_id = f"test_dec_{int(datetime.utcnow().timestamp())}"
        record = DecisionRecord(
            decision_id=dec_id,
            timestamp=datetime.utcnow(),
            symbol="NVDA",
            market_regime=MarketRegime.BULL_TREND,
            signal_direction=SignalDirection.BUY,
            signal_score=85.0,
            reasons=["Confluencia alcista de indicadores"],
            risk_decision=RiskDecision.APPROVED,
            risk_reasons=["Riesgo 1% validado"],
            order_id="ord_nvda_1",
            order_status=OrderStatus.FILLED,
            execution_price=120.50
        )

        # 1. Guardar decisión
        audit_repo.save_decision(record)
        decisions = audit_repo.get_decisions(limit=10)
        found = any(d["decision_id"] == dec_id for d in decisions)
        assert found is True

        # 2. Guardar orden de paper broker
        order = PaperOrder(
            order_id="ord_nvda_1",
            decision_id=dec_id,
            symbol="NVDA",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
            requested_price=120.50,
            stop_loss=118.00,
            take_profit=125.50,
            status=OrderStatus.FILLED,
            avg_fill_price=120.55,
            commission=0.05,
            slippage=0.05,
            created_at=datetime.utcnow()
        )
        audit_repo.save_order(order)

        # 3. Guardar snapshot de cuenta
        audit_repo.save_account_snapshot(
            equity=100000.0,
            cash=98795.0,
            realized_pnl=0.0,
            unrealized_pnl=5.0,
            positions_count=1
        )

    def test_dashboard_html_endpoint(self):
        """Verifica que el dashboard HTML se sirva correctamente con código 200."""
        res = client.get("/")
        assert res.status_code == 200
        assert "AI TRADING AGENT 1.0" in res.text
        assert "KILL SWITCH" in res.text
        assert "Analizador Institucional" in res.text

        res_dash = client.get("/dashboard")
        assert res_dash.status_code == 200
        assert "AI TRADING AGENT 1.0" in res_dash.text
