"""
ai_trading_agent.strategy_lab.discovery.quantitative_hardening
==============================================================
Módulo de Refuerzo Cuantitativo (Quantitative Hardening) — FASE 4.6.
Rediseño del Modelo de Evaluación Cuantitativa:
- Economic Edge Score (0 - 100) y Clasificación (NO_EDGE, WEAK_EDGE, POSITIVE_EDGE)
- Pure Robustness Score (0 - 100)
- Strategy Quality Score Compuesto (0 - 100)
- OOS Stability Score (Magnitud Absoluta + Retención Relativa)
- Protecciones estables contra Baseline PnL <= 0 en Slippage Resilience
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


class EconomicEdgeClassification(str, Enum):
    NO_EDGE = "NO_EDGE"         # PF <= 1.00
    WEAK_EDGE = "WEAK_EDGE"     # PF entre 1.00 y 1.10 o OOS Sharpe <= 0
    POSITIVE_EDGE = "POSITIVE_EDGE" # PF > 1.10 y OOS Sharpe > 0


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


def calculate_economic_edge_score(
    profit_factor: float,
    expectancy: float,
    is_sharpe: float,
    oos_sharpe: float,
    trade_count: int
) -> Tuple[float, EconomicEdgeClassification]:
    """
    Calcula el Economic Edge Score (0 a 100) y su clasificación formal.
    Reglas estrictas:
    - Si trade_count == 0 o profit_factor <= 1.00 o valores inválidos (NaN/Inf): NO_EDGE (0.0 pts)
    - Si profit_factor entre 1.00 y 1.10 o OOS Sharpe <= 0 o Expectancy <= 0: WEAK_EDGE (Score capado entre 5.0 y 25.0 pts)
    - Si profit_factor > 1.10 y OOS Sharpe > 0 y Expectancy > 0: POSITIVE_EDGE
    """
    import math
    if (
        trade_count <= 0 or 
        math.isnan(profit_factor) or 
        math.isinf(profit_factor) or 
        profit_factor <= 1.00
    ):
        return 0.0, EconomicEdgeClassification.NO_EDGE

    if math.isnan(expectancy) or math.isinf(expectancy):
        expectancy = 0.0
    if math.isnan(oos_sharpe) or math.isinf(oos_sharpe):
        oos_sharpe = 0.0

    if profit_factor <= 1.10 or oos_sharpe <= 0.0 or expectancy <= 0.0:
        # Ventaja débil
        pf_excess = max(0.0, profit_factor - 1.0)
        score = min(25.0, 5.0 + (pf_excess / 0.10) * 20.0)
        return round(score, 2), EconomicEdgeClassification.WEAK_EDGE

    # Ventaja positiva confirmada (Monótona, base 25.0 tras superar WEAK_EDGE)
    base_score = 25.0
    pf_component = min(30.0, (profit_factor - 1.10) * 30.0)
    sharpe_component = min(25.0, max(0.0, oos_sharpe) * 15.0)
    exp_component = min(20.0, max(0.0, expectancy) * 10.0)

    total_score = min(100.0, base_score + pf_component + sharpe_component + exp_component)
    return round(total_score, 2), EconomicEdgeClassification.POSITIVE_EDGE


def calculate_oos_stability_score(
    is_sharpe: float,
    oos_sharpe: float,
    is_pnl: float = 1.0,
    oos_pnl: float = 1.0
) -> float:
    """
    Calcula el OOS Stability Score (0 a 100) combinando retención relativa y magnitud absoluta.
    Penaliza explícitamente OOS Sharpe negativo, PnL negativo, o valores NaN/Inf.
    """
    import math
    if (
        math.isnan(oos_sharpe) or 
        math.isinf(oos_sharpe) or 
        oos_sharpe <= 0.0 or 
        math.isnan(oos_pnl) or 
        math.isinf(oos_pnl) or 
        oos_pnl <= 0.0
    ):
        return 0.0

    if math.isnan(is_sharpe) or math.isinf(is_sharpe) or is_sharpe <= 0.0:
        retention = 0.0
    else:
        retention = min(1.0, oos_sharpe / max(0.1, is_sharpe))

    # Factor de magnitud absoluta (premia Sharpe OOS altos como 1.5+ sobre 0.10)
    abs_magnitude_factor = min(1.0, max(0.0, oos_sharpe) / 1.5)

    composite = (retention * 0.50 + abs_magnitude_factor * 0.50) * 100.0
    return round(min(100.0, max(0.0, composite)), 2)


def calculate_slippage_resilience_score(
    baseline_pnl: float,
    high_stress_pnl: float
) -> float:
    """
    Calcula la resiliencia a slippage (0 a 100) protegida contra Baseline PnL <= 0 o cerca de 0 y NaN/Inf.
    """
    import math
    if (
        math.isnan(baseline_pnl) or 
        math.isinf(baseline_pnl) or 
        baseline_pnl <= 0.0 or 
        math.isnan(high_stress_pnl) or 
        math.isinf(high_stress_pnl)
    ):
        return 0.0

    retention = max(0.0, high_stress_pnl / baseline_pnl)
    score = min(100.0, retention * 100.0)
    return round(score, 2)


def calculate_strategy_quality_score(
    economic_edge_score: float,
    robustness_score: float,
    trade_count: int,
    is_sharpe: float,
    oos_sharpe: float,
    is_pnl: float,
    oos_pnl: float,
    baseline_pnl: float,
    high_stress_pnl: float,
    overfit_risk: float = 0.0,
    complexity_penalty: float = 0.0
) -> float:
    """
    Calcula el Strategy Quality Score compuesto (0 a 100).
    Ponderaciones iniciales de investigación:
    - Economic Edge: 30%
    - Robustness: 30%
    - Evidence Quality: 15%
    - OOS Stability: 10%
    - Slippage Resilience: 10%
    - Simplicidad: 5% (100 - overfit_risk)
    Penaliza drásticamente baja actividad / 0 trades.
    """
    import math
    if trade_count <= 0:
        return 0.0

    if math.isnan(economic_edge_score) or math.isinf(economic_edge_score):
        economic_edge_score = 0.0
    else:
        economic_edge_score = min(100.0, max(0.0, economic_edge_score))

    if math.isnan(robustness_score) or math.isinf(robustness_score):
        robustness_score = 0.0
    else:
        robustness_score = min(100.0, max(0.0, robustness_score))

    evidence_level = classify_statistical_evidence(trade_count)
    evidence_scores = {
        StatisticalEvidenceLevel.NO_DATA: 0.0,
        StatisticalEvidenceLevel.LOW_SAMPLE: 20.0,
        StatisticalEvidenceLevel.PRELIMINARY: 50.0,
        StatisticalEvidenceLevel.MODERATE_EVIDENCE: 80.0,
        StatisticalEvidenceLevel.STRONG_EVIDENCE: 100.0
    }
    evidence_score = evidence_scores.get(evidence_level, 0.0)

    oos_stability = calculate_oos_stability_score(is_sharpe, oos_sharpe, is_pnl, oos_pnl)
    slippage_resilience = calculate_slippage_resilience_score(baseline_pnl, high_stress_pnl)
    
    simplicity_penalty = (0.0 if math.isnan(overfit_risk) else overfit_risk) + (0.0 if math.isnan(complexity_penalty) else complexity_penalty)
    simplicity_score = min(100.0, max(0.0, 100.0 - simplicity_penalty))

    weighted = (
        (economic_edge_score * 0.30) +
        (robustness_score * 0.30) +
        (evidence_score * 0.15) +
        (oos_stability * 0.10) +
        (slippage_resilience * 0.10) +
        (simplicity_score * 0.05)
    )

    # Penalización por baja muestra de trades (SamplePenalty)
    # Si trade_count < 8: penalización lineal trade_count / 8.0.
    # Si trade_count >= 8: sample_penalty = 1.0 (sin penalización).
    if trade_count < 8:
        sample_penalty = trade_count / 8.0
        weighted *= sample_penalty

    return round(min(100.0, max(0.0, weighted)), 2)


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
                "baseline": {"net_pnl": 0.0, "trades": 0},
                "normal_stress": {"net_pnl": 0.0, "trades": 0},
                "high_stress": {"net_pnl": 0.0, "trades": 0},
                "degradation_pct": 0.0,
                "slippage_resilience_score": 0.0,
                "status": "NO_DATA"
            }

        total_pnl = sum(t.get("net_pnl", 0.0) for t in trades)
        normal_stress_pnl = total_pnl * 0.85
        high_stress_pnl = total_pnl * 0.60

        degradation = round((1.0 - (high_stress_pnl / total_pnl)) * 100.0, 2) if total_pnl > 0 else 0.0
        resilience = calculate_slippage_resilience_score(total_pnl, high_stress_pnl)

        return {
            "baseline": {"net_pnl": round(total_pnl, 2), "slippage_ticks": baseline_slippage_ticks},
            "normal_stress": {"net_pnl": round(normal_stress_pnl, 2), "slippage_ticks": 2.0},
            "high_stress": {"net_pnl": round(high_stress_pnl, 2), "slippage_ticks": 4.0},
            "degradation_pct": degradation,
            "slippage_resilience_score": resilience,
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


def calculate_generalization_stability_score(
    window_pfs: List[float],
    window_expectancies: List[float],
    window_sharpes: List[float],
    window_trades: List[int]
) -> float:
    """
    Calcula el Generalization Stability Score (GSS, 0 a 100) — FASE 9.
    Métrica diagnóstica exclusiva para research prioritization. No modifica el SQS oficial.
    Evalúa:
    1. Consistencia del Profit Factor entre ventanas (40 pts)
    2. Consistencia de la Expectancy (25 pts)
    3. Consistencia del Sharpe Ratio (20 pts)
    4. Suficiencia de operaciones en todas las ventanas (15 pts)
    Penaliza colapsos severos en cualquier ventana (ej. PF < 0.80).
    """
    import numpy as np
    import math

    if not window_pfs or len(window_pfs) < 2:
        return 0.0

    valid_pfs = [p for p in window_pfs if not math.isnan(p) and not math.isinf(p)]
    if len(valid_pfs) < len(window_pfs):
        return 0.0

    # 1. Consistencia de PF (40 pts)
    min_pf = min(valid_pfs)
    mean_pf = float(np.mean(valid_pfs))
    std_pf = float(np.std(valid_pfs))

    if min_pf <= 0.0:
        pf_pts = 0.0
    elif min_pf >= 1.05 and std_pf <= 0.20:
        pf_pts = 40.0
    elif min_pf >= 1.00:
        pf_pts = max(10.0, 40.0 - (std_pf * 50.0))
    elif min_pf >= 0.85:
        pf_pts = max(5.0, 20.0 - (std_pf * 30.0))
    else:
        pf_pts = 0.0  # Colapso en alguna ventana

    # 2. Consistencia de Expectancy (25 pts)
    valid_exps = [e for e in window_expectancies if not math.isnan(e) and not math.isinf(e)]
    positive_exp_count = sum(1 for e in valid_exps if e > 0)
    exp_ratio = positive_exp_count / max(1, len(valid_exps))
    exp_pts = exp_ratio * 25.0

    # 3. Consistencia de Sharpe (20 pts)
    valid_sharpes = [s for s in window_sharpes if not math.isnan(s) and not math.isinf(s)]
    positive_sharpe_count = sum(1 for s in valid_sharpes if s > 0)
    sharpe_ratio = positive_sharpe_count / max(1, len(valid_sharpes))
    sharpe_pts = sharpe_ratio * 20.0

    # 4. Suficiencia de Trades (15 pts)
    min_trades = min(window_trades) if window_trades else 0
    if min_trades >= 30:
        trade_pts = 15.0
    elif min_trades >= 15:
        trade_pts = 10.0
    elif min_trades >= 8:
        trade_pts = 5.0
    else:
        trade_pts = 0.0

    total_gss = min(100.0, max(0.0, pf_pts + exp_pts + sharpe_pts + trade_pts))
    return round(total_gss, 2)

