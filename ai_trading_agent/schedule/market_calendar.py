"""
ai_trading_agent.schedule.market_calendar
=========================================
Servicio centralizado de Zonas Horarias (America/New_York via zoneinfo) y Calendario Bursátil de EE. UU. (NYSE/NASDAQ).
Determina festivos, cierres anticipados, fases de sesión y próximas aperturas/cierres sin hardcodear desfases UTC.
"""

import logging
from datetime import datetime, date, time, timedelta, timezone
import zoneinfo
from typing import Optional, Dict, Any, List, Tuple
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class MarketCalendarService:
    """Servicio de Zonas Horarias y Calendario Bursátil US (NYSE/NASDAQ)."""

    def __init__(self, tz_name: str = "America/New_York", config_path: Optional[str] = None):
        self.tz_name = tz_name
        self.tz = zoneinfo.ZoneInfo(self.tz_name)
        self._custom_now_fn = None  # Para inyección de reloj en pruebas unitarias

        # Cargar configuración si existe
        self.config = {}
        if config_path:
            p = Path(config_path)
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        self.config = yaml.safe_load(f) or {}
                except Exception as e:
                    logger.warning(f"No se pudo cargar {config_path}: {e}")

    def set_mock_clock(self, mock_fn):
        """Permite inyectar un reloj personalizado para pruebas deterministas."""
        self._custom_now_fn = mock_fn

    def get_now(self) -> datetime:
        """Devuelve la fecha/hora actual en la zona horaria del mercado (America/New_York)."""
        if self._custom_now_fn:
            dt = self._custom_now_fn()
            if dt.tzinfo is None:
                return dt.replace(tzinfo=self.tz)
            return dt.astimezone(self.tz)
        return datetime.now(self.tz)

    def is_weekend(self, dt: Optional[datetime] = None) -> bool:
        """Retorna True si es Sábado (5) o Domingo (6)."""
        check_dt = dt or self.get_now()
        return check_dt.weekday() in (5, 6)

    def get_us_holidays(self, year: int) -> Dict[date, str]:
        """Calcula los festivos oficiales de la bolsa de Nueva York (NYSE/NASDAQ) para un año dado."""
        holidays = {}

        # 1. New Year's Day (Enero 1)
        nyd = date(year, 1, 1)
        if nyd.weekday() == 6:  # Si cae en Domingo, se observa el Lunes Jan 2
            holidays[date(year, 1, 2)] = "New Year's Day (Observado)"
        elif nyd.weekday() != 5:  # Si cae en Sábado, el viernes 31 de dic del año anterior es el holiday
            holidays[nyd] = "New Year's Day"

        # 2. Martin Luther King Jr. Day (Tercer Lunes de Enero)
        holidays[self._nth_weekday(year, 1, 0, 3)] = "Martin Luther King Jr. Day"

        # 3. Presidents' Day (Tercer Lunes de Febrero)
        holidays[self._nth_weekday(year, 2, 0, 3)] = "Presidents' Day"

        # 4. Good Friday (Viernes Santo - Cálculo de Pascua)
        good_friday = self._get_good_friday(year)
        if good_friday:
            holidays[good_friday] = "Good Friday"

        # 5. Memorial Day (Último Lunes de Mayo)
        holidays[self._last_weekday(year, 5, 0)] = "Memorial Day"

        # 6. Juneteenth (Junio 19)
        jt = date(year, 6, 19)
        if jt.weekday() == 6:
            holidays[date(year, 6, 20)] = "Juneteenth (Observado)"
        elif jt.weekday() == 5:
            holidays[date(year, 6, 18)] = "Juneteenth (Observado)"
        else:
            holidays[jt] = "Juneteenth"

        # 7. Independence Day (Julio 4)
        indep = date(year, 7, 4)
        if indep.weekday() == 6:
            holidays[date(year, 7, 5)] = "Independence Day (Observado)"
        elif indep.weekday() == 5:
            holidays[date(year, 7, 3)] = "Independence Day (Observado)"
        else:
            holidays[indep] = "Independence Day"

        # 8. Labor Day (Primer Lunes de Septiembre)
        holidays[self._nth_weekday(year, 9, 0, 1)] = "Labor Day"

        # 9. Thanksgiving Day (Cuarto Jueves de Noviembre)
        holidays[self._nth_weekday(year, 11, 3, 4)] = "Thanksgiving Day"

        # 10. Christmas Day (Diciembre 25)
        xmas = date(year, 12, 25)
        if xmas.weekday() == 6:
            holidays[date(year, 12, 26)] = "Christmas Day (Observado)"
        elif xmas.weekday() == 5:
            holidays[date(year, 12, 24)] = "Christmas Day (Observado)"
        else:
            holidays[xmas] = "Christmas Day"

        return holidays

    def get_early_closes(self, year: int) -> Dict[date, str]:
        """Calcula los días con cierre anticipado (1:00 PM ET) para la bolsa de Nueva York."""
        early_closes = {}

        # Víspera del 4 de Julio (Julio 3 si es día hábil)
        j3 = date(year, 7, 3)
        if j3.weekday() < 5:
            early_closes[j3] = "Independence Day Eve (Cierre 1:00 PM ET)"

        # Viernes después de Thanksgiving (Black Friday - Día después del 4° Jueves de Nov)
        thanksgiving = self._nth_weekday(year, 11, 3, 4)
        black_friday = thanksgiving + timedelta(days=1)
        early_closes[black_friday] = "Black Friday (Cierre 1:00 PM ET)"

        # Nochebuena (Diciembre 24 si es día hábil)
        c_eve = date(year, 12, 24)
        if c_eve.weekday() < 5 and c_eve not in self.get_us_holidays(year):
            early_closes[c_eve] = "Christmas Eve (Cierre 1:00 PM ET)"

        return early_closes

    def is_holiday(self, dt: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
        """Verifica si la fecha indicada es festivo bursátil en EE. UU."""
        check_dt = dt or self.get_now()
        d = check_dt.date()
        holidays = self.get_us_holidays(d.year)
        if d in holidays:
            return True, holidays[d]
        return False, None

    def is_early_close(self, dt: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
        """Verifica si la fecha indicada tiene cierre anticipado a la 1:00 PM ET."""
        check_dt = dt or self.get_now()
        d = check_dt.date()
        early = self.get_early_closes(d.year)
        if d in early:
            return True, early[d]
        return False, None

    def is_trading_day(self, dt: Optional[datetime] = None) -> bool:
        """Retorna True si la fecha es un día de negociación bursátil válido (no fin de semana, no festivo)."""
        check_dt = dt or self.get_now()
        if self.is_weekend(check_dt):
            return False
        is_hol, _ = self.is_holiday(check_dt)
        return not is_hol

    def get_market_state(self, dt: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Determina el estado operativo del mercado en tiempo real.
        Retorna: status (PREMARKET, REGULAR, AFTER_HOURS, CLOSED, HOLIDAY),
                 window_name, description, is_trading_day, close_time.
        """
        now = dt or self.get_now()
        current_time = now.time()
        current_date = now.date()

        is_hol, hol_name = self.is_holiday(now)
        if is_hol:
            return {
                "status": "HOLIDAY",
                "window": "HOLIDAY",
                "description": f"Mercado Cerrado por Festivo ({hol_name})",
                "is_trading_day": False,
                "regular_close": "16:00"
            }

        if self.is_weekend(now):
            day_name = "Sábado" if now.weekday() == 5 else "Domingo"
            return {
                "status": "CLOSED",
                "window": "WEEKEND",
                "description": f"Fin de Semana ({day_name}) - Escáner e Infraestructura 24/7",
                "is_trading_day": False,
                "regular_close": "16:00"
            }

        is_early, early_reason = self.is_early_close(now)
        close_hour, close_minute = (13, 0) if is_early else (16, 0)
        close_str = f"{close_hour:02d}:{close_minute:02d}"

        t_prem_start = time(4, 0)
        t_prem_prep_start = time(7, 0)
        t_open = time(9, 30)
        t_close = time(close_hour, close_minute)
        t_after_end = time(20, 0)

        if current_time < t_prem_start:
            status = "CLOSED"
            window = "OVERNIGHT"
            desc = "Madrugada Pre-Premarket"
        elif t_prem_start <= current_time < t_prem_prep_start:
            status = "PREMARKET"
            window = "PREMARKET_EARLY"
            desc = "Premarket Temprano (4:00 AM - 7:00 AM ET)"
        elif t_prem_prep_start <= current_time < time(9, 20):
            status = "PREMARKET"
            window = "PREMARKET_PREP"
            desc = "Preparación Premarket & Detección Gaps (7:00 AM - 9:20 AM ET)"
        elif time(9, 20) <= current_time < t_open:
            status = "PREMARKET"
            window = "PREMARKET_FINAL"
            desc = "Informe Premarket & Configuración Apertura (9:20 AM - 9:30 AM ET)"
        elif t_open <= current_time < time(10, 30) and current_time < t_close:
            status = "REGULAR"
            window = "OPENING_ORB"
            desc = "Apertura de Mercado & Ventana ORB (9:30 AM - 10:30 AM ET)"
        elif time(10, 30) <= current_time < time(15, 30) and current_time < t_close:
            status = "REGULAR"
            window = "REGULAR_SESSION"
            desc = "Sesión Regular de Negociación (10:30 AM - 3:30 PM ET)"
        elif time(15, 30) <= current_time < t_close:
            status = "REGULAR"
            window = "CLOSING_PREP"
            desc = "Preparación de Cierre & Square-Off (3:30 PM - 4:00 PM ET)"
        elif t_close <= current_time < time(17, 0):
            status = "AFTER_HOURS"
            window = "POST_CLOSE_REVIEW"
            desc = "Revisión Post-Cierre & Journal Daily Report (4:00 PM - 5:00 PM ET)"
        elif time(18, 0) <= current_time < time(19, 0):
            status = "CLOSED"
            window = "NIGHTLY_PREP"
            desc = "Análisis Nocturno de Preparación (6:00 PM - 7:00 PM ET)"
        elif time(17, 0) <= current_time < t_after_end:
            status = "AFTER_HOURS"
            window = "AFTER_HOURS"
            desc = "Sesión Extendida After-Hours (5:00 PM - 8:00 PM ET)"
        else:
            status = "CLOSED"
            window = "NIGHT"
            desc = "Noche - Mercado Cerrado"

        return {
            "status": status,
            "window": window,
            "description": desc,
            "is_trading_day": True,
            "is_early_close": is_early,
            "early_close_reason": early_reason,
            "regular_close": close_str
        }

    def get_next_market_open(self, dt: Optional[datetime] = None) -> datetime:
        """Calcula la fecha y hora exacta de la próxima apertura de mercado regular (09:30 AM ET)."""
        now = dt or self.get_now()
        check_date = now.date()

        # Si hoy es día hábil y es antes de las 9:30 AM, la apertura es hoy
        if self.is_trading_day(now) and now.time() < time(9, 30):
            return datetime.combine(check_date, time(9, 30), tzinfo=self.tz)

        # Buscar el siguiente día hábil
        check_date += timedelta(days=1)
        while True:
            candidate_dt = datetime.combine(check_date, time(9, 30), tzinfo=self.tz)
            if self.is_trading_day(candidate_dt):
                return candidate_dt
            check_date += timedelta(days=1)

    def get_next_market_close(self, dt: Optional[datetime] = None) -> datetime:
        """Calcula la fecha y hora exacta del próximo cierre de mercado regular (4:00 PM o 1:00 PM en cierre anticipado)."""
        now = dt or self.get_now()
        check_date = now.date()

        # Si hoy es día hábil y es antes del cierre de hoy
        if self.is_trading_day(now):
            is_early, _ = self.is_early_close(now)
            c_time = time(13, 0) if is_early else time(16, 0)
            if now.time() < c_time:
                return datetime.combine(check_date, c_time, tzinfo=self.tz)

        # Buscar el siguiente día hábil
        check_date += timedelta(days=1)
        while True:
            candidate_dt = datetime.combine(check_date, time(12, 0), tzinfo=self.tz)
            if self.is_trading_day(candidate_dt):
                is_early, _ = self.is_early_close(candidate_dt)
                c_time = time(13, 0) if is_early else time(16, 0)
                return datetime.combine(check_date, c_time, tzinfo=self.tz)
            check_date += timedelta(days=1)

    # --- Métodos auxiliares de cálculo de festivos ---

    def _nth_weekday(self, year: int, month: int, weekday: int, n: int) -> date:
        """Devuelve la fecha del N-ésimo día de la semana en un mes dado (0=Lunes, 3=Jueves)."""
        count = 0
        for day in range(1, 32):
            try:
                d = date(year, month, day)
                if d.weekday() == weekday:
                    count += 1
                    if count == n:
                        return d
            except ValueError:
                break
        raise ValueError(f"No existe el {n}° día del mes {month}/{year}")

    def _last_weekday(self, year: int, month: int, weekday: int) -> date:
        """Devuelve el último día de la semana específico en un mes dado."""
        last_d = None
        for day in range(1, 32):
            try:
                d = date(year, month, day)
                if d.weekday() == weekday:
                    last_d = d
            except ValueError:
                break
        if last_d:
            return last_d
        raise ValueError(f"No se encontró el último día de la semana en {month}/{year}")

    def _get_good_friday(self, year: int) -> Optional[date]:
        """Calcula el Viernes Santo usando el algoritmo de Butcher / Meeus."""
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        easter = date(year, month, day)
        return easter - timedelta(days=2)


# Instancia global predeterminada
market_calendar = MarketCalendarService(config_path="config/market_schedule.yaml")
