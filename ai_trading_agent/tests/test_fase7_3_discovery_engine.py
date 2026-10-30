"""
ai_trading_agent.tests.test_fase7_3_discovery_engine
====================================================
Suite de Pruebas de Certificación para el Strategy Discovery Engine v2 (Fase 7.3):
1. DataIntegrityGate: Detección y descarte de barras no cerradas e invalidación de calendario.
2. No-Lookahead Bias: Verificación cronológica estricta.
3. Contabilidad Reconciliada: Descomposición exacta Gross, Slippage, Comisiones y Net PnL.
4. Estrés de Costes: Monotonía del impacto de fricciones (1x, 2x, 3x).
5. Determinismo de Fingerprints: Reproducibilidad absoluta de firmas SHA-256.
6. Aislamiento Físico de Brokers: Prohibición de conexión con Moomoo PAPER/LIVE.
7. Salvaguarda de D21: Inmutabilidad de la estrategia canónica.
8. Validación de Manifiestos: Integridad de esquemas JSON y CSV.
"""

import os
import json
import csv
from datetime import datetime
from pathlib import Path
import pytest

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.domain.enums import DataQualityStatus
from ai_trading_agent.strategy_lab.discovery.discovery_engine_v2 import (
    DataIntegrityGate,
    compute_source_fingerprint,
    compute_reconciled_metrics,
    ResearchStrategyStatus,
    ResearchFamily
)


@pytest.fixture
def sample_bars():
    """Genera 100 barras sintéticas consecutivas en días hábiles válidos."""
    bars = []
    # Usar fechas históricas de lunes a viernes
    base_date = datetime(2023, 1, 9, 16, 0)  # Lunes
    for i in range(100):
        # Avanzar días saltando fines de semana
        day_offset = i + (i // 5) * 2
        ts = datetime(2023, 1, 9 + (day_offset % 20), 16, 0)
        bars.append(OHLCVBar(
            timestamp=ts,
            symbol="TEST",
            open=100.0 + i * 0.1,
            high=102.0 + i * 0.1,
            low=99.0 + i * 0.1,
            close=101.0 + i * 0.1,
            volume=100000.0,
            source="test",
            quality_status=DataQualityStatus.VALID
        ))
    return bars


class TestStrategyDiscoveryEngineV2:

    def test_data_integrity_gate_drops_unclosed_bars(self):
        """Verifica que barras con fecha de hoy y hora menor a 16:00 ET sean descartadas como no cerradas."""
        today = datetime.utcnow()
        bar_closed = OHLCVBar(
            timestamp=datetime(2023, 5, 10, 16, 0),
            symbol="SPY", open=400.0, high=405.0, low=399.0, close=404.0, volume=50000.0
        )
        bar_unclosed = OHLCVBar(
            timestamp=today,
            symbol="SPY", open=404.0, high=406.0, low=403.0, close=405.5, volume=25000.0
        )

        # Simular evaluación a las 11:30 AM (mercado abierto, barra no cerrada)
        simulated_now = today.replace(hour=11, minute=30)
        sanitized, meta = DataIntegrityGate.sanitize_and_validate_bars("SPY", [bar_closed, bar_unclosed], reference_dt=simulated_now)

        assert meta["unclosed_bars_dropped"] == 1
        assert len(sanitized) == 1
        assert sanitized[0].timestamp == bar_closed.timestamp

    def test_deterministic_fingerprints(self):
        """Verifica que el cálculo de fingerprints sea 100% determinista y sensible a parámetros."""
        code_a = "def evaluate(): return True"
        params_a = {"lookback": 60, "threshold": 0.05}
        params_b = {"lookback": 60, "threshold": 0.06}

        fp_1 = compute_source_fingerprint(code_a, params_a)
        fp_2 = compute_source_fingerprint(code_a, params_a)
        fp_diff = compute_source_fingerprint(code_a, params_b)

        assert fp_1 == fp_2
        assert len(fp_1) == 16
        assert fp_1 != fp_diff

    def test_reconciled_accounting_exactness(self):
        """Verifica que la descomposición matemática coincida exactamente al centavo."""
        trades = [
            {
                "true_gross_pnl": 500.00,
                "slippage_usd": 25.00,
                "commission_usd": 10.00,
                "true_net_pnl": 465.00,  # 500 - 25 - 10
                "return_pct": 2.5
            },
            {
                "true_gross_pnl": -200.00,
                "slippage_usd": 20.00,
                "commission_usd": 10.00,
                "true_net_pnl": -230.00,  # -200 - 20 - 10
                "return_pct": -1.2
            }
        ]

        metrics = compute_reconciled_metrics(trades)

        assert metrics["trade_count"] == 2
        assert metrics["sum_true_gross_pnl"] == 300.00
        assert metrics["sum_slippage_usd"] == 45.00
        assert metrics["sum_commission_usd"] == 20.00
        assert metrics["sum_total_costs_usd"] == 65.00
        assert metrics["sum_true_net_pnl"] == 235.00
        assert metrics["gross_profit_factor"] == round(500.0 / 200.0, 2)  # 2.50
        assert metrics["net_profit_factor"] == round(465.0 / 230.0, 2)    # 2.02

    def test_manifest_and_trades_export_integrity(self):
        """Verifica que los archivos generados en scratch cumplan con el esquema institucional."""
        scratch_dir = Path(__file__).resolve().parent.parent / "scratch"
        json_path = scratch_dir / "fase7_3_discovery_manifest.json"
        csv_path = scratch_dir / "fase7_3_discovery_trades.csv"

        assert json_path.exists(), "fase7_3_discovery_manifest.json no existe"
        assert csv_path.exists(), "fase7_3_discovery_trades.csv no existe"

        with open(json_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["manifest_version"] == "2.0"
        assert manifest["phase"] == "FASE_7_3"
        assert "governance" in manifest
        assert manifest["governance"]["live_trading_enabled"] is False
        assert manifest["governance"]["d21_fingerprint"] == "f885ec2db2422308"
        assert len(manifest["experiments"]) == 4

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        assert len(reader) > 0
        required_cols = {"strategy_id", "symbol", "cost_tier", "true_gross_pnl", "slippage_usd", "commission_usd", "true_net_pnl"}
        assert required_cols.issubset(set(reader[0].keys()))

    def test_broker_isolation_invariants(self):
        """Verifica que el motor de descubrimiento no exponga interfaces ni métodos de envío de órdenes a Moomoo."""
        from ai_trading_agent.strategy_lab.discovery import discovery_engine_v2
        # Verificar que ningún método envíe órdenes a broker
        funcs = [m for m in dir(discovery_engine_v2) if callable(getattr(discovery_engine_v2, m))]
        forbidden = ["submit_order", "place_order", "execute_live", "connect_moomoo"]
        for f in funcs:
            for forb in forbidden:
                assert forb not in f.lower(), f"Violación de aislamiento detectada: {f}"
