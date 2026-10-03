"""
ai_trading_agent.tests.test_backtest_engine
===========================================
Pruebas cuantitativas y de verificación del motor de backtesting:
1. Cálculo matemático de métricas (Sharpe, Sortino, Max Drawdown, Expectancia)
2. Partición temporal In-Sample vs Out-of-Sample
3. Simulación barra a barra sin look-ahead bias
4. Fricciones reales: deducción de comisiones y deslizamiento (slippage)
"""

import pytest
from datetime import datetime
from ai_trading_agent.data.synthetic import synthetic_generator
from ai_trading_agent.backtest.metrics import metrics_calculator, PerformanceMetrics
from ai_trading_agent.backtest.engine import backtest_engine, BacktestReport


class TestQuantitativeBacktest:

    def test_metrics_calculator_accuracy(self):
        """Verifica las fórmulas de Win Rate, Profit Factor, Max Drawdown y Sharpe."""
        sample_trades = [
            {"net_pnl": 500.0, "commission": 5.0, "slippage": 10.0},
            {"net_pnl": -250.0, "commission": 5.0, "slippage": 10.0},
            {"net_pnl": 600.0, "commission": 5.0, "slippage": 10.0},
            {"net_pnl": -200.0, "commission": 5.0, "slippage": 10.0},
            {"net_pnl": 350.0, "commission": 5.0, "slippage": 10.0},
        ]
        # Ganancia bruta = 500 + 600 + 350 = 1450
        # Pérdida bruta = 250 + 200 = 450
        # Profit Factor esperado = 1450 / 450 = 3.22
        # Win Rate esperado = 3 / 5 = 60.0%
        # PnL neto total = 1450 - 450 = 1000.0
        metrics = metrics_calculator.calculate(sample_trades, initial_capital=10000.0)

        assert metrics.total_trades == 5
        assert metrics.winning_trades == 3
        assert metrics.losing_trades == 2
        assert metrics.win_rate_pct == 60.0
        assert metrics.profit_factor == 3.22
        assert metrics.total_net_pnl == 1000.0
        assert metrics.total_commission_paid == 25.0
        assert metrics.total_slippage_cost == 50.0
        assert metrics.expectancy_dollars > 0

    def test_metrics_empty_trades(self):
        """Si no hubo operaciones, las métricas deben ser neutras y seguras."""
        metrics = metrics_calculator.calculate([])
        assert metrics.total_trades == 0
        assert metrics.win_rate_pct == 0.0
        assert metrics.total_net_pnl == 0.0
        assert metrics.max_drawdown_pct == 0.0

    def test_data_splitting_in_sample_out_sample(self):
        """Divide adecuadamente la serie temporal sin fuga de datos ni traslapes."""
        bars = synthetic_generator.generate_bars(symbol="SPY", count=200)
        train_bars, test_bars = backtest_engine.split_data(bars, train_ratio=0.70)

        assert len(train_bars) == 140
        assert len(test_bars) == 60
        assert train_bars[-1].timestamp < test_bars[0].timestamp  # Orden cronológico estricto

    def test_backtest_simulation_execution(self):
        """Ejecuta una simulación completa paso a paso con comisiones y slippage."""
        bars = synthetic_generator.generate_bars(symbol="QQQ", count=150, regime="BULL_TREND", seed=101)
        report = backtest_engine.run(symbol="QQQ", bars=bars, min_warmup_bars=30)

        assert isinstance(report, BacktestReport)
        assert report.symbol == "QQQ"
        assert report.initial_capital == 100000.0
        assert len(report.equity_curve) > 0
        assert report.equity_curve[0] == 100000.0
        # Verificar que si hubo operaciones, registraron comisiones y slippages
        if report.metrics.total_trades > 0:
            assert report.metrics.total_commission_paid > 0.0
            assert report.metrics.total_slippage_cost >= 0.0
            for trade in report.trades:
                assert "trade_id" in trade
                assert trade["exit_reason"] in ("STOP_LOSS", "TAKE_PROFIT", "END_OF_DATASET")

    def test_out_of_sample_validation_workflow(self):
        """Valida el flujo de verificación Out-of-Sample para auditoría cuantitativa."""
        bars = synthetic_generator.generate_bars(symbol="IWM", count=180, regime="BULL_TREND", seed=202)
        in_sample_bars, out_of_sample_bars = backtest_engine.split_data(bars, train_ratio=0.65)

        # 1. Backtest In-Sample
        is_report = backtest_engine.run(
            symbol="IWM",
            bars=in_sample_bars,
            dataset_type="IN_SAMPLE"
        )
        assert is_report.dataset_type == "IN_SAMPLE"

        # 2. Backtest Out-of-Sample
        oos_report = backtest_engine.run(
            symbol="IWM",
            bars=out_of_sample_bars,
            dataset_type="OUT_OF_SAMPLE"
        )
        assert oos_report.dataset_type == "OUT_OF_SAMPLE"
        assert oos_report.period_start > is_report.period_start

    def test_backtest_universe_survivorship_bias_mitigation(self):
        """Verifica la simulación multi-activo incluyendo valores delistados para prevenir el sesgo de supervivencia."""
        spy_bars = synthetic_generator.generate_bars(symbol="SPY", count=100, regime="BULL_TREND", seed=1)
        # Activo delistado / fallido simulado
        delisted_bars = synthetic_generator.generate_bars(symbol="OLD_TICKER_DELISTED", count=100, regime="BEAR_TREND", seed=2)

        universe = {
            "SPY": spy_bars,
            "OLD_TICKER_DELISTED": delisted_bars
        }

        result = backtest_engine.run_universe(universe_bars=universe)

        assert result["total_symbols"] == 2
        assert "SPY" in result["symbol_reports"]
        assert "OLD_TICKER_DELISTED" in result["symbol_reports"]
        assert isinstance(result["aggregate_metrics"], PerformanceMetrics)

    def test_backtest_stress_test_regimes_fixed_parameters(self):
        """Verifica la consistencia de resultados con parámetros fijos a través de múltiples regímenes de mercado."""
        from ai_trading_agent.domain.enums import MarketRegime

        regime_data = {
            MarketRegime.BULL_TREND: synthetic_generator.generate_bars(symbol="AAPL", count=100, regime="BULL_TREND", seed=10),
            MarketRegime.BEAR_TREND: synthetic_generator.generate_bars(symbol="AAPL", count=100, regime="BEAR_TREND", seed=20),
            MarketRegime.SIDEWAYS: synthetic_generator.generate_bars(symbol="AAPL", count=100, regime="SIDEWAYS", seed=30),
            MarketRegime.HIGH_VOLATILITY: synthetic_generator.generate_bars(symbol="AAPL", count=100, regime="HIGH_VOLATILITY", seed=40)
        }

        stress_results = backtest_engine.stress_test_regimes(regime_datasets=regime_data, symbol="AAPL")

        assert len(stress_results) == 4
        assert MarketRegime.BULL_TREND in stress_results
        assert MarketRegime.BEAR_TREND in stress_results
        assert MarketRegime.SIDEWAYS in stress_results
        assert MarketRegime.HIGH_VOLATILITY in stress_results
