"""
ai_trading_agent.orchestrator
=============================
Orquestador central del flujo cuantitativo y explicativo (Instrucción 4 y 11).
Coordina el pipeline de análisis de extremo a extremo sin eludir ningún control de riesgo.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.enums import (
    TradingMode, SignalDirection, RiskDecision, OrderSide, OrderType, OrderStatus
)
from ai_trading_agent.domain.models import (
    OHLCVBar, PaperOrder, DecisionRecord
)
from ai_trading_agent.data.validation import data_validator
from ai_trading_agent.market.indicators import indicators
from ai_trading_agent.market.regime import regime_detector
from ai_trading_agent.strategies.trend import trend_strategy
from ai_trading_agent.strategies.momentum import momentum_strategy
from ai_trading_agent.strategies.mean_reversion import mean_reversion_strategy
from ai_trading_agent.strategies.orb import orb_strategy
from ai_trading_agent.strategies.options_flow import options_flow_analyzer
from ai_trading_agent.signals.aggregator import signal_aggregator
from ai_trading_agent.signals.confirmation_engine import confirmation_engine
from ai_trading_agent.risk.engine import risk_engine
from ai_trading_agent.execution.paper_broker import paper_broker
from ai_trading_agent.execution.brokers.unified_manager import unified_broker
from ai_trading_agent.journal.trade_journal import trade_journal
from ai_trading_agent.notifications.telegram_service import telegram_notifier


class TradingPipelineOrchestrator:
    """Coordina el ciclo de vida de análisis, riesgo y simulación."""

    def __init__(self, mode: TradingMode = None):
        self.mode = mode or settings.TRADING_MODE
        self.strategies = [trend_strategy, momentum_strategy, mean_reversion_strategy, orb_strategy]

    def process_symbol(
        self,
        symbol: str,
        bars: List[OHLCVBar],
        options_context: Optional[Dict[str, Any]] = None,
        event_calendar: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo para un símbolo:
        1. Validación de datos
        2. Cálculo de indicadores
        3. Detección de régimen de mercado
        4. Evaluación de estrategias
        5. Agregación de señales y No-Trade Engine
        6. Validación del Confirmation Engine (Earnings, VIX extremo, Opciones)
        7. Evaluación del Deterministic Risk Engine
        8. Gate de modo operativo (ANALYSIS_ONLY vs PAPER_TRADING)
        9. Estructuración opcional de contrato de opciones (presupuesto < $200 USD)
        10. Registro inmutable en TradeJournal
        """
        now = bars[-1].timestamp if bars else datetime.utcnow()

        # 1. Validación de Calidad de Datos
        valid, quality_status, val_msg = data_validator.validate_bar_series(bars)
        if not valid:
            return {
                "status": "REJECTED",
                "phase": "DATA_VALIDATION",
                "reason": val_msg,
                "symbol": symbol
            }

        # 2. Indicadores Técnicos
        ind = indicators.calculate_all(bars)

        # 3. Detección de Régimen
        regime, regime_reason = regime_detector.detect_regime(ind)

        # 4. Evaluación de Estrategias
        signals = [s.evaluate(symbol, bars, ind, regime) for s in self.strategies]

        # 5. Agregación y No-Trade Engine
        aggregated_signal, proposal = signal_aggregator.aggregate(symbol, signals, now)

        if not aggregated_signal.is_actionable or not proposal:
            record = DecisionRecord(
                decision_id=aggregated_signal.decision_id,
                timestamp=now,
                symbol=symbol,
                market_regime=regime,
                signal_direction=aggregated_signal.direction,
                signal_score=aggregated_signal.score,
                reasons=[aggregated_signal.rejection_reason or "No-Trade"],
                risk_decision=RiskDecision.REJECTED,
                risk_reasons=["No superó la confluencia o activó el No-Trade Engine"]
            )
            trade_journal.log_decision(record)

            return {
                "status": "NO_TRADE",
                "decision_id": aggregated_signal.decision_id,
                "symbol": symbol,
                "market_regime": regime,
                "score": aggregated_signal.score,
                "reason": aggregated_signal.rejection_reason
            }

        # 6. Confirmación Multidimensional y Filtro de Eventos Macro/Earnings (Instrucción 10)
        confirmed, confirmed_proposal, confirm_msg = confirmation_engine.confirm_proposal(
            proposal=proposal,
            agg_signal=aggregated_signal,
            regime=regime,
            options_context=options_context,
            event_calendar=event_calendar
        )

        if not confirmed or not confirmed_proposal:
            record = DecisionRecord(
                decision_id=proposal.decision_id,
                timestamp=now,
                symbol=symbol,
                market_regime=regime,
                signal_direction=proposal.direction,
                signal_score=aggregated_signal.score,
                reasons=[confirm_msg],
                risk_decision=RiskDecision.REJECTED,
                risk_reasons=[confirm_msg]
            )
            trade_journal.log_decision(record)

            return {
                "status": "CONFIRMATION_REJECTED",
                "decision_id": proposal.decision_id,
                "symbol": symbol,
                "market_regime": regime,
                "score": aggregated_signal.score,
                "reason": confirm_msg
            }

        proposal = confirmed_proposal

        # 7. Evaluación de Riesgo Determinista
        account = paper_broker.get_account_summary()
        risk_assessment = risk_engine.assess_proposal(
            proposal=proposal,
            equity=account["equity"],
            daily_pnl=account["realized_pnl"],
            open_positions=paper_broker.get_positions()
        )

        if risk_assessment.decision != RiskDecision.APPROVED:
            record = DecisionRecord(
                decision_id=proposal.decision_id,
                timestamp=now,
                symbol=symbol,
                market_regime=regime,
                signal_direction=proposal.direction,
                signal_score=aggregated_signal.score,
                reasons=[proposal.rationale],
                risk_decision=RiskDecision.REJECTED,
                risk_reasons=risk_assessment.reasons
            )
            trade_journal.log_decision(record)

            return {
                "status": "RISK_REJECTED",
                "decision_id": proposal.decision_id,
                "symbol": symbol,
                "market_regime": regime,
                "reasons": risk_assessment.reasons
            }

        # 8. Gate Operativo (Modos de Ejecución)
        order_record_id = None
        order_status = None
        execution_price = None

        if self.mode == TradingMode.ANALYSIS_ONLY:
            decision_msg = "Aprobado para análisis (Modo ANALYSIS_ONLY activo: orden no simulada por diseño)"
        elif self.mode == TradingMode.PAPER_TRADING:
            side = OrderSide.BUY if proposal.direction == SignalDirection.BUY else OrderSide.SELL
            order = PaperOrder(
                order_id=f"ord_{proposal.decision_id}",
                decision_id=proposal.decision_id,
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=risk_assessment.approved_quantity,
                requested_price=proposal.entry_price,
                stop_loss=proposal.stop_loss,
                take_profit=proposal.take_profit,
                created_at=now
            )
            filled_order = unified_broker.submit_order(order, mode=self.mode)
            order_record_id = filled_order.order_id
            order_status = filled_order.status
            execution_price = filled_order.avg_fill_price
            broker_label = unified_broker.active_broker_name.upper()
            decision_msg = f"Orden Paper ejecutada en {broker_label}: {filled_order.quantity} acciones @ ${execution_price:,.2f}"
        else:
            decision_msg = f"Modo {self.mode} registrado"

        # 9. Estructuración Opcional de Contrato de Opciones (< $200 USD)
        option_contract = options_flow_analyzer.structure_option_contract(
            symbol=symbol,
            current_price=proposal.entry_price,
            direction=proposal.direction.value
        )

        # 10. Registro Inmutable en TradeJournal
        record = DecisionRecord(
            decision_id=proposal.decision_id,
            timestamp=now,
            symbol=symbol,
            market_regime=regime,
            signal_direction=proposal.direction,
            signal_score=aggregated_signal.score,
            reasons=[proposal.rationale, decision_msg],
            risk_decision=RiskDecision.APPROVED,
            risk_reasons=risk_assessment.reasons,
            order_id=order_record_id,
            order_status=order_status,
            execution_price=execution_price
        )
        trade_journal.log_decision(record)

        result_payload = {
            "status": "APPROVED",
            "decision_id": proposal.decision_id,
            "symbol": symbol,
            "market_regime": regime,
            "direction": proposal.direction,
            "score": aggregated_signal.score,
            "quantity": risk_assessment.approved_quantity,
            "entry_price": proposal.entry_price,
            "stop_loss": proposal.stop_loss,
            "take_profit": proposal.take_profit,
            "rr_ratio": proposal.rr_ratio,
            "trading_mode": self.mode,
            "active_broker": unified_broker.active_broker_name,
            "order_id": order_record_id,
            "order_status": order_status,
            "execution_price": execution_price,
            "rationale": proposal.rationale,
            "option_contract": option_contract.model_dump()
        }

        # 11. Notificación Automática a Telegram (si está habilitado)
        try:
            telegram_notifier.send_signal_alert(result_payload)
        except Exception:
            pass

        return result_payload


orchestrator = TradingPipelineOrchestrator()
