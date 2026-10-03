"""
ai_trading_agent.scanner.report_formatter
=========================================
Formateador institucional de reportes de fin de semana en Markdown estructurado
cumpliendo las 12 secciones requeridas por el Master Project Plan (Instrucción 8).
"""

from typing import Dict, Any


def format_report_to_markdown(report: Dict[str, Any]) -> str:
    """Genera un documento Markdown completo de 12 secciones a partir del reporte del escáner."""
    lines = []
    lines.append(f"# AI TRADING AGENT 1.0 — REPORTE DE FIN DE SEMANA ({report.get('execution_day', 'SCAN')})")
    lines.append(f"**ID de Auditoría:** `{report.get('scan_id')}`  ")
    lines.append(f"**Fecha de Análisis:** `{report.get('timestamp')}`  ")
    lines.append(f"**Datos vigentes al:** `{report.get('data_as_of_date')}`  ")
    lines.append(f"**Estado Parcial:** `{'SÍ' if report.get('is_partial') else 'NO'}`\n")
    lines.append("---\n")

    # 1. Resumen general del mercado
    lines.append("## 1. Resumen General del Mercado")
    lines.append(report.get("market_overview", "Sin datos.") + "\n")

    # 2. Régimen observado en SPY, QQQ e IWM
    lines.append("## 2. Régimen Observado en SPY, QQQ e IWM")
    benchmarks = report.get("indices_regimes") or report.get("benchmark_regimes", {})
    if benchmarks:
        lines.append("| Benchmark | Régimen Observado |")
        lines.append("| :--- | :--- |")
        for sym, b_data in benchmarks.items():
            reg_val = b_data if isinstance(b_data, str) else b_data.get('regime', 'N/A')
            lines.append(f"| **{sym}** | {reg_val} |")
    else:
        lines.append("No se registraron regímenes de referencia.")
    lines.append("")

    # 3. Principales cambios de tendencia y volatilidad
    lines.append("## 3. Principales Cambios de Tendencia y Volatilidad")
    trend_changes = report.get("trend_and_volatility_shifts") or report.get("trend_volatility_changes", [])
    if trend_changes:
        for tc in trend_changes:
            lines.append(f"- {tc}")
    else:
        lines.append("Sin anomalías de volatilidad detectadas.")
    lines.append("")

    # 4. Lista de activos detectados
    lines.append("## 4. Lista de Activos Detectados y Categorizados")
    candidates = report.get("candidates", [])
    if candidates:
        lines.append("| Símbolo | Condición Principal | Régimen | Último Cierre | S / P / R | RS vs SPY |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for c in candidates:
            price = c.get('last_historical_price', c.get('last_price', 0))
            regime = c.get('market_regime', c.get('regime', 'N/A'))
            s = c.get('key_support', c.get('support_level', 0))
            p = c.get('pivot_point', c.get('pivot_level', 0))
            r = c.get('key_resistance', c.get('resistance_level', 0))
            rs = c.get('relative_strength_vs_spy', c.get('relative_strength_spy', 1.0))
            lines.append(
                f"| **{c.get('symbol')}** | `{c.get('primary_condition')}` | {regime} | "
                f"${price:.2f} | S:${s:.2f} P:${p:.2f} R:${r:.2f} | {rs:.2f}x |"
            )
    else:
        lines.append("No se detectaron candidatos en este ciclo.")
    lines.append("")

    # 5. Candidatos a ruptura
    lines.append("## 5. Candidatos a Ruptura (Breakout Watch)")
    breakouts = report.get("breakout_candidates", [])
    if breakouts:
        for b in breakouts:
            lines.append(f"- **{b}**")
    else:
        lines.append("Ninguno.")
    lines.append("")

    # 6. Candidatos de momentum
    lines.append("## 6. Candidatos de Momentum (Momentum Watch)")
    momentum = report.get("momentum_candidates", [])
    if momentum:
        for m in momentum:
            lines.append(f"- **{m}**")
    else:
        lines.append("Ninguno.")
    lines.append("")

    # 7. Candidatos de mean reversion
    lines.append("## 7. Candidatos de Mean Reversion")
    mr = report.get("mean_reversion_candidates", [])
    if mr:
        for m in mr:
            lines.append(f"- **{m}**")
    else:
        lines.append("Ninguno.")
    lines.append("")

    # 8. Eventos económicos y resultados próximos
    lines.append("## 8. Eventos Económicos y Resultados Próximos")
    events = report.get("economic_and_earnings_events") or report.get("upcoming_events", [])
    if events:
        for ev in events:
            lines.append(f"- {ev}")
    else:
        lines.append("Sin eventos de alto impacto reportados.")
    lines.append("")

    # 9. Riesgos y condiciones de no operar
    lines.append("## 9. Riesgos y Condiciones de No Operar")
    risks = report.get("no_trade_risks", [])
    if risks:
        for r in risks:
            lines.append(f"- ⚠️ {r}")
    else:
        lines.append("No se activaron bloqueos de riesgo de no operar.")
    lines.append("")

    # 10. Escenarios para la próxima sesión
    lines.append("## 10. Escenarios para la Próxima Sesión")
    if candidates:
        for c in candidates:
            price = c.get('last_historical_price', c.get('last_price', 0))
            s = c.get('key_support', c.get('support_level', 0))
            p = c.get('pivot_point', c.get('pivot_level', 0))
            r = c.get('key_resistance', c.get('resistance_level', 0))
            lines.append(f"### Símbolo: {c.get('symbol')} (${price:.2f})")
            lines.append(f"- **Niveles Clave:** Soporte: `${s:.2f}` | Pivot: `${p:.2f}` | Resistencia: `${r:.2f}`")
            lines.append(f"- **Estrategias Aplicables:** {', '.join(c.get('applicable_strategies', []))}")
            
            bull = c.get("bullish_scenario")
            if bull:
                trig = bull.get('trigger_level', bull.get('trigger_price', 0))
                inval = bull.get('invalidation_level', 0)
                desc = bull.get('rationale', bull.get('description', ''))
                conf = bull.get('required_confirmation', ', '.join(bull.get('confirmations_needed', [])))
                lines.append(f"  - **🟢 Escenario Alcista:** {desc}")
                lines.append(f"    - *Gatillo:* `${trig:.2f}` | *Invalidación:* `${inval:.2f}`")
                lines.append(f"    - *Confirmaciones requeridas:* {conf}")
                lines.append(f"    - *Condición de invalidación:* {bull.get('invalidation_condition')}")

            bear = c.get("bearish_scenario")
            if bear:
                trig = bear.get('trigger_level', bear.get('trigger_price', 0))
                inval = bear.get('invalidation_level', 0)
                desc = bear.get('rationale', bear.get('description', ''))
                conf = bear.get('required_confirmation', ', '.join(bear.get('confirmations_needed', [])))
                lines.append(f"  - **🔴 Escenario Bajista:** {desc}")
                lines.append(f"    - *Gatillo:* `${trig:.2f}` | *Invalidación:* `${inval:.2f}`")
                lines.append(f"    - *Confirmaciones requeridas:* {conf}")
                lines.append(f"    - *Condición de invalidación:* {bear.get('invalidation_condition')}")

            opt = c.get("options_candidate_contract")
            if opt:
                lines.append(f"  - **📋 Candidato de Opción (< $200 USD):** `{opt.get('contract_type')}` Strike ${opt.get('strike', 0):.2f} (Venc: {opt.get('expiry')}) — Est: ${opt.get('estimated_premium', 0):.2f}/acc (${opt.get('total_contract_cost', 0):.2f} total)")
            lines.append("")
            lines.append("")
    else:
        lines.append("Sin candidatos detallados.")
    lines.append("")

    # 11. Datos faltantes y limitaciones
    lines.append("## 11. Datos Faltantes y Limitaciones")
    missing = report.get("missing_data_limitations", [])
    if missing:
        for m in missing:
            lines.append(f"- {m}")
    else:
        lines.append("Todos los datos requeridos fueron verificados satisfactoriamente.")
    lines.append("")

    # 12. Estado del sistema
    lines.append("## 12. Estado del Sistema y Modos Operativos")
    lines.append(f"- **Modo Operativo:** `{report.get('system_status', 'ANALYSIS_ONLY')}`")
    lines.append("- **Regla de Ejecución:** ANÁLISIS EXCLUSIVAMENTE. Cero órdenes automáticas.")
    lines.append(f"- **Versión de Estrategia:** `{report.get('strategy_version', 'v1.0.0')}`\n")
    lines.append("---\n*Generado automáticamente por AI Trading Agent 1.0 — Módulo Weekend Market Scanner*")

    return "\n".join(lines)
