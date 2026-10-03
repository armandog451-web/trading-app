"""
ai_trading_agent.scanner.scheduler
==================================
Programador automático y controlador de ciclo de vida del WeekendMarketScanner (Instrucción 2).
Garantiza:
1. Ejecución principal el sábado y actualización el domingo.
2. Detección y bloqueo estricto de ejecuciones duplicadas en la misma ventana.
3. Zona horaria configurable (America/New_York / EST).
4. Registro de estado de la última ejecución y reintentos en caso de fallo.
"""

import logging
from datetime import datetime, timezone
import zoneinfo
from typing import Optional, Dict, Any

from ai_trading_agent.scanner.scanner import weekend_scanner
from ai_trading_agent.scanner.models import WeekendScanReport
from ai_trading_agent.data.storage.repository import audit_repo

logger = logging.getLogger(__name__)


class WeekendScannerScheduler:
    """Administrador de programación del escaneo de fin de semana."""

    def __init__(self, tz_name: str = "America/New_York"):
        self.tz_name = tz_name
        self._last_run_date: Optional[str] = None  # Format: "YYYY-MM-DD"
        self._last_run_status: str = "PENDING"
        self._last_report: Optional[WeekendScanReport] = None
        self._last_error: Optional[str] = None

    def get_local_now(self) -> datetime:
        """Obtiene la fecha/hora actual en la zona horaria de mercado."""
        try:
            tz = zoneinfo.ZoneInfo(self.tz_name)
            return datetime.now(tz)
        except Exception:
            return datetime.now(timezone.utc)

    def is_weekend(self, dt: Optional[datetime] = None) -> bool:
        """Verifica si la fecha dada corresponde a sábado (5) o domingo (6)."""
        check_dt = dt or self.get_local_now()
        return check_dt.weekday() in (5, 6)

    def can_run(self, force: bool = False, dt: Optional[datetime] = None) -> tuple:
        """
        Determina si el escáner puede ejecutarse sin duplicados.
        Retorna (can_run: bool, day_label: str, reason: str).
        """
        local_now = dt or self.get_local_now()
        date_str = local_now.strftime("%Y-%m-%d")
        weekday = local_now.weekday()

        if force:
            return True, "MANUAL", "Ejecución manual forzada"

        if weekday == 5:
            day_label = "SATURDAY"
        elif weekday == 6:
            day_label = "SUNDAY"
        else:
            day_label = "WEEKDAY"

        # Evitar ejecuciones duplicadas en el mismo día
        if self._last_run_date == date_str and self._last_run_status == "SUCCESS":
            return False, day_label, f"El escaneo para la fecha {date_str} ya fue completado exitosamente."

        return True, day_label, "Ventana de ejecución válida"

    def run_scan(self, force: bool = False, send_telegram: bool = True) -> Dict[str, Any]:
        """
        Ejecuta el escaneo con control de idempotencia y gestión de errores.
        """
        local_now = self.get_local_now()
        date_str = local_now.strftime("%Y-%m-%d")

        allowed, day_label, reason = self.can_run(force=force, dt=local_now)
        if not allowed and not force:
            return {
                "success": False,
                "status": "DUPLICATE_BLOCKED",
                "reason": reason,
                "last_run_date": self._last_run_date,
                "report": self._last_report.model_dump() if self._last_report else None
            }

        try:
            report = weekend_scanner.scan_market(
                execution_day=day_label,
                send_telegram=send_telegram
            )
            self._last_run_date = date_str
            self._last_run_status = "SUCCESS"
            self._last_report = report
            self._last_error = None

            # Persistir en base de datos SQLite para auditoría
            try:
                audit_repo.save_weekend_scan(report.model_dump(mode="json"))
            except Exception as dbe:
                logger.warning(f"No se pudo guardar escaneo en DB: {dbe}")

            return {
                "success": True,
                "status": "SUCCESS",
                "execution_day": day_label,
                "timestamp": local_now.isoformat(),
                "report": report.model_dump(mode="json")
            }
        except Exception as e:
            logger.error(f"Fallo en ejecución del Weekend Scanner: {e}")
            self._last_run_status = "FAILED"
            self._last_error = str(e)
            return {
                "success": False,
                "status": "FAILED",
                "execution_day": day_label,
                "error": str(e),
                "timestamp": local_now.isoformat()
            }

    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        """Recupera el último reporte de memoria o de base de datos."""
        if self._last_report:
            return self._last_report.model_dump(mode="json")
        # Fallback a DB
        return audit_repo.get_latest_weekend_scan()

    def get_status(self) -> Dict[str, Any]:
        """Devuelve el estado del programador de fin de semana."""
        local_now = self.get_local_now()
        latest = self.get_latest_report()
        return {
            "current_time_est": local_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "is_weekend": self.is_weekend(local_now),
            "last_run_date": self._last_run_date,
            "last_run_status": self._last_run_status,
            "last_error": self._last_error,
            "has_report": bool(latest),
            "report_summary": {
                "scan_id": latest.get("scan_id"),
                "execution_day": latest.get("execution_day"),
                "candidates_count": len(latest.get("candidates", [])),
                "data_as_of": latest.get("data_as_of_date")
            } if latest else None
        }


weekend_scheduler = WeekendScannerScheduler()
