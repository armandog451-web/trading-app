"""
Script de Prueba en Seco (Dry-Run): test_oracle_agent.py
========================================================
Verifica la cadena completa del Agente Interceptor de Noticias y Riesgo con IA
simulando una señal en "US.QQQ" SIN enviar órdenes reales ni PAPER a Moomoo OpenD.

Pruebas incluidas:
  1. NewsCollector ("Los Sentidos"): extracción de símbolo limpio ("US.QQQ" -> "QQQ")
     y descarga RSS (Yahoo Finance, CNBC, MarketWatch) con timeout de 5s.
  2. TradingAgentJudge ("El Criterio en 4 Niveles"):
     - Escenario A: Filtro 1 (Regla Monetaria Mecánica -> STEP_1_RISK_GUARD).
     - Escenario B: Señal real en "US.QQQ" con titulares en vivo (Filtro 2/3 si hay API key o Filtro 4 FAIL_SAFE_BYPASS).
     - Escenario C: Simulación controlada de Filtro 2 (DOUBT) -> Filtro 3 (STEP_3_DEEP_AI con conteo alcista/bajista).
  3. ShadowLogger ("Modo Espejo"): persistencia en SQLite (`agent_audit.db`) y verificación de registros.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from unittest.mock import patch

from news_collector import NewsCollector
from ai_judge import TradingAgentJudge
from shadow_logger import ShadowLogger


def run_dry_run_test(send_telegram: bool = False) -> None:
    print("=" * 72)
    print("🚀 INICIANDO PRUEBA DRY-RUN: AGENTE INTERCEPTOR DE NOTICIAS Y RIESGO IA")
    print("=" * 72)

    # 1. Prueba de NewsCollector con "US.QQQ"
    collector = NewsCollector(timeout_seconds=5, max_headlines=15, lookback_hours=2.0)
    clean_symbol = collector.clean_ticker("US.QQQ")
    print(f"\n[PASO 2] NewsCollector: 'US.QQQ' -> símbolo limpio: '{clean_symbol}'")
    assert clean_symbol == "QQQ", f"Se esperaba 'QQQ', se obtuvo '{clean_symbol}'"

    headlines = collector.get_recent_headlines("US.QQQ")
    print(f"[PASO 2] Titulares recientes (últimas 2h) obtenidos: {len(headlines)}")
    for idx, title in enumerate(headlines[:5], start=1):
        print(f"   {idx}. {title}")
    if len(headlines) > 5:
        print(f"   ... (+{len(headlines) - 5} titulares adicionales)")

    # Señal simulada sobre US.QQQ (Dry-Run, sin tocar Moomoo place_order)
    simulated_signal = {
        "strategy": "DRY_RUN_ORACLE_TEST",
        "symbol": "US.QQQ",
        "direction": "LONG",
        "entry_price": 505.25,
        "stop_loss": 501.80,
        "take_profit": 512.50,
    }

    judge = TradingAgentJudge()
    print(f"[PASO 3] Límite diario configurado: ${judge.max_daily_loss_usd:,.2f} | Modelos: {judge.FAST_GEMINI_MODEL} / {judge.DEEP_GEMINI_MODEL}")
    assert judge.max_daily_loss_usd == 250.0, f"Se esperaba límite $250.0, se obtuvo {judge.max_daily_loss_usd}"
    logger_shadow = ShadowLogger()

    # 2. Escenario A: Filtro 1 (Regla Monetaria Mecánica)
    print("\n" + "-" * 72)
    print("[PASO 3 - ESCENARIO A] Prueba de Filtro 1 (Límite de pérdida diaria $250 alcanzado)")
    decision_risk = judge.evaluate_signal(
        signal=simulated_signal,
        headlines=headlines if headlines else ["QQQ rallies on tech earnings"],
        current_daily_pnl=-260.0,  # Supera el límite de -$250.00
    )
    print(f"   -> Resultado Filtro 1: {decision_risk}")
    assert decision_risk["allow_trade"] is False
    assert decision_risk["step_triggered"] == "STEP_1_RISK_GUARD"

    row_id_a = logger_shadow.log_decision(
        signal=simulated_signal,
        decision=decision_risk,
        send_telegram=send_telegram,
    )
    print(f"   -> Registrado en agent_audit.db con ID={row_id_a}")

    # 3. Escenario B: Evaluación con configuración actual de .env y titulares reales
    print("\n" + "-" * 72)
    print("[PASO 3 - ESCENARIO B] Evaluación en vivo de 'US.QQQ' (PnL diario = +$120.00)")
    test_headlines = (
        headlines
        if headlines
        else ["Nasdaq 100 ETF QQQ holds steady ahead of market open"]
    )
    decision_live = judge.evaluate_signal(
        signal=simulated_signal,
        headlines=test_headlines,
        current_daily_pnl=120.0,
    )
    print(f"   -> Proveedor IA detectado en .env: {judge.provider or 'NINGUNO (Modo Fail-Safe)'}")
    print(f"   -> Resultado Evaluación: {decision_live}")
    assert "allow_trade" in decision_live
    assert "step_triggered" in decision_live
    assert "reason" in decision_live

    row_id_b = logger_shadow.log_decision(
        signal=simulated_signal,
        decision=decision_live,
        send_telegram=send_telegram,
    )
    print(f"   -> Registrado en agent_audit.db con ID={row_id_b}")

    # 4. Escenario C: Verificación determinista de Filtro 2 (DOUBT) -> Filtro 3 (STEP_3_DEEP_AI)
    print("\n" + "-" * 72)
    print("[PASO 3 - ESCENARIO C] Prueba de escalado Filtro 2 (DOUBT) -> Filtro 3 (Segunda Opinión)")

    def _mock_llm(prompt: str, system_instruction: str, tier: str = "fast") -> dict:
        if tier == "fast":
            return {
                "verdict": "DOUBT",
                "reason": "Titulares mixtos entre datos de inflación y ganancias de chips IA.",
            }
        return {
            "bullish_count": 6,
            "bearish_count": 3,
            "verdict": "ALLOW",
            "reason": "Predominio de titulares alcistas en semiconductores compensa cautela macro.",
        }

    with patch.object(judge, "_call_llm", side_effect=_mock_llm):
        decision_deep = judge.evaluate_signal(
            signal=simulated_signal,
            headlines=test_headlines,
            current_daily_pnl=120.0,
        )
    print(f"   -> Resultado Filtro 3: {decision_deep}")
    assert decision_deep["allow_trade"] is True
    assert decision_deep["step_triggered"] == "STEP_3_DEEP_AI"

    row_id_c = logger_shadow.log_decision(
        signal=simulated_signal,
        decision=decision_deep,
        send_telegram=send_telegram,
    )
    print(f"   -> Registrado en agent_audit.db con ID={row_id_c}")

    # 5. Verificación de registros en SQLite (agent_audit.db)
    print("\n" + "-" * 72)
    print(f"[PASO 4] Verificando base de datos SQLite: {logger_shadow.db_path}")
    with sqlite3.connect(logger_shadow.db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, timestamp, strategy, symbol, direction,
                   entry_price, stop_loss, take_profit,
                   approved, step_triggered, reason
            FROM agent_audit_log
            ORDER BY id DESC
            LIMIT 3
            """
        ).fetchall()

    for r in rows:
        print(
            f"   [SQLite Row #{r[0]}] {r[1]} | {r[2]} | {r[3]} {r[4]} | "
            f"Entry={r[5]} SL={r[6]} TP={r[7]} | Approved={r[8]} | "
            f"Step={r[9]} | Reason={r[10]}"
        )

    print("\n" + "=" * 72)
    print("✅ DRY-RUN COMPLETADO CON ÉXITO — CERO ÓRDENES ENVIADAS A MOOMOO")
    print("=" * 72)


if __name__ == "__main__":
    send_tg = "--telegram" in sys.argv or os.getenv("TEST_SEND_TELEGRAM", "0") == "1"
    run_dry_run_test(send_telegram=send_tg)
