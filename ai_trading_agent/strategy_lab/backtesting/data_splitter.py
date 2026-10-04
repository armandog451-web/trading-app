"""
ai_trading_agent.strategy_lab.backtesting.data_splitter
========================================================
División estricta de datos (In-Sample, Out-of-Sample, Walk-Forward, Final Holdout)
para la prevención total de Data Leakage y Look-Ahead Bias.
"""

from typing import List, Tuple, Dict, Any
from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.strategy_lab.core.models import DataSplitType


class LabDataSplitter:
    """Divide series temporales cronológicas para investigación cuantitativa."""

    @staticmethod
    def split_in_sample_out_sample_holdout(
        bars: List[OHLCVBar],
        in_sample_ratio: float = 0.60,
        out_sample_ratio: float = 0.20
    ) -> Dict[DataSplitType, List[OHLCVBar]]:
        """
        Divide las barras cronológicas en:
        - IN_SAMPLE (60%)
        - OUT_OF_SAMPLE (20%)
        - FINAL_HOLDOUT (20% Protegido)
        """
        if not bars:
            return {
                DataSplitType.IN_SAMPLE: [],
                DataSplitType.OUT_OF_SAMPLE: [],
                DataSplitType.FINAL_HOLDOUT: []
            }

        n = len(bars)
        is_idx = int(n * in_sample_ratio)
        oos_idx = is_idx + int(n * out_sample_ratio)

        return {
            DataSplitType.IN_SAMPLE: bars[:is_idx],
            DataSplitType.OUT_OF_SAMPLE: bars[is_idx:oos_idx],
            DataSplitType.FINAL_HOLDOUT: bars[oos_idx:]
        }

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
