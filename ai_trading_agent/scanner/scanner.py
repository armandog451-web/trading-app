"""
ai_trading_agent.scanner.scanner
================================
Módulo central WeekendMarketScanner (Instrucciones del Add-on Module).
Ejecuta el escaneo de preparación durante el fin de semana sin emitir órdenes.
Diseñado para operar con datos históricos de cierre cuando el mercado está cerrado.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.enums import MarketRegime, DataQualityStatus
from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.data.providers.yfinance_provider import yfinance_provider
from ai_trading_agent.data.validation import data_validator
from ai_trading_agent.market.indicators import indicators
from ai_trading_agent.market.regime import regime_detector
from ai_trading_agent.strategies.options_flow import options_flow_analyzer
from ai_trading_agent.scanner.models import (
    CandidateCondition, MarketScenario, AssetWeekendPlan, WeekendScanReport
)
from ai_trading_agent.notifications.telegram_service import telegram_notifier

logger = logging.getLogger(__name__)


class WeekendMarketScanner:
    """Escáner cuantitativo de fin de semana para preparación de la sesión siguiente."""

    DEFAULT_WATCHLIST = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "AMD"]

    def __init__(self, custom_watchlist: Optional[List[str]] = None):
        self.watchlist = custom_watchlist or self.DEFAULT_WATCHLIST
        self.last_report: Optional[WeekendScanReport] = None

    def scan_market(
        self,
        execution_day: str = "MANUAL",
        symbols: Optional[List[str]] = None,
        send_telegram: bool = True
    ) -> WeekendScanReport:
        """
        Ejecuta el escaneo completo de fin de semana.
        ESTRICTAMENTE ANALYSIS ONLY: Ninguna orden real o simulada es creada.
        """
        target_universe = symbols or self.watchlist
        now = datetime.now(timezone.utc)
        scan_id = f"wscan_{int(now.timestamp())}"

        candidates: List[AssetWeekendPlan] = []
        indices_regimes: Dict[str, str] = {}
        missing_data_limitations: List[str] = []
        economic_events: List[str] = []
        data_as_of_date = now

        # 1. Obtener datos de referencia para SPY (para fuerza relativa)
        spy_bars = yfinance_provider.get_historical_bars("SPY", count=60, interval="1d")
        spy_return_20d = 0.0
        if len(spy_bars) >= 20:
            spy_return_20d = (spy_bars[-1].close - spy_bars[-20].close) / spy_bars[-20].close
            data_as_of_date = spy_bars[-1].timestamp
        else:
            missing_data_limitations.append("SPY: Historial diario limitado para cálculo de Fuerza Relativa.")

        # 2. Analizar cada activo del universo
        for sym in target_universe:
            try:
                plan, regime_str, events = self._analyze_asset(sym, spy_return_20d)
                candidates.append(plan)
                if sym in ("SPY", "QQQ", "IWM"):
                    indices_regimes[sym] = regime_str
                if events:
                    economic_events.extend(events)
            except Exception as e:
                logger.error(f"Error escaneando {sym}: {e}")
                missing_data_limitations.append(f"{sym}: Error en procesamiento ({str(e)})")

        # 3. Clasificación agregada de candidatos
        breakouts = [c.symbol for c in candidates if c.primary_condition == CandidateCondition.BREAKOUT_WATCH]
        momentums = [c.symbol for c in candidates if c.primary_condition in (CandidateCondition.MOMENTUM_WATCH, CandidateCondition.TREND_CONTINUATION)]
        mean_revs = [c.symbol for c in candidates if c.primary_condition == CandidateCondition.MEAN_REVERSION_WATCH]

        # 4. Síntesis y Cambios de Tendencia Observados
        shifts = []
        for sym, reg in indices_regimes.items():
            shifts.append(f"Índice {sym}: Régimen de fondo {reg}.")

        market_summary = (
            f"Escaneo de fin de semana ({execution_day}) completado para {len(candidates)} activos. "
            f"SPY régimen {indices_regimes.get('SPY', 'NEUTRAL')}, QQQ régimen {indices_regimes.get('QQQ', 'NEUTRAL')}. "
            f"Detectados {len(breakouts)} candidatos de ruptura, {len(momentums)} de momentum y {len(mean_revs)} de reversión a la media."
        )

        no_trade_risks = [
            "Mercado cerrado: Todos los niveles representan zonas clave de preparación para la apertura del lunes.",
            "Requiere confirmación de volumen (RVOL >= 1.4x) y confluencia técnica antes de autorizar entradas.",
            "Prohibido operar antes de la apertura oficial de la sesión o si hay GAP binario descontrolado."
        ]

        report = WeekendScanReport(
            scan_id=scan_id,
            timestamp=now,
            execution_day=execution_day,
            data_as_of_date=data_as_of_date,
            universe_scanned=target_universe,
            market_overview=market_summary,
            indices_regimes=indices_regimes,
            trend_and_volatility_shifts=shifts,
            candidates=candidates,
            breakout_candidates=breakouts,
            momentum_candidates=momentums,
            mean_reversion_candidates=mean_revs,
            economic_and_earnings_events=list(set(economic_events)),
            no_trade_risks=no_trade_risks,
            missing_data_limitations=missing_data_limitations,
            system_status="ANALYSIS_ONLY",
            is_partial=bool(missing_data_limitations)
        )

        self.last_report = report

        # 5. Notificación opcional a Telegram
        if send_telegram and telegram_notifier.is_configured:
            try:
                self._send_telegram_summary(report)
            except Exception as e:
                logger.warning(f"Error enviando reporte a Telegram: {e}")

        return report

    def classify_candidate(
        self,
        last_price: float,
        key_res: float,
        atr: float,
        rsi: float,
        bb_lower: float,
        macd_hist: float,
        relative_strength: float,
        regime: MarketRegime,
        has_earnings_soon: bool
    ) -> tuple:
        """Clasifica un activo en una de las 9 condiciones de análisis."""
        primary_cond = CandidateCondition.NO_TRADE
        secondary_conds = []

        if has_earnings_soon:
            primary_cond = CandidateCondition.EARNINGS_RISK
            secondary_conds.append(CandidateCondition.NO_TRADE)
        elif regime == MarketRegime.HIGH_VOLATILITY:
            primary_cond = CandidateCondition.HIGH_VOLATILITY
        elif abs(last_price - key_res) <= (1.2 * atr):
            primary_cond = CandidateCondition.BREAKOUT_WATCH
            secondary_conds.append(CandidateCondition.ORB_CANDIDATE)
        elif rsi < 32 and last_price <= bb_lower:
            primary_cond = CandidateCondition.MEAN_REVERSION_WATCH
        elif rsi > 55 and macd_hist > 0 and relative_strength > 1.05:
            primary_cond = CandidateCondition.MOMENTUM_WATCH
            secondary_conds.append(CandidateCondition.TREND_CONTINUATION)
        elif regime in (MarketRegime.BULL_TREND, MarketRegime.BEAR_TREND):
            primary_cond = CandidateCondition.TREND_CONTINUATION
        else:
            primary_cond = CandidateCondition.ORB_CANDIDATE

        return primary_cond, secondary_conds

    def _analyze_asset(self, symbol: str, spy_benchmark_return: float) -> tuple:
        """Analiza un activo individual y genera sus escenarios alcista y bajista."""
        # Usar barras diarias históricas recientes
        bars = yfinance_provider.get_historical_bars(symbol, count=60, interval="1d")
        cal = yfinance_provider.get_event_calendar(symbol)

        events = []
        has_earnings_soon = cal.get("has_earnings_today", False)
        if has_earnings_soon:
            events.append(f"{symbol}: Reporte de beneficios corporativos (Earnings) programado próximamente.")

        if not bars or len(bars) < 25:
            # Reporte parcial por datos insuficientes
            empty_scenario = MarketScenario(
                direction="NEUTRAL",
                trigger_level=0.0,
                rationale="Datos históricos insuficientes",
                invalidation_level=0.0,
                invalidation_condition="Sin datos",
                required_confirmation="Esperar datos"
            )
            now = datetime.now(timezone.utc)
            plan = AssetWeekendPlan(
                symbol=symbol,
                last_historical_price=0.0,
                last_price_timestamp=now,
                trend="UNKNOWN",
                market_regime="INSUFFICIENT_DATA",
                primary_condition=CandidateCondition.INSUFFICIENT_DATA,
                key_support=0.0,
                key_resistance=0.0,
                pivot_point=0.0,
                relative_strength_vs_spy=1.0,
                bullish_scenario=empty_scenario,
                bearish_scenario=empty_scenario,
                liquidity_and_volatility_risk="Alta incertidumbre",
                data_quality_status="INSUFFICIENT_DATA"
            )
            return plan, "INSUFFICIENT_DATA", events

        # Cálculos de Indicadores y Régimen
        ind = indicators.calculate_all(bars)
        regime, _ = regime_detector.detect_regime(ind)

        last_bar = bars[-1]
        last_price = last_bar.close
        last_time = last_bar.timestamp

        # Fuerza Relativa vs SPY (20 periodos)
        asset_return_20d = (last_price - bars[-20].close) / bars[-20].close if len(bars) >= 20 else 0.0
        relative_strength = round(1.0 + (asset_return_20d - spy_benchmark_return), 2)

        # Soportes, Resistencias y Pivots verificables
        recent_highs = [b.high for b in bars[-20:]]
        recent_lows = [b.low for b in bars[-20:]]
        key_res = max(recent_highs)
        key_sup = min(recent_lows)
        pivot = round((last_bar.high + last_bar.low + last_bar.close) / 3.0, 2)
        atr = max(ind["atr"], 0.20)

        # Detección de Condición Primaria
        primary_cond, secondary_conds = self.classify_candidate(
            last_price=last_price,
            key_res=key_res,
            atr=atr,
            rsi=ind["rsi"],
            bb_lower=ind["bb_lower"],
            macd_hist=ind["macd_hist"],
            relative_strength=relative_strength,
            regime=regime,
            has_earnings_soon=has_earnings_soon
        )

        # Escenario Alcista
        bullish_trigger = round(max(key_res, pivot + (0.5 * atr)), 2)
        bullish_invalidation = round(pivot - (0.5 * atr), 2)
        bullish_scenario = MarketScenario(
            direction="BULLISH",
            trigger_level=bullish_trigger,
            rationale=f"Ruptura con volumen sobre nivel ${bullish_trigger:.2f} con RSI ({ind['rsi']:.1f}) en expansión.",
            invalidation_level=bullish_invalidation,
            invalidation_condition=f"Retroceso y cierre por debajo del pivote ${bullish_invalidation:.2f}.",
            required_confirmation="Apertura sobre pivote + RVOL >= 1.4x en los primeros 15 min de sesión."
        )

        # Escenario Bajista
        bearish_trigger = round(min(key_sup, pivot - (0.5 * atr)), 2)
        bearish_invalidation = round(pivot + (0.5 * atr), 2)
        bearish_scenario = MarketScenario(
            direction="BEARISH",
            trigger_level=bearish_trigger,
            rationale=f"Pérdida del soporte institucional ${bearish_trigger:.2f} con presión de venta relativa.",
            invalidation_level=bearish_invalidation,
            invalidation_condition=f"Reincorporación alcista por encima de ${bearish_invalidation:.2f}.",
            required_confirmation="Aceptación bajo soporte + volumen relativo vendedor."
        )

        # Opciones Pre-Market Preparation (presupuesto <= $200 USD)
        option_contract = None
        if primary_cond in (CandidateCondition.BREAKOUT_WATCH, CandidateCondition.MOMENTUM_WATCH, CandidateCondition.TREND_CONTINUATION):
            dir_str = "BUY" if relative_strength >= 1.0 else "SELL"
            opt_prop = options_flow_analyzer.structure_option_contract(
                symbol=symbol,
                current_price=last_price,
                direction=dir_str,
                days_to_exp=21
            )
            option_contract = opt_prop.model_dump()

        strat_apps = []
        if primary_cond == CandidateCondition.BREAKOUT_WATCH:
            strat_apps = ["Opening Range Breakout (ORB)", "Momentum Expansion"]
        elif primary_cond == CandidateCondition.MEAN_REVERSION_WATCH:
            strat_apps = ["Bollinger Mean Reversion", "VWAP Pullback"]
        elif primary_cond == CandidateCondition.TREND_CONTINUATION:
            strat_apps = ["Trend Following (EMA 9/21)", "MACD Expansion"]
        else:
            strat_apps = ["ORB 15-Min", "Análisis Discrecional"]

        plan = AssetWeekendPlan(
            symbol=symbol,
            last_historical_price=round(last_price, 2),
            last_price_timestamp=last_time,
            trend=regime.value if hasattr(regime, "value") else str(regime),
            market_regime=regime.value if hasattr(regime, "value") else str(regime),
            primary_condition=primary_cond,
            secondary_conditions=secondary_conds,
            key_support=round(key_sup, 2),
            key_resistance=round(key_res, 2),
            pivot_point=pivot,
            relative_strength_vs_spy=relative_strength,
            bullish_scenario=bullish_scenario,
            bearish_scenario=bearish_scenario,
            upcoming_events=events,
            has_earnings_soon=has_earnings_soon,
            liquidity_and_volatility_risk=f"ATR diario: ${atr:.2f} ({round((atr/last_price)*100, 1)}%)",
            applicable_strategies=strat_apps,
            data_quality_status=DataQualityStatus.VALID.value,
            options_candidate_contract=option_contract
        )

        return plan, regime.value if hasattr(regime, "value") else str(regime), events

    def _send_telegram_summary(self, report: WeekendScanReport) -> None:
        """Emite el resumen ejecutivo del escaneo a Telegram."""
        breakouts_str = ", ".join(report.breakout_candidates) or "Ninguno"
        momentum_str = ", ".join(report.momentum_candidates) or "Ninguno"
        mean_rev_str = ", ".join(report.mean_reversion_candidates) or "Ninguno"

        spy_reg = report.indices_regimes.get("SPY", "N/A")
        qqq_reg = report.indices_regimes.get("QQQ", "N/A")

        text = (
            f"📅 *SUPERROBOT — INFORME DE FIN DE SEMANA*\n"
            f"───────────────────────────────\n"
            f"🎯 *Ejecución:* `{report.execution_day}` | *Fecha Datos:* `{report.data_as_of_date.strftime('%Y-%m-%d')}`\n"
            f"🏛️ *Régimen SPY:* `{spy_reg}` | *QQQ:* `{qqq_reg}`\n\n"
            f"⚡ *CANDIDATOS PARA EL LUNES:*\n"
            f"• 🚀 *Rupturas (Breakout):* `{breakouts_str}`\n"
            f"• 📈 *Momentum / Tendencia:* `{momentum_str}`\n"
            f"• 🔄 *Reversión a la Media:* `{mean_rev_str}`\n\n"
            f"🛡️ *Eventos / Earnings:* {len(report.economic_and_earnings_events)} detectados\n"
            f"───────────────────────────────\n"
            f"💡 _Modo ANALYSIS_ONLY activo. Todos los niveles son preparatorios para apertura del lunes._"
        )
        telegram_notifier.send_message_sync(text)


weekend_scanner = WeekendMarketScanner()
