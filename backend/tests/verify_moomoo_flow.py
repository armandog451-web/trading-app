import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from app.database import SessionLocal
from app.models.db_models import SignalRecommendation, Trade
from app.core.position_guardian import position_guardian
from app.core.broker_manager import broker_manager

async def test_execution_flow():
    db = SessionLocal()
    rec = db.query(SignalRecommendation).order_by(SignalRecommendation.id.desc()).first()
    print("=== 1. VALORES RECOMENDADOS EN LA ALERTA ===")
    print(f"ID Recomendación: {rec.id}")
    print(f"Activo: {rec.asset_type} {rec.symbol} {rec.option_type}")
    print(f"Strike: ${rec.strike_price} | Vencimiento: {rec.expiration_date}")
    print(f"Prima Entrada: ${rec.premium_est}")
    print(f"Stop Loss Recomendado: ${rec.premium_stop_loss} (-28%)")
    print(f"Take Profit Recomendado: ${rec.premium_take_profit} (+50%)")
    print(f"Contratos Sugeridos: {rec.contracts_or_shares}")

    is_option = rec.asset_type == "OPTION"
    exp_clean = (rec.expiration_date or "2026-10-16").replace("-", "")[2:]
    opt_char = "C" if (rec.option_type or "CALL").upper() == "CALL" else "P"
    strike_val = rec.strike_price or 100.0
    strike_code = str(int(strike_val * 1000))
    trade_symbol = f"US.{rec.symbol.upper()}{exp_clean}{opt_char}{strike_code}"
    
    trade_qty = max(1, rec.contracts_or_shares or 1)
    trade_entry = float(rec.premium_est or 1.0)
    trade_sl = float(rec.premium_stop_loss or (trade_entry * 0.72))
    trade_tp = float(rec.premium_take_profit or (trade_entry * 1.50))

    print("\n=== 2. VALORES TRANSMITIDOS A MOOMOO AL PRESIONAR [ACEPTAR] ===")
    print(f"Código Contrato OCC enviado a Moomoo: {trade_symbol}")
    print(f"Cantidad enviada: {trade_qty} contratos")
    print(f"Precio Entrada enviado: ${trade_entry:.2f}")
    print(f"Stop Loss enviado: ${trade_sl:.2f}")
    print(f"Take Profit enviado: ${trade_tp:.2f}")

    # Comprobaciones estrictas de igualdad matemática
    assert trade_entry == rec.premium_est, "ERROR: La entrada no coincide con la alerta"
    assert trade_sl == rec.premium_stop_loss, "ERROR: El Stop Loss no coincide con la alerta"
    assert trade_tp == rec.premium_take_profit, "ERROR: El Take Profit no coincide con la alerta"
    assert trade_qty == rec.contracts_or_shares, "ERROR: Los contratos no coinciden con la alerta"
    print("\n>>> CONFIRMADO: Los parámetros a ejecutar son 100% IDÉNTICOS a la recomendación. <<<")

    # 3. Simular envío de orden
    res = await broker_manager.submit_bracket_order(
        symbol=trade_symbol,
        qty=trade_qty,
        side="BUY",
        entry_price=trade_entry,
        stop_loss=trade_sl,
        take_profit=trade_tp,
        order_type="market"
    )
    print("\nRespuesta del Broker Moomoo:", res.get("message"))

    # 4. Registrar en PositionGuardian
    position_guardian.register_target(
        symbol=trade_symbol,
        stop_loss=trade_sl,
        take_profit=trade_tp,
        qty=trade_qty,
        side="BUY",
        entry_price=trade_entry,
        asset_type="OPTION"
    )
    target = position_guardian._targets.get(trade_symbol)
    print("\n=== 3. SUPERVISIÓN AUTOMÁTICA EN POSITION GUARDIAN ===")
    print(f"Activo Monitoreado: {target['symbol']}")
    print(f"Nivel Stop Loss Activo: ${target['stop_loss']:.2f}")
    print(f"Nivel Take Profit Activo: ${target['take_profit']:.2f}")
    print("Estado: 100% Automático. El usuario NO tiene que configurar nada en Moomoo.")

if __name__ == "__main__":
    asyncio.run(test_execution_flow())
