"""
ai_trading_agent.strategy_lab.shadow.shadow_evaluator
=====================================================
Evaluador prospectivo autónomo para la campaña Shadow (Bloque C y Bloque F).
Responsable de:
- Descarga y saneamiento de barras diarias completamente cerradas.
- Evaluación determinista sin look-ahead de las estrategias candidatas congeladas.
- Orquestación del simulador de ejecución causal (Señal T -> Fill T+1).
- Registro estricto en el ledger append-only para todas las sesiones (con y sin señal).
- Mantenimiento del reloj de validación forward y control de hitos (20, 60, 90 sesiones).
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.discovery.discovery_engine_v2 import (
    DataIntegrityGate,
    generate_signals_MR_VolCond_ZScore_V1,
    generate_signals_CS_RelMom_VolAdj_V2
)

from .campaign_models import (
    ShadowCampaignStatus,
    CostScenario,
    ShadowValidationClock,
    ShadowEventType,
    CampaignFreezeManifest
)
from .crypto_ledger import ShadowEvidenceLedger
from .shadow_simulator import ShadowExecutionSimulator


class AutonomousShadowEvaluator:
    """
    Motor evaluador prospectivo independiente para el Strategy Laboratory.
    Desacoplado físicamente del runtime de órdenes de Moomoo y de D21.
    """

    def __init__(
        self,
        repo_root: Path,
        manifest_a: CampaignFreezeManifest,
        manifest_b: CampaignFreezeManifest,
        cost_scenario: CostScenario = CostScenario.TIER_1X
    ):
        self.repo_root = Path(repo_root)
        self.manifest_a = manifest_a
        self.manifest_b = manifest_b
        self.cost_scenario = cost_scenario

        self.storage_dir = self.repo_root / "ai_trading_agent" / "scratch" / "shadow_campaigns"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Ledgers independientes por estrategia
        self.ledger_a = ShadowEvidenceLedger(manifest_a.campaign_id, manifest_a.strategy_id, self.storage_dir)
        self.ledger_b = ShadowEvidenceLedger(manifest_b.campaign_id, manifest_b.strategy_id, self.storage_dir)

        # Simuladores independientes de ejecución
        self.simulator_a = ShadowExecutionSimulator(
            strategy_id=manifest_a.strategy_id,
            initial_capital_usd=manifest_a.capital_allocation_usd,
            risk_budget_per_trade_usd=manifest_a.risk_budget_per_trade_usd,
            max_concurrent_positions=manifest_a.max_concurrent_positions,
            cost_scenario=cost_scenario
        )
        self.simulator_b = ShadowExecutionSimulator(
            strategy_id=manifest_b.strategy_id,
            initial_capital_usd=manifest_b.capital_allocation_usd,
            risk_budget_per_trade_usd=manifest_b.risk_budget_per_trade_usd,
            max_concurrent_positions=manifest_b.max_concurrent_positions,
            cost_scenario=cost_scenario
        )

        # Relojes de validación independientes
        self.clock_a = self._load_or_init_clock(manifest_a)
        self.clock_b = self._load_or_init_clock(manifest_b)

        self.gate = DataIntegrityGate()

    def _load_or_init_clock(self, manifest: CampaignFreezeManifest) -> ShadowValidationClock:
        """Carga o inicializa el reloj de validación forward para una estrategia."""
        clock_file = self.storage_dir / f"validation_clock_{manifest.strategy_id}.json"
        if clock_file.exists():
            with open(clock_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ShadowValidationClock(**data)

        clock = ShadowValidationClock(
            strategy_id=manifest.strategy_id,
            t0_timestamp_utc=manifest.t0_timestamp_utc,
            t0_market_session=manifest.t0_first_prospective_session
        )
        self._save_clock(clock)
        return clock

    def _save_clock(self, clock: ShadowValidationClock):
        """Persiste atómicamente el reloj de validación en disco."""
        clock_file = self.storage_dir / f"validation_clock_{clock.strategy_id}.json"
        with open(clock_file, "w", encoding="utf-8") as f:
            f.write(clock.model_dump_json(indent=2))

    def _compute_bar_hash(self, bar: OHLCVBar) -> str:
        """Calcula el hash criptográfico SHA-256 de una barra cerrada."""
        raw = f"{bar.symbol}:{bar.timestamp}:{bar.open}:{bar.high}:{bar.low}:{bar.close}:{bar.volume}".encode('utf-8')
        return hashlib.sha256(raw).hexdigest()

    def evaluate_market_session(
        self,
        session_date: str,
        bars_by_symbol: Dict[str, List[OHLCVBar]],
        open_prices_next_session: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta la evaluación formal de una sesión bursátil cerrada T:
        1. Comprueba integridad de datos y rechaza barras no cerradas o anteriores a T0.
        2. Procesa salidas de posiciones abiertas basadas en la barra actual.
        3. Procesa aperturas pendientes de la sesión anterior (si se proporcionan open_prices).
        4. Evalúa las señales para Candidate A y Candidate B.
        5. Encola órdenes para apertura de T+1 si hay señal.
        6. Registra cada decisión en el ledger inmutable.
        7. Actualiza contadores del reloj forward e hitos.
        """
        eval_time_utc = datetime.utcnow().isoformat()
        results = {
            "session_date": session_date,
            "evaluated_at_utc": eval_time_utc,
            "candidate_a": {"signals": [], "orders": [], "exits": []},
            "candidate_b": {"signals": [], "orders": [], "exits": []},
            "data_quality_ok": True
        }

        # 1. Comprobar que todas las series tengan barras cerradas válidas
        current_bars: Dict[str, OHLCVBar] = {}
        for sym in self.manifest_a.universe_symbols:
            if sym not in bars_by_symbol or not bars_by_symbol[sym]:
                results["data_quality_ok"] = False
                self.clock_a.data_quality_failures += 1
                self.clock_b.data_quality_failures += 1
                return results

            clean_bars, meta = self.gate.sanitize_and_validate_bars(sym, bars_by_symbol[sym])
            if not clean_bars:
                results["data_quality_ok"] = False
                return results
            current_bars[sym] = clean_bars[-1]

        # 2. Si hay precios de apertura de la sesión actual, procesar fills pendientes primero
        # (ejecución en la apertura de la sesión)
        open_prices = {s: current_bars[s].open for s in current_bars}
        fills_a = self.simulator_a.process_session_open_fills(session_date, open_prices)
        for fill_rec, pos in fills_a:
            self.clock_a.shadow_positions_opened += 1
            bar_h = self._compute_bar_hash(current_bars[fill_rec["symbol"]])
            self.ledger_a.append_entry(
                entry_id=f"ENTRY-FILL-{self.manifest_a.strategy_id}-{fill_rec['symbol']}-{session_date}",
                market_date=session_date,
                symbol=fill_rec["symbol"],
                event_type=ShadowEventType.ORDER_FILLED,
                signal_direction="BUY",
                reason=f"Apertura ejecutada en T+1 a ${fill_rec['fill_price']:.2f} con slippage y comisiones",
                strategy_fingerprint=self.manifest_a.combined_strategy_fingerprint_sha256,
                bar_hash=bar_h,
                simulated_fill=fill_rec,
                open_position=pos.model_dump(),
                portfolio_cash=self.simulator_a.current_cash,
                portfolio_equity=self.simulator_a.portfolio_equity,
                drawdown_pct=self.simulator_a.max_drawdown_pct,
                timestamp_utc=eval_time_utc
            )

        fills_b = self.simulator_b.process_session_open_fills(session_date, open_prices)
        for fill_rec, pos in fills_b:
            self.clock_b.shadow_positions_opened += 1
            bar_h = self._compute_bar_hash(current_bars[fill_rec["symbol"]])
            self.ledger_b.append_entry(
                entry_id=f"ENTRY-FILL-{self.manifest_b.strategy_id}-{fill_rec['symbol']}-{session_date}",
                market_date=session_date,
                symbol=fill_rec["symbol"],
                event_type=ShadowEventType.ORDER_FILLED,
                signal_direction="BUY",
                reason=f"Apertura ejecutada en T+1 a ${fill_rec['fill_price']:.2f} con slippage y comisiones",
                strategy_fingerprint=self.manifest_b.combined_strategy_fingerprint_sha256,
                bar_hash=bar_h,
                simulated_fill=fill_rec,
                open_position=pos.model_dump(),
                portfolio_cash=self.simulator_b.current_cash,
                portfolio_equity=self.simulator_b.portfolio_equity,
                drawdown_pct=self.simulator_b.max_drawdown_pct,
                timestamp_utc=eval_time_utc
            )

        # 3. Evaluar salidas de posiciones abiertas al cierre de la sesión
        exits_a = self.simulator_a.process_session_close_and_exits(session_date, current_bars)
        for exit_rec, pos in exits_a:
            self.clock_a.shadow_positions_closed += 1
            bar_h = self._compute_bar_hash(current_bars[exit_rec["symbol"]])
            self.ledger_a.append_entry(
                entry_id=f"EXIT-FILL-{self.manifest_a.strategy_id}-{exit_rec['symbol']}-{session_date}",
                market_date=session_date,
                symbol=exit_rec["symbol"],
                event_type=ShadowEventType.POSITION_CLOSED,
                signal_direction="SELL",
                reason=f"Salida {exit_rec['exit_reason']} a ${exit_rec['exit_fill_price']:.2f}. Net PnL: ${exit_rec['true_net_pnl']:.2f}",
                strategy_fingerprint=self.manifest_a.combined_strategy_fingerprint_sha256,
                bar_hash=bar_h,
                simulated_fill=exit_rec,
                open_position=pos.model_dump(),
                realized_gross_pnl=exit_rec["true_gross_pnl"],
                realized_net_pnl=exit_rec["true_net_pnl"],
                costs_usd=exit_rec["total_costs_usd"],
                portfolio_cash=self.simulator_a.current_cash,
                portfolio_equity=self.simulator_a.portfolio_equity,
                drawdown_pct=self.simulator_a.max_drawdown_pct,
                timestamp_utc=eval_time_utc
            )
            results["candidate_a"]["exits"].append(exit_rec)

        exits_b = self.simulator_b.process_session_close_and_exits(session_date, current_bars)
        for exit_rec, pos in exits_b:
            self.clock_b.shadow_positions_closed += 1
            bar_h = self._compute_bar_hash(current_bars[exit_rec["symbol"]])
            self.ledger_b.append_entry(
                entry_id=f"EXIT-FILL-{self.manifest_b.strategy_id}-{exit_rec['symbol']}-{session_date}",
                market_date=session_date,
                symbol=exit_rec["symbol"],
                event_type=ShadowEventType.POSITION_CLOSED,
                signal_direction="SELL",
                reason=f"Salida {exit_rec['exit_reason']} a ${exit_rec['exit_fill_price']:.2f}. Net PnL: ${exit_rec['true_net_pnl']:.2f}",
                strategy_fingerprint=self.manifest_b.combined_strategy_fingerprint_sha256,
                bar_hash=bar_h,
                simulated_fill=exit_rec,
                open_position=pos.model_dump(),
                realized_gross_pnl=exit_rec["true_gross_pnl"],
                realized_net_pnl=exit_rec["true_net_pnl"],
                costs_usd=exit_rec["total_costs_usd"],
                portfolio_cash=self.simulator_b.current_cash,
                portfolio_equity=self.simulator_b.portfolio_equity,
                drawdown_pct=self.simulator_b.max_drawdown_pct,
                timestamp_utc=eval_time_utc
            )
            results["candidate_b"]["exits"].append(exit_rec)

        # 4. Generación de Señales de la Sesión T
        # Candidate A: MR_VolCond_ZScore_V1 (Single Asset evaluations)
        params_a = self.manifest_a.parameters_frozen
        for sym in self.manifest_a.universe_symbols:
            series = bars_by_symbol[sym]
            bar = current_bars[sym]
            bar_h = self._compute_bar_hash(bar)

            signals = generate_signals_MR_VolCond_ZScore_V1(
                series,
                z_lookback=params_a["z_lookback"],
                z_threshold=params_a["z_threshold"],
                atr_period=params_a["atr_period"],
                atr_expansion_mult=params_a["atr_expansion_mult"]
            )
            has_signal = signals[-1] if signals else False

            if has_signal:
                self.clock_a.shadow_signals_generated += 1
                reason_txt = f"Señal de sobreventa extrema Z-Score <= {params_a['z_threshold']} con expansión de volatilidad"
                order = self.simulator_a.queue_entry_signal(
                    signal_date=session_date,
                    symbol=sym,
                    signal_close_price=bar.close,
                    stop_loss_pct=params_a["stop_loss_pct"],
                    profit_target_pct=params_a["profit_target_pct"],
                    max_holding_bars=params_a["max_holding"],
                    reason=reason_txt
                )
                self.ledger_a.append_entry(
                    entry_id=f"EVAL-SIG-{self.manifest_a.strategy_id}-{sym}-{session_date}",
                    market_date=session_date,
                    symbol=sym,
                    event_type=ShadowEventType.SIGNAL_GENERATED,
                    signal_direction="BUY",
                    reason=reason_txt,
                    strategy_fingerprint=self.manifest_a.combined_strategy_fingerprint_sha256,
                    bar_hash=bar_h,
                    simulated_order=order,
                    portfolio_cash=self.simulator_a.current_cash,
                    portfolio_equity=self.simulator_a.portfolio_equity,
                    drawdown_pct=self.simulator_a.max_drawdown_pct,
                    timestamp_utc=eval_time_utc
                )
                results["candidate_a"]["signals"].append({"symbol": sym, "close": bar.close, "order": order})
            else:
                # Registrar explícitamente día sin señal (mandato Bloque C/E)
                self.ledger_a.append_entry(
                    entry_id=f"EVAL-NOSIG-{self.manifest_a.strategy_id}-{sym}-{session_date}",
                    market_date=session_date,
                    symbol=sym,
                    event_type=ShadowEventType.NO_SIGNAL,
                    signal_direction="NO_TRADE",
                    reason="Condición de sobreventa o expansión no alcanzada (No-Trade)",
                    strategy_fingerprint=self.manifest_a.combined_strategy_fingerprint_sha256,
                    bar_hash=bar_h,
                    portfolio_cash=self.simulator_a.current_cash,
                    portfolio_equity=self.simulator_a.portfolio_equity,
                    drawdown_pct=self.simulator_a.max_drawdown_pct,
                    timestamp_utc=eval_time_utc
                )

        # Candidate B: CS_RelMom_VolAdj_V2 (Cross Sectional)
        params_b = self.manifest_b.parameters_frozen
        signals_map_b = generate_signals_CS_RelMom_VolAdj_V2(
            bars_by_symbol,
            rebalance_period=params_b["rebalance_period"],
            momentum_lookback=params_b["momentum_lookback"]
        )

        for sym in self.manifest_b.universe_symbols:
            bar = current_bars[sym]
            bar_h = self._compute_bar_hash(bar)
            has_signal_b = signals_map_b[sym][-1] if (sym in signals_map_b and signals_map_b[sym]) else False

            if has_signal_b:
                self.clock_b.shadow_signals_generated += 1
                reason_b = "Activo seleccionado en Top 2 Sharpe-Momentum a 60 días"
                order_b = self.simulator_b.queue_entry_signal(
                    signal_date=session_date,
                    symbol=sym,
                    signal_close_price=bar.close,
                    stop_loss_pct=params_b["stop_loss_pct"],
                    profit_target_pct=params_b["profit_target_pct"],
                    max_holding_bars=params_b["max_holding"],
                    reason=reason_b
                )
                self.ledger_b.append_entry(
                    entry_id=f"EVAL-SIG-{self.manifest_b.strategy_id}-{sym}-{session_date}",
                    market_date=session_date,
                    symbol=sym,
                    event_type=ShadowEventType.SIGNAL_GENERATED,
                    signal_direction="BUY",
                    reason=reason_b,
                    strategy_fingerprint=self.manifest_b.combined_strategy_fingerprint_sha256,
                    bar_hash=bar_h,
                    simulated_order=order_b,
                    portfolio_cash=self.simulator_b.current_cash,
                    portfolio_equity=self.simulator_b.portfolio_equity,
                    drawdown_pct=self.simulator_b.max_drawdown_pct,
                    timestamp_utc=eval_time_utc
                )
                results["candidate_b"]["signals"].append({"symbol": sym, "close": bar.close, "order": order_b})
            else:
                self.ledger_b.append_entry(
                    entry_id=f"EVAL-NOSIG-{self.manifest_b.strategy_id}-{sym}-{session_date}",
                    market_date=session_date,
                    symbol=sym,
                    event_type=ShadowEventType.NO_SIGNAL,
                    signal_direction="NO_TRADE",
                    reason="Fuera de ventana de rebalanceo o activo no clasificado en Top 2",
                    strategy_fingerprint=self.manifest_b.combined_strategy_fingerprint_sha256,
                    bar_hash=bar_h,
                    portfolio_cash=self.simulator_b.current_cash,
                    portfolio_equity=self.simulator_b.portfolio_equity,
                    drawdown_pct=self.simulator_b.max_drawdown_pct,
                    timestamp_utc=eval_time_utc
                )

        # 5. Actualizar Relojes e Hitos de Validación Forward
        self._update_clock_progress(self.clock_a, session_date, eval_time_utc)
        self._update_clock_progress(self.clock_b, session_date, eval_time_utc)

        self._save_clock(self.clock_a)
        self._save_clock(self.clock_b)

        return results

    def _update_clock_progress(self, clock: ShadowValidationClock, session_date: str, eval_time_utc: str):
        """Actualiza sesiones acumuladas y evalúa hitos institucionales (20, 60, 90 sesiones)."""
        clock.valid_shadow_evaluation_sessions += 1
        clock.market_sessions_elapsed += 1
        clock.last_evaluated_session = session_date
        clock.last_evaluated_at_utc = eval_time_utc

        # Calcular días calendario transcurridos desde T0
        try:
            d0 = datetime.fromisoformat(clock.t0_timestamp_utc.replace("Z", "+00:00")).date()
            d_cur = datetime.strptime(session_date, "%Y-%m-%d").date()
            clock.calendar_days_since_t0 = max(0, (d_cur - d0).days)
        except Exception:
            clock.calendar_days_since_t0 += 1

        # Hitos de validación (Bloque F)
        if clock.valid_shadow_evaluation_sessions >= 20 and not clock.milestone_20_sessions_reached:
            clock.milestone_20_sessions_reached = True
        if clock.valid_shadow_evaluation_sessions >= 60 and not clock.milestone_60_sessions_reached:
            clock.milestone_60_sessions_reached = True
        if clock.valid_shadow_evaluation_sessions >= 90 and not clock.milestone_90_sessions_reached:
            clock.milestone_90_sessions_reached = True

    def get_status_summary(self) -> Dict[str, Any]:
        """Devuelve el estado consolidado de la campaña Shadow para reporting."""
        return {
            "mode": "RESEARCH / ANALYSIS_ONLY",
            "campaign_status": "COLLECTING_EVIDENCE",
            "t0_first_prospective_session": self.manifest_a.t0_first_prospective_session,
            "cost_scenario": self.cost_scenario.value,
            "broker_isolation": "AIR_GAPPED_100_PERCENT",
            "d21_operational_mode": "Moomoo PAPER (TrdEnv.SIMULATE)",
            "candidate_a": {
                "strategy_id": self.manifest_a.strategy_id,
                "fingerprint": self.manifest_a.combined_strategy_fingerprint_sha256[:16],
                "clock": self.clock_a.model_dump(),
                "metrics": self.simulator_a.get_summary_metrics(),
                "ledger_entries_count": self.ledger_a.get_entry_count(),
                "ledger_head_hash": self.ledger_a.get_latest_hash()[:16]
            },
            "candidate_b": {
                "strategy_id": self.manifest_b.strategy_id,
                "fingerprint": self.manifest_b.combined_strategy_fingerprint_sha256[:16],
                "clock": self.clock_b.model_dump(),
                "metrics": self.simulator_b.get_summary_metrics(),
                "ledger_entries_count": self.ledger_b.get_entry_count(),
                "ledger_head_hash": self.ledger_b.get_latest_hash()[:16]
            }
        }
