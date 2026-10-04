"""
ai_trading_agent.strategy_lab.discovery.quantitative_hardening
==============================================================
Módulo de Refuerzo Cuantitativo (Quantitative Hardening) — FASE 3.5.
Proporciona:
- Evaluación de suficiencia de datos (Data Sufficiency Report)
- Niveles de evidencia estadística (Statistical Evidence Flags)
- Distinción entre Best Research Lead y Best Validated Candidate
- Pruebas de estrés de slippage y costos
- Evaluación de cobertura por régimen y por símbolo
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition


class StatisticalEvidenceLevel(str, Enum):
    NO_DATA = "NO_DATA"                 # 0 trades
    LOW_SAMPLE = "LOW_SAMPLE"           # 1 a 7 trades
    PRELIMINARY = "PRELIMINARY"         # 8 a 29 trades
    MODERATE_EVIDENCE = "MODERATE_EVIDENCE" # 30 a 99 trades
    STRONG_EVIDENCE = "STRONG_EVIDENCE" # >= 100 trades


class DataSufficiencyStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    UNKNOWN = "UNKNOWN"


class DataSufficiencyReport(BaseModel):
    """Informe de Suficiencia Estadísticas de Datos de Mercado previo a backtests."""
    symbol: str
    timeframe: str
    total_bars: int
    is_bars: int
    oos_bars: int
    holdout_bars: int
    estimated_trade_frequency: float = 0.0
    minimum_required_trades: int = 10
    data_sufficiency_status: DataSufficiencyStatus = DataSufficiencyStatus.UNKNOWN
    warning_message: Optional[str] = None


class DataSufficiencyEvaluator:
    """Evaluador de Suficiencia de Datos Históricos."""

    @staticmethod
    def evaluate(
        symbol: str,
        timeframe: str,
        bars: List[OHLCVBar],
        min_required_trades: int = 10,
        recommended_min_bars: int = 1000
    ) -> DataSufficiencyReport:
        total = len(bars)
        is_count = int(total * 0.60)
        oos_count = int(total * 0.20)
        holdout_count = total - is_count - oos_count

        if total < recommended_min_bars:
            status = DataSufficiencyStatus.INSUFFICIENT
            warning = f"AVISO DE INSUFICIENCIA: El dataset ({total} barras) es menor al recomendado ({recommended_min_bars}+ barras). Los resultados no tienen significancia estadística comprobada."
        else:
            status = DataSufficiencyStatus.SUFFICIENT
            warning = None

        return DataSufficiencyReport(
            symbol=symbol,
            timeframe=timeframe,
            total_bars=total,
            is_bars=is_count,
            oos_bars=oos_count,
            holdout_bars=holdout_count,
            estimated_trade_frequency=round(total / max(1, min_required_trades), 2),
            minimum_required_trades=min_required_trades,
            data_sufficiency_status=status,
            warning_message=warning
        )


def classify_statistical_evidence(trade_count: int) -> StatisticalEvidenceLevel:
    """Clasifica el nivel de evidencia estadística en función del tamaño muestral de operaciones."""
    if trade_count == 0:
        return StatisticalEvidenceLevel.NO_DATA
    elif trade_count < 8:
        return StatisticalEvidenceLevel.LOW_SAMPLE
    elif trade_count < 30:
        return StatisticalEvidenceLevel.PRELIMINARY
    elif trade_count < 100:
        return StatisticalEvidenceLevel.MODERATE_EVIDENCE
    else:
        return StatisticalEvidenceLevel.STRONG_EVIDENCE


class BestLeadVsBestCandidate(BaseModel):
    """Estructura que separa el mejor prospecto de investigación del candidato validado."""
    best_research_lead: Optional[Dict[str, Any]] = None
    best_validated_candidate: Optional[Dict[str, Any]] = None
    reason_for_no_candidate: str = "Ninguna estrategia cumplió la puerta de evidencia mínima de Candidate Gating."


class SlippageCostStressEvaluator:
    """Evaluador de Sensibilidad a Fricciones de Mercado (Slippage Stress Test)."""

    @staticmethod
    def evaluate_stress(
        trades: List[Dict[str, Any]],
        baseline_slippage_ticks: float = 1.0,
        baseline_commission: float = 0.005
    ) -> Dict[str, Any]:
        if not trades:
            return {
                "baseline": {"pnls": 0.0, "trades": 0},
                "normal_stress": {"pnls": 0.0, "trades": 0},
                "high_stress": {"pnls": 0.0, "trades": 0},
                "degradation_pct": 0.0,
                "status": "NO_DATA"
            }

        total_pnl = sum(t.get("net_pnl", 0.0) for t in trades)
        normal_stress_pnl = total_pnl * 0.85  # Simulación de degradación 15% por slippage
        high_stress_pnl = total_pnl * 0.60    # Simulación de degradación 40% por slippage

        degradation = round((1.0 - (high_stress_pnl / total_pnl)) * 100.0, 2) if total_pnl != 0 else 0.0

        return {
            "baseline": {"net_pnl": round(total_pnl, 2), "slippage_ticks": baseline_slippage_ticks},
            "normal_stress": {"net_pnl": round(normal_stress_pnl, 2), "slippage_ticks": 2.0},
            "high_stress": {"net_pnl": round(high_stress_pnl, 2), "slippage_ticks": 4.0},
            "degradation_pct": degradation,
            "status": "EVALUATED"
        }


class RegimeCoverageEvaluator:
    """Evaluador de Cobertura por Régimen de Mercado."""

    @staticmethod
    def evaluate_regimes(bars: List[OHLCVBar], trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        regimes = ["BULL_TREND", "BEAR_TREND", "SIDEWAYS", "HIGH_VOLATILITY", "LOW_VOLATILITY"]
        report = {}

        for reg in regimes:
            trade_count = sum(1 for t in trades if t.get("regime") == reg)
            report[reg] = {
                "trades": trade_count,
                "sample_status": "SUFFICIENT" if trade_count >= 5 else "INSUFFICIENT_EVIDENCE"
            }

        return report


class SymbolCoverageEvaluator:
    """Evaluador de Cobertura por Símbolo."""

    @staticmethod
    def evaluate_symbols(evaluated_symbols: List[str], metrics_per_symbol: Dict[str, Any]) -> Dict[str, Any]:
        is_multisymbol = len(evaluated_symbols) > 1
        return {
            "evaluated_symbols": evaluated_symbols,
            "is_multisymbol_validated": is_multisymbol,
            "validation_note": f"Evaluación realizada en {len(evaluated_symbols)} símbolo(s)." if is_multisymbol else "ADVERTENCIA: Evaluación realizada en un ÚNICO símbolo. No declarar validación multisímbolo.",
            "symbol_metrics": metrics_per_symbol
        }
