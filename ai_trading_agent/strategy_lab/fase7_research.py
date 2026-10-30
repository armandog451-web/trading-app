"""
ai_trading_agent.strategy_lab.fase7_research
===========================================
Módulo de Investigación Cuantitativa Fase 7.0 (Strategy Laboratory).
Investigación y backtesting aislado de estrategias Momentum y Mean Reversion.

INVARIANTES DE GOBERNANZA:
1. Modo operativo exclusivo: RESEARCH / ANALYSIS_ONLY.
2. Conexión a brokers Moomoo PAPER o LIVE: ESTRICTAMENTE BLOQUEADA (Air-Gapped).
3. Regímenes de mercado permitidos: TRENDING_BULL, RANGING e INDETERMINATE (MarketRegimeV1).
4. En régimen INDETERMINATE: abstención obligatoria de trading (NO_TRADE).
5. Inmutabilidad absoluta de D21 (f885ec2db2422308).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
import math
import numpy as np

from ai_trading_agent.domain.enums import SignalDirection
from ai_trading_agent.domain.models import OHLCVBar, StrategySignal
from ai_trading_agent.dual_strategy.regime import MarketRegimeV1, RegimeEvaluationRecord
from ai_trading_agent.strategy_lab.core.models import StrategyStatus


class ResearchIsolationViolation(PermissionError):
    """Lanzada si una estrategia de investigación intenta conectarse o emitir órdenes a un broker."""
    pass


@dataclass
class ResearchTrade:
    """Registro simulado aislado para análisis cuantitativo en Fase 7."""
    strategy_id: str
    symbol: str
    entry_bar_timestamp: str
    exit_bar_timestamp: str
    entry_price: float
    exit_price: float
    direction: SignalDirection
    shares: int
    gross_pnl: float
    net_pnl: float
    commission: float
    slippage: float
    holding_days: int
    exit_reason: str
    market_regime: MarketRegimeV1


@dataclass
class ResearchPerformanceSummary:
    strategy_id: str
    family: str
    target_regime: MarketRegimeV1
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown_pct: float
    total_net_pnl: float
    avg_trade_pnl: float
    status: str = "RESEARCH_ONLY"


class BaseFase7ResearchStrategy:
    """Clase base aislada para estrategias experimentales de Fase 7."""

    def __init__(self, strategy_id: str, family: str, target_regime: MarketRegimeV1, parameters: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.family = family
        self.target_regime = target_regime
        self.parameters = parameters
        self.status = StrategyStatus.RESEARCH
        self.trading_mode = "ANALYSIS_ONLY"

    @property
    def allow_broker_execution(self) -> bool:
        """Invariante de seguridad: jamás se permite ejecución en broker."""
        return False

    def block_broker_execution(self):
        """Bloquea cualquier intento de enviar la orden a un broker real o paper."""
        if not self.allow_broker_execution:
            raise ResearchIsolationViolation(
                f"VIOLACIÓN DE AISLAMIENTO: {self.strategy_id} está en modo {self.status.value} / {self.trading_mode}. "
                "Conexión a broker Moomoo PAPER/LIVE físicamente prohibida."
            )

    def evaluate_signal(
        self,
        symbol: str,
        bars: List[OHLCVBar],
        regime: MarketRegimeV1,
        indicators: Dict[str, Any]
    ) -> StrategySignal:
        raise NotImplementedError


class MomentumTrendPullbackV1(BaseFase7ResearchStrategy):
    """
    Estrategia de Momentum: Retrocesos a media en tendencia alcista consolidada.
    Condición de Régimen: Requiere exclusivamente TRENDING_BULL.
    En INDETERMINATE o RANGING: NO_TRADE.
    """

    def __init__(self, strategy_id: str = "MOM_TrendPullback_V1", parameters: Optional[Dict[str, Any]] = None):
        params = parameters or {
            "ema_fast": 20,
            "sma_slow": 50,
            "min_rsi": 40.0,
            "max_rsi": 60.0,
            "min_rvol": 1.20,
            "atr_mult_stop": 1.5,
            "atr_mult_tp": 2.5,
            "max_holding_days": 5
        }
        super().__init__(
            strategy_id=strategy_id,
            family="MOMENTUM",
            target_regime=MarketRegimeV1.TRENDING_BULL,
            parameters=params
        )

    def evaluate_signal(
        self,
        symbol: str,
        bars: List[OHLCVBar],
        regime: MarketRegimeV1,
        indicators: Dict[str, Any]
    ) -> StrategySignal:
        now_ts = bars[-1].timestamp if bars else datetime.utcnow()

        # 1. Filtro estricto de régimen: Solo opera en TRENDING_BULL
        if regime != MarketRegimeV1.TRENDING_BULL:
            reason = "ABSTENCION_REGIMEN_INDETERMINATE" if regime == MarketRegimeV1.INDETERMINATE else f"REGIMEN_NO_PERMITIDO: {regime.value}"
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version="1.0",
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                reasons=[reason],
                timestamp=now_ts
            )

        if not bars or len(bars) < 55:
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version="1.0",
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                reasons=["INSUFFICIENT_BARS"],
                timestamp=now_ts
            )

        current_bar = bars[-1]
        close = current_bar.close
        low = current_bar.low
        rsi = indicators.get("rsi", 50.0)
        rvol = indicators.get("rvol", 1.0)
        ema_fast = indicators.get("ema_20", close)
        sma_slow = indicators.get("sma_50", close * 0.95)

        # Reglas cuantitativas de entrada
        in_pullback = low <= ema_fast * 1.01 and close >= ema_fast * 0.99
        above_slow = close > sma_slow
        rsi_valid = self.parameters["min_rsi"] <= rsi <= self.parameters["max_rsi"]
        rvol_valid = rvol >= self.parameters["min_rvol"]

        if in_pullback and above_slow and rsi_valid and rvol_valid:
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version="1.0",
                symbol=symbol,
                direction=SignalDirection.BUY,
                score=82.0,
                reasons=[
                    f"MOM_TrendPullback setup: Close={close:.2f} retesteando EMA20({ema_fast:.2f}), "
                    f">SMA50({sma_slow:.2f}), RSI={rsi:.1f}, RVOL={rvol:.2f}x bajo TRENDING_BULL"
                ],
                timestamp=now_ts
            )

        return StrategySignal(
            strategy_id=self.strategy_id,
            strategy_version="1.0",
            symbol=symbol,
            direction=SignalDirection.NO_TRADE,
            score=0.0,
            reasons=["CONDICIONES_NO_CUMPLIDAS"],
            timestamp=now_ts
        )


class MeanReversionRsiBollingerV1(BaseFase7ResearchStrategy):
    """
    Estrategia de Mean Reversion: Sobreventa extrema intradiaria/swing en rango lateral.
    Condición de Régimen: Requiere exclusivamente RANGING.
    En INDETERMINATE o TRENDING_BULL: NO_TRADE.
    """

    def __init__(self, strategy_id: str = "MR_RsiBollinger_V1", parameters: Optional[Dict[str, Any]] = None):
        params = parameters or {
            "rsi_period": 4,
            "rsi_oversold": 25.0,
            "bb_period": 20,
            "bb_std": 2.0,
            "min_rvol": 1.0,
            "max_holding_days": 3
        }
        super().__init__(
            strategy_id=strategy_id,
            family="MEAN_REVERSION",
            target_regime=MarketRegimeV1.RANGING,
            parameters=params
        )

    def evaluate_signal(
        self,
        symbol: str,
        bars: List[OHLCVBar],
        regime: MarketRegimeV1,
        indicators: Dict[str, Any]
    ) -> StrategySignal:
        now_ts = bars[-1].timestamp if bars else datetime.utcnow()

        # 1. Filtro estricto de régimen: Solo opera en RANGING
        if regime != MarketRegimeV1.RANGING:
            reason = "ABSTENCION_REGIMEN_INDETERMINATE" if regime == MarketRegimeV1.INDETERMINATE else f"REGIMEN_NO_PERMITIDO: {regime.value}"
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version="1.0",
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                reasons=[reason],
                timestamp=now_ts
            )

        if not bars or len(bars) < 30:
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version="1.0",
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                reasons=["INSUFFICIENT_BARS"],
                timestamp=now_ts
            )

        current_bar = bars[-1]
        close = current_bar.close
        low = current_bar.low
        rsi_4 = indicators.get("rsi_4", 50.0)
        bb_lower = indicators.get("bb_lower", close * 0.98)
        bb_middle = indicators.get("bb_middle", close)

        # Reglas cuantitativas de entrada para reversión a la media
        oversold = rsi_4 <= self.parameters["rsi_oversold"]
        pierced_lower = low <= bb_lower or close <= bb_lower * 1.005

        if oversold and pierced_lower:
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version="1.0",
                symbol=symbol,
                direction=SignalDirection.BUY,
                score=80.0,
                reasons=[
                    f"MR_RsiBollinger setup: Close={close:.2f} en banda inferior BB({bb_lower:.2f}), "
                    f"RSI(4)={rsi_4:.1f} <= {self.parameters['rsi_oversold']} bajo régimen RANGING"
                ],
                timestamp=now_ts
            )

        return StrategySignal(
            strategy_id=self.strategy_id,
            strategy_version="1.0",
            symbol=symbol,
            direction=SignalDirection.NO_TRADE,
            score=0.0,
            reasons=["CONDICIONES_NO_CUMPLIDAS"],
            timestamp=now_ts
        )


class IsolatedResearchBacktester:
    """
    Simulador determinista de backtest exclusivo para la Fase 7.
    Aislado de producción: aplica comisiones ($0.005/acción) y slippage (5 bps) fijos.
    No toca ninguna tabla de ejecución de producción ni emite eventos a brokers.
    """

    def __init__(self, commission_per_share: float = 0.005, slippage_bps: float = 5.0):
        self.commission_per_share = commission_per_share
        self.slippage_rate = slippage_bps / 10000.0

    def run_simulation(
        self,
        strategy: BaseFase7ResearchStrategy,
        symbol: str,
        bars: List[OHLCVBar],
        regime_series: List[MarketRegimeV1],
        capital_allocated: float = 100000.0
    ) -> ResearchPerformanceSummary:
        # Garantizar que sea estrictamente una estrategia de RESEARCH no conectable a broker
        if strategy.allow_broker_execution or strategy.status != StrategyStatus.RESEARCH:
            raise ResearchIsolationViolation("Solo se permite backtest sobre estrategias en estado RESEARCH.")

        trades: List[ResearchTrade] = []
        in_trade = False
        entry_price = 0.0
        entry_idx = 0
        shares = 0
        entry_bar_ts = ""

        # Precomputar indicadores básicos
        closes = [b.close for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        volumes = [b.volume for b in bars]

        for i in range(55, len(bars)):
            curr_bar = bars[i]
            regime = regime_series[i] if i < len(regime_series) else MarketRegimeV1.INDETERMINATE

            # Indicadores sintéticos para simulación de la barra
            # Simple cálculo rolling de RSI y Medias
            slice_close = closes[max(0, i-50):i+1]
            sma_50 = float(np.mean(slice_close)) if len(slice_close) >= 50 else curr_bar.close
            ema_20 = float(np.mean(closes[max(0, i-20):i+1]))
            diffs = np.diff(slice_close[-15:]) if len(slice_close) >= 15 else np.array([0.0])
            gains = np.maximum(diffs, 0)
            losses = np.maximum(-diffs, 0)
            avg_gain = float(np.mean(gains)) if len(gains) > 0 else 0.001
            avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.001
            rs = avg_gain / (avg_loss + 1e-9)
            rsi = 100.0 - (100.0 / (1.0 + rs))

            diffs4 = np.diff(slice_close[-5:]) if len(slice_close) >= 5 else np.array([0.0])
            rs4 = (float(np.mean(np.maximum(diffs4, 0))) + 1e-9) / (float(np.mean(np.maximum(-diffs4, 0))) + 1e-9)
            rsi_4 = 100.0 - (100.0 / (1.0 + rs4))

            std_20 = float(np.std(closes[max(0, i-20):i+1])) if len(closes) >= 20 else 1.0
            bb_lower = ema_20 - 2.0 * std_20
            bb_middle = ema_20

            avg_vol_20 = float(np.mean(volumes[max(0, i-20):i])) if i >= 20 else curr_bar.volume
            rvol = curr_bar.volume / (avg_vol_20 + 1e-9)

            indicators = {
                "rsi": rsi,
                "rsi_4": rsi_4,
                "rvol": rvol,
                "ema_20": ema_20,
                "sma_50": sma_50,
                "bb_lower": bb_lower,
                "bb_middle": bb_middle
            }

            if not in_trade:
                signal = strategy.evaluate_signal(symbol, bars[:i+1], regime, indicators)
                if signal.direction == SignalDirection.BUY:
                    # Simular entrada con deslizamiento
                    fill_price = curr_bar.close * (1.0 + self.slippage_rate)
                    risk_amount = capital_allocated * 0.0025  # 0.25% riesgo
                    stop_dist = max(curr_bar.close * 0.02, 1.0)
                    shares = max(10, int(risk_amount / stop_dist))
                    entry_price = fill_price
                    entry_idx = i
                    entry_bar_ts = str(curr_bar.timestamp)
                    in_trade = True
            else:
                holding_days = i - entry_idx
                max_holding = strategy.parameters.get("max_holding_days", 5)
                # Salida por tiempo o por objetivo de retorno
                return_pct = (curr_bar.close - entry_price) / entry_price
                exit_signal = False
                exit_reason = ""

                if holding_days >= max_holding:
                    exit_signal = True
                    exit_reason = "TIME_EXIT"
                elif return_pct >= 0.035:
                    exit_signal = True
                    exit_reason = "PROFIT_TARGET"
                elif return_pct <= -0.02:
                    exit_signal = True
                    exit_reason = "STOP_LOSS"

                if exit_signal:
                    exit_fill = curr_bar.close * (1.0 - self.slippage_rate)
                    gross = (exit_fill - entry_price) * shares
                    comm = (self.commission_per_share * shares) * 2.0
                    slip = (entry_price * self.slippage_rate + exit_fill * self.slippage_rate) * shares
                    net = gross - comm

                    trades.append(ResearchTrade(
                        strategy_id=strategy.strategy_id,
                        symbol=symbol,
                        entry_bar_timestamp=entry_bar_ts,
                        exit_bar_timestamp=str(curr_bar.timestamp),
                        entry_price=entry_price,
                        exit_price=exit_fill,
                        direction=SignalDirection.BUY,
                        shares=shares,
                        gross_pnl=gross,
                        net_pnl=net,
                        commission=comm,
                        slippage=slip,
                        holding_days=holding_days,
                        exit_reason=exit_reason,
                        market_regime=regime
                    ))
                    in_trade = False

        # Resumen de Métricas
        if not trades:
            return ResearchPerformanceSummary(
                strategy_id=strategy.strategy_id,
                family=strategy.family,
                target_regime=strategy.target_regime,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate_pct=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                max_drawdown_pct=0.0,
                total_net_pnl=0.0,
                avg_trade_pnl=0.0
            )

        pnls = [t.net_pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / len(pnls)) * 100.0
        gross_win = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)

        # Drawdown
        cum_pnl = np.cumsum(pnls)
        peak = np.maximum.accumulate(cum_pnl)
        dd = peak - cum_pnl
        max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0
        max_dd_pct = (max_dd / capital_allocated) * 100.0

        # Sharpe ratio simplificado (retorno medio / dev std)
        mean_pnl = float(np.mean(pnls))
        std_pnl = float(np.std(pnls)) if len(pnls) > 1 else 1.0
        sharpe = (mean_pnl / (std_pnl + 1e-9)) * math.sqrt(252 / 5.0)

        return ResearchPerformanceSummary(
            strategy_id=strategy.strategy_id,
            family=strategy.family,
            target_regime=strategy.target_regime,
            total_trades=len(trades),
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate_pct=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd_pct,
            total_net_pnl=sum(pnls),
            avg_trade_pnl=mean_pnl
        )
