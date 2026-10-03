"""
run_agent_tests.py
==================
Script de ejecución y validación de la suite de pruebas de AI Trading Agent 1.0.
"""

import sys
from pathlib import Path

# Asegurar que el root del proyecto esté en sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest

if __name__ == "__main__":
    print("=" * 70)
    print(" EJECUTANDO SUITE DE PRUEBAS DE SEGURIDAD Y CALIDAD - FASE 1")
    print("=" * 70)

    test_path = str(root_dir / "ai_trading_agent" / "tests")
    exit_code = pytest.main([test_path, "-v", "--tb=short"])

    print("=" * 70)
    if exit_code == 0:
        print(" [ÉXITO] TODAS LAS PRUEBAS CRÍTICAS HAN PASADO SATISFACTORIAMENTE.")
    else:
        print(f" [FALLO] Código de salida de pytest: {exit_code}")
    print("=" * 70)
    sys.exit(exit_code)
