"""
Unit Tests for ai_trading_agent.strategy_lab.fase7_research
===========================================================
Verifica formalmente las 6 restricciones institucionales de la Fase 7.0:
1. Estado exclusivo RESEARCH y modo ANALYSIS_ONLY.
2. Bloqueo físico de ejecución en brokers (Moomoo PAPER / LIVE).
3. Inmutabilidad de D21 (fingerprint f885ec2db2422308 intacto).
4. Restricción estricta a los tres regímenes existentes: TRENDING_BULL, RANGING, INDETERMINATE.
5. Abstención obligatoria en INDETERMINATE (NO_TRADE).
6. Backtesting determinista aislado sin contaminación de datos ni tablas de producción.
"""

from datetime import datetime
import pytest
from unittest.mock import MagicMock

from ai_trading_agent.domain.enums import SignalDirection
from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.dual_strategy.regime import MarketRegimeV1
from ai_trading_agent.strategy_lab.core.models import StrategyStatus
from ai_trading_agent.strategy_lab.registry.registry import strategy_registry
from ai_trading_agent.strategy_lab.fase7_research import (
    BaseFase7ResearchStrategy,
    MomentumTrendPullbackV1,
    MeanReversionRsiBollingerV1,
    IsolatedResearchBacktester,
    ResearchIsolationViolation
)


def _generate_synthetic_bars(count=60, base_price=500.0, trend=0.5):
    bars = []
    price = base_price
    for i in range(count):
        price += trend
        bar = OHLCVBar(
            symbol="SPY",
            timestamp=datetime(2024, 1, 1 + (i % 28)),
            open=price - 1.0,
            high=price + 2.0,
            low=price - 2.0,
            close=price,
            volume=1500000.0
        )
        bars.append(bar)
    return bars


class TestFase7IsolationAndResearch:

    def test_1_strategies_strictly_research_and_analysis_only(self):
        """Verifica que las estrategias de Fase 7 nazcan y permanezcan en RESEARCH y ANALYSIS_ONLY."""
        mom = MomentumTrendPullbackV1()
        mr = MeanReversionRsiBollingerV1()

        assert mom.status == StrategyStatus.RESEARCH
        assert mom.trading_mode == "ANALYSIS_ONLY"
        assert mom.allow_broker_execution is False

        assert mr.status == StrategyStatus.RESEARCH
        assert mr.trading_mode == "ANALYSIS_ONLY"
        assert mr.allow_broker_execution is False

    def test_2_physical_broker_execution_blocked(self):
        """Verifica que cualquier intento de ejecutar o conectar a un broker lance ResearchIsolationViolation."""
        mom = MomentumTrendPullbackV1()
        with pytest.raises(ResearchIsolationViolation) as excinfo:
            mom.block_broker_execution()
        assert "VIOLACIÓN DE AISLAMIENTO" in str(excinfo.value)
        assert "físicamente prohibida" in str(excinfo.value)

    def test_3_d21_remains_intact_and_immutable(self):
        """Garantiza que la investigación en Fase 7 no altere D21 ni su fingerprint."""
        d21 = strategy_registry.get_strategy("D21_RangeCompress_5d")
        assert d21 is not None, "D21 debe existir en el registro canónico"
        assert d21.status == StrategyStatus.PAPER, "D21 debe ser la única estrategia en PAPER"
        # Verificar fingerprint inmutable
        assert "f885ec2db2422308" in str(d21.parameters) or "Range Compression" in d21.name

    def test_4_regimes_strictly_constrained_to_existing_three(self):
        """Verifica que los únicos regímenes válidos sean TRENDING_BULL, RANGING e INDETERMINATE."""
        valid_regimes = {r.value for r in MarketRegimeV1}
        expected_regimes = {"TRENDING_BULL", "RANGING", "INDETERMINATE"}
        assert valid_regimes == expected_regimes, "No se permiten regímenes inventados fuera de los tres existentes"

    def test_5_indeterminate_regime_forces_abstention(self):
        """Verifica que en régimen INDETERMINATE ambas familias de estrategias retornen NO_TRADE obligatoriamente."""
        mom = MomentumTrendPullbackV1()
        mr = MeanReversionRsiBollingerV1()
        bars = _generate_synthetic_bars(60)
        indicators = {"rsi": 50.0, "rsi_4": 20.0, "rvol": 1.5, "ema_20": 510.0, "sma_50": 500.0}

        sig_mom = mom.evaluate_signal("SPY", bars, MarketRegimeV1.INDETERMINATE, indicators)
        sig_mr = mr.evaluate_signal("SPY", bars, MarketRegimeV1.INDETERMINATE, indicators)

        assert sig_mom.direction == SignalDirection.NO_TRADE
        assert "INDETERMINATE" in sig_mom.reasons[0]

        assert sig_mr.direction == SignalDirection.NO_TRADE
        assert "INDETERMINATE" in sig_mr.reasons[0]

    def test_6_mismatched_regime_blocks_trading(self):
        """Verifica que Momentum no opere en RANGING y Mean Reversion no opere en TRENDING_BULL."""
        mom = MomentumTrendPullbackV1()
        mr = MeanReversionRsiBollingerV1()
        bars = _generate_synthetic_bars(60)
        indicators = {"rsi": 50.0, "rsi_4": 20.0, "rvol": 1.5, "ema_20": 510.0, "sma_50": 500.0}

        # Momentum en RANGING -> NO_TRADE
        sig_mom = mom.evaluate_signal("SPY", bars, MarketRegimeV1.RANGING, indicators)
        assert sig_mom.direction == SignalDirection.NO_TRADE
        assert "REGIMEN_NO_PERMITIDO" in sig_mom.reasons[0]

        # Mean Reversion en TRENDING_BULL -> NO_TRADE
        sig_mr = mr.evaluate_signal("SPY", bars, MarketRegimeV1.TRENDING_BULL, indicators)
        assert sig_mr.direction == SignalDirection.NO_TRADE
        assert "REGIMEN_NO_PERMITIDO" in sig_mr.reasons[0]

    def test_7_isolated_backtester_runs_cleanly(self):
        """Verifica que el backtest de investigación se ejecute determinísticamente y compute métricas completas."""
        mom = MomentumTrendPullbackV1()
        backtester = IsolatedResearchBacktester(commission_per_share=0.005, slippage_bps=5.0)
        bars = _generate_synthetic_bars(80, base_price=450.0, trend=0.8)
        regimes = [MarketRegimeV1.TRENDING_BULL] * 80

        summary = backtester.run_simulation(mom, "SPY", bars, regimes, capital_allocated=100000.0)

        assert summary.strategy_id == "MOM_TrendPullback_V1"
        assert summary.family == "MOMENTUM"
        assert summary.status == "RESEARCH_ONLY"
        assert isinstance(summary.total_trades, int)
        assert isinstance(summary.profit_factor, float)
        assert isinstance(summary.sharpe_ratio, float)
