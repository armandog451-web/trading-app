#!/usr/bin/env python3
# =====================================================================
# AGENTE ANTIGRAVITY: DEMOSTRADOR Y VALIDADOR DE BACKTESTING MT5
# =====================================================================
import sys
import os
import asyncio
from pathlib import Path

# Añadir 'backend' al path de Python
root_dir = Path(__file__).resolve().parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.mt5.mt5_connector import mt5_connector
from app.backtest.mt5_backtest_engine import mt5_backtest_engine


async def main():
    print("=" * 70)
    print(" MOTOR CUANTITATIVO TRADEPULSE: BACKTESTING METATRADER 5 (MT5)")
    print(" Estrategia: Order Blocks (OB) + Filtro RVOL + EMA 50/200")
    print("=" * 70)

    # 1. Verificar e inicializar conexión a MetaTrader 5
    print("\n[1/3] Conectando con MetaTrader 5 Terminal local...")
    if not mt5_connector.initialize():
        print("[-] Error: No se pudo conectar al terminal MT5. Asegúrate de tener MT5 instalado o abierto.")
        return

    status = mt5_connector.get_terminal_status()
    t_info = status.get("terminal_info", {})
    print(f"[+] Terminal Conectado: {t_info.get('name', 'MT5')} Build {t_info.get('build', 'N/A')} [{t_info.get('company', 'MetaQuotes')}]")
    print(f"[+] Ruta de datos: {t_info.get('data_path', 'N/A')}")

    # 2. Ejecutar Backtest sobre EURUSD (M5) y SPY (M5)
    test_universe = ["EURUSD", "SPY"]
    for sym in test_universe:
        print("\n" + "-" * 70)
        print(f"[2/3] Ejecutando simulación histórica para {sym} (Velas 5 Minutos)...")
        print("-" * 70)

        res = await mt5_backtest_engine.run_mt5_backtest(
            symbols=[sym],
            timeframe="M5",
            bars_count=1000,
            initial_capital=100000.0,
            risk_per_trade_pct=1.0,
            rvol_threshold=1.4,
            tp1_rr=1.5,
            tp2_rr=3.0
        )

        print("\n=== RESULTADOS INSTITUCIONALES DEL BACKTEST ===")
        print(f"• Estrategia:          {res['strategy']}")
        print(f"• Fuente de Datos:     {res['data_source']}")
        print(f"• Temporalidad:        {res['timeframe']} ({sym})")
        print(f"• Capital Inicial:     ${res['initial_capital']:,.2f}")
        print(f"• Capital Final:       ${res['final_equity']:,.2f}")
        print(f"• Ganancia Neta:       ${res['net_profit']:+,.2f} ({res['total_return_pct']:+.2f}%)")
        print(f"• Factor de Beneficio: {res['profit_factor']}")
        print(f"• Tasa de Acierto:     {res['win_rate_pct']}%")
        print(f"• Drawdown Máximo:     -{res['max_drawdown_pct']}% (${res['max_drawdown_dollar']:,.2f})")
        print(f"• Ratio de Sharpe:     {res['sharpe_ratio']}")
        print(f"• Total Operaciones:   {res['total_trades']} ({res['winning_trades']} Ganadas / {res['losing_trades']} Perdidas / {res['breakeven_trades']} Breakeven)")

        if res['trades']:
            print("\nÚltimos 3 Trades de la Simulación:")
            for t in res['trades'][-3:]:
                print(f"  [{t['entry_time']}] {t['side']} {t['symbol']} @ {t['entry_price']} -> Salida: {t['exit_price']} | PnL: ${t['pnl']} ({t['exit_reason']})")

    # 3. Notificación y Cierre
    print("\n[3/3] Cerrando conexión segura con MT5...")
    mt5_connector.shutdown()
    print("[+] Proceso completado exitosamente.\n")


if __name__ == "__main__":
    asyncio.run(main())
