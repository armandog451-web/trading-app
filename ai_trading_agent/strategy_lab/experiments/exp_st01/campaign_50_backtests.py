"""
ai_trading_agent.strategy_lab.experiments.exp_st01.campaign_50_backtests
========================================================================
Campaña de 50 Backtests Independientes para ST_EMA200_V1.

Matriz 10 Activos x 5 Temporalidades:
- Activos: SPY, QQQ, IWM, DIA, XLK, XLF, XLE, GLD, TLT, EFA
- Temporalidades: M15, M30, H1, H4, D1
- Registro forense en CSV y JSON con auditoría de datos y estado de suficiencia.
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from typing import List, Dict, Any, Tuple, Optional
import json
import csv
from dataclasses import asdict
import pandas as pd

from ai_trading_agent.strategy_lab.experiments.exp_st01.supertrend_indicator import SuperTrendCalculator
from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_strategy import StEma200Strategy
from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_backtester import (
    StEma200Backtester,
    BacktestMetricsST,
    TradeRecordST,
    COST_TIERS,
)
from ai_trading_agent.strategy_lab.experiments.exp_st01.data_loader import (
    ExpSt01DataLoader,
    ASSETS_UNIVERSE,
    TIMEFRAMES,
    DataCoverageAudit,
)


class Campaign50BacktestsRunner:
    """Ejecutor de la matriz de 50 backtests para ST_EMA200_V1."""

    def __init__(
        self,
        ema_period: int = 200,
        atr_period: int = 10,
        multiplier: float = 3.0,
        tp_r: float = 1.5,
        output_dir: Optional[Path] = None,
    ):
        self.output_dir = output_dir or Path(__file__).resolve().parent
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_loader = ExpSt01DataLoader()
        self.strategy = StEma200Strategy(
            ema_period=ema_period,
            atr_period=atr_period,
            supertrend_multiplier=multiplier,
            tp_r_multiple=tp_r,
        )
        self.backtester = StEma200Backtester(
            strategy=self.strategy,
            initial_equity=100000.0,
            risk_per_trade=250.0,
            cost_model=COST_TIERS["1x"],
        )

    def run_all(self) -> Tuple[List[BacktestMetricsST], Dict[str, List[TradeRecordST]], List[DataCoverageAudit]]:
        all_metrics: List[BacktestMetricsST] = []
        all_trades: Dict[str, List[TradeRecordST]] = {}
        all_audits: List[DataCoverageAudit] = []

        total_runs = len(ASSETS_UNIVERSE) * len(TIMEFRAMES)
        current_run = 0

        print(f"=== INICIANDO CAMPAÑA DE {total_runs} BACKTESTS (ST_EMA200_V1) ===")

        for sym in ASSETS_UNIVERSE:
            for tf in TIMEFRAMES:
                current_run += 1
                key = f"{sym}_{tf}"
                print(f"[{current_run}/{total_runs}] Procesando {key}...")

                bars, audit = self.data_loader.load_or_fetch(sym, tf)
                all_audits.append(audit)

                metrics, trades = self.backtester.run(sym, tf, bars)
                all_metrics.append(metrics)
                all_trades[key] = trades

                print(
                    f"   -> Barras: {len(bars)} | Trades: {metrics.total_trades} | "
                    f"WinRate: {metrics.win_rate:.1f}% | NetPnL: ${metrics.net_pnl:.2f} | "
                    f"PF: {metrics.profit_factor:.2f} | Sharpe: {metrics.sharpe_ratio:.2f} | Status: {metrics.status}"
                )

        self._export_matrix(all_metrics, all_audits)
        print("=== CAMPAÑA DE 50 BACKTESTS FINALIZADA CON ÉXITO ===")
        return all_metrics, all_trades, all_audits

    def _export_matrix(self, metrics: List[BacktestMetricsST], audits: List[DataCoverageAudit]):
        # 1. Exportar CSV
        csv_file = self.output_dir / "exp_st01_50_backtests_matrix.csv"
        audit_dict = {f"{a.symbol}_{a.timeframe}": a for a in audits}

        rows = []
        for m in metrics:
            key = f"{m.symbol}_{m.timeframe}"
            aud = audit_dict.get(key)
            row = asdict(m)
            row["bars_count"] = aud.total_bars if aud else 0
            row["data_start"] = aud.first_date if aud else "N/A"
            row["data_end"] = aud.last_date if aud else "N/A"
            row["data_notes"] = aud.notes if aud else "N/A"
            rows.append(row)

        if rows:
            keys = rows[0].keys()
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(rows)

        # 2. Exportar JSON
        json_file = self.output_dir / "exp_st01_50_backtests_matrix.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)

        print(f"Matriz exportada a:\n  - {csv_file}\n  - {json_file}")


if __name__ == "__main__":
    runner = Campaign50BacktestsRunner()
    runner.run_all()
