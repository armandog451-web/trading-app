"""
ai_trading_agent.strategy_lab.experiments.engine
=================================================
Motor de Experimentos Cuantitativos Reproducibles (Experiment Engine).
Ejecuta simulaciones por lotes, sweeps de parámetros y registra auditorías completas en SQLite.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import uuid

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.data.synthetic import synthetic_generator
from ai_trading_agent.backtest.engine import backtest_engine
from ai_trading_agent.strategy_lab.core.models import LabExperiment, LabStrategyDefinition
from ai_trading_agent.strategy_lab.strategies.composable import ComposableStrategy
from database import get_connection


class ExperimentEngine:
    """Ejecuta experimentos reproducibles y guarda auditorías en la base de datos."""

    def run_experiment(
        self,
        hypothesis_id: str = "HYP_DEFAULT",
        strategy_def: Optional[LabStrategyDefinition] = None,
        symbol: str = "SPY",
        timeframe: str = "15m",
        bar_count: int = 150,
        random_seed: int = 42,
        bars: Optional[List[OHLCVBar]] = None,
        strategy: Optional[ComposableStrategy] = None,
        parameters: Optional[Dict[str, Any]] = None,
        name: str = ""
    ) -> LabExperiment:
        exp_id = f"EXP-{uuid.uuid4().hex[:8].upper()}"

        # 1. Generar datos deterministas según la semilla
        eval_bars = bars if bars is not None else synthetic_generator.generate_bars(
            symbol=symbol,
            count=bar_count,
            regime="BULL_TREND",
            seed=random_seed
        )

        # 2. Instanciar la estrategia compuesta o usar la recibida
        if strategy is not None:
            comp_strat = strategy
            strat_id = strategy.strategy_id
            strat_version = strategy.version
            params = parameters or strategy.parameters
            universe = ["SPY", "QQQ"]
            features = list(strategy.rules.keys())
        elif strategy_def is not None:
            comp_strat = ComposableStrategy(
                strategy_id=strategy_def.strategy_id,
                name=strategy_def.name,
                version=strategy_def.version,
                parameters=strategy_def.parameters,
                rules=strategy_def.rules
            )
            strat_id = strategy_def.strategy_id
            strat_version = strategy_def.version
            params = strategy_def.parameters
            universe = strategy_def.universe
            features = list(strategy_def.rules.keys())
        else:
            raise ValueError("Se requiere strategy_def o strategy para ejecutar el experimento.")

        report = backtest_engine.run(symbol=symbol, bars=eval_bars, strategy=comp_strat)

        metrics_data = {
            "total_trades": report.metrics.total_trades,
            "win_rate_pct": report.metrics.win_rate_pct,
            "profit_factor": report.metrics.profit_factor,
            "sharpe_ratio": report.metrics.sharpe_ratio,
            "max_drawdown_pct": report.metrics.max_drawdown_pct,
            "total_net_pnl": report.metrics.total_net_pnl,
            "expectancy_dollars": report.metrics.expectancy_dollars,
            "trades": report.trades
        }

        experiment = LabExperiment(
            experiment_id=exp_id,
            hypothesis_id=hypothesis_id,
            strategy_id=strat_id,
            strategy_version=strat_version,
            dataset_version=f"synthetic_seed_{random_seed}",
            universe=universe,
            symbols=[symbol],
            timeframe=timeframe,
            parameters=params,
            features=features,
            metrics=metrics_data,
            status="COMPLETED",
            created_at=datetime.utcnow()
        )

        # 3. Persistir experimento en SQLite
        self._save_experiment_to_db(experiment)
        return experiment

    def _save_experiment_to_db(self, exp: LabExperiment):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lab_experiments
            (experiment_id, hypothesis_id, strategy_id, strategy_version, dataset_version, universe, symbols, timeframe, parameters_json, features_json, metrics_json, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(experiment_id) DO UPDATE SET
            metrics_json = excluded.metrics_json,
            status = excluded.status
        """, (
            exp.experiment_id,
            exp.hypothesis_id,
            exp.strategy_id,
            exp.strategy_version,
            exp.dataset_version,
            json.dumps(exp.universe),
            json.dumps(exp.symbols),
            exp.timeframe,
            json.dumps(exp.parameters, default=str),
            json.dumps(exp.features, default=str),
            json.dumps(exp.metrics, default=str),
            exp.status,
            exp.created_at.isoformat()
        ))
        conn.commit()
        conn.close()


experiment_engine = ExperimentEngine()
