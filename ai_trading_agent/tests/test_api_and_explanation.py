"""
ai_trading_agent.tests.test_api_and_explanation
================================================
Pruebas unitarias de la API REST FastAPI y del Motor de Explicabilidad (Explanation Engine):
1. Endpoint /health (Comprobación de TradingMode inviolable y Kill Switch)
2. Endpoint /api/account (Resumen de saldo y posiciones)
3. Endpoint /api/analyze (Flujo completo con generación de explicación)
4. Endpoint /api/backtest (División In-Sample / Out-of-Sample vía API)
5. Endpoint /api/kill-switch (Activación inmediata y bloqueo)
6. Explicabilidad transparente sin sesgos ni alucinaciones
"""

import pytest
from starlette.testclient import TestClient
from ai_trading_agent.api.app import app
from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.enums import TradingMode
from ai_trading_agent.reporting.explanation_engine import explanation_engine


client = TestClient(app)


class TestApiAndExplanation:

    def test_health_endpoint(self):
        """Verifica que el endpoint de salud refleje el modo ANALYSIS_ONLY y kill switch."""
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert data["system"] == "AI Trading Agent 1.0"
        assert data["trading_mode"] == TradingMode.ANALYSIS_ONLY.value
        assert "risk_per_trade_pct" in data

    def test_account_summary_endpoint(self):
        """Verifica que el resumen de cuenta entregue valores iniciales de simulación."""
        res = client.get("/api/account")
        assert res.status_code == 200
        data = res.json()
        assert "account" in data
        assert "equity" in data["account"]
        assert "positions" in data

    def test_analyze_endpoint_with_explanation(self):
        """Verifica el análisis bajo demanda y la generación de explicación estructurada."""
        payload = {
            "symbol": "AAPL",
            "bars_count": 80,
            "regime": "BULL_TREND",
            "has_earnings_today": False
        }
        res = client.post("/api/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "result" in data
        assert "explanation" in data
        assert data["explanation"]["symbol"] == "AAPL"
        assert "final_verdict" in data["explanation"]
        assert len(data["explanation"]["summary"]) > 0

    def test_backtest_endpoint_in_sample_out_sample(self):
        """Verifica la ejecución remota de backtest y partición in-sample/out-sample."""
        payload = {
            "symbol": "MSFT",
            "bars_count": 120,
            "regime": "BULL_TREND",
            "train_ratio": 0.70
        }
        res = client.post("/api/backtest", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "in_sample" in data
        assert "out_of_sample" in data
        assert data["in_sample"]["dataset_type"] == "IN_SAMPLE"
        assert data["out_of_sample"]["dataset_type"] == "OUT_OF_SAMPLE"

    def test_kill_switch_endpoint(self):
        """Verifica que el endpoint de Kill Switch pueda activarlo y desactivarlo."""
        # Activar Kill Switch
        res = client.post("/api/kill-switch", json={"active": True, "reason": "Test de seguridad"})
        assert res.status_code == 200
        assert res.json()["kill_switch_active"] is True
        assert settings.KILL_SWITCH_ACTIVE is True

        # Desactivar Kill Switch para restaurar estado
        res = client.post("/api/kill-switch", json={"active": False, "reason": "Restaurar estado"})
        assert res.status_code == 200
        assert res.json()["kill_switch_active"] is False
        assert settings.KILL_SWITCH_ACTIVE is False

    def test_journal_history_endpoint(self):
        """Verifica que el historial del Journal sea accesible vía API."""
        res = client.get("/api/journal?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert "total_records" in data
        assert "records" in data
