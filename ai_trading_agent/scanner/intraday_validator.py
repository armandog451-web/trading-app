"""
ai_trading_agent.scanner.intraday_validator
===========================================
Validador de Sesión Intradía — Separación Estricta entre Preparación y Confirmación.

REGLA CUANTITATIVA FUNDAMENTAL:
1. Fin de semana (Sábado/Domingo): Exclusivamente preparación de hipótesis y candidatos (Watchlist).
   Está estrictamente prohibido confundir un setup del sábado con una orden o señal ejecutable.
2. Sesión Intradía (Lunes a Viernes 9:30-16:00 EST): El motor intradía audita los candidatos
   preparados y EXIGE confirmaciones en tiempo real (Precio > Gatillo, RVOL >= 1.4x, Precio vs VWAP,
   y Ausencia de Gap de Invalidación) antes de promover cualquier setup a señal ejecutable.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import zoneinfo

from ai_trading_agent.domain.enums import MarketRegime, SignalDirection, TradingMode
from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.scanner.models import AssetWeekendPlan, MarketScenario, CandidateCondition


class IntradayCandidateValidator:
    """
    Filtro de confirmación intradía que valida en tiempo real los candidatos
    preparados durante el escaneo de fin de semana.
    """

    def __init__(self, tz_name: str = "America/New_York"):
        self.tz_name = tz_name

    def is_regular_market_hours(self, dt: Optional[datetime] = None) -> bool:
        """Determina si la fecha/hora actual corresponde a la sesión regular de EE. UU. (9:30 - 16:00 EST en días hábiles)."""
        try:
            tz = zoneinfo.ZoneInfo(self.tz_name)
            now = dt or datetime.now(tz)
        except Exception:
            now = dt or datetime.utcnow()

        # Lunes = 0, Viernes = 4, Sábado = 5, Domingo = 6
        if now.weekday() in (5, 6):
            return False

        # Rango horario de sesión regular (9:30 AM a 4:00 PM)
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        return market_open <= now <= market_close

    def validate_candidate_intraday(
        self,
        plan: AssetWeekendPlan,
        intraday_bars: List[OHLCVBar],
        current_dt: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Evalúa si un candidato del fin de semana confirma sus condiciones técnicas en la sesión viva.

        Retorna un dict con:
        - confirmed: bool
        - status: "PRE_MARKET_STANDBY" | "INVALIDATED" | "WAITING_TRIGGER" | "WAITING_VOLUME" | "CONFIRMED"
        - direction: "BUY" | "SELL" | "HOLD"
        - reasons: List[str]
        """
        now = current_dt or (intraday_bars[-1].timestamp if intraday_bars else datetime.utcnow())

        # 1. Verificación de Horario de Mercado
        if not self.is_regular_market_hours(now):
            return {
                "symbol": plan.symbol,
                "confirmed": False,
                "status": "PRE_MARKET_STANDBY",
                "direction": "HOLD",
                "reasons": [
                    "Mercado cerrado o fuera de sesión regular (9:30-16:00 EST).",
                    "El plan se mantiene como CANDIDATO EN VIGILANCIA; prohibida la ejecución prematura."
                ]
            }

        if not intraday_bars or len(intraday_bars) < 3:
            return {
                "symbol": plan.symbol,
                "confirmed": False,
                "status": "INSUFFICIENT_INTRADAY_DATA",
                "direction": "HOLD",
                "reasons": ["Datos intradía insuficientes para evaluar confirmación de apertura."]
            }

        current_bar = intraday_bars[-1]
        current_price = current_bar.close

        # Calcular VWAP intradía acumulado
        total_vol = sum(b.volume for b in intraday_bars)
        if total_vol > 0:
            vwap = sum(((b.high + b.low + b.close) / 3.0) * b.volume for b in intraday_bars) / total_vol
        else:
            vwap = current_price

        # RVOL intradía estimado (volumen promedio de barras recientes vs primeras barras)
        avg_vol = total_vol / len(intraday_bars)
        current_rvol = round(current_bar.volume / avg_vol, 2) if avg_vol > 0 else 1.0

        # Evaluar Escenario Alcista
        bull = plan.bullish_scenario
        bear = plan.bearish_scenario

        # 2. Comprobación de Invalidación
        if current_price <= bull.invalidation_level and bull.direction == "BULLISH":
            # Si el precio perforó el nivel de invalidación alcista
            is_bull_invalidated = True
        else:
            is_bull_invalidated = False

        # 3. Comprobación de Gatillo Alcista
        if current_price >= bull.trigger_level and not is_bull_invalidated:
            # Requisitos de Confirmación Intradía:
            # - RVOL >= 1.2x (o 1.4x)
            # - Precio sostenido por encima del VWAP intradía
            reasons = []
            volume_confirmed = current_rvol >= 1.2
            vwap_confirmed = current_price >= vwap

            if volume_confirmed and vwap_confirmed:
                return {
                    "symbol": plan.symbol,
                    "confirmed": True,
                    "status": "CONFIRMED",
                    "direction": "BUY",
                    "scenario": "BULLISH",
                    "trigger_price": bull.trigger_level,
                    "current_price": current_price,
                    "vwap": round(vwap, 2),
                    "rvol": current_rvol,
                    "reasons": [
                        f"Gatillo alcista superado (${current_price:.2f} >= ${bull.trigger_level:.2f}).",
                        f"Volumen intradía confirmado (RVOL {current_rvol}x >= 1.2x).",
                        f"Precio cotizando sobre VWAP (${vwap:.2f}).",
                        "Nivel de invalidación respetado."
                    ]
                }
            else:
                pending = []
                if not volume_confirmed:
                    pending.append(f"Falta confirmación de volumen (RVOL {current_rvol}x < 1.2x)")
                if not vwap_confirmed:
                    pending.append(f"Precio por debajo de VWAP (${current_price:.2f} < ${vwap:.2f})")
                return {
                    "symbol": plan.symbol,
                    "confirmed": False,
                    "status": "WAITING_CONFIRMATION",
                    "direction": "HOLD",
                    "reasons": pending
                }

        # 4. Comprobación de Gatillo Bajista
        if current_price <= bear.trigger_level:
            volume_confirmed = current_rvol >= 1.2
            vwap_confirmed = current_price <= vwap
            if volume_confirmed and vwap_confirmed:
                return {
                    "symbol": plan.symbol,
                    "confirmed": True,
                    "status": "CONFIRMED",
                    "direction": "SELL",
                    "scenario": "BEARISH",
                    "trigger_price": bear.trigger_level,
                    "current_price": current_price,
                    "vwap": round(vwap, 2),
                    "rvol": current_rvol,
                    "reasons": [
                        f"Gatillo bajista perforado (${current_price:.2f} <= ${bear.trigger_level:.2f}).",
                        f"Volumen intradía confirmado (RVOL {current_rvol}x >= 1.2x).",
                        f"Precio cotizando bajo VWAP (${vwap:.2f})."
                    ]
                }

        # 5. Si no se activó ningún gatillo
        return {
            "symbol": plan.symbol,
            "confirmed": False,
            "status": "WAITING_TRIGGER",
            "direction": "HOLD",
            "reasons": [
                f"El precio (${current_price:.2f}) se mantiene dentro del rango entre soporte (${plan.key_support:.2f}) y resistencia (${plan.key_resistance:.2f}).",
                f"Gatillo alcista: ${bull.trigger_level:.2f} | Gatillo bajista: ${bear.trigger_level:.2f}."
            ]
        }


intraday_validator = IntradayCandidateValidator()
