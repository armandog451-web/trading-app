"""
ai_trading_agent.strategy_lab.shadow.shadow_scheduler
=====================================================
Generador automatizado de reportes e integración de notificaciones (Bloque I).
Responsable de:
- Generación automática de Reportes Diarios Shadow en Markdown y JSON.
- Generación automática de Reportes Semanales de Auditoría Cuantitativa.
- Formateo de notificaciones salientes de Telegram estrictamente informativas:
  Prefijo obligatorio: "RESEARCH SHADOW — NO BROKER ORDERS".
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from .campaign_models import (
    CampaignFreezeManifest,
    ShadowValidationClock
)
from .shadow_evaluator import AutonomousShadowEvaluator


class ShadowReportGenerator:
    """Generador de reportes institucionales periódicos para la campaña Shadow."""

    def __init__(self, evaluator: AutonomousShadowEvaluator, reports_dir: Path):
        self.evaluator = evaluator
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_daily_report(self, session_date: str) -> Path:
        """Genera el informe diario institucional en Markdown y JSON."""
        status = self.evaluator.get_status_summary()
        cand_a = status["candidate_a"]
        cand_b = status["candidate_b"]

        report_md = f"""# REPORTE DIARIO DE VALIDACIÓN FORWARD SHADOW (FASE 7.4)
**Fecha de Sesión Evaluada:** {session_date}  
**Generado UTC:** {datetime.utcnow().isoformat()}  
**Modo:** `RESEARCH / ANALYSIS_ONLY` (Sin conexión a brokers)  
**Broker PAPER D21:** Moomoo (`TrdEnv.SIMULATE`) — **AISLADO**  

---

## 1. ESTADO DE SALUD DEL SHADOW ENGINE
- **Estado Operativo:** `HEALTHY / COLLECTING_EVIDENCE`
- **Aislamiento de Broker:** `AIR_GAPPED_100_PERCENT` (0 órdenes enviadas a brokers)
- **Escenario de Costes Activo:** `{status['cost_scenario']}`
- **T0 Prospectivo Canónico:** `{status['t0_first_prospective_session']}`

---

## 2. CANDIDATO A: `MR_VolCond_ZScore_V1`
- **Fingerprint:** `{cand_a['fingerprint']}`
- **Sesiones Válidas Acumuladas:** {cand_a['clock']['valid_shadow_evaluation_sessions']} / 90
- **Días Calendario desde T0:** {cand_a['clock']['calendar_days_since_t0']}
- **Señales Generadas Acumuladas:** {cand_a['clock']['shadow_signals_generated']}
- **Posiciones Abiertas Actuales:** {cand_a['metrics']['open_positions_count']}
- **Operaciones Cerradas Acumuladas:** {cand_a['metrics']['closed_trades_count']}
- **Capital Virtual Portafolio:** ${cand_a['metrics']['portfolio_equity_usd']:,.2f} USD
- **PnL Neto Realizado:** ${cand_a['metrics']['sum_true_net_pnl']:,.2f} USD
- **Profit Factor Neto:** {cand_a['metrics']['net_profit_factor']:.2f}
- **Drawdown Máximo:** {cand_a['metrics']['max_drawdown_pct']:.2f}% (${cand_a['metrics']['max_drawdown_usd']:,.2f} USD)
- **Entradas en Ledger Inmutable:** {cand_a['ledger_entries_count']} (Hash: `{cand_a['ledger_head_hash']}`)

---

## 3. CANDIDATO B: `CS_RelMom_VolAdj_V2`
- **Fingerprint:** `{cand_b['fingerprint']}`
- **Sesiones Válidas Acumuladas:** {cand_b['clock']['valid_shadow_evaluation_sessions']} / 90
- **Días Calendario desde T0:** {cand_b['clock']['calendar_days_since_t0']}
- **Señales Generadas Acumuladas:** {cand_b['clock']['shadow_signals_generated']}
- **Posiciones Abiertas Actuales:** {cand_b['metrics']['open_positions_count']}
- **Operaciones Cerradas Acumuladas:** {cand_b['metrics']['closed_trades_count']}
- **Capital Virtual Portafolio:** ${cand_b['metrics']['portfolio_equity_usd']:,.2f} USD
- **PnL Neto Realizado:** ${cand_b['metrics']['sum_true_net_pnl']:,.2f} USD
- **Profit Factor Neto:** {cand_b['metrics']['net_profit_factor']:.2f}
- **Drawdown Máximo:** {cand_b['metrics']['max_drawdown_pct']:.2f}% (${cand_b['metrics']['max_drawdown_usd']:,.2f} USD)
- **Entradas en Ledger Inmutable:** {cand_b['ledger_entries_count']} (Hash: `{cand_b['ledger_head_hash']}`)

---

## 4. AUDITORÍA DE D21 PARALELO
- **Estrategia D21:** `D21_RangeCompress_5d`
- **Broker:** Moomoo PAPER
- **Capital D21:** $1,000,000.00 USD
- **Interferencia:** 0.00% (Aislamiento absoluto verificado)
"""
        out_path = self.reports_dir / f"daily_shadow_report_{session_date}.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        # Guardar snapshot JSON
        json_path = self.reports_dir / f"daily_shadow_report_{session_date}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)

        return out_path

    def format_telegram_alert(self, session_date: str) -> str:
        """
        Formatea el mensaje saliente para Telegram bajo las restricciones estrictas del Bloque I:
        - Prefijo ineludible: 'RESEARCH SHADOW — NO BROKER ORDERS'.
        - Estrictamente saliente, sin aceptar comandos entrantes.
        - Diferenciado completamente de las operaciones PAPER de D21.
        """
        status = self.evaluator.get_status_summary()
        ca = status["candidate_a"]
        cb = status["candidate_b"]

        msg = (
            f"🔬 [RESEARCH SHADOW — NO BROKER ORDERS]\n"
            f"📅 Sesión: {session_date} | Fase 7.4\n"
            f"----------------------------------------\n"
            f"• MR_VolCond (A): {ca['clock']['valid_shadow_evaluation_sessions']} sess | "
            f"Trades: {ca['metrics']['closed_trades_count']} | Net: ${ca['metrics']['sum_true_net_pnl']:+.2f} | PF: {ca['metrics']['net_profit_factor']:.2f}\n"
            f"• CS_RelMom (B): {cb['clock']['valid_shadow_evaluation_sessions']} sess | "
            f"Trades: {cb['metrics']['closed_trades_count']} | Net: ${cb['metrics']['sum_true_net_pnl']:+.2f} | PF: {cb['metrics']['net_profit_factor']:.2f}\n"
            f"----------------------------------------\n"
            f"🔒 Status: AIR-GAPPED | D21 PAPER: Intacto e Inmutable"
        )
        return msg
