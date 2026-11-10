"""
ai_trading_agent.strategy_lab.experiments.exp_st02.run_st02_service
===================================================================
Servicio autónomo y desacoplado para la campaña Forward Shadow EXP-ST02.
Campaña: CAMP-SHADOW-EXP-ST02-2026

Principios de Diseño:
1. Desacoplamiento total: No depende del scheduler central ni de FastAPI.
2. Cuatro carteras virtuales aisladas (GLD BASE/H5, DIA BASE/H5).
3. Calendario NYSE estricto: 7 ciclos en jornada regular, 4 ciclos en cierre anticipado, 0 en festivos.
4. Causalidad estricta: Una barra solo se evalúa tras su cierre físico + delta (90s).
5. Aislamiento total: Cero conexiones o envíos de órdenes a brokers (LIVE o PAPER).
6. Idempotencia y encadenamiento SHA-256 en libros contables JSONL.
7. Control atómico de instancia mediante PID lockfile y Kill-Switch cooperativo.
8. Política anti-retroactiva: Barras no observadas en su ventana temporal se clasifican como LATE_START_SKIPPED.
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
from pathlib import Path
from datetime import datetime, date, time as dt_time, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
import zoneinfo

# Asegurar path al repo root
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dotenv import load_dotenv
load_dotenv(repo_root / ".env")

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.data.providers.yfinance_provider import YFinanceMarketDataProvider
from ai_trading_agent.schedule.market_calendar import MarketCalendarService
from ai_trading_agent.strategy_lab.experiments.exp_st02.st02_hourly_runner import (
    St02HourlyRunner,
    CausalLatencyViolation,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_ledger import (
    ShadowLedgerST02,
    GENESIS_PREV_HASH,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_models import (
    ShadowEventTypeST02,
)
from ai_trading_agent.strategy_lab.experiments.exp_st02.st02_telegram_notifier import (
    St02TelegramNotifier,
)

NY_TZ = zoneinfo.ZoneInfo("America/New_York")

ACTIVE_PORTFOLIOS = [
    "ST02-GLD-BASE",
    "ST02-GLD-H5",
    "ST02-DIA-BASE",
    "ST02-DIA-H5",
]

PORTFOLIO_SYMBOLS = {
    "ST02-GLD-BASE": "GLD",
    "ST02-GLD-H5": "GLD",
    "ST02-DIA-BASE": "DIA",
    "ST02-DIA-H5": "DIA",
}


class St02AutonomousService:
    """Daemon de ejecución horaria autónomo para EXP-ST02."""

    def __init__(
        self,
        ledgers_dir: Optional[Path] = None,
        lock_file: Optional[Path] = None,
        stop_file: Optional[Path] = None,
        log_file: Optional[Path] = None,
        calendar: Optional[MarketCalendarService] = None,
        data_provider: Optional[Any] = None,
    ):
        self.exp_st02_dir = repo_root / "ai_trading_agent" / "strategy_lab" / "experiments" / "exp_st02"
        self.ledgers_dir = ledgers_dir or (self.exp_st02_dir / "ledgers")
        self.lock_file = lock_file or (self.exp_st02_dir / "exp_st02_service.pid")
        self.stop_file = stop_file or (self.exp_st02_dir / "exp_st02.stop")
        self.log_file = log_file or (self.exp_st02_dir / "st02_service.log")

        self.calendar = calendar or MarketCalendarService(tz_name="America/New_York")
        # En EXP-ST02 las barras sintéticas están estrictamente prohibidas
        self.data_provider = data_provider or YFinanceMarketDataProvider(fallback_to_synthetic=False)
        self.runner: Optional[St02HourlyRunner] = None
        self.telegram_notifier = St02TelegramNotifier(exp_dir=self.exp_st02_dir)
        self.is_running = False

        # Configurar logging
        self._setup_logging()

        # Telemetría de servicio
        self.telemetry = {
            "service_name": "EXP-ST02-AUTONOMOUS-DAEMON",
            "campaign_id": "CAMP-SHADOW-EXP-ST02-2026",
            "status": "INITIALIZING",
            "pid": os.getpid(),
            "started_at_utc": None,
            "last_cycle_evaluated": None,
            "cycles_completed": 0,
            "bars_evaluated": 0,
            "signals_generated": 0,
            "ledger_integrity": "UNCHECKED",
        }

    def _setup_logging(self):
        self.logger = logging.getLogger("St02AutonomousService")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            formatter = logging.Formatter("%(asctime)s [%(levelname)s] [ST02_DAEMON] %(message)s")
            # Stream handler
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(formatter)
            self.logger.addHandler(sh)
            # File handler si la ruta es accesible
            try:
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                fh = logging.FileHandler(str(self.log_file), encoding="utf-8")
                fh.setFormatter(formatter)
                self.logger.addHandler(fh)
            except Exception as e:
                self.logger.warning(f"No se pudo crear file handler para logs: {e}")

    # =========================================================================
    # 1. LOCK ATÓMICO Y GESTIÓN DE INSTANCIAS
    # =========================================================================
    def acquire_lock(self) -> bool:
        """Adquiere lock exclusivo garantizando exclusión atómica de instancias."""
        if self.lock_file.exists():
            try:
                content = self.lock_file.read_text(encoding="utf-8").strip()
                old_pid = int(content.split(":")[0])
                # Verificar si el proceso sigue vivo en Windows
                if self._is_pid_alive(old_pid):
                    self.logger.error(f"Instancia concurrente activa detectada (PID {old_pid}). Abortando arranque.")
                    return False
                else:
                    self.logger.warning(f"Lock huérfano detectado de PID {old_pid}. Limpiando lock anterior.")
            except Exception:
                pass

        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            self.lock_file.write_text(f"{os.getpid()}:{int(time.time())}", encoding="utf-8")
            return True
        except Exception as e:
            self.logger.error(f"Fallo al escribir lockfile: {e}")
            return False

    def release_lock(self):
        """Libera el lock exclusivo al finalizar."""
        try:
            if self.lock_file.exists():
                content = self.lock_file.read_text(encoding="utf-8").strip()
                if content.startswith(str(os.getpid())):
                    self.lock_file.unlink(missing_ok=True)
        except Exception as e:
            self.logger.warning(f"Error al liberar lockfile: {e}")

    @staticmethod
    def _is_pid_alive(pid: int) -> bool:
        """Verifica si un PID está actualmente en ejecución en Windows sin psutil."""
        if pid <= 0:
            return False
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False

    # =========================================================================
    # 2. RECUPERACIÓN Y VERIFICACIÓN CRIPTOGRÁFICA PREVIA AL ARRANQUE
    # =========================================================================
    def verify_startup_integrity(self) -> Tuple[bool, Dict[str, Any]]:
        """Audita estrictamente los cuatro ledgers antes de admitir cualquier operación."""
        self.logger.info("Auditando integridad criptográfica SHA-256 de los 4 ledgers canónicos...")
        results = {}
        all_valid = True

        for cid in ACTIVE_PORTFOLIOS:
            ledger_path = self.ledgers_dir / f"ledger_{cid}.jsonl"
            if not ledger_path.exists() or ledger_path.stat().st_size == 0:
                self.logger.error(f"Ledger ausente o vacío para {cid}: {ledger_path}")
                results[cid] = {"valid": False, "error": "MISSING_OR_EMPTY"}
                all_valid = False
                continue

            ledger = ShadowLedgerST02("CAMP-SHADOW-EXP-ST02-2026", cid, ledger_file=ledger_path)
            is_valid, violations = ledger.verify_integrity()
            results[cid] = {"valid": is_valid, "violations": violations}
            if not is_valid:
                all_valid = False
                self.logger.error(f"Violación de integridad criptográfica en {cid}: {violations}")

        self.telemetry["ledger_integrity"] = "VERIFIED_VALID" if all_valid else "CORRUPTED"
        return all_valid, results

    # =========================================================================
    # 3. CICLOS DE MERCADO Y PROGRAMACIÓN CAUSAL
    # =========================================================================
    def get_session_cycle_specs(self, session_date: date) -> List[Dict[str, Any]]:
        """
        Calcula la especificación exacta de ciclos causales H1 para la fecha dada.
        - Jornada regular: 7 ciclos (10:31:30 a 16:01:30 EST).
        - Cierre anticipado (13:00): 4 ciclos (10:31:30 a 13:01:30 EST).
        - Festivo/Fin de semana: 0 ciclos.
        """
        ref_dt = datetime.combine(session_date, dt_time(10, 0), tzinfo=NY_TZ)
        if not self.calendar.is_trading_day(ref_dt):
            return []

        is_early_close, _ = self.calendar.is_early_close(ref_dt)

        if not is_early_close:
            # 7 ciclos regulares
            return [
                {
                    "cycle_num": 1,
                    "bar_start_et": dt_time(9, 30),
                    "bar_close_et": dt_time(10, 30),
                    "expected_duration_minutes": 60,
                    "scheduled_trigger_et": dt_time(10, 31, 30),
                },
                {
                    "cycle_num": 2,
                    "bar_start_et": dt_time(10, 30),
                    "bar_close_et": dt_time(11, 30),
                    "expected_duration_minutes": 60,
                    "scheduled_trigger_et": dt_time(11, 31, 30),
                },
                {
                    "cycle_num": 3,
                    "bar_start_et": dt_time(11, 30),
                    "bar_close_et": dt_time(12, 30),
                    "expected_duration_minutes": 60,
                    "scheduled_trigger_et": dt_time(12, 31, 30),
                },
                {
                    "cycle_num": 4,
                    "bar_start_et": dt_time(12, 30),
                    "bar_close_et": dt_time(13, 30),
                    "expected_duration_minutes": 60,
                    "scheduled_trigger_et": dt_time(13, 31, 30),
                },
                {
                    "cycle_num": 5,
                    "bar_start_et": dt_time(13, 30),
                    "bar_close_et": dt_time(14, 30),
                    "expected_duration_minutes": 60,
                    "scheduled_trigger_et": dt_time(14, 31, 30),
                },
                {
                    "cycle_num": 6,
                    "bar_start_et": dt_time(14, 30),
                    "bar_close_et": dt_time(15, 30),
                    "expected_duration_minutes": 60,
                    "scheduled_trigger_et": dt_time(15, 31, 30),
                },
                {
                    "cycle_num": 7,
                    "bar_start_et": dt_time(15, 30),
                    "bar_close_et": dt_time(16, 0),
                    "expected_duration_minutes": 30,
                    "scheduled_trigger_et": dt_time(16, 1, 30),
                },
            ]
        else:
            # 4 ciclos de cierre anticipado a las 13:00
            return [
                {
                    "cycle_num": 1,
                    "bar_start_et": dt_time(9, 30),
                    "bar_close_et": dt_time(10, 30),
                    "expected_duration_minutes": 60,
                    "scheduled_trigger_et": dt_time(10, 31, 30),
                },
                {
                    "cycle_num": 2,
                    "bar_start_et": dt_time(10, 30),
                    "bar_close_et": dt_time(11, 30),
                    "expected_duration_minutes": 60,
                    "scheduled_trigger_et": dt_time(11, 31, 30),
                },
                {
                    "cycle_num": 3,
                    "bar_start_et": dt_time(11, 30),
                    "bar_close_et": dt_time(12, 30),
                    "expected_duration_minutes": 60,
                    "scheduled_trigger_et": dt_time(12, 31, 30),
                },
                {
                    "cycle_num": 4,
                    "bar_start_et": dt_time(12, 30),
                    "bar_close_et": dt_time(13, 0),
                    "expected_duration_minutes": 30,
                    "scheduled_trigger_et": dt_time(13, 1, 30),
                },
            ]

    # =========================================================================
    # 4. EJECUCIÓN DE CICLO INDIVIDUAL CON VALIDACIÓN ESTRICTA
    # =========================================================================
    def execute_cycle(
        self,
        cycle_spec: Dict[str, Any],
        session_date: date,
        current_time_et: Optional[datetime] = None,
        bars_by_symbol: Optional[Dict[str, List[OHLCVBar]]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta un ciclo individual de evaluación horaria con validación causal y preservación.
        """
        now_et = current_time_et or self.calendar.get_now()
        trigger_dt = datetime.combine(session_date, cycle_spec["scheduled_trigger_et"], tzinfo=NY_TZ)
        close_dt = datetime.combine(session_date, cycle_spec["bar_close_et"], tzinfo=NY_TZ)

        # 1. Validación de causación: No evaluar antes del cierre físico
        if now_et < close_dt:
            raise CausalLatencyViolation(
                f"Intento de evaluación anticipada: now={now_et} < close={close_dt} para ciclo {cycle_spec['cycle_num']}"
            )

        # 2. Inicio tardío / Barra no evaluable en tiempo real
        # Si se ejecuta significativamente después de la ventana permitida (ej. > 45 min tarde)
        is_late_start = (now_et - trigger_dt) > timedelta(minutes=45)

        cycle_result = {
            "cycle_num": cycle_spec["cycle_num"],
            "session_date": str(session_date),
            "status": "SUCCESS",
            "evaluations": {},
            "is_late_start": is_late_start,
        }

        if is_late_start:
            self.logger.warning(
                f"Ciclo {cycle_spec['cycle_num']} iniciado con desfase temporal excesivo (LATE_START_SKIPPED)."
            )
            cycle_result["status"] = "LATE_START_SKIPPED"
            return cycle_result

        # Inicializar runner si no existe
        if self.runner is None:
            self.runner = St02HourlyRunner(ledgers_dir=self.ledgers_dir)

        # 3. Evaluar cada cartera
        for cid in ACTIVE_PORTFOLIOS:
            symbol = PORTFOLIO_SYMBOLS[cid]
            symbol_bars = (bars_by_symbol or {}).get(symbol, [])

            if not symbol_bars:
                cycle_result["status"] = "DATA_FEED_ERROR"
                cycle_result["evaluations"][cid] = {"status": "DATA_FEED_ERROR", "error": f"No bars for {symbol}"}
                continue

            # Buscar la barra correspondiente al ciclo
            target_idx = None
            for idx, b in enumerate(symbol_bars):
                b_et = b.timestamp.astimezone(NY_TZ) if b.timestamp.tzinfo else b.timestamp.replace(tzinfo=timezone.utc).astimezone(NY_TZ)
                if b_et.date() == session_date and b_et.time() == cycle_spec["bar_start_et"]:
                    target_idx = idx
                    break

            if target_idx is None:
                cycle_result["status"] = "DATA_FEED_ERROR"
                cycle_result["evaluations"][cid] = {"status": "BAR_NOT_FOUND"}
                continue

            # Validar que no sea barra sintética
            target_bar = symbol_bars[target_idx]
            if getattr(target_bar, "source", "") == "synthetic":
                cycle_result["status"] = "DATA_FEED_ERROR"
                cycle_result["evaluations"][cid] = {
                    "status": "DATA_FEED_ERROR",
                    "error": f"Barras sintéticas estrictamente prohibidas en EXP-ST02 para {symbol}"
                }
                continue

            # Evaluar barra usando el runner certificado
            res = self.runner.evaluate_bar(
                candidate_id=cid,
                bars=symbol_bars,
                target_bar_idx=target_idx,
                evaluation_timestamp_utc=now_et.astimezone(timezone.utc),
            )
            cycle_result["evaluations"][cid] = res
            self.telemetry["bars_evaluated"] += 1
            if res.get("signal") and res["signal"] != "NO_SIGNAL":
                self.telemetry["signals_generated"] += 1

        self.telemetry["cycles_completed"] += 1
        self.telemetry["last_cycle_evaluated"] = f"{session_date}_C{cycle_spec['cycle_num']}"
        return cycle_result

    # =========================================================================
    # 5. KILL-SWITCH Y BUCLE PRINCIPAL (DAEMON)
    # =========================================================================
    def should_stop(self) -> bool:
        """Verifica si existe orden de detención o señal externa."""
        if self.stop_file.exists():
            self.logger.info("Fichero de parada detectado (Kill-Switch). Deteniendo daemon.")
            return True
        return not self.is_running

    def run_daemon(self, poll_interval_sec: int = 15):
        """Bucle principal de ejecución autónoma."""
        if not self.acquire_lock():
            sys.exit(1)
        self.stop_file.unlink(missing_ok=True)

        valid_crypto, diag = self.verify_startup_integrity()
        if not valid_crypto:
            self.logger.error("Abortando ejecución por fallo de integridad criptográfica en ledgers.")
            self.release_lock()
            sys.exit(2)

        self.is_running = True
        self.telemetry["status"] = "RUNNING"
        self.telemetry["started_at_utc"] = datetime.now(timezone.utc).isoformat()
        self.logger.info(f"Servicio EXP-ST02 iniciado exitosamente en modo autónomo (PID {os.getpid()}).")

        # Registrar manejador de señales
        def _handle_signal(sig, frame):
            self.logger.info(f"Señal de interrupción recibida ({sig}). Iniciando parada ordenada.")
            self.is_running = False

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        try:
            while not self.should_stop():
                now_et = self.calendar.get_now()
                today = now_et.date()
                specs = self.get_session_cycle_specs(today)

                for spec in specs:
                    trigger_dt = datetime.combine(today, spec["scheduled_trigger_et"], tzinfo=NY_TZ)
                    # Ventana de disparo: dentro de los 5 minutos del trigger
                    if trigger_dt <= now_et < (trigger_dt + timedelta(minutes=5)):
                        cycle_id = f"{today}_C{spec['cycle_num']}"
                        if self.telemetry.get("last_cycle_evaluated") != cycle_id:
                            self.logger.info(f"Disparando evaluación causal de ciclo {spec['cycle_num']} ({cycle_id})...")
                            try:
                                bars_by_symbol = {}
                                for sym in ['GLD', 'DIA']:
                                    bars = self.data_provider.get_historical_bars(symbol=sym, count=250, interval='60m')
                                    bars_by_symbol[sym] = bars
                                res = self.execute_cycle(
                                    cycle_spec=spec,
                                    session_date=today,
                                    current_time_et=now_et,
                                    bars_by_symbol=bars_by_symbol
                            )
                                self.logger.info(f"Ciclo {spec['cycle_num']} evaluado: status={res.get('status')}")
                                try:
                                    if self.telegram_notifier.is_configured:
                                        self.telegram_notifier.notify_cycle_result(
                                            cycle_spec=spec,
                                            cycle_result=res,
                                            bars_by_symbol=bars_by_symbol,
                                        )
                                        if res.get("status") in ("DATA_FEED_ERROR", "LATE_START_SKIPPED"):
                                            self.telegram_notifier.notify_critical_alert(
                                                alert_type=res.get("status"),
                                                details=f"Ciclo {spec['cycle_num']} finalizado con estado {res.get('status')}.",
                                                cycle_num=spec["cycle_num"],
                                            )
                                except Exception as tg_ex:
                                    self.logger.warning(f"Error enviando notificacion Telegram de ciclo: {tg_ex}")
                            except Exception as ex:
                                self.logger.error(f"Error evaluando ciclo {spec['cycle_num']}: {ex}")
                            self.telemetry["last_cycle_evaluated"] = cycle_id

                time.sleep(poll_interval_sec)

        except Exception as e:
            self.logger.error(f"Error imprevisto en bucle daemon: {e}", exc_info=True)
        finally:
            self.logger.info("Cerrando servicio EXP-ST02 y liberando recursos...")
            self.release_lock()
            self.telemetry["status"] = "STOPPED"


def main():
    parser = argparse.ArgumentParser(description="Daemon autónomo de evaluación horaria para EXP-ST02.")
    parser.add_argument("--daemon", action="store_true", help="Inicia el servicio en bucle autónomo.")
    parser.add_argument("--status", action="store_true", help="Muestra el estado operativo del servicio.")
    parser.add_argument("--stop", action="store_true", help="Envía orden de detención limpia al servicio.")
    parser.add_argument("--verify-ledgers", action="store_true", help="Verifica la integridad SHA-256 de los ledgers.")
    args = parser.parse_args()

    service = St02AutonomousService()

    if args.status:
        if service.lock_file.exists():
            content = service.lock_file.read_text(encoding="utf-8").strip()
            pid = int(content.split(":")[0])
            alive = service._is_pid_alive(pid)
            print(f"STATUS: {'RUNNING' if alive else 'STALE_LOCK'} | PID: {pid}")
        else:
            print("STATUS: STOPPED (No active lockfile)")
        sys.exit(0)

    if args.stop:
        service.stop_file.parent.mkdir(parents=True, exist_ok=True)
        service.stop_file.write_text(f"STOP_REQUESTED_AT_{int(time.time())}", encoding="utf-8")
        try:
            if service.telegram_notifier.is_configured:
                service.telegram_notifier.notify_critical_alert(
                    alert_type="KILL_SWITCH_ACTIVATED",
                    details="Orden de parada limpia (Kill-Switch) emitida via CLI.",
                )
        except Exception:
            pass
        print("Orden de parada (Kill-Switch) registrada en stopfile.")
        sys.exit(0)

    if args.verify_ledgers:
        valid, details = service.verify_startup_integrity()
        print(f"CRYPTOGRAPHIC_INTEGRITY: {'VALID' if valid else 'FAILED'}")
        for cid, info in details.items():
            print(f"  {cid}: valid={info['valid']}")
        sys.exit(0 if valid else 1)

    if args.daemon:
        print("Iniciando EXP-ST02 Autonomous Daemon...")
        service.run_daemon()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
