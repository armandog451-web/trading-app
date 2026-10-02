import logging
import numpy as np
from database import get_connection

logger = logging.getLogger(__name__)

class BacktestValidator:
    def __init__(self, expected_win_rate: float = 0.62, max_tolerated_dd: float = 0.04):
        self.expected_win_rate = expected_win_rate
        self.max_tolerated_dd = max_tolerated_dd
        self.trade_history = []  # Lista de P&L porcentuales o binarios (1: win, 0: loss)
        self._load_history_from_db()

    def _load_history_from_db(self):
        """Carga el historial reciente de operaciones cerradas desde la base de datos."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pnl FROM signals 
                WHERE status = 'EJECUTADA' AND pnl IS NOT NULL AND pnl != 0.0
                ORDER BY id ASC LIMIT 50
            """)
            rows = cursor.fetchall()
            conn.close()
            for r in rows:
                self.trade_history.append(float(r["pnl"]))
            if self.trade_history:
                logger.info(f"BacktestValidator: {len(self.trade_history)} operaciones históricas cargadas.")
        except Exception as e:
            logger.debug(f"Error cargando historial para BacktestValidator: {e}")

    def record_trade(self, pnl: float):
        self.trade_history.append(pnl)
        health = self.evaluate_health()
        logger.info(f"BacktestValidator: Trade registrado (P&L: {pnl:+.2f}). Estado de salud: {health['status']} (Multiplicador: {health['size_multiplier']}x)")

    def evaluate_health(self) -> dict:
        """Evalúa las últimas 20 operaciones contra el perfil del backtest."""
        if len(self.trade_history) < 20:
            return {
                "status": "WARMUP",
                "action": "CONTINUE",
                "size_multiplier": 1.0,
                "current_win_rate": round(len([p for p in self.trade_history if p > 0]) / max(1, len(self.trade_history)) * 100, 1) if self.trade_history else 0.0,
                "expected_win_rate": round(self.expected_win_rate * 100, 1),
                "trades_count": len(self.trade_history),
                "reason": f"Fase de calentamiento ({len(self.trade_history)}/20 operaciones necesarias)"
            }

        recent = self.trade_history[-20:]
        wins = [p for p in recent if p > 0]
        current_win_rate = len(wins) / len(recent)
        
        # 1. Fallo severo: Detener ejecución
        if current_win_rate < (self.expected_win_rate - 0.20):
            logging.critical("Falla estructural de estrategia: Win rate colapsado.")
            return {
                "status": "CIRCUIT_BREAKER",
                "action": "PAUSE_TRADING",
                "reason": f"Win Rate real ({current_win_rate:.2%}) muy inferior al backtest ({self.expected_win_rate:.2%})",
                "size_multiplier": 0.0,
                "current_win_rate": round(current_win_rate * 100, 1),
                "expected_win_rate": round(self.expected_win_rate * 100, 1),
                "trades_count": len(recent)
            }

        # 2. Desviación moderada: Reducir tamaño a la mitad y exigir más filtro
        if current_win_rate < (self.expected_win_rate - 0.10):
            logging.warning("Desviación detectada: Reduciendo tamaño de posición.")
            return {
                "status": "DEGRADED",
                "action": "REDUCE_SIZE",
                "size_multiplier": 0.5,  # Orden máxima pasa de $300 a $150
                "reason": f"Desviación moderada de Win Rate ({current_win_rate:.2%} vs esperado {self.expected_win_rate:.2%})",
                "current_win_rate": round(current_win_rate * 100, 1),
                "expected_win_rate": round(self.expected_win_rate * 100, 1),
                "trades_count": len(recent)
            }

        return {
            "status": "HEALTHY",
            "action": "CONTINUE",
            "size_multiplier": 1.0,
            "current_win_rate": round(current_win_rate * 100, 1),
            "expected_win_rate": round(self.expected_win_rate * 100, 1),
            "trades_count": len(recent),
            "reason": f"Estrategia saludable (Win Rate real {current_win_rate:.2%} en línea con backtest)"
        }

backtest_validator = BacktestValidator()
