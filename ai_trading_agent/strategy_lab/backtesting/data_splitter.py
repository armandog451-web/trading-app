"""
ai_trading_agent.strategy_lab.backtesting.data_splitter
========================================================
División estricta de datos (In-Sample, Out-of-Sample, Walk-Forward, Final Holdout)
para la prevención total de Data Leakage y Look-Ahead Bias.
"""

from typing import List, Tuple, Dict, Any
from datetime import datetime
import logging
from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.core.models import DataSplitType
from database import log_event

logger = logging.getLogger(__name__)


class ProtectedDataset:
    """
    Contenedor de dataset dividido con protección estricta (LOCKED) sobre FINAL_HOLDOUT.
    Evita Data Leakage y Overfitting impidiendo el acceso a Holdout durante optimización.
    """

    def __init__(self, splits: Dict[DataSplitType, List[OHLCVBar]]):
        self.splits = splits
        self.is_holdout_locked: bool = True
        self.unlock_audit_trail: List[Dict[str, Any]] = []

    def get_optimization_bars(self) -> List[OHLCVBar]:
        """Devuelve únicamente barras IN_SAMPLE y OUT_OF_SAMPLE para optimización/investigación."""
        in_sample = self.splits.get(DataSplitType.IN_SAMPLE, [])
        out_sample = self.splits.get(DataSplitType.OUT_OF_SAMPLE, [])
        return in_sample + out_sample

    def get_split(self, split_type: DataSplitType, purpose: str = "RESEARCH") -> List[OHLCVBar]:
        """
        Devuelve el subconjunto solicitado.
        Si se solicita FINAL_HOLDOUT mientras está LOCKED para propósito de optimización/investigación,
        lanza PermissionError.
        """
        if split_type == DataSplitType.FINAL_HOLDOUT and self.is_holdout_locked:
            if purpose.upper() in ["OPTIMIZATION", "RESEARCH", "MUTATION", "FITTING", "SEARCH"]:
                msg = "ACCESO DENEGADO: El dataset FINAL_HOLDOUT está estrictamente BLOQUEADO (LOCKED) para optimización e investigación."
                logger.error(msg)
                raise PermissionError(msg)

        return self.splits.get(split_type, [])

    def unlock_holdout(self, reason: str, actor: str = "HUMAN_AUDITOR") -> List[OHLCVBar]:
        """
        Desbloquea explícitamente el FINAL_HOLDOUT para auditoría final y registra la entrada inmutable.
        NUNCA debe llamarse automáticamente durante iteraciones de optimización.
        """
        self.is_holdout_locked = False
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "actor": actor,
            "reason": reason
        }
        self.unlock_audit_trail.append(audit_entry)
        log_event("WARNING", f"FINAL_HOLDOUT DESBLOQUEADO por {actor}. Razón: {reason}")
        return self.splits.get(DataSplitType.FINAL_HOLDOUT, [])


class LabDataSplitter:
    """Divide series temporales cronológicas para investigación cuantitativa."""

    @staticmethod
    def split_in_sample_out_sample_holdout(
        bars: List[OHLCVBar],
        in_sample_ratio: float = 0.60,
        out_sample_ratio: float = 0.20
    ) -> ProtectedDataset:
        """
        Divide las barras cronológicas en:
        - IN_SAMPLE (60%)
        - OUT_OF_SAMPLE (20%)
        - FINAL_HOLDOUT (20% Protegido / LOCKED)
        """
        if not bars:
            return ProtectedDataset({
                DataSplitType.IN_SAMPLE: [],
                DataSplitType.OUT_OF_SAMPLE: [],
                DataSplitType.FINAL_HOLDOUT: []
            })

        n = len(bars)
        is_idx = int(n * in_sample_ratio)
        oos_idx = is_idx + int(n * out_sample_ratio)

        splits = {
            DataSplitType.IN_SAMPLE: bars[:is_idx],
            DataSplitType.OUT_OF_SAMPLE: bars[is_idx:oos_idx],
            DataSplitType.FINAL_HOLDOUT: bars[oos_idx:]
        }
        return ProtectedDataset(splits)

    @staticmethod
    def generate_walk_forward_windows(
        bars: List[OHLCVBar],
        train_window_size: int = 60,
        test_window_size: int = 20,
        step_size: int = 20
    ) -> List[Tuple[List[OHLCVBar], List[OHLCVBar]]]:
        """
        Genera ventanas móviles Walk-Forward de Entrenamiento y Validación.
        """
        windows = []
        if len(bars) < (train_window_size + test_window_size):
            return windows

        start_idx = 0
        while (start_idx + train_window_size + test_window_size) <= len(bars):
            train_bars = bars[start_idx : start_idx + train_window_size]
            test_bars = bars[start_idx + train_window_size : start_idx + train_window_size + test_window_size]
            windows.append((train_bars, test_bars))
            start_idx += step_size

        return windows


lab_data_splitter = LabDataSplitter()
