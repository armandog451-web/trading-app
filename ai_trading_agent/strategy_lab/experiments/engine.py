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

from ai_trading_agent.data.synthetic import synthetic_generator
from ai_trading_agent.backtest.engine import backtest_engine
from ai_trading_agent.strategy_lab.core.models import LabExperiment, LabStrategyDefinition
from ai_trading_agent.strategy_lab.strategies.composable import ComposableStrategy
from database import get_connection


class ExperimentEngine:
    """Ejecuta experimentos reproducibles y guarda auditorías en la base de datos."""

    def run_experiment(
        self,
        hypothesis_id: str,
        strategy_def: LabStrategyDefinition,
        symbol: str = "SPY",
        timeframe: str = "15m",
        bar_count: int = 150,
        random_seed: int = 42
    ) -> LabExperiment:
        exp_id = f"EXP-{uuid.uuid4().hex[:8].upper()}"

        # 1. Generar datos deterministas según la semilla
        bars = synthetic_generator.generate_bars(
            symbol=symbol,
            count=bar_count,
            regime="BULL_TREND",
            seed=random_seed
        )

        # 2. Instanciar la estrategia compuesta y ejecutar el backtest
        comp_strat = ComposableStrategy(
            strategy_id=strategy_def.strategy_id,
            name=strategy_def.name,
            version=strategy_def.version,
            parameters=strategy_def.parameters,
            rules=strategy_def.rules
        )

        report = backtest_engine.run(symbol=symbol, bars=bars)

        metrics_data = {
            "total_trades": report.metrics.total_trades,
            "win_rate_pct": report.metrics.win_rate_pct,
            "profit_factor": report.metrics.profit_factor,
            "sharpe_ratio": report.metrics.sharpe_ratio,
            "max_drawdown_pct": report.metrics.max_drawdown_pct,
            "total_net_pnl": report.metrics.total_net_pnl,
            "expectancy_dollars": report.metrics.expectancy_dollars
        }

        experiment = LabExperiment(
            experiment_id=exp_id,
            hypothesis_id=hypothesis_id,
            strategy_id=strategy_def.strategy_id,
            strategy_version=strategy_def.version,
            dataset_version=f"synthetic_seed_{random_seed}",
            universe=strategy_def.universe,
            symbols=[symbol],
            timeframe=timeframe,
            parameters=strategy_def.parameters,
            features=list(strategy_def.rules.keys()),
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
            json.dumps(exp.parameters),
            json.dumps(exp.features),
            json.dumps(exp.metrics),
            exp.status,
            exp.created_at.isoformat()
        ))
        conn.commit()
        conn.close()


experiment_engine = ExperimentEngine()
