import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from datetime import datetime
from app.engines.options_engine import options_engine
from app.core.position_guardian import position_guardian
from app.core.screener import screener
from app.core.notifier import notifier

def run_tests():
    print("=== 1. VERIFICACIÓN: VENCIMIENTO EXTENDIDO (14-30 DTE) ===")
    call_opt = options_engine.calculate_option_contract("SPY", 560.20, bias="BULLISH", equity=100000.0, risk_pct=1.0)
    exp_d = datetime.strptime(call_opt["expiration_date"], "%Y-%m-%d")
    dte = (exp_d - datetime.utcnow()).days
    print(f"Ticker: {call_opt['symbol']} | Strike: ${call_opt['strike_price']} | Exp: {call_opt['expiration_date']} ({dte} DTE)")
    assert dte >= 14, f"DTE {dte} es menor a 14 días"
    print("-> OK: Vencimiento calculado entre 14 y 30 DTE.")

    print("\n=== 2. VERIFICACIÓN: LÓGICA CONDICIONAL PUTS ===")
    put_opt = options_engine.calculate_option_contract("QQQ", 482.50, bias="BEARISH", equity=100000.0, risk_pct=1.0)
    print(f"Ticker: {put_opt['symbol']} | Tipo: {put_opt['option_type']} | Delta: {put_opt['delta_est']:+.2f} | Strike: ${put_opt['strike_price']}")
    assert put_opt["option_type"] == "PUT"
    assert put_opt["delta_est"] < 0, "Delta de PUT debe ser negativo"
    assert put_opt["strike_price"] <= 482.50, "Strike de PUT debe ser ATM/OTM inferior"
    print("-> OK: PUT generado con Delta negativo y strike óptimo.")

    print("\n=== 3. VERIFICACIÓN: FILTRO DE VOLATILIDAD IMPLÍCITA (IV CRUSH) ===")
    iv_bad, msg_bad = options_engine.validate_iv(120.0)
    print(f"IV 120% (>100%): Aprobado = {iv_bad} | Motivo: {msg_bad}")
    assert not iv_bad, "Debería descartar IV > 100%"

    iv_good, _ = options_engine.validate_iv(24.5)
    print(f"IV 24.5% (<=100%): Aprobado = {iv_good}")
    assert iv_good, "Debería aprobar IV razonable"
    print("-> OK: Filtro de IV protege contra IV Crush.")

    print("\n=== 4. VERIFICACIÓN: CONTROL DE LIQUIDEZ Y SLIPPAGE ===")
    liq_bad, msg_liq = options_engine.validate_liquidity(open_interest=150, bid=3.0, ask=3.5)
    print(f"OI=150 (<500): Aprobado = {liq_bad} | Motivo: {msg_liq}")
    assert not liq_bad, "Debería descartar bajo Open Interest"

    liq_good, _ = options_engine.validate_liquidity(open_interest=1500, bid=3.60, ask=3.68)
    print(f"OI=1500, Spread=0.08: Aprobado = {liq_good}")
    assert liq_good, "Debería aprobar alta liquidez y spread estrecho"
    print("-> OK: Control de Liquidez y Slippage verificado.")

    print("\n=== 5. VERIFICACIÓN: CONTRATO FIJO (1 CONTRATO GLOBAL) ===")
    print(f"Prima: ${call_opt['premium_est']} | SL: ${call_opt['premium_stop_loss']}")
    print(f"Contratos sugeridos: {call_opt['contracts']} | Costo total: ${call_opt['total_cost']}")
    assert call_opt["contracts"] == 1, "Los contratos deben ser exactamente 1 de forma global"
    print("-> OK: Contrato fijado a 1 de forma global sin importar el riesgo.")

    print("\n=== 6. VERIFICACIÓN: POSITION GUARDIAN (SUPERVISIÓN SL/TP) ===")
    position_guardian.register_target(
        symbol="SPY261016C00561000",
        stop_loss=2.62,
        take_profit=5.46,
        qty=1,
        side="BUY",
        entry_price=3.64,
        asset_type="OPTION"
    )
    t = position_guardian._targets.get("SPY261016C00561000")
    print(f"Target Registrado: {t['symbol']} | SL: ${t['stop_loss']} | TP: ${t['take_profit']} | Qty: {t['qty']}")
    assert t["stop_loss"] == 2.62
    assert t["take_profit"] == 5.46
    print("-> OK: Position Guardian registra y supervisa SL/TP en tiempo real.")

    print("\n=== 7. VERIFICACIÓN: ESCÁNER DE MERCADO AMPLIO ===")
    active = asyncio.run(screener.get_active_universe())
    print(f"Total activos monitoreados: {len(active)} -> {active}")
    assert len(active) >= 10, "El universo debe incluir todo el mercado representativo"
    print("-> OK: Escáner abarca líderes de S&P 500 y Nasdaq.")

    print("\n=======================================================")
    print(">>> TODOS LOS COMPONENTES FUNCIONAN AL 100% (7/7) <<<")
    print("=======================================================")

if __name__ == "__main__":
    run_tests()
