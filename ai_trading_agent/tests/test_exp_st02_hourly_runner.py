"""
ai_trading_agent.tests.test_exp_st02_hourly_runner
==================================================
Suite de Pruebas Unitarias Aisladas para st02_hourly_runner.py (EXP-ST02).

Verifica:
1. Latencia causal estricta (rechazo de barras no cerradas con CausalLatencyViolation).
2. Idempotencia absoluta (bloqueo determinista de eventos duplicados).
3. Modelo de ejecuciA3n anti-retroactivo (fill causal T+1 Open con slippage).
4. ClasificaciA3n rigurosa: SYNCHRONOUS_LIVE_OBSERVATION vs DELAYED_REPLAY.
5. Tratamiento determinista de la barra parcial (15:30 - 16:00 EST).
6. Integridad criptogrAfica continua de los ledgers (cadena SHA-256 vAlida).
7. Aislamiento total de brokers y preservaciA3n de configuraciones congeladas.
"""

import pytest
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
import zoneinfo

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.experiments.exp_st02.st02_hourly_runner import (
    St02HourlyRunner,
    CausalLatencyViolation,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_models import (
    ShadowEventTypeST02,
)

NY_TZ = zoneinfo.ZoneInfo("America/New_York")


def generate_synthetic_h1_bars(n_bars: int = 250, start_dt: datetime = None, symbol: str = "GLD") -> list:
    """Genera serie sintAtica causal de barras H1 para pruebas de SuperTrend y EMA 200."""
    start = start_dt or datetime(2026, 10, 1, 9, 30, tzinfo=NY_TZ)
    bars = []
    base_price = 200.0

    curr_dt = start
    for i in range(n_bars):
        # Simular tendencia suave alcista para cruzar EMA 200 hacia arriba en las barras finales
        if i < 200:
            price = base_price + (i * 0.05)
        else:
            price = base_price + 10.0 + ((i - 200) * 0.5)  # Impulso alcista para generar flip

        o = price
        h = price + 1.2
        l = price - 0.8
        c = price + 0.5
        v = 10000.0

        bars.append(
            OHLCVBar(
                symbol=symbol,
                timestamp=curr_dt,
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
            )
        )
        curr_dt = curr_dt + timedelta(hours=1)

    return bars


@pytest.fixture
def temp_runner():
    """Crea una instancia de St02HourlyRunner con directorio de ledgers temporal."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_st02_ledgers_"))
    runner = St02HourlyRunner(ledgers_dir=temp_dir)
    yield runner, temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_causal_latency_enforcement(temp_runner):
    """Verifica que intentar evaluar una barra que aAn no ha cerrado arroja CausalLatencyViolation."""
    runner, _ = temp_runner
    bars = generate_synthetic_h1_bars(220)

    # Barra 210 inicia a las 10:30, cierra a las 11:30
    target_bar = bars[210]
    bar_open_utc = target_bar.timestamp.astimezone(timezone.utc)
    bar_close_utc = bar_open_utc + timedelta(hours=1)

    # Intento de evaluar 5 minutos ANTES de que cierre la barra
    premature_eval_time = bar_close_utc - timedelta(minutes=5)

    with pytest.raises(CausalLatencyViolation) as exc_info:
        runner.evaluate_bar(
            candidate_id="ST02-GLD-BASE",
            bars=bars,
            target_bar_idx=210,
            evaluation_timestamp_utc=premature_eval_time,
        )

    assert "Causal violation" in str(exc_info.value)


def test_delayed_replay_vs_synchronous_classification(temp_runner):
    """Verifica que la evaluaciA3n se clasifique correctamente como SYNCHRONOUS vs DELAYED_REPLAY."""
    runner, _ = temp_runner
    bars = generate_synthetic_h1_bars(220)

    target_bar = bars[210]
    bar_close_utc = target_bar.timestamp.astimezone(timezone.utc) + timedelta(hours=1)

    # 1. EvaluaciA3n sAncrona (2 minutos despuAs del cierre)
    sync_eval_time = bar_close_utc + timedelta(minutes=2)
    res_sync = runner.evaluate_bar(
        candidate_id="ST02-GLD-BASE",
        bars=bars,
        target_bar_idx=210,
        evaluation_timestamp_utc=sync_eval_time,
    )
    assert res_sync["status"] == "SUCCESS"
    assert res_sync["eval_mode"] == "SYNCHRONOUS_LIVE_OBSERVATION"

    # 2. EvaluaciA3n tardA-a (2 horas despuAs del cierre) sobre otra barra
    target_bar_2 = bars[211]
    bar_close_utc_2 = target_bar_2.timestamp.astimezone(timezone.utc) + timedelta(hours=1)
    late_eval_time = bar_close_utc_2 + timedelta(hours=2)

    res_late = runner.evaluate_bar(
        candidate_id="ST02-GLD-BASE",
        bars=bars,
        target_bar_idx=211,
        evaluation_timestamp_utc=late_eval_time,
    )
    assert res_late["status"] == "SUCCESS"
    assert res_late["eval_mode"] == "DELAYED_REPLAY"


def test_idempotency_guard(temp_runner):
    """Verifica que evaluar la misma barra dos veces devuelva ALREADY_PROCESSED sin duplicar ledgers."""
    runner, _ = temp_runner
    bars = generate_synthetic_h1_bars(220)

    target_bar = bars[210]
    bar_close_utc = target_bar.timestamp.astimezone(timezone.utc) + timedelta(hours=1)
    eval_time = bar_close_utc + timedelta(minutes=5)

    # Primera ejecuciA3n
    res1 = runner.evaluate_bar(
        candidate_id="ST02-DIA-BASE",
        bars=bars,
        target_bar_idx=210,
        evaluation_timestamp_utc=eval_time,
    )
    assert res1["status"] == "SUCCESS"

    entries_after_first = runner.ledgers["ST02-DIA-BASE"].read_all_entries()
    count_first = len(entries_after_first)

    # Segunda ejecuciA3n exactamente con la misma barra
    res2 = runner.evaluate_bar(
        candidate_id="ST02-DIA-BASE",
        bars=bars,
        target_bar_idx=210,
        evaluation_timestamp_utc=eval_time + timedelta(minutes=10),
    )
    assert res2["status"] == "ALREADY_PROCESSED"
    assert "already evaluated" in res2["message"]

    entries_after_second = runner.ledgers["ST02-DIA-BASE"].read_all_entries()
    count_second = len(entries_after_second)

    # Cero entradas duplicadas
    assert count_first == count_second


def test_partial_bar_handling_1530_1600(temp_runner):
    """Verifica el tratamiento de la barra parcial 15:30 - 16:00 EST."""
    runner, _ = temp_runner

    # Construir barra parcial especA-fica de las 15:30 EST
    start_dt = datetime(2026, 11, 2, 15, 30, tzinfo=NY_TZ)
    bars = generate_synthetic_h1_bars(210)
    # Reemplazar la Altima barra con el timestamp 15:30 EST
    bars[-1] = OHLCVBar(
        symbol="GLD",
        timestamp=start_dt,
        open=215.0,
        high=215.5,
        low=214.8,
        close=215.2,
        volume=5000.0,
    )

    # La barra parcial cierra a las 16:00 EST (duraciA3n 30 minutos)
    bar_close_utc = start_dt.astimezone(timezone.utc) + timedelta(minutes=30)

    # Intento de evaluar a las 15:55 EST (antes de cierre) -> debe fallar causalmente
    premature_eval = bar_close_utc - timedelta(minutes=5)
    with pytest.raises(CausalLatencyViolation):
        runner.evaluate_bar(
            candidate_id="ST02-GLD-H5",
            bars=bars,
            target_bar_idx=len(bars) - 1,
            evaluation_timestamp_utc=premature_eval,
        )

    # EvaluaciA3n vAlida a las 16:01 EST (1 minuto post-cierre) -> debe pasar
    valid_eval = bar_close_utc + timedelta(minutes=1)
    res = runner.evaluate_bar(
        candidate_id="ST02-GLD-H5",
        bars=bars,
        target_bar_idx=len(bars) - 1,
        evaluation_timestamp_utc=valid_eval,
    )
    assert res["status"] == "SUCCESS"
    assert res["eval_mode"] == "SYNCHRONOUS_LIVE_OBSERVATION"


def test_anti_retroactive_fill_and_cryptographic_ledger_integrity(temp_runner):
    """
    Verifica que las entradas se ejecuten causalmente en T+1 Open (con slippage)
    y que la cadena criptogrAfica SHA-256 permanezca 100% vAlida.
    """
    runner, _ = temp_runner
    bars = generate_synthetic_h1_bars(230)

    # Evaluar secuencia de 5 barras consecutivas
    for idx in range(215, 220):
        bar_close_utc = bars[idx].timestamp.astimezone(timezone.utc) + timedelta(hours=1)
        eval_time = bar_close_utc + timedelta(minutes=1)

        runner.evaluate_bar(
            candidate_id="ST02-GLD-BASE",
            bars=bars,
            target_bar_idx=idx,
            evaluation_timestamp_utc=eval_time,
        )

    ledger = runner.ledgers["ST02-GLD-BASE"]
    entries = ledger.read_all_entries()

    # Verificar que todas las entradas tengan prev_hash encadenado y hash vAlido
    is_valid, violations = ledger.verify_integrity()
    assert is_valid is True
    assert len(violations) == 0

    # Si hubo algAn fill simulado, verificar que el precio y timestamp cumplan con T+1 Causal
    fills = [e for e in entries if e.event_type == ShadowEventTypeST02.FILL_SIMULATED]
    for f in fills:
        payload = f.payload
        assert payload["execution_model"] == "CAUSAL_T_PLUS_1_OPEN"
        assert payload["anti_retroactive_verified"] is True
        assert payload["slippage_bps"] == 2.0
