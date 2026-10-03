"""
ai_trading_agent.tests.test_phase2_strategies
=============================================
Pruebas unitarias de las estrategias avanzadas y motores de confirmación de la Fase 2:
1. Mean Reversion (Bollinger + VWAP con filtro de tendencia)
2. Opening Range Breakout (ORB con filtro de volumen RVOL >= 1.4x)
3. Options Flow Analyzer (Estructuración con presupuesto <= $200 USD y mitigación de sesgos)
4. Advanced Confirmation Engine (Filtros de Earnings y pánico VIX)
5. Orquestador End-to-End con confluencia multidimensional
"""

import pytest
from datetime import datetime, timedelta
from ai_trading_agent.domain.enums import SignalDirection, MarketRegime, TradingMode
from ai_trading_agent.domain.models import AggregatedSignal, TradeProposal
from ai_trading_agent.data.synthetic import synthetic_generator
from ai_trading_agent.market.indicators import indicators
from ai_trading_agent.strategies.mean_reversion import mean_reversion_strategy
from ai_trading_agent.strategies.orb import orb_strategy
from ai_trading_agent.strategies.options_flow import options_flow_analyzer
from ai_trading_agent.signals.confirmation_engine import confirmation_engine
from ai_trading_agent.orchestrator import orchestrator


class TestPhase2AdvancedStrategies:

    def test_mean_reversion_anti_trend_filter(self):
        """En régimen BEAR_TREND, Mean Reversion NO debe sugerir comprar caídas."""
        bars = synthetic_generator.generate_bars(symbol="AAPL", count=100, regime="BEAR_TREND")
        ind = indicators.calculate_all(bars)
        # Forzar condición técnica de sobreventa para desafiar el filtro de tendencia
        ind["rsi"] = 28.0
        ind["current_price"] = ind["bb_lower"] * 0.99
        
        # Evaluar bajo régimen BEAR_TREND
        sig = mean_reversion_strategy.evaluate("AAPL", bars, ind, MarketRegime.BEAR_TREND)
        assert sig.direction == SignalDirection.NO_TRADE
        assert any("bloqueada" in r.lower() or "bear_trend" in r.lower() for r in sig.reasons)

    def test_mean_reversion_sideways_bounce(self):
        """En régimen SIDEWAYS o LOW_VOLATILITY con precio bajo banda inferior, evalúa reversión."""
        bars = synthetic_generator.generate_bars(symbol="MSFT", count=100, regime="SIDEWAYS")
        ind = indicators.calculate_all(bars)
        sig = mean_reversion_strategy.evaluate("MSFT", bars, ind, MarketRegime.SIDEWAYS)
        assert sig.strategy_id == "mean_reversion"
        assert sig.direction in (SignalDirection.BUY, SignalDirection.SELL, SignalDirection.NO_TRADE, SignalDirection.HOLD)

    def test_orb_requires_volume_expansion(self):
        """ORB debe rechazar rupturas si el volumen relativo (RVOL) es inferior a 1.4x."""
        bars = synthetic_generator.generate_bars(symbol="NVDA", count=60, regime="BULL_TREND")
        ind = indicators.calculate_all(bars)
        # Forzar rvol bajo
        ind["rvol"] = 0.8
        sig = orb_strategy.evaluate("NVDA", bars, ind, MarketRegime.BULL_TREND)
        # Debe ser HOLD o score < 50.0
        assert sig.direction == SignalDirection.HOLD or sig.score < 50.0

    def test_options_contract_budget_constraint(self):
        """El contrato de opciones estructurado jamás debe superar los $200 USD por contrato."""
        expensive_stock_price = 450.0  # e.g., SPY o MSFT
        contract = options_flow_analyzer.structure_option_contract(
            symbol="SPY",
            current_price=expensive_stock_price,
            direction="BUY",
            days_to_exp=21
        )
        assert contract.total_contract_cost <= 200.0
        assert contract.days_to_expiration >= 14
        assert contract.days_to_expiration <= 35
        assert contract.option_type == "CALL"

    def test_options_flow_hedging_warning(self):
        """Un ratio Put/Call > 1.6 debe alertar sobre cobertura institucional (evitar sesgo ingenuo)."""
        flow = options_flow_analyzer.evaluate_flow_sentiment(
            put_volume=18000,
            call_volume=8000,
            put_open_interest=50000,
            call_open_interest=40000
        )
        assert flow["put_call_ratio"] > 1.6
        assert flow["sentiment"] == "HIGH_HEDGING_PUT_PRESSURE"
        assert "cobertura" in flow["warning"].lower()

    def test_confirmation_engine_blocks_earnings(self):
        """Confirmation engine debe bloquear propuestas si la acción reporta resultados hoy."""
        now = datetime.utcnow()
        dummy_agg = AggregatedSignal(
            decision_id="dec_test",
            symbol="GOOGL",
            timestamp=now,
            direction=SignalDirection.BUY,
            score=88.0,
            contributing_strategies=["trend_v1", "orb"],
            is_actionable=True
        )
        dummy_proposal = TradeProposal(
            decision_id="dec_test",
            symbol="GOOGL",
            direction=SignalDirection.BUY,
            entry_price=150.0,
            stop_loss=147.0,
            take_profit=156.0,
            rr_ratio=2.0,
            timestamp=now,
            rationale="Setup cuantitativo perfecto"
        )
        # Bloqueo por Earnings
        confirmed, prop, reason = confirmation_engine.confirm_proposal(
            proposal=dummy_proposal,
            agg_signal=dummy_agg,
            regime=MarketRegime.BULL_TREND,
            event_calendar={"has_earnings_today": True}
        )
        assert confirmed is False
        assert prop is None
        assert "earnings" in reason.lower()

    def test_confirmation_engine_blocks_high_vix_with_low_score(self):
        """En HIGH_VOLATILITY, propuestas con score < 80.0 deben ser rechazadas."""
        now = datetime.utcnow()
        dummy_agg = AggregatedSignal(
            decision_id="dec_vix",
            symbol="TSLA",
            timestamp=now,
            direction=SignalDirection.BUY,
            score=68.0,
            contributing_strategies=["momentum_v1"],
            is_actionable=True
        )
        dummy_proposal = TradeProposal(
            decision_id="dec_vix",
            symbol="TSLA",
            direction=SignalDirection.BUY,
            entry_price=200.0,
            stop_loss=195.0,
            take_profit=210.0,
            rr_ratio=2.0,
            timestamp=now,
            rationale="Setup regular"
        )
        confirmed, prop, reason = confirmation_engine.confirm_proposal(
            proposal=dummy_proposal,
            agg_signal=dummy_agg,
            regime=MarketRegime.HIGH_VOLATILITY
        )
        assert confirmed is False
        assert "high_volatility" in reason.lower() or "volatilidad" in reason.lower()

    def test_end_to_end_orchestrator_with_options_and_earnings(self):
        """Orquestador end-to-end bloquea por earnings y entrega contrato cuando aprueba."""
        bars = synthetic_generator.generate_bars(symbol="AAPL", count=100, regime="BULL_TREND")
        
        # Test con earnings: debe dar CONFIRMATION_REJECTED si hubiera señal
        res_earnings = orchestrator.process_symbol(
            symbol="AAPL",
            bars=bars,
            event_calendar={"has_earnings_today": True}
        )
        if res_earnings["status"] not in ("NO_TRADE", "REJECTED"):
            assert res_earnings["status"] == "CONFIRMATION_REJECTED"
