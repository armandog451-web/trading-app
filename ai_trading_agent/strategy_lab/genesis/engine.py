"""
ai_trading_agent.strategy_lab.genesis.engine
=============================================
Strategy Genesis Engine & Hypothesis Engine.
Genera hipótesis cuantitativas y crea/muta estrategias de forma autónoma con trazabilidad de linaje.
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import uuid

from ai_trading_agent.domain.enums import MarketRegime
from ai_trading_agent.strategy_lab.core.models import (
    LabHypothesis, HypothesisStatus, LabStrategyDefinition, StrategyStatus, StrategyLineage, StrategyComplexityCalculator
)
from ai_trading_agent.strategy_lab.strategies.composable import ComposableStrategy


class HypothesisEngine:
    """Motor de Generación de Hipótesis Cuantitativas."""

    def generate_hypothesis(
        self,
        hypothesis_type: str = "ORB_VOLATILITY",
        generated_by: str = "AI_RESEARCH_AGENT"
    ) -> LabHypothesis:
        h_id = f"HYP-{uuid.uuid4().hex[:8].upper()}"

        if hypothesis_type == "ORB_VOLATILITY":
            return LabHypothesis(
                hypothesis_id=h_id,
                description="Opening Range Breakout (15m) produce mayor expectancia durante sesiones de alta volatilidad con RVOL > 1.5x.",
                generated_by=generated_by,
                timestamp=datetime.utcnow(),
                features_used=["RVOL", "ATR", "VWAP", "OPEN_RANGE_15M"],
                market_conditions=["HIGH_VOLATILITY", "BULL_TREND"],
                expected_behavior="Profit Factor > 1.8x con Win Rate > 55%",
                experiment_plan="Probar ORB 15m con filtro RVOL 1.5x en SPY y QQQ en timeframe 15m.",
                status=HypothesisStatus.NEW
            )
        elif hypothesis_type == "MEAN_REVERSION_SIDEWAYS":
            return LabHypothesis(
                hypothesis_id=h_id,
                description="Reversión a la media basada en bandas Bollinger + VWAP en rangos laterales (SIDEWAYS) reduce falsas rupturas.",
                generated_by=generated_by,
                timestamp=datetime.utcnow(),
                features_used=["RSI", "BOLLINGER_BANDS", "VWAP"],
                market_conditions=["SIDEWAYS", "LOW_VOLATILITY"],
                expected_behavior="Sharpe > 1.5 en mercados de rango lateral",
                experiment_plan="Simular rebote en bandas exteriores en SPY cuando RSI < 30 o RSI > 70 en régimen SIDEWAYS.",
                status=HypothesisStatus.NEW
            )
        else:
            return LabHypothesis(
                hypothesis_id=h_id,
                description="Cruce de tendencia EMA9/EMA21 con filtro de volumen confirma aceleración de tendencia alcista.",
                generated_by=generated_by,
                timestamp=datetime.utcnow(),
                features_used=["EMA_9", "EMA_21", "VWAP", "RVOL"],
                market_conditions=["BULL_TREND"],
                expected_behavior="Expectancia positiva > $150/trade en tendencias fuertes",
                experiment_plan="Backtest de Trend Following con R:R 2.0x.",
                status=HypothesisStatus.NEW
            )


class StrategyGenesisEngine:
    """Motor de Generación y Mutación Evolutiva de Estrategias."""

    def __init__(self):
        pass

    def create_seed_strategies(self) -> List[LabStrategyDefinition]:
        """Crea la librería semilla de estrategias iniciales."""
        now = datetime.utcnow()
        seeds = [
            LabStrategyDefinition(
                strategy_id="STR-MOM-SPY-v1.0",
                name="Intraday Momentum SPY",
                version="1.0",
                description="Momentum intradía basado en ema9/ema21, VWAP y filtro RVOL.",
                status=StrategyStatus.RESEARCH,
                universe=["SPY"],
                timeframes=["15m"],
                parameters={"min_rvol": 1.4, "atr_stop_mult": 1.5, "rr_target": 2.0, "min_rsi": 35.0, "max_rsi": 65.0},
                rules={"entry_conditions": ["ema9 > ema21", "close > vwap", "rvol >= 1.4"], "filters": ["BULL_TREND", "SIDEWAYS"]}
            ),
            LabStrategyDefinition(
                strategy_id="STR-ORB-QQQ-v1.0",
                name="Opening Range Breakout QQQ",
                version="1.0",
                description="Ruptura de rango de apertura de 15m con volumen expansivo.",
                status=StrategyStatus.RESEARCH,
                universe=["QQQ"],
                timeframes=["15m"],
                parameters={"min_rvol": 1.5, "atr_stop_mult": 1.2, "rr_target": 2.5, "min_rsi": 40.0, "max_rsi": 70.0},
                rules={"entry_conditions": ["breakout_15m", "rvol >= 1.5"], "filters": ["HIGH_VOLATILITY", "BULL_TREND"]}
            ),
            LabStrategyDefinition(
                strategy_id="STR-MR-AAPL-v1.0",
                name="Mean Reversion Bollinger AAPL",
                version="1.0",
                description="Reversión a la media desde bandas Bollinger en mercados laterales.",
                status=StrategyStatus.RESEARCH,
                universe=["AAPL"],
                timeframes=["15m"],
                parameters={"min_rvol": 1.1, "atr_stop_mult": 1.0, "rr_target": 1.5, "min_rsi": 25.0, "max_rsi": 75.0},
                rules={"entry_conditions": ["rsi_exhaustion", "bollinger_rejection"], "filters": ["SIDEWAYS"]}
            )
        ]
        return seeds

    def mutate_strategy(
        self,
        parent: LabStrategyDefinition,
        mutation_reason: str,
        experiment_id: str = "",
        failure_analysis: Optional[Any] = None
    ) -> Tuple[LabStrategyDefinition, StrategyLineage]:
        """Genera una variante hija mutando parámetros controladamente y registrando el linaje."""
        new_version_num = round(float(parent.version) + 0.1, 1)
        child_id = f"{parent.strategy_id.rsplit('-v', 1)[0]}-v{new_version_num}"

        # Mutación controlada de parámetros guiada por el diagnóstico de fallos si existe
        new_params = parent.parameters.copy()
        mutation_details = []

        if failure_analysis and hasattr(failure_analysis, "failure_type"):
            ftype = failure_analysis.failure_type
            if ftype == "EXCESSIVE_DRAWDOWN":
                new_params["atr_stop_mult"] = round(new_params.get("atr_stop_mult", 1.5) * 1.2, 2)
                mutation_details.append(f"atr_stop_mult={new_params['atr_stop_mult']} (+20% por Drawdown Excesivo)")
            elif ftype in ["INSUFFICIENT_PROFIT_FACTOR", "LOW_EXPECTANCY"]:
                new_params["rr_target"] = round(new_params.get("rr_target", 2.0) + 0.3, 1)
                mutation_details.append(f"rr_target={new_params['rr_target']} (+0.3 R:R por Expectancia Baja)")
            elif ftype == "HIGH_SLIPPAGE_SENSITIVITY":
                new_params["min_rvol"] = round(new_params.get("min_rvol", 1.2) * 1.15, 2)
                mutation_details.append(f"min_rvol={new_params['min_rvol']} (+15% RVOL por Fricción)")
            else:
                new_params["min_rvol"] = round(new_params.get("min_rvol", 1.2) * 1.1, 2)
                new_params["rr_target"] = round(new_params.get("rr_target", 2.0) + 0.2, 1)
                mutation_details.append("min_rvol +10%, rr_target +0.2")
        else:
            if "min_rvol" in new_params:
                new_params["min_rvol"] = round(new_params["min_rvol"] * 1.1, 2)
            if "rr_target" in new_params:
                new_params["rr_target"] = round(new_params["rr_target"] + 0.2, 1)
            mutation_details.append(f"min_rvol={new_params.get('min_rvol')}, rr_target={new_params.get('rr_target')}")

        mutation_desc = f"Mutación guiada: {', '.join(mutation_details)}"
        now = datetime.utcnow()
        child = LabStrategyDefinition(
            strategy_id=child_id,
            name=f"{parent.name} (Mutación v{new_version_num})",
            version=str(new_version_num),
            description=f"Variante mutada de {parent.strategy_id} por {mutation_reason}",
            parent_strategy_id=parent.strategy_id,
            created_by="AI_RESEARCH_AGENT",
            created_at=now,
            updated_at=now,
            status=StrategyStatus.RESEARCH,
            universe=parent.universe,
            timeframes=parent.timeframes,
            parameters=new_params,
            rules=parent.rules
        )

        lineage = StrategyLineage(
            parent_id=parent.strategy_id,
            child_id=child_id,
            mutation_description=mutation_desc,
            reason=mutation_reason,
            experiment_id=experiment_id,
            created_at=now
        )

        return child, lineage


hypothesis_engine = HypothesisEngine()
genesis_engine = StrategyGenesisEngine()
