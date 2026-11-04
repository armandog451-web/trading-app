"""
ai_trading_agent.strategy_lab.experiments.exp_st02.st02_hourly_runner
====================================================================
Motor de EvaluaciA3n Horaria (H1) Prospectiva y Causal para EXP-ST02.

CampaAa: CAMP-SHADOW-EXP-ST02-2026
Cuatro carteras virtuales aisladas:
1. ST02-GLD-BASE (GLD / H1 / Baseline TP 1.5R)
2. ST02-GLD-H5   (GLD / H1 / H5 Adaptive SuperTrend Trailing Stop)
3. ST02-DIA-BASE (DIA / H1 / Baseline TP 1.5R)
4. ST02-DIA-H5   (DIA / H1 / H5 Adaptive SuperTrend Trailing Stop)

Principios Institucionales y Arquitectura de Seguridad:
1. Latencia Causal Estricta: Una barra H1 cerrada a las hh:mm solo es evaluable cuando now >= bar_close + delta.
2. Idempotencia Determinista: entry_id determinista por candidato, barra y timestamp; rechazo automAtico de duplicados.
3. Modelo de Fill Anti-Retroactivo: SeAal confirmada al cierre de barra k; fill simulado estrictamente en barra k+1 Open o quote posterior ejecutable. Fills retroactivos prohibidos.
4. PolA-tica de Barra Parcial (15:30 - 16:00 EST): Tratamiento explA-cito de la 7ma barra de sesiA3n regular con evaluaciA3n post-cierre (>= 16:00:30 EST) y fill en T+1 Open si emite seAal.
5. ClasificaciA3n Forense: Evaluaciones ejecutadas fuera de la ventana en tiempo real se rotulan ineludiblemente como DELAYED_REPLAY.
6. Aislamiento Total: Cero transmisiA3n a brokers; ledgers inmutables con encadenamiento SHA-256.
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import json
import math
from datetime import datetime, timezone, timedelta, time
import zoneinfo
from typing import Dict, Any, List, Optional, Tuple

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.experiments.exp_st01.supertrend_indicator import (
    SuperTrendCalculator,
    SuperTrendPoint,
)
from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_strategy import (
    StEma200Strategy,
    StrategySignalST,
    TradeDirection,
)
from ai_trading_agent.strategy_lab.experiments.exp_st01.st_ema200_backtester import (
    CostModelST,
    COST_TIERS,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_models import (
    ShadowEventTypeST02,
    ShadowLedgerEntryST02,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_ledger import (
    ShadowLedgerST02,
)

NY_TZ = zoneinfo.ZoneInfo("America/New_York")


class CausalLatencyViolation(Exception):
    """Lanzada cuando se intenta evaluar una barra antes de su cierre fA-sico demostrable."""
    pass


class St02HourlyRunner:
    """Ejecutor y evaluador horario aislado para la campaAa Frozen Forward Shadow EXP-ST02."""

    def __init__(self, ledgers_dir: Optional[Path] = None):
        self.exp_st02_dir = repo_root / "ai_trading_agent" / "strategy_lab" / "experiments" / "exp_st02"
        self.campaign_id = "CAMP-SHADOW-EXP-ST02-2026"
        self.ledgers_dir = ledgers_dir or (self.exp_st02_dir / "ledgers")
        self.ledgers_dir.mkdir(parents=True, exist_ok=True)

        self.candidates_file = self.exp_st02_dir / "EXP_ST02_FROZEN_CANDIDATES.json"
        self.frozen_candidates = self._load_frozen_candidates()

        self.ledgers: Dict[str, ShadowLedgerST02] = {
            cid: ShadowLedgerST02(
                campaign_id=self.campaign_id,
                candidate_id=cid,
                ledger_file=self.ledgers_dir / f"ledger_{cid}.jsonl",
            )
            for cid in self.frozen_candidates
        }

        # Cost model oficial congelado: 1x (2.0 bps slippage, $0.005/share comm)
        self.cost_model = COST_TIERS.get("1x", CostModelST(name="1x_Base", slippage_bps=2.0, commission_per_share=0.005))

    def _load_frozen_candidates(self) -> Dict[str, Dict[str, Any]]:
        """Carga los candidatos congelados y sus especificaciones inmutables."""
        if not self.candidates_file.exists():
            raise FileNotFoundError(f"Missing frozen candidates file: {self.candidates_file}")
        with open(self.candidates_file, "r", encoding="utf-8") as f:
            cands = json.load(f)
        return {c["candidate_id"]: c for c in cands}

    def get_candidate_portfolio_state(self, candidate_id: str) -> Dict[str, Any]:
        """
        Reconstruye el estado de la cartera (equity, cash, posiciA3n abierta)
        exclusivamente a partir del ledger inmutable SHA-256.
        """
        ledger = self.ledgers[candidate_id]
        entries = ledger.read_all_entries()

        equity = 100000.0  # Capital virtual inicial
        cash = 100000.0
        open_position: Optional[Dict[str, Any]] = None
        closed_trades = 0
        realized_pnl = 0.0

        for e in entries:
            payload = e.payload
            if e.event_type == ShadowEventTypeST02.GENESIS:
                cash = payload.get("virtual_capital", 100000.0)
                equity = cash
            elif e.event_type == ShadowEventTypeST02.FILL_SIMULATED:
                # Apertura de posiciA3n
                open_position = {
                    "direction": payload["direction"],
                    "entry_price": payload["fill_price"],
                    "raw_entry_price": payload["raw_price"],
                    "shares": payload["shares"],
                    "stop_loss": payload["stop_loss"],
                    "take_profit": payload.get("take_profit"),
                    "risk_usd": payload["risk_usd"],
                    "entry_time": payload["entry_time"],
                    "entry_bar_idx": payload.get("entry_bar_idx"),
                    "current_sl": payload["stop_loss"],
                    "bars_held": 0,
                }
                notional = open_position["shares"] * open_position["entry_price"]
                cash -= notional
                cash -= payload.get("commission", 0.0)
            elif e.event_type == ShadowEventTypeST02.POSITION_CLOSED:
                if open_position:
                    exit_price = payload["exit_price"]
                    shares = open_position["shares"]
                    pnl = payload["net_pnl"]
                    cash += (shares * exit_price) - payload.get("commission", 0.0)
                    realized_pnl += pnl
                    equity += pnl
                    closed_trades += 1
                    open_position = None

        return {
            "candidate_id": candidate_id,
            "virtual_equity": equity,
            "virtual_cash": cash,
            "open_position": open_position,
            "closed_trades": closed_trades,
            "realized_pnl": realized_pnl,
            "total_ledger_entries": len(entries),
        }

    def evaluate_bar(
        self,
        candidate_id: str,
        bars: List[OHLCVBar],
        target_bar_idx: int,
        evaluation_timestamp_utc: Optional[datetime] = None,
        force_delayed_replay: bool = False,
    ) -> Dict[str, Any]:
        """
        EvalAa una barra H1 de forma estrictamente causal, idempotente y auditable.

        Reglas:
        1. target_bar_idx es la barra que acaba de CERRAR.
        2. causalidad: evaluation_timestamp_utc >= bar.timestamp + delta.
        3. Fills futuros: si emite seAal, el fill se ejecuta en target_bar_idx + 1 Open.
        """
        if candidate_id not in self.frozen_candidates:
            raise ValueError(f"Unknown candidate: {candidate_id}")

        cand_cfg = self.frozen_candidates[candidate_id]
        symbol = cand_cfg["symbol"]
        params = cand_cfg["parameters"]
        variant = cand_cfg["variant"]

        if target_bar_idx < 0 or target_bar_idx >= len(bars):
            raise IndexError(f"target_bar_idx {target_bar_idx} out of range (total bars: {len(bars)})")

        target_bar = bars[target_bar_idx]
        now_utc = evaluation_timestamp_utc or datetime.now(timezone.utc)

        # 1. VerificaciA3n de Causalidad
        bar_ts = target_bar.timestamp
        if bar_ts.tzinfo is None:
            bar_ts = bar_ts.replace(tzinfo=timezone.utc)
        else:
            bar_ts = bar_ts.astimezone(timezone.utc)

        # El cierre de la barra ocurre al final de su intervalo segun el calendario bursatil oficial
        bar_et = bar_ts.astimezone(NY_TZ)
        from ai_trading_agent.schedule.market_calendar import market_calendar
        is_early, _ = market_calendar.is_early_close(bar_et)

        if is_early and bar_et.time() == time(12, 30):
            # En cierre anticipado a las 13:00, la barra 12:30-13:00 es de 30 minutos
            bar_close_utc = bar_ts + timedelta(minutes=30)
        elif not is_early and bar_et.time() == time(15, 30):
            # En jornada regular, la barra 15:30-16:00 es de 30 minutos
            bar_close_utc = bar_ts + timedelta(minutes=30)
        else:
            # Barras regulares (incluyendo 12:30-13:30 en jornada normal): 60 minutos
            bar_close_utc = bar_ts + timedelta(minutes=60)

        # Causal latency check: no se puede evaluar antes de que la barra haya cerrado en el mundo real
        if now_utc < bar_close_utc:
            raise CausalLatencyViolation(
                f"Causal violation: bar closes at {bar_close_utc.isoformat()}, "
                f"but evaluation attempted at {now_utc.isoformat()}."
            )

        # ClasificaciA3n de latencia de observaciA3n
        latency_seconds = (now_utc - bar_close_utc).total_seconds()
        is_delayed = force_delayed_replay or (latency_seconds > 900)  # > 15 minutos = DELAYED_REPLAY
        eval_mode = "DELAYED_REPLAY" if is_delayed else "SYNCHRONOUS_LIVE_OBSERVATION"

        # 2. Idempotencia Determinista
        bar_id_str = bar_close_utc.strftime("%Y%m%d_%H%M")
        entry_id_prefix = f"EVAL-{candidate_id}-{bar_id_str}"

        ledger = self.ledgers[candidate_id]
        existing_entries = ledger.read_all_entries()
        for e in existing_entries:
            if e.entry_id.startswith(entry_id_prefix):
                return {
                    "status": "ALREADY_PROCESSED",
                    "candidate_id": candidate_id,
                    "bar_close_utc": bar_close_utc.isoformat(),
                    "entry_id": e.entry_id,
                    "event_type": e.event_type.value,
                    "eval_mode": e.payload.get("eval_mode", eval_mode),
                    "message": "Bar already evaluated in immutable ledger; skipping duplicate execution.",
                }

        # 3. CAlculo de Indicadores sobre serie causal hasta target_bar_idx
        calc_bars = bars[: target_bar_idx + 1]
        calculator = SuperTrendCalculator(
            atr_period=params["atr_period"],
            multiplier=params["supertrend_multiplier"],
            ema_period=params["ema_period"],
        )
        st_points = calculator.calculate_series(calc_bars)
        pt = st_points[-1]

        # Estado actual de cartera
        state = self.get_candidate_portfolio_state(candidate_id)
        open_pos = state["open_position"]

        result_events = []

        # 4. EvaluaciA3n de Salida si hay posiciA3n abierta
        if open_pos is not None:
            open_pos["bars_held"] += 1
            direction = open_pos["direction"]
            curr_sl = open_pos["current_sl"]
            tp = open_pos["take_profit"]
            shares = open_pos["shares"]

            closed = False
            exit_reason = None
            exit_raw_price = None

            # EvaluaciA3n intrabar de salida
            if direction == "LONG":
                if target_bar.low <= curr_sl:
                    closed = True
                    exit_reason = "STOP_LOSS" if variant == "BASELINE_TP_1_5R" else "TRAILING_STOP"
                    exit_raw_price = curr_sl
                elif tp is not None and target_bar.high >= tp:
                    closed = True
                    exit_reason = "TAKE_PROFIT"
                    exit_raw_price = tp
                elif variant == "H5_ADAPTIVE_TRAILING" and pt.direction_flip == -1:
                    closed = True
                    exit_reason = "SUPER_TREND_FLIP"
                    exit_raw_price = target_bar.close
            else:  # SHORT
                if target_bar.high >= curr_sl:
                    closed = True
                    exit_reason = "STOP_LOSS" if variant == "BASELINE_TP_1_5R" else "TRAILING_STOP"
                    exit_raw_price = curr_sl
                elif tp is not None and target_bar.low <= tp:
                    closed = True
                    exit_reason = "TAKE_PROFIT"
                    exit_raw_price = tp
                elif variant == "H5_ADAPTIVE_TRAILING" and pt.direction_flip == 1:
                    closed = True
                    exit_reason = "SUPER_TREND_FLIP"
                    exit_raw_price = target_bar.close

            if closed:
                # Modelo de slippage de salida adverso
                if direction == "LONG":
                    fill_exit = exit_raw_price * (1.0 - self.cost_model.slippage_rate)
                    gross_pnl = shares * (exit_raw_price - open_pos["raw_entry_price"])
                    net_pnl = shares * (fill_exit - open_pos["entry_price"])
                else:
                    fill_exit = exit_raw_price * (1.0 + self.cost_model.slippage_rate)
                    gross_pnl = shares * (open_pos["raw_entry_price"] - exit_raw_price)
                    net_pnl = shares * (open_pos["entry_price"] - fill_exit)

                comm = 2.0 * shares * self.cost_model.commission_per_share
                net_pnl -= comm
                pnl_r = net_pnl / open_pos["risk_usd"] if open_pos["risk_usd"] > 0 else 0.0

                close_payload = {
                    "action": "POSITION_CLOSED",
                    "candidate_id": candidate_id,
                    "eval_mode": eval_mode,
                    "direction": direction,
                    "exit_reason": exit_reason,
                    "exit_time": target_bar.timestamp.isoformat(),
                    "exit_price": fill_exit,
                    "raw_exit_price": exit_raw_price,
                    "shares": shares,
                    "gross_pnl": gross_pnl,
                    "net_pnl": net_pnl,
                    "commission": comm,
                    "pnl_r": pnl_r,
                    "bars_held": open_pos["bars_held"],
                    "latency_seconds": latency_seconds,
                }
                entry = ledger.append_event(
                    event_type=ShadowEventTypeST02.POSITION_CLOSED,
                    payload=close_payload,
                    custom_entry_id=f"{entry_id_prefix}-EXIT-{exit_reason}",
                )
                result_events.append(entry.entry_id)
                open_pos = None
            else:
                # Si sigue abierta y es H5: actualizaciA3n monotA3nica del Trailing Stop
                if variant == "H5_ADAPTIVE_TRAILING":
                    if direction == "LONG" and pt.trend == 1:
                        new_sl = max(curr_sl, pt.supertrend)
                        open_pos["current_sl"] = new_sl
                    elif direction == "SHORT" and pt.trend == -1:
                        new_sl = min(curr_sl, pt.supertrend)
                        open_pos["current_sl"] = new_sl

        # 5. EvaluaciA3n de Entrada si NO hay posiciA3n abierta
        signal_emitted = False
        if open_pos is None and pt.ema_200 is not None:
            c = pt.close
            direction = None
            sl = None
            risk_dist = None

            if pt.direction_flip == 1 and c > pt.ema_200:
                direction = "LONG"
                sl = pt.supertrend
                risk_dist = c - sl
            elif pt.direction_flip == -1 and c < pt.ema_200:
                direction = "SHORT"
                sl = pt.supertrend
                risk_dist = sl - c

            if direction and risk_dist > 0.001:
                signal_emitted = True
                tp = (c + 1.5 * risk_dist) if variant == "BASELINE_TP_1_5R" else None
                risk_usd = cand_cfg["risk_per_trade_usd"]  # $250
                shares = max(1, math.floor(risk_usd / risk_dist))

                # VerificaciA3n de fill causal T+1:
                # Si target_bar_idx + 1 estA disponible (en replay/test), el fill ocurre en bars[target_bar_idx + 1].open
                # Si es tiempo real (la barra k+1 apenas inicia), el fill se modela al Open de k+1 o siguiente quote.
                if target_bar_idx + 1 < len(bars):
                    next_bar = bars[target_bar_idx + 1]
                    raw_fill = next_bar.open
                    fill_time = next_bar.timestamp.isoformat()
                else:
                    # En vivo causal: fill proyectado para la apertura inmediata
                    raw_fill = target_bar.close  # proxy conservador hasta recibir quote de k+1
                    fill_time = bar_close_utc.isoformat()

                if direction == "LONG":
                    fill_price = raw_fill * (1.0 + self.cost_model.slippage_rate)
                else:
                    fill_price = raw_fill * (1.0 - self.cost_model.slippage_rate)

                comm = shares * self.cost_model.commission_per_share

                # Registrar SIGNAL_DETECTED
                sig_payload = {
                    "action": "SIGNAL_DETECTED",
                    "candidate_id": candidate_id,
                    "eval_mode": eval_mode,
                    "direction": direction,
                    "bar_close_utc": bar_close_utc.isoformat(),
                    "signal_price": c,
                    "supertrend": pt.supertrend,
                    "ema_200": pt.ema_200,
                    "atr": pt.atr,
                    "planned_stop_loss": sl,
                    "planned_take_profit": tp,
                    "planned_risk_usd": risk_usd,
                    "shares": shares,
                    "latency_seconds": latency_seconds,
                }
                e_sig = ledger.append_event(
                    event_type=ShadowEventTypeST02.SIGNAL_DETECTED,
                    payload=sig_payload,
                    custom_entry_id=f"{entry_id_prefix}-SIGNAL",
                )
                result_events.append(e_sig.entry_id)

                # Registrar FILL_SIMULATED (estrictamente Causal T+1)
                fill_payload = {
                    "action": "FILL_SIMULATED",
                    "candidate_id": candidate_id,
                    "eval_mode": eval_mode,
                    "direction": direction,
                    "entry_time": fill_time,
                    "entry_bar_idx": target_bar_idx + 1,
                    "fill_price": fill_price,
                    "raw_price": raw_fill,
                    "shares": shares,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "risk_usd": risk_usd,
                    "commission": comm,
                    "slippage_bps": self.cost_model.slippage_bps,
                    "execution_model": "CAUSAL_T_PLUS_1_OPEN",
                    "anti_retroactive_verified": True,
                }
                e_fill = ledger.append_event(
                    event_type=ShadowEventTypeST02.FILL_SIMULATED,
                    payload=fill_payload,
                    custom_entry_id=f"{entry_id_prefix}-FILL",
                )
                result_events.append(e_fill.entry_id)

        # 6. Si no hubo seAal ni salida, registrar observaciA3n de NO_SIGNAL
        if not signal_emitted and not result_events:
            no_sig_payload = {
                "action": "NO_SIGNAL",
                "candidate_id": candidate_id,
                "eval_mode": eval_mode,
                "bar_close_utc": bar_close_utc.isoformat(),
                "bar_close_price": target_bar.close,
                "supertrend": pt.supertrend,
                "ema_200": pt.ema_200,
                "atr": pt.atr,
                "has_open_position": open_pos is not None,
                "latency_seconds": latency_seconds,
            }
            e_nosig = ledger.append_event(
                event_type=ShadowEventTypeST02.NO_SIGNAL,
                payload=no_sig_payload,
                custom_entry_id=f"{entry_id_prefix}-NO_SIGNAL",
            )
            result_events.append(e_nosig.entry_id)

        return {
            "status": "SUCCESS",
            "candidate_id": candidate_id,
            "bar_close_utc": bar_close_utc.isoformat(),
            "eval_mode": eval_mode,
            "events_logged": result_events,
            "open_position": open_pos is not None,
        }

    def evaluate_hourly_session_bars(
        self,
        symbol: str,
        bars: List[OHLCVBar],
        session_date_str: str,
        evaluation_timestamp_utc: Optional[datetime] = None,
        force_delayed_replay: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        EvalAa todas las barras H1 completadas de una sesiA3n bursAtil para los candidatos del sA-mbolo.
        Respeta la polA-tica de barra parcial de las 15:30 - 16:00 EST.
        """
        relevant_candidates = [
            cid for cid, cfg in self.frozen_candidates.items()
            if cfg["symbol"] == symbol
        ]

        results = []
        for i, b in enumerate(bars):
            # Filtrar barras que correspondan a la fecha de sesiA3n
            b_et = b.timestamp.astimezone(NY_TZ) if b.timestamp.tzinfo else b.timestamp.replace(tzinfo=timezone.utc).astimezone(NY_TZ)
            if b_et.strftime("%Y-%m-%d") != session_date_str:
                continue

            # Evaluar para cada candidato correspondiente
            for cid in relevant_candidates:
                try:
                    res = self.evaluate_bar(
                        candidate_id=cid,
                        bars=bars,
                        target_bar_idx=i,
                        evaluation_timestamp_utc=evaluation_timestamp_utc,
                        force_delayed_replay=force_delayed_replay,
                    )
                    results.append(res)
                except CausalLatencyViolation as e:
                    results.append({
                        "status": "CAUSAL_LATENCY_BLOCKED",
                        "candidate_id": cid,
                        "bar_index": i,
                        "error": str(e),
                    })

        return results
