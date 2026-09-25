import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from app.strategies.strategy_orb import orb_strategy
from app.database import SessionLocal
from app.models.db_models import SignalRecommendation

def create_synthetic_orb_data(
    base_price: float = 560.0,
    breakout_type: str = "LONG",
    volume_surge: bool = True
) -> pd.DataFrame:
    """
    Genera serie de 60 barras de 1 minuto simulando la sesión desde las 09:30 EST.
    - 09:30 a 09:45 (15 min): Rango de apertura.
    - 09:46 en adelante: Vela de prueba (ruptura alcista, bajista o fakeout).
    """
    base_time = datetime(2026, 9, 24, 9, 30, 0)
    times = [base_time + timedelta(minutes=i) for i in range(40)]

    np.random.seed(42)
    closes = [base_price]
    for _ in range(39):
        closes.append(closes[-1] + np.random.uniform(-0.15, 0.15))

    highs = [c + np.random.uniform(0.05, 0.20) for c in closes]
    lows = [c - np.random.uniform(0.05, 0.20) for c in closes]
    opens = [lows[i] + (highs[i] - lows[i]) * 0.5 for i in range(40)]
    
    # Volumen regular: ~10,000 acciones por minuto
    volumes = [int(np.random.uniform(8000, 12000)) for _ in range(40)]

    # Vela en índice 20 (09:50 EST): Ruptura intencional
    or_high_15 = max(highs[:15])
    or_low_15 = min(lows[:15])

    if breakout_type == "LONG":
        closes[20] = or_high_15 + 0.60
        highs[20] = closes[20] + 0.10
        lows[20] = or_high_15 + 0.20
        volumes[20] = 25000 if volume_surge else 8500  # 2.5x vs 0.85x
    elif breakout_type == "SHORT":
        closes[20] = or_low_15 - 0.60
        lows[20] = closes[20] - 0.10
        highs[20] = or_low_15 - 0.20
        volumes[20] = 25000 if volume_surge else 8500
    else:
        # Dentro del rango
        closes[20] = (or_high_15 + or_low_15) / 2.0

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    }, index=pd.DatetimeIndex(times))

    return df

def test_orb_suite():
    print("==================================================================")
    print("   SUITE DE PRUEBAS: ESTRATEGIA ORB CON FILTRO DE VOLUMEN")
    print("==================================================================")

    # 1. TEST: Cálculo de Techo y Piso del Opening Range (15 minutos)
    df_long = create_synthetic_orb_data(base_price=560.0, breakout_type="LONG", volume_surge=True)
    or_high, or_low, is_completed = orb_strategy.compute_opening_range(df_long)
    
    print(f"\n1. RANGO DE APERTURA (15 min):")
    print(f"   Techo (OR High): ${or_high:.2f}")
    print(f"   Piso  (OR Low) : ${or_low:.2f}")
    print(f"   Rango Total    : ${(or_high - or_low):.2f}")
    print(f"   Rango Completo : {is_completed}")
    assert or_high > or_low, "OR High debe ser estrictamente mayor que OR Low"
    assert is_completed, "El rango de 15 minutos debe estar completado tras las 09:45"

    # 2. TEST: Ruptura Alcista con Volumen Fuerte (>= 1.5x) -> CALL
    breakout_long = orb_strategy.evaluate_breakout("SPY", df_long.iloc[:21], or_high, or_low)
    print(f"\n2. RUPTURA ALCISTA (LONG con Volumen Surge):")
    assert breakout_long is not None, "Debe detectar ruptura alcista válida"
    print(f"   Dirección        : {breakout_long['direction']} ({breakout_long['option_type']})")
    print(f"   Precio Ruptura   : ${breakout_long['breakout_price']:.2f} > Techo ${or_high:.2f}")
    print(f"   Ratio de Volumen : {breakout_long['volume_ratio']}x (Requerido: >= 1.5x)")
    assert breakout_long["direction"] == "LONG"
    assert breakout_long["option_type"] == "CALL"
    assert breakout_long["volume_ratio"] >= 1.5

    # 3. TEST: Ruptura Falsa Alcista (Fakeout - Volumen Débil < 1.5x)
    df_fake_long = create_synthetic_orb_data(base_price=560.0, breakout_type="LONG", volume_surge=False)
    fakeout_res = orb_strategy.evaluate_breakout("SPY", df_fake_long.iloc[:21], or_high, or_low)
    print(f"\n3. FILTRO DE FAKEOUT (Ruptura con Volumen Débil):")
    print(f"   Resultado: {fakeout_res} (Señal correctamente descartada)")
    assert fakeout_res is None, "Debe descartar la ruptura si el volumen no supera 1.5x"

    # 4. TEST: Ruptura Bajista con Volumen Fuerte (>= 1.5x) -> PUT
    df_short = create_synthetic_orb_data(base_price=560.0, breakout_type="SHORT", volume_surge=True)
    breakout_short = orb_strategy.evaluate_breakout("SPY", df_short.iloc[:21], or_high, or_low)
    print(f"\n4. RUPTURA BAJISTA (SHORT con Volumen Surge):")
    assert breakout_short is not None, "Debe detectar ruptura bajista válida"
    print(f"   Dirección        : {breakout_short['direction']} ({breakout_short['option_type']})")
    print(f"   Precio Ruptura   : ${breakout_short['breakout_price']:.2f} < Piso ${or_low:.2f}")
    print(f"   Ratio de Volumen : {breakout_short['volume_ratio']}x (Requerido: >= 1.5x)")
    assert breakout_short["direction"] == "SHORT"
    assert breakout_short["option_type"] == "PUT"
    assert breakout_short["volume_ratio"] >= 1.5

    # 5. TEST: Estructura de Alerta de Opciones y 1 Solo Contrato Global Fijo
    signal = orb_strategy.generate_signal_payload(breakout_long)
    print(f"\n5. ESTRUCTURA DE ALERTA DE OPCIONES & RIESGO:")
    print(f"   Subyacente      : {signal['symbol']}")
    print(f"   Tipo Contrato   : {signal['option_type']}")
    print(f"   Strike          : ${signal['strike_price']}")
    print(f"   Vencimiento     : {signal['expiration_date']}")
    print(f"   Prima Estimada  : ${signal['premium_est']}")
    print(f"   Stop Loss Prima : ${signal['premium_stop_loss']} (-28%)")
    print(f"   Take Profit 1   : ${signal['premium_take_profit']} (+50%)")
    print(f"   Contratos Fijos : {signal['contracts']} contrato")
    assert signal["contracts"] == 1, "Los contratos deben ser exactamente 1 contrato fijo"
    assert signal["contracts_or_shares"] == 1, "contracts_or_shares debe ser exactamente 1"
    assert signal["premium_stop_loss"] < signal["premium_est"]
    assert signal["premium_take_profit"] > signal["premium_est"]

    print("\n==================================================================")
    print(">>> TODOS LOS TESTS DE LA ESTRATEGIA ORB PASARON AL 100% (5/5) <<<")
    print("==================================================================")

if __name__ == "__main__":
    test_orb_suite()
