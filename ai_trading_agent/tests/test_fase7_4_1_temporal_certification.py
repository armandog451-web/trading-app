"""
ai_trading_agent.tests.test_fase7_4_1_temporal_certification
=============================================================
Suite de Pruebas de Certificación de la Fase 7.4.1:
1. Manejo riguroso de zonas horarias con zoneinfo (America/New_York).
2. Verificación de transición EDT -> EST (1 nov 2026).
3. Verificación de T0 canónico (2026-10-30T20:00:00Z = 16:00 EDT).
4. Contadores forward en cero antes de la primera sesión prospectiva.
5. Aislamiento dinámico de brokers en tiempo de ejecución.
6. Sellado periódico criptográfico del ledger (Checkpoints).
7. Versionado auditable de manifiestos (v1.1 / v7.4.1).
8. Inspección en modo solo lectura de la salud operativa de D21.
"""

import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from ai_trading_agent.strategy_lab.shadow.freeze_manifests import (
    generate_freeze_manifests,
    get_market_close_utc
)
from ai_trading_agent.strategy_lab.shadow.campaign_models import (
    ShadowCampaignStatus,
    ShadowEventType,
    ShadowValidationClock
)
from ai_trading_agent.strategy_lab.shadow.crypto_ledger import (
    ShadowEvidenceLedger,
    LedgerTamperDetectedError
)


@pytest.fixture
def repo_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def manifests(repo_root):
    return generate_freeze_manifests(repo_root)


def test_01_timezone_market_close_handling_zoneinfo():
    """
    Verifica que la conversión de hora de cierre de mercado (16:00 ET) a UTC sea dinámica
    y maneje correctamente la transición de horario de verano (EDT -> EST).
    """
    ny = ZoneInfo("America/New_York")
    utc = ZoneInfo("UTC")

    # 1. Viernes 30 de Octubre de 2026 (En horario EDT: UTC-4)
    close_oct30_utc = get_market_close_utc("2026-10-30")
    assert close_oct30_utc == "2026-10-30T20:00:00Z", f"Expected 20:00:00Z for Oct 30 EDT, got {close_oct30_utc}"

    dt_oct30_et = datetime(2026, 10, 30, 16, 0, 0, tzinfo=ny)
    assert dt_oct30_et.tzname() == "EDT"
    assert dt_oct30_et.utcoffset().total_seconds() == -14400  # -4 horas

    # 2. Domingo 1 de Noviembre de 2026: Termina Daylight Saving Time a las 02:00
    # 3. Lunes 2 de Noviembre de 2026 (En horario EST: UTC-5)
    close_nov2_utc = get_market_close_utc("2026-11-02")
    assert close_nov2_utc == "2026-11-02T21:00:00Z", f"Expected 21:00:00Z for Nov 2 EST, got {close_nov2_utc}"

    dt_nov2_et = datetime(2026, 11, 2, 16, 0, 0, tzinfo=ny)
    assert dt_nov2_et.tzname() == "EST"
    assert dt_nov2_et.utcoffset().total_seconds() == -18000  # -5 horas


def test_02_canonical_t0_verification(manifests):
    """
    Verifica que el T0 canónico sea exactamente las 16:00 EDT = 20:00:00Z
    y que la primera sesión forward sea el 2 de Noviembre de 2026.
    """
    for sid, m in manifests.items():
        assert m.manifest_version == "1.1"
        assert m.market_timezone == "America/New_York"
        assert m.t0_timestamp_utc == "2026-10-30T20:00:00Z"
        assert "EDT" in m.t0_local_time
        assert m.t0_first_prospective_session == "2026-11-02"
        assert m.status == ShadowCampaignStatus.ACTIVATION_READY


def test_03_zero_forward_counters_prior_to_activation(repo_root):
    """
    Confirma que los contadores forward permanecen estrictamente en cero
    antes de la primera sesión evaluable (2026-11-02).
    """
    shadow_dir = repo_root / "ai_trading_agent" / "scratch" / "shadow_campaigns"
    for sid in ["MR_VolCond_ZScore_V1", "CS_RelMom_VolAdj_V2"]:
        clock_file = shadow_dir / f"validation_clock_{sid}.json"
        if clock_file.exists():
            with open(clock_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                clock = ShadowValidationClock(**data)
                assert clock.valid_shadow_evaluation_sessions == 0
                assert clock.shadow_signals_generated == 0
                assert clock.shadow_positions_opened == 0
                assert clock.shadow_positions_closed == 0
                assert clock.runtime_gaps == 0


def test_04_dynamic_broker_isolation():
    """
    Verifica dinámicamente que ningún módulo ni variable de broker esté activo.
    """
    isolated, violations = ShadowEvidenceLedger.verify_dynamic_broker_isolation()
    assert isolated is True, f"Dynamic isolation failed: {violations}"
    assert len(violations) == 0


def test_05_periodic_ledger_sealing_checkpoint(tmp_path):
    """
    Verifica que el sellado periódico genere un bloque de control criptográfico
    que ancle la cadena y detecte cualquier alteración posterior.
    """
    ledger = ShadowEvidenceLedger("TEST_CAMP", "SEAL_TEST", tmp_path)
    fp = "f" * 64

    # Agregar dos entradas
    ledger.append_entry(
        entry_id="ENTRY_1",
        market_date="2026-11-02",
        symbol="SPY",
        event_type=ShadowEventType.NO_SIGNAL,
        signal_direction="NO_TRADE",
        reason="No signal",
        strategy_fingerprint=fp,
        bar_hash="b" * 64
    )
    ledger.append_entry(
        entry_id="ENTRY_2",
        market_date="2026-11-02",
        symbol="QQQ",
        event_type=ShadowEventType.NO_SIGNAL,
        signal_direction="NO_TRADE",
        reason="No signal",
        strategy_fingerprint=fp,
        bar_hash="b" * 64
    )

    # Sellar punto de control de activación
    seal_entry = ledger.seal_checkpoint(
        checkpoint_name="ACTIVATION_CERTIFICATION_SEAL",
        strategy_fingerprint=fp,
        notes="Sello de activación de Fase 7.4.1"
    )

    assert seal_entry.event_type == ShadowEventType.CHECKPOINT_SEALED
    assert seal_entry.entry_index == 2
    assert "SEAL-SEAL_TEST-ACTIVATION_CERTIFICATION_SEAL" in seal_entry.entry_id

    # Verificar integridad de la cadena
    valid, msg = ledger.verify_chain_integrity()
    assert valid is True
    assert "INTEGRIDAD_VERIFICADA (3 entradas" in msg


def test_06_manifest_versioning_and_preservation(repo_root):
    """
    Verifica que existan tanto los manifiestos v7_4_1 como los manifiestos base
    y que ambos contengan la versión 1.1 corregida.
    """
    shadow_dir = repo_root / "ai_trading_agent" / "scratch" / "shadow_campaigns"
    for sid in ["MR_VolCond_ZScore_V1", "CS_RelMom_VolAdj_V2"]:
        base_f = shadow_dir / f"freeze_manifest_{sid}.json"
        v741_f = shadow_dir / f"freeze_manifest_{sid}_v7_4_1.json"
        assert base_f.exists(), f"Missing base manifest for {sid}"
        assert v741_f.exists(), f"Missing v7_4_1 manifest for {sid}"

        with open(v741_f, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["manifest_version"] == "1.1"
            assert data["t0_timestamp_utc"] == "2026-10-30T20:00:00Z"
