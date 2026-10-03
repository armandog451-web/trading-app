"""
ai_trading_agent.tests.test_brokers_and_telegram
================================================
Pruebas unitarias de:
1. Servicio de alertas a Telegram (@LaraMayaBot)
2. Adaptador de Moomoo OpenD (US Paper)
3. Adaptador de Alpaca Markets (Paper)
4. Gestor unificado de brokers (UnifiedBrokerManager)
5. Endpoints de control de broker y envío de balances
"""

import pytest
from starlette.testclient import TestClient

from ai_trading_agent.api.app import app
from ai_trading_agent.domain.enums import OrderSide, OrderType, OrderStatus
from ai_trading_agent.domain.models import PaperOrder
from ai_trading_agent.notifications.telegram_service import telegram_notifier
from ai_trading_agent.execution.brokers.moomoo_adapter import moomoo_adapter
from ai_trading_agent.execution.brokers.alpaca_adapter import alpaca_adapter
from ai_trading_agent.execution.brokers.unified_manager import unified_broker


client = TestClient(app)


class TestBrokersAndTelegram:

    def test_telegram_service_configured(self):
        """Verifica que el servicio de Telegram esté configurado con el bot del usuario."""
        assert telegram_notifier.is_configured is True
        assert "8885408454" in telegram_notifier.bot_token
        assert telegram_notifier.chat_id == "8887098910"

    def test_moomoo_adapter_resilience(self):
        """Verifica que el adaptador de Moomoo devuelva resumen de cuenta y posiciones sin error."""
        acc = moomoo_adapter.get_account_summary()
        assert "broker" in acc
        assert "cash" in acc
        assert "equity" in acc
        assert acc["cash"] > 0

        pos = moomoo_adapter.get_positions()
        assert isinstance(pos, list)

    def test_alpaca_adapter_resilience(self):
        """Verifica que el adaptador de Alpaca opere en modo Paper/Simulación sin error."""
        acc = alpaca_adapter.get_account_summary()
        assert "broker" in acc
        assert "cash" in acc
        assert "equity" in acc
        assert acc["equity"] > 0

        pos = alpaca_adapter.get_positions()
        assert isinstance(pos, list)

    def test_unified_broker_switching(self):
        """Verifica que el gestor unificado conmute dinámicamente entre Moomoo y Alpaca."""
        # Conmutar a Alpaca
        unified_broker.set_active_broker("alpaca")
        assert unified_broker.active_broker_name == "alpaca"
        acc_alpaca = unified_broker.get_account_summary()
        assert "Alpaca" in acc_alpaca["broker"]

        # Conmutar a Moomoo
        unified_broker.set_active_broker("moomoo")
        assert unified_broker.active_broker_name == "moomoo"
        acc_moomoo = unified_broker.get_account_summary()
        assert "Moomoo" in acc_moomoo["broker"]

    def test_api_broker_switch_endpoint(self):
        """Verifica el endpoint REST /api/broker/switch."""
        res = client.post("/api/broker/switch", json={"broker": "moomoo"})
        assert res.status_code == 200
        data = res.json()
        assert data["active_broker"] == "moomoo"
        assert "account" in data

    def test_api_telegram_test_endpoint(self):
        """Verifica el endpoint /api/telegram/test."""
        res = client.post("/api/telegram/test")
        assert res.status_code == 200
        data = res.json()
        assert "bot_configured" in data
        assert data["bot_configured"] is True

    def test_api_telegram_balance_endpoint(self):
        """Verifica el endpoint /api/telegram/balance."""
        res = client.post("/api/telegram/balance")
        assert res.status_code == 200
        data = res.json()
        assert "broker" in data
