"""
ai_trading_agent.strategy_lab.backtesting.multi_timeframe_synchronizer
========================================================================
Módulo institucional de Sincronización Multi-Timeframe y Prevención de Data Leakage (Fase 7).

Garantías Cuantitativas Institucionales:
1. Sincronización Estricta de Barras Cerradas (Closed-Bar Only):
   - Al evaluar una barra en timeframe intradía (1H o 15m) en tiempo T_curr,
     únicamente se permite el acceso a información de timeframes superiores (1D o 1H)
     que provenga de barras ESTRICTAMENTE CERRADAS antes de T_curr.
   - En timeframe diario (1D), para una barra intradía en la fecha D,
     la barra 1D disponible es la cerrada en D-1 o anterior (timestamp.date() < D).
   - En timeframe horario (1H), para una barra de 15m en tiempo T,
     la barra 1H disponible debe tener tiempo de cierre <= T.
2. Cero Sesgo de Anticipación (Zero Look-Ahead Bias):
   - Validación explícita de timestamps con lanzamiento de ValueError si se detecta
     fuga de información futura.
3. Evaluación y Simulación de Estrategias Híbridas Multi-Timeframe:
   - Permite combinar Filtro de Contexto / Régimen Diario (1D) con Setups de Entrada Intradía (1H)
     y Timing / Gatillo fino (15m).
4. Calculador de Complejidad Multi-Timeframe:
   - Cuantifica la penalización por complejidad estructural:
     Complexity = min(100.0, (timeframes * 15) + (features * 8) + (conditions * 5) + (parameters * 4))
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field

from ai_trading_agent.domain.models import OHLCVBar, StrategySignal
from ai_trading_agent.domain.enums import SignalDirection, MarketRegime
from ai_trading_agent.market.indicators import indicators
from ai_trading_agent.market.regime import regime_detector


class MultiTimeframeComplexityCalculator:
    """Calcula el Score de Complejidad para estrategias multi-timeframe."""

    @staticmethod
    def calculate(
        timeframes_count: int,
        features_count: int,
        conditions_count: int,
        parameters_count: int,
        total_trades: int = 100
    ) -> float:
        """
        Fórmula institucional:
        Base = (TF * 15) + (Features * 8) + (Conditions * 5) + (Params * 4)
        Penalización por muestra escasa si total_trades < 30.
        """
        base = (timeframes_count * 15.0) + (features_count * 8.0) + (conditions_count * 5.0) + (parameters_count * 4.0)
        trade_penalty = 0.0
        if total_trades < 30:
            trade_penalty = (30 - total_trades) * 1.5

        return min(100.0, round(base + trade_penalty, 2))


class MultiTimeframeSynchronizer:
    """
    Sincronizador determinista de series temporales multi-timeframe.
    Asegura que el contexto superior sea estrictamente causal (cerrado antes del punto de evaluación).
    """

    @staticmethod
    def get_closed_daily_bars(
        current_timestamp: datetime,
        daily_bars: List[OHLCVBar]
    ) -> List[OHLCVBar]:
        """
        Devuelve únicamente las barras diarias que se cerraron antes de la sesión de current_timestamp.
        Regla: bar.timestamp.date() < current_timestamp.date()
        Si se procesa en el mismo día, la barra de ese día AÚN NO HA CERRADO.
        """
        curr_date = current_timestamp.date()
        valid_bars = [b for b in daily_bars if b.timestamp.date() < curr_date]
        return valid_bars

    @staticmethod
    def get_closed_higher_timeframe_bars(
        current_timestamp: datetime,
        higher_tf_bars: List[OHLCVBar],
        higher_tf: str = "1h"
    ) -> List[OHLCVBar]:
        """
        Devuelve barras de timeframe superior cerradas antes o en current_timestamp.
        Para '1d': timestamp.date() < current_timestamp.date()
        Para '1h' con evaluación en 15m: bar.timestamp + 1h <= current_timestamp
        o si los timestamps representan el cierre: bar.timestamp <= current_timestamp.
        Por convención canónica de Yahoo/pandas, el timestamp de la barra suele ser el inicio.
        Si la barra horaria empieza a las 10:00, cierra a las 11:00.
        A las 10:45, la barra de las 10:00 NO ha cerrado aún.
        """
        if higher_tf == "1d":
            return MultiTimeframeSynchronizer.get_closed_daily_bars(current_timestamp, higher_tf_bars)

        delta = timedelta(hours=1) if higher_tf == "1h" else timedelta(minutes=15)
        # Una barra está cerrada si su tiempo de inicio + duración <= current_timestamp
        valid_bars = [b for b in higher_tf_bars if (b.timestamp + delta) <= current_timestamp]
        return valid_bars

    @staticmethod
    def validate_no_lookahead(
        eval_timestamp: datetime,
        context_bars: List[OHLCVBar],
        context_tf: str = "1d"
    ) -> bool:
        """
        Valida que ninguna barra en context_bars contenga información futura o no cerrada
        respecto a eval_timestamp. Lanza ValueError si hay violación de causalidad.
        """
        if not context_bars:
            return True

        for b in context_bars:
            if context_tf == "1d":
                if b.timestamp.date() >= eval_timestamp.date():
                    raise ValueError(
                        f"CRITICAL LOOK-AHEAD BIAS: Barra diaria con fecha {b.timestamp.date()} "
                        f"no está cerrada al evaluar {eval_timestamp}."
                    )
            elif context_tf == "1h":
                bar_close = b.timestamp + timedelta(hours=1)
                if bar_close > eval_timestamp:
                    raise ValueError(
                        f"CRITICAL LOOK-AHEAD BIAS: Barra 1H con inicio {b.timestamp} "
                        f"(cierre {bar_close}) no está cerrada al evaluar {eval_timestamp}."
                    )
        return True


class MultiTimeframeStrategyEvaluator:
    """
    Evaluador determinista de señales e híbridos multi-timeframe.
    Ejecuta combinaciones de 1D Context / Regime + 1H Entry / Exit + 15m Trigger.
    """

    def __init__(
        self,
        config_type: str = "CONFIG_A",  # CONFIG_A, CONFIG_B, CONFIG_C, CONFIG_D, BASELINE_1D, BASELINE_1H
        parameters: Optional[Dict[str, Any]] = None,
        strategy_id: str = "MTF_STRAT",
        version: str = "1.0"
    ):
        self.config_type = config_type
        self.parameters = parameters or {}
        self.strategy_id = strategy_id
        self.version = version

        # Parámetros configurables
        self.trend_sma_fast = self.parameters.get("trend_sma_fast", 20)
        self.trend_sma_slow = self.parameters.get("trend_sma_slow", 50)
        self.rsi_period = self.parameters.get("rsi_period", 14)
        self.rsi_lower = self.parameters.get("rsi_lower", 35.0)
        self.rsi_upper = self.parameters.get("rsi_upper", 65.0)
        self.rvol_threshold = self.parameters.get("rvol_threshold", 1.1)
        self.atr_mult = self.parameters.get("atr_mult", 1.5)
        self.rr_ratio = self.parameters.get("rr_ratio", 2.0)
        self.trailing_atr_mult = self.parameters.get("trailing_atr_mult", 2.0)

    def evaluate_1d_context(self, daily_bars: List[OHLCVBar]) -> Dict[str, Any]:
        """Evalúa el régimen y tendencia en el timeframe diario (1D) cerrado."""
        if not daily_bars or len(daily_bars) < 25:
            return {"trend": "NEUTRAL", "regime": MarketRegime.SIDEWAYS, "daily_bullish": False, "daily_bearish": False}

        d_ind = indicators.calculate_all(daily_bars)
        d_regime, _ = regime_detector.detect_regime(d_ind)

        close = daily_bars[-1].close
        sma_fast = d_ind.get("sma20", close)
        sma_slow = d_ind.get("sma50", close)
        ema9 = d_ind.get("ema9", close)
        ema21 = d_ind.get("ema21", close)

        bullish = (close > sma_slow) and (sma_fast >= sma_slow) and (ema9 >= ema21)
        bearish = (close < sma_slow) and (sma_fast <= sma_slow) and (ema9 <= ema21)

        trend = "BULLISH" if bullish else ("BEARISH" if bearish else "NEUTRAL")

        return {
            "trend": trend,
            "regime": d_regime,
            "daily_bullish": bullish,
            "daily_bearish": bearish,
            "close": close,
            "sma_fast": sma_fast,
            "sma_slow": sma_slow
        }

    def evaluate_15m_trigger(self, m15_bars: List[OHLCVBar]) -> Dict[str, Any]:
        """Evalúa el micro-timing en timeframe 15m cerrado."""
        if not m15_bars or len(m15_bars) < 15:
            return {"trigger": "NONE", "trigger_long": False, "trigger_short": False}

        m_ind = indicators.calculate_all(m15_bars)
        close = m15_bars[-1].close
        vwap = m_ind.get("vwap", close)
        rsi = m_ind.get("rsi", 50.0)
        rvol = m_ind.get("rvol", 1.0)

        trigger_long = (close > vwap) and (rsi > 45.0) and (rvol >= self.rvol_threshold)
        trigger_short = (close < vwap) and (rsi < 55.0) and (rvol >= self.rvol_threshold)

        return {
            "trigger": "BUY" if trigger_long else ("SELL" if trigger_short else "NONE"),
            "trigger_long": trigger_long,
            "trigger_short": trigger_short,
            "rsi": rsi,
            "vwap": vwap
        }

    def evaluate_hybrid_signal(
        self,
        symbol: str,
        current_1h_bar: OHLCVBar,
        history_1h: List[OHLCVBar],
        closed_daily_bars: List[OHLCVBar],
        closed_15m_bars: Optional[List[OHLCVBar]] = None
    ) -> StrategySignal:
        """
        Evalúa la barra horaria actual integrando el contexto 1D y el timing 15m opcional.
        """
        # Validación de seguridad contra look-ahead bias
        MultiTimeframeSynchronizer.validate_no_lookahead(
            eval_timestamp=current_1h_bar.timestamp,
            context_bars=closed_daily_bars,
            context_tf="1d"
        )

        close = current_1h_bar.close
        h1_ind = indicators.calculate_all(history_1h)
        h1_regime, _ = regime_detector.detect_regime(h1_ind)
        rsi = h1_ind.get("rsi", 50.0)
        rvol = h1_ind.get("rvol", 1.0)
        vwap = h1_ind.get("vwap", close)
        atr = h1_ind.get("atr", close * 0.01)
        ema9 = h1_ind.get("ema9", close)
        ema21 = h1_ind.get("ema21", close)

        # Contexto 1D
        d_ctx = self.evaluate_1d_context(closed_daily_bars)

        # Baseline 1D puro (evalúa solo tendencia y contexto diario proyectado)
        if self.config_type == "BASELINE_1D":
            if d_ctx["daily_bullish"] and (d_ctx["regime"] == MarketRegime.BULL_TREND):
                sl = round(close - (atr * self.atr_mult * 2.0), 2)
                tp = round(close + ((close - sl) * self.rr_ratio), 2)
                return StrategySignal(
                    strategy_id=self.strategy_id,
                    strategy_version=self.version,
                    symbol=symbol,
                    direction=SignalDirection.BUY,
                    score=70.0,
                    entry_price=close,
                    stop_loss=sl,
                    take_profit=tp,
                    reasons=["1D Baseline: Tendencia Alcista Diaria Fuerte"],
                    timestamp=current_1h_bar.timestamp
                )
            elif d_ctx["daily_bearish"] and (d_ctx["regime"] == MarketRegime.BEAR_TREND):
                sl = round(close + (atr * self.atr_mult * 2.0), 2)
                tp = round(close - ((sl - close) * self.rr_ratio), 2)
                return StrategySignal(
                    strategy_id=self.strategy_id,
                    strategy_version=self.version,
                    symbol=symbol,
                    direction=SignalDirection.SELL,
                    score=70.0,
                    entry_price=close,
                    stop_loss=sl,
                    take_profit=tp,
                    reasons=["1D Baseline: Tendencia Bajista Diaria"],
                    timestamp=current_1h_bar.timestamp
                )
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                reasons=["1D Baseline: Sin tendencia diaria definida"],
                timestamp=current_1h_bar.timestamp
            )

        # Baseline 1H puro (ignora contexto diario)
        if self.config_type == "BASELINE_1H":
            is_1h_mr_long = (rsi <= self.rsi_lower) and (close <= vwap) and (rvol >= self.rvol_threshold)
            is_1h_mr_short = (rsi >= self.rsi_upper) and (close >= vwap) and (rvol >= self.rvol_threshold)

            if is_1h_mr_long:
                sl = round(close - (atr * self.atr_mult), 2)
                tp = round(close + ((close - sl) * self.rr_ratio), 2)
                return StrategySignal(
                    strategy_id=self.strategy_id,
                    strategy_version=self.version,
                    symbol=symbol,
                    direction=SignalDirection.BUY,
                    score=72.0,
                    entry_price=close,
                    stop_loss=sl,
                    take_profit=tp,
                    reasons=[f"1H Baseline: RSI sobreventa ({rsi:.1f})"],
                    timestamp=current_1h_bar.timestamp
                )
            elif is_1h_mr_short:
                sl = round(close + (atr * self.atr_mult), 2)
                tp = round(close - ((sl - close) * self.rr_ratio), 2)
                return StrategySignal(
                    strategy_id=self.strategy_id,
                    strategy_version=self.version,
                    symbol=symbol,
                    direction=SignalDirection.SELL,
                    score=72.0,
                    entry_price=close,
                    stop_loss=sl,
                    take_profit=tp,
                    reasons=[f"1H Baseline: RSI sobrecompra ({rsi:.1f})"],
                    timestamp=current_1h_bar.timestamp
                )
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                reasons=["1H Baseline: Sin setup 1H"],
                timestamp=current_1h_bar.timestamp
            )

        # CONFIG_A: 1D Context (Trend) + 1H Entry (Pullback / Mean-Reversion aligned with trend)
        if self.config_type == "CONFIG_A":
            # Si 1D es Alcista, buscamos pullback en 1H (RSI bajo o cruce alcista) para entrar a favor
            if d_ctx["daily_bullish"]:
                h1_pullback_long = (rsi <= 48.0) and (close > vwap * 0.99) and (rvol >= self.rvol_threshold)
                if h1_pullback_long:
                    sl = round(close - (atr * self.atr_mult), 2)
                    tp = round(close + ((close - sl) * self.rr_ratio), 2)
                    return StrategySignal(
                        strategy_id=self.strategy_id,
                        strategy_version=self.version,
                        symbol=symbol,
                        direction=SignalDirection.BUY,
                        score=80.0,
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        reasons=[f"Config A: 1D Alcista + 1H Pullback Entry (RSI: {rsi:.1f}, RVOL: {rvol:.2f})"],
                        timestamp=current_1h_bar.timestamp
                    )
            elif d_ctx["daily_bearish"]:
                h1_pullback_short = (rsi >= 52.0) and (close < vwap * 1.01) and (rvol >= self.rvol_threshold)
                if h1_pullback_short:
                    sl = round(close + (atr * self.atr_mult), 2)
                    tp = round(close - ((sl - close) * self.rr_ratio), 2)
                    return StrategySignal(
                        strategy_id=self.strategy_id,
                        strategy_version=self.version,
                        symbol=symbol,
                        direction=SignalDirection.SELL,
                        score=80.0,
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        reasons=[f"Config A: 1D Bajista + 1H Pullback Entry (RSI: {rsi:.1f}, RVOL: {rvol:.2f})"],
                        timestamp=current_1h_bar.timestamp
                    )
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                reasons=["Config A: Sin alineación 1D Context + 1H Entry"],
                timestamp=current_1h_bar.timestamp
            )

        # CONFIG_B: 1D Regime Filter + 1H Momentum/Trend Entry + 1H Dynamic Exit
        if self.config_type == "CONFIG_B":
            # Requiere régimen diario explícito BULL_TREND o BEAR_TREND
            if d_ctx["regime"] == MarketRegime.BULL_TREND and d_ctx["daily_bullish"]:
                h1_mom_long = (ema9 > ema21) and (close > vwap) and (rvol >= self.rvol_threshold)
                if h1_mom_long:
                    sl = round(close - (atr * self.atr_mult), 2)
                    tp = round(close + ((close - sl) * self.rr_ratio * 1.2), 2)  # RR expansivo
                    return StrategySignal(
                        strategy_id=self.strategy_id,
                        strategy_version=self.version,
                        symbol=symbol,
                        direction=SignalDirection.BUY,
                        score=85.0,
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        reasons=[f"Config B: 1D BULL_TREND + 1H Momentum Entry (EMA9>21, RVOL: {rvol:.2f})"],
                        timestamp=current_1h_bar.timestamp
                    )
            elif d_ctx["regime"] == MarketRegime.BEAR_TREND and d_ctx["daily_bearish"]:
                h1_mom_short = (ema9 < ema21) and (close < vwap) and (rvol >= self.rvol_threshold)
                if h1_mom_short:
                    sl = round(close + (atr * self.atr_mult), 2)
                    tp = round(close - ((sl - close) * self.rr_ratio * 1.2), 2)
                    return StrategySignal(
                        strategy_id=self.strategy_id,
                        strategy_version=self.version,
                        symbol=symbol,
                        direction=SignalDirection.SELL,
                        score=85.0,
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        reasons=[f"Config B: 1D BEAR_TREND + 1H Momentum Entry (EMA9<21, RVOL: {rvol:.2f})"],
                        timestamp=current_1h_bar.timestamp
                    )
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                reasons=["Config B: Sin confirmación 1D Regime + 1H Momentum"],
                timestamp=current_1h_bar.timestamp
            )

        # CONFIG_C: 1D Context + 1H Entry Setup + 15m Execution Timing Trigger
        if self.config_type == "CONFIG_C":
            m15_trig = self.evaluate_15m_trigger(closed_15m_bars or [])
            if d_ctx["daily_bullish"] and (ema9 > ema21):
                # Requiere gatillo 15m a favor
                if m15_trig["trigger_long"]:
                    sl = round(close - (atr * self.atr_mult), 2)
                    tp = round(close + ((close - sl) * self.rr_ratio), 2)
                    return StrategySignal(
                        strategy_id=self.strategy_id,
                        strategy_version=self.version,
                        symbol=symbol,
                        direction=SignalDirection.BUY,
                        score=88.0,
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        reasons=["Config C: 1D Context + 1H Setup + 15m Timing Trigger ALCISTA"],
                        timestamp=current_1h_bar.timestamp
                    )
            elif d_ctx["daily_bearish"] and (ema9 < ema21):
                if m15_trig["trigger_short"]:
                    sl = round(close + (atr * self.atr_mult), 2)
                    tp = round(close - ((sl - close) * self.rr_ratio), 2)
                    return StrategySignal(
                        strategy_id=self.strategy_id,
                        strategy_version=self.version,
                        symbol=symbol,
                        direction=SignalDirection.SELL,
                        score=88.0,
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        reasons=["Config C: 1D Context + 1H Setup + 15m Timing Trigger BAJISTA"],
                        timestamp=current_1h_bar.timestamp
                    )
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                reasons=["Config C: Filtro 1D+1H+15m no gatillado simultáneamente"],
                timestamp=current_1h_bar.timestamp
            )

        # CONFIG_D: 1D Context + 1H Entry + Salida Asimétrica Basada en Volatilidad (ATR Trailing)
        if self.config_type == "CONFIG_D":
            if d_ctx["daily_bullish"]:
                h1_long = (rsi <= 45.0 or (ema9 > ema21 and close > vwap)) and (rvol >= self.rvol_threshold)
                if h1_long:
                    sl = round(close - (atr * self.atr_mult * 0.9), 2)
                    tp = round(close + ((close - sl) * 3.0), 2)  # Asymmetric 3.0 R:R
                    return StrategySignal(
                        strategy_id=self.strategy_id,
                        strategy_version=self.version,
                        symbol=symbol,
                        direction=SignalDirection.BUY,
                        score=82.0,
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        reasons=["Config D: 1D Context + 1H Entry + Asymmetric Volatility Exit (3.0R)"],
                        timestamp=current_1h_bar.timestamp
                    )
            elif d_ctx["daily_bearish"]:
                h1_short = (rsi >= 55.0 or (ema9 < ema21 and close < vwap)) and (rvol >= self.rvol_threshold)
                if h1_short:
                    sl = round(close + (atr * self.atr_mult * 0.9), 2)
                    tp = round(close - ((sl - close) * 3.0), 2)
                    return StrategySignal(
                        strategy_id=self.strategy_id,
                        strategy_version=self.version,
                        symbol=symbol,
                        direction=SignalDirection.SELL,
                        score=82.0,
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        reasons=["Config D: 1D Context + 1H Entry + Asymmetric Volatility Exit (3.0R)"],
                        timestamp=current_1h_bar.timestamp
                    )
            return StrategySignal(
                strategy_id=self.strategy_id,
                strategy_version=self.version,
                symbol=symbol,
                direction=SignalDirection.NO_TRADE,
                score=0.0,
                reasons=["Config D: Sin señal con salida asimétrica"],
                timestamp=current_1h_bar.timestamp
            )

        return StrategySignal(
            strategy_id=self.strategy_id,
            strategy_version=self.version,
            symbol=symbol,
            direction=SignalDirection.NO_TRADE,
            score=0.0,
            reasons=["Configuración desconocida"],
            timestamp=current_1h_bar.timestamp
        )


class MultiTimeframeBacktestSimulator:
    """
    Simulador determinista paso a paso para estrategias multi-timeframe.
    Recorre las barras horarias (1H) y sincroniza barras diarias (1D) cerradas y 15m cerradas.
    Aplica rigurosamente comisiones institucionales ($0.005/acción) y slippage (5 bps).
    """

    def __init__(
        self,
        evaluator: MultiTimeframeStrategyEvaluator,
        initial_capital: float = 100000.0,
        commission_per_share: float = 0.005,
        slippage_pct: float = 0.0005,
        risk_per_trade_pct: float = 0.01
    ):
        self.evaluator = evaluator
        self.initial_capital = initial_capital
        self.commission_per_share = commission_per_share
        self.slippage_pct = slippage_pct
        self.risk_per_trade_pct = risk_per_trade_pct

    def run_simulation(
        self,
        symbol: str,
        h1_bars: List[OHLCVBar],
        daily_bars: List[OHLCVBar],
        m15_bars: Optional[List[OHLCVBar]] = None,
        min_warmup: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la simulación temporal cronológica.
        Retorna la lista de trades completados.
        """
        if len(h1_bars) <= min_warmup:
            return []

        capital = self.initial_capital
        closed_trades: List[Dict[str, Any]] = []
        active_position: Optional[Dict[str, Any]] = None

        for t in range(min_warmup, len(h1_bars)):
            curr_bar = h1_bars[t]
            history_1h = h1_bars[:t + 1]

            # 1. Gestionar posición activa si existe
            if active_position is not None:
                side = active_position["side"]
                entry_p = active_position["entry_price"]
                stop_l = active_position["stop_loss"]
                take_p = active_position["take_profit"]
                qty = active_position["quantity"]

                exit_price = None
                exit_reason = None

                if side == "BUY":
                    if curr_bar.low <= stop_l:
                        exit_price = min(curr_bar.open, stop_l)
                        exit_reason = "STOP_LOSS"
                    elif curr_bar.high >= take_p:
                        exit_price = max(curr_bar.open, take_p)
                        exit_reason = "TAKE_PROFIT"
                elif side == "SELL":
                    if curr_bar.high >= stop_l:
                        exit_price = max(curr_bar.open, stop_l)
                        exit_reason = "STOP_LOSS"
                    elif curr_bar.low <= take_p:
                        exit_price = min(curr_bar.open, take_p)
                        exit_reason = "TAKE_PROFIT"

                if exit_price is not None:
                    if side == "BUY":
                        adj_exit = exit_price * (1.0 - self.slippage_pct)
                        gross_pnl = (adj_exit - entry_p) * qty
                    else:
                        adj_exit = exit_price * (1.0 + self.slippage_pct)
                        gross_pnl = (entry_p - adj_exit) * qty

                    exit_comm = qty * self.commission_per_share
                    exit_slip = abs(exit_price - adj_exit) * qty
                    total_comm = active_position["entry_commission"] + exit_comm
                    total_slip = active_position["entry_slippage"] + exit_slip
                    net_pnl = round(gross_pnl - exit_comm, 2)

                    capital += net_pnl
                    closed_trades.append({
                        "trade_id": f"mtf_t_{len(closed_trades)+1}",
                        "symbol": symbol,
                        "side": side,
                        "entry_time": active_position["entry_time"],
                        "exit_time": curr_bar.timestamp,
                        "entry_price": round(entry_p, 2),
                        "exit_price": round(adj_exit, 2),
                        "quantity": qty,
                        "gross_pnl": round(gross_pnl, 2),
                        "net_pnl": net_pnl,
                        "commission": round(total_comm, 2),
                        "slippage": round(total_slip, 2),
                        "exit_reason": exit_reason
                    })
                    active_position = None

            # 2. Si no hay posición activa, sincronizar timeframes y evaluar señal
            if active_position is None:
                closed_daily = MultiTimeframeSynchronizer.get_closed_daily_bars(
                    current_timestamp=curr_bar.timestamp,
                    daily_bars=daily_bars
                )

                closed_m15 = []
                if m15_bars:
                    closed_m15 = MultiTimeframeSynchronizer.get_closed_higher_timeframe_bars(
                        current_timestamp=curr_bar.timestamp,
                        higher_tf_bars=m15_bars,
                        higher_tf="15m"
                    )
                signal = self.evaluator.evaluate_hybrid_signal(
                    symbol=symbol,
                    current_1h_bar=curr_bar,
                    history_1h=history_1h,
                    closed_daily_bars=closed_daily,
                    closed_15m_bars=closed_m15
                )

                if signal.direction in [SignalDirection.BUY, SignalDirection.SELL] and signal.entry_price and signal.stop_loss and signal.take_profit:
                    risk_capital = capital * self.risk_per_trade_pct
                    price_risk = abs(signal.entry_price - signal.stop_loss)
                    if price_risk > 0:
                        raw_qty = int(risk_capital / price_risk)
                        max_shares = int((capital * 0.20) / signal.entry_price)
                        qty = max(1, min(raw_qty, max_shares))

                        if signal.direction == SignalDirection.BUY:
                            fill_p = signal.entry_price * (1.0 + self.slippage_pct)
                            side_str = "BUY"
                        else:
                            fill_p = signal.entry_price * (1.0 - self.slippage_pct)
                            side_str = "SELL"

                        entry_comm = qty * self.commission_per_share
                        entry_slip = abs(signal.entry_price - fill_p) * qty
                        capital -= entry_comm

                        active_position = {
                            "side": side_str,
                            "entry_time": curr_bar.timestamp,
                            "entry_price": fill_p,
                            "stop_loss": signal.stop_loss,
                            "take_profit": signal.take_profit,
                            "quantity": qty,
                            "entry_commission": entry_comm,
                            "entry_slippage": entry_slip
                        }

        return closed_trades
