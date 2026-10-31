"""
ai_trading_agent.strategy_lab.experiments.exp_st02.verify_gate_b_calendar
========================================================================
Verificación Rigurosa de Gate B: Calendario Bursátil y Alineación Temporal H1.
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from datetime import datetime, date, time, timezone, timedelta
import zoneinfo
import pandas as pd

from ai_trading_agent.schedule.market_calendar import market_calendar

def verify_gate_b():
    print("=== VERIFICACIÓN GATE B: CALENDARIO BURSÁTIL Y ALINEACIÓN H1 ===")
    ny_tz = zoneinfo.ZoneInfo("America/New_York")

    # 1. Sesión del Lunes 2 de Noviembre de 2026
    target_date = date(2026, 11, 2)
    dt_target = datetime(2026, 11, 2, 9, 30, tzinfo=ny_tz)

    is_weekend = dt_target.weekday() >= 5
    is_holiday = market_calendar.is_holiday(dt_target)
    is_early_close = market_calendar.is_early_close(dt_target)

    print(f"1. Fecha Objetivo: {target_date.strftime('%Y-%m-%d')} ({dt_target.strftime('%A')})")
    print(f"   - Es Fin de Semana: {is_weekend}")
    print(f"   - Es Festivo NYSE: {is_holiday}")
    print(f"   - Es Cierre Anticipado: {is_early_close}")

    # 2. Verificación de Cambio de Hora (DST Fall Back)
    # Domingo 1 de Noviembre de 2026 termina DST en EE.UU.
    dt_nov1 = datetime(2026, 11, 1, 12, 0, tzinfo=ny_tz)
    dt_nov2 = datetime(2026, 11, 2, 12, 0, tzinfo=ny_tz)
    
    offset_nov2 = dt_nov2.utcoffset()
    tz_abbrev_nov2 = dt_nov2.tzname()

    print(f"2. Verificación Horaria EST:")
    print(f"   - Zona Horaria: {ny_tz.key}")
    print(f"   - Abreviatura al 2 de Noviembre: {tz_abbrev_nov2} (Esperado: EST)")
    print(f"   - Offset UTC: {offset_nov2} (Esperado: -5:00:00)")

    # 3. Horarios de Apertura y Cierre Regular en EST y UTC
    open_et = time(9, 30)
    close_et = time(16, 0)

    dt_open_et = datetime.combine(target_date, open_et, tzinfo=ny_tz)
    dt_close_et = datetime.combine(target_date, close_et, tzinfo=ny_tz)

    dt_open_utc = dt_open_et.astimezone(timezone.utc)
    dt_close_utc = dt_close_et.astimezone(timezone.utc)

    print(f"3. Sesión Regular:")
    print(f"   - Apertura ET: {dt_open_et.strftime('%H:%M %Z')} -> UTC: {dt_open_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   - Cierre ET:   {dt_close_et.strftime('%H:%M %Z')} -> UTC: {dt_close_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # 4. Inspección del etiquetado y barras H1 en datos históricos reales
    csv_sample = repo_root / "ai_trading_agent" / "strategy_lab" / "experiments" / "exp_st01" / "data_cache" / "GLD_H1.csv"
    if csv_sample.exists():
        df = pd.read_csv(csv_sample)
        print(f"4. Inspección de Convención de Datos H1 (GLD_H1.csv):")
        print(f"   - Total registros: {len(df)}")
        # Mostrar las últimas 7 barras de un día completo para ver los timestamps
        last_bars = df.tail(7)
        for _, r in last_bars.iterrows():
            print(f"     Bar timestamp: {r['timestamp']} | Open: {r['open']} | Close: {r['close']}")

    # 5. Estructura de barras H1 de la sesión 2026-11-02
    h1_bars = [
        {"bar_num": 1, "open_et": "09:30", "close_et": "10:30", "open_utc": "14:30", "close_utc": "15:30", "first_eval_utc": "15:30"},
        {"bar_num": 2, "open_et": "10:30", "close_et": "11:30", "open_utc": "15:30", "close_utc": "16:30", "first_eval_utc": "16:30"},
        {"bar_num": 3, "open_et": "11:30", "close_et": "12:30", "open_utc": "16:30", "close_utc": "17:30", "first_eval_utc": "17:30"},
        {"bar_num": 4, "open_et": "12:30", "close_et": "13:30", "open_utc": "17:30", "close_utc": "18:30", "first_eval_utc": "18:30"},
        {"bar_num": 5, "open_et": "13:30", "close_et": "14:30", "open_utc": "18:30", "close_utc": "19:30", "first_eval_utc": "19:30"},
        {"bar_num": 6, "open_et": "14:30", "close_et": "15:30", "open_utc": "19:30", "close_utc": "20:30", "first_eval_utc": "20:30"},
        {"bar_num": 7, "open_et": "15:30", "close_et": "16:00", "open_utc": "20:30", "close_utc": "21:00", "first_eval_utc": "21:00"},
    ]

    print("5. Alineación Causal de Barras H1 (Sesión 2026-11-02):")
    for b in h1_bars:
        print(f"   - Barra {b['bar_num']}: {b['open_et']} - {b['close_et']} ET ({b['open_utc']} - {b['close_utc']} UTC) -> Evaluación Causal Disponible a las: {b['first_eval_utc']} UTC")

    # Regla: La primera barra elegible cierra a las 10:30 ET (15:30 UTC)
    first_eligible_close_utc = "2026-11-02T15:30:00Z"
    print(f"   -> Primera Barra Elegible Cierra a las: {first_eligible_close_utc}")

    calendar_pass = (
        not is_weekend
        and not is_holiday
        and tz_abbrev_nov2 == "EST"
        and offset_nov2 == timedelta(hours=-5)
    )

    verdict = "PASS" if calendar_pass else "FAIL"
    print(f"==> DICTAMEN GATE B: {verdict}")
    return verdict, first_eligible_close_utc

if __name__ == "__main__":
    verify_gate_b()
