"""
ai_trading_agent.portfolio.monitor
==================================
Monitor de cartera en tiempo real y protector de posiciones (Instrucción 15).
Calcula P&L no realizado y aplica Auto Break-Even dinámico (+1.0R).
"""

from datetime import datetime
from typing import Dict, List, Tuple
from ai_trading_agent.domain.models import Position
from ai_trading_agent.execution.paper_broker import PaperBroker


class PortfolioMonitor:
    def __init__(self, broker: PaperBroker):
        self.broker = broker

    def update_positions_with_price(self, symbol: str, current_price: float) -> List[Tuple[str, str, float]]:
        """
        Actualiza el precio actual de la posición, P&L no realizado
        y evalúa si corresponde activar Auto Break-Even (+1.0R) o ejecutar salida.
        """
        closed_events = []
        positions = self.broker.positions

        if symbol not in positions:
            return closed_events

        pos = positions[symbol]
        pos.current_price = current_price
        pos.updated_at = datetime.utcnow()

        risk_dist = abs(pos.avg_entry_price - pos.stop_loss)
        be_trigger = pos.avg_entry_price + risk_dist  # +1.0R alcanzado

        # 1. Regla Auto Break-Even (+1.0R)
        if not pos.break_even_active and current_price >= be_trigger:
            pos.break_even_active = True
            pos.stop_loss = pos.avg_entry_price  # Riesgo cero asegurado

        # 2. Calcular P&L no realizado
        pos.unrealized_pnl = round((current_price - pos.avg_entry_price) * pos.quantity, 2)

        # 3. Comprobar Salidas por Take Profit o Stop Loss
        if current_price >= pos.take_profit:
            pnl = round((pos.take_profit - pos.avg_entry_price) * pos.quantity, 2)
            self.broker.cash += (pos.quantity * pos.take_profit)
            del positions[symbol]
            closed_events.append((symbol, "TAKE_PROFIT", pnl))
        elif current_price <= pos.stop_loss:
            pnl = round((pos.stop_loss - pos.avg_entry_price) * pos.quantity, 2)
            self.broker.cash += (pos.quantity * pos.stop_loss)
            del positions[symbol]
            closed_events.append((symbol, "STOP_LOSS", pnl))

        return closed_events


portfolio_monitor = PortfolioMonitor(broker=None)
