import math
from datetime import datetime, timezone
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class RiskEngine:
    """
    Capa 5: Motor de Gestión de Riesgo Institucional y Validación R:R.
    Controla el Circuit Breaker diario, dimensionamiento de posición exacto (1%),
    verificación estricta de relación Riesgo:Beneficio (>= 1:2) y cierre intraday.
    """

    def __init__(self):
        self.max_daily_loss_pct = settings.MAX_DAILY_LOSS_PCT
        self.risk_per_trade_pct = settings.RISK_PER_TRADE_PCT
        self.min_rr_ratio = settings.MIN_RR_RATIO
        self.auto_square_off_time = settings.AUTO_SQUARE_OFF_TIME

    def is_circuit_breaker_tripped(self, starting_equity: float, realized_pnl: float, unrealized_pnl: float) -> tuple[bool, float]:
        """
        Calcula la pérdida acumulada en la sesión.
        Si la pérdida total supera el límite máximo permitido (ej. 2%), activa el Circuit Breaker.
        """
        total_pnl = realized_pnl + unrealized_pnl
        loss_limit_dollars = starting_equity * (self.max_daily_loss_pct / 100.0)

        if total_pnl < 0 and abs(total_pnl) >= loss_limit_dollars:
            return True, abs(total_pnl)
        return False, total_pnl

    def should_square_off(self, now: datetime | None = None) -> bool:
        """
        Verifica si se ha alcanzado la hora de cierre forzoso intraday (15:50 EST).
        """
        if now is None:
            now = datetime.now()

        # Comparar hora y minuto actual en formato HH:MM
        current_hm = now.strftime("%H:%M")
        return current_hm >= self.auto_square_off_time

    def evaluate_and_size_order(
        self,
        equity: float,
        daily_loss: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        side: str = "BUY"
    ) -> tuple[bool, str, dict]:
        """
        Valida que la operación cumpla todos los estándares cuantitativos de riesgo
        y calcula el tamaño de posición exacto.
        """
        # 1. Comprobar Circuit Breaker
        tripped, _ = self.is_circuit_breaker_tripped(equity, -abs(daily_loss) if daily_loss > 0 else daily_loss, 0)
        if tripped:
            return False, f"CIRCUIT BREAKER ACTIVO: Se ha alcanzado el límite de pérdida diaria (-{self.max_daily_loss_pct}%). Bloqueada nueva entrada.", {}

        # 2. Validar coherencia de precios
        if side == "BUY":
            if stop_loss >= entry_price:
                return False, "Stop Loss inválido para orden de compra (debe ser menor al precio de entrada)", {}
            if take_profit <= entry_price:
                return False, "Take Profit inválido para orden de compra (debe ser mayor al precio de entrada)", {}
            risk_distance = entry_price - stop_loss
            reward_distance = take_profit - entry_price
        else:
            if stop_loss <= entry_price:
                return False, "Stop Loss inválido para orden de venta corta (debe ser mayor al precio de entrada)", {}
            if take_profit >= entry_price:
                return False, "Take Profit inválido para orden de venta corta (debe ser menor al precio de entrada)", {}
            risk_distance = stop_loss - entry_price
            reward_distance = entry_price - take_profit

        if risk_distance <= 0.001:
            return False, "Distancia a Stop Loss despreciable o nula", {}

        # 3. Comprobar Ratio Riesgo / Beneficio (R:R)
        actual_rr = round(reward_distance / risk_distance, 2)
        if actual_rr < self.min_rr_ratio:
            return False, f"Ratio R:R insuficiente: 1:{actual_rr}. Se exige un mínimo estricto de 1:{self.min_rr_ratio}.", {}

        # 4. Dimensionamiento de posición (Risk Sizing)
        # Se arriesga exactamente el 1% del capital disponible
        cash_to_risk = equity * (self.risk_per_trade_pct / 100.0)
        shares = math.floor(cash_to_risk / risk_distance)

        if shares <= 0:
            return False, "El capital de la cuenta o distancia al Stop Loss no permite comprar al menos 1 acción.", {}

        total_position_value = shares * entry_price
        # Evitar sobreapalancamiento (máximo 90% del capital en una sola posición intraday)
        if total_position_value > equity * 0.90:
            shares = math.floor((equity * 0.90) / entry_price)

        risk_metrics = {
            "shares": shares,
            "risk_per_share": round(risk_distance, 2),
            "reward_per_share": round(reward_distance, 2),
            "total_risk_dollars": round(shares * risk_distance, 2),
            "total_potential_profit": round(shares * reward_distance, 2),
            "risk_reward_ratio": actual_rr,
            "position_capital": round(shares * entry_price, 2)
        }

        return True, f"Aprobado por Motor de Riesgo: R:R 1:{actual_rr} | {shares} acciones | Riesgo: ${risk_metrics['total_risk_dollars']} (1%)", risk_metrics

risk_engine = RiskEngine()
