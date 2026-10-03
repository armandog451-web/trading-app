"""
ai_trading_agent.signals.aggregator
===================================
Agregador cuantitativo de señales y No-Trade Engine (Instrucción 10).
Combina señales, resuelve contradicciones y emite NO_TRADE explícito cuando corresponda.
"""

import uuid
from datetime import datetime
from typing import List, Tuple, Optional
from ai_trading_agent.domain.enums import SignalDirection, DataQualityStatus
from ai_trading_agent.domain.models import StrategySignal, AggregatedSignal, TradeProposal


class SignalAggregator:
    """Motor de confluencia y filtrado de señales."""

    def __init__(self, min_confluence_score: float = 65.0):
        self.min_confluence_score = min_confluence_score

    def aggregate(
        self,
        symbol: str,
        signals: List[StrategySignal],
        timestamp: datetime = None
    ) -> Tuple[AggregatedSignal, Optional[TradeProposal]]:
        """
        Combina señales individuales bajo reglas transparentes de confluencia y no-trade.
        """
        decision_id = f"dec_{uuid.uuid4().hex[:12]}"
        timestamp = timestamp or datetime.utcnow()

        if not signals:
            agg = AggregatedSignal(
                decision_id=decision_id,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                timestamp=timestamp,
                contributing_strategies=[],
                is_actionable=False,
                rejection_reason="No se recibieron señales de estrategias"
            )
            return agg, None

        # 1. Filtro de Calidad de Datos
        for s in signals:
            if s.data_quality != DataQualityStatus.VALID:
                agg = AggregatedSignal(
                    decision_id=decision_id,
                    symbol=symbol,
                    direction=SignalDirection.NO_TRADE,
                    score=0.0,
                    timestamp=timestamp,
                    contributing_strategies=[s.strategy_id],
                    is_actionable=False,
                    rejection_reason=f"Datos no confiables o ausentes en {s.strategy_id} ({s.data_quality})"
                )
                return agg, None

        # 2. Detección de Contradicciones (Buy vs Sell)
        has_buy = any(s.direction == SignalDirection.BUY for s in signals)
        has_sell = any(s.direction == SignalDirection.SELL for s in signals)

        if has_buy and has_sell:
            conflicts = ["Contradicción directa entre estrategias: Una indica COMPRA y otra VENTA"]
            agg = AggregatedSignal(
                decision_id=decision_id,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                timestamp=timestamp,
                contributing_strategies=[s.strategy_id for s in signals],
                conflicts_detected=conflicts,
                is_actionable=False,
                rejection_reason="Señales contradictorias (No-Trade Engine activado)"
            )
            return agg, None

        active_signals = [s for s in signals if s.direction in (SignalDirection.BUY, SignalDirection.SELL)]

        if not active_signals:
            agg = AggregatedSignal(
                decision_id=decision_id,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                timestamp=timestamp,
                contributing_strategies=[s.strategy_id for s in signals],
                is_actionable=False,
                rejection_reason="Ninguna estrategia detectó condiciones operativas"
            )
            return agg, None

        # 3. Puntuación Ponderada
        avg_score = float(sum(s.score for s in active_signals) / len(active_signals))
        primary_sig = max(active_signals, key=lambda s: s.score)
        direction = primary_sig.direction

        if avg_score < self.min_confluence_score:
            agg = AggregatedSignal(
                decision_id=decision_id,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=round(avg_score, 1),
                timestamp=timestamp,
                contributing_strategies=[s.strategy_id for s in active_signals],
                is_actionable=False,
                rejection_reason=f"Puntuación de confluencia insuficiente: {avg_score:.1f} < {self.min_confluence_score}"
            )
            return agg, None

        # 4. Generar Propuesta de Trade
        entry = primary_sig.entry_price
        sl = primary_sig.stop_loss
        tp = primary_sig.take_profit
        rr = round(abs(tp - entry) / (abs(entry - sl) + 1e-9), 2)

        agg = AggregatedSignal(
            decision_id=decision_id,
            symbol=symbol,
            direction=direction,
            score=round(avg_score, 1),
            timestamp=timestamp,
            contributing_strategies=[s.strategy_id for s in active_signals],
            conflicts_detected=primary_sig.conflicts,
            is_actionable=True
        )

        proposal = TradeProposal(
            decision_id=decision_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            rr_ratio=rr,
            timestamp=timestamp,
            rationale=f"Confluencia {'ALCISTA' if direction == SignalDirection.BUY else 'BAJISTA'} aprobada por {', '.join(agg.contributing_strategies)}"
        )

        return agg, proposal


signal_aggregator = SignalAggregator()
