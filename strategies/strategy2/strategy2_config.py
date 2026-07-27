# -*- coding: utf-8 -*-
"""
Created on Sun Jul 12 09:25:48 2026

@author: mohak
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class Strategy2Config:

    # ==========================
    # Data
    # ==========================

    history_window: int = 60

    # Optional.
    # Production -> None
    # Backtesting -> supplied by Experiment
    start_date: date | None = None

    end_date: date | None = None

    # ==========================
    # RSI
    # ==========================

    rsi_period: int = 14

    # ==========================
    # Trend
    # ==========================

    ema_fast_period: int = 20

    ema_slow_period: int = 50

    # ==========================
    # Delivery
    # ==========================

    delivery_short_window: int = 5

    delivery_medium_window: int = 20

    delivery_long_window: int = 60

    delivery_recent_weight: float = 0.50

    delivery_medium_weight: float = 0.50

    # ==========================
    # Volume
    # ==========================

    volume_short_window: int = 5

    volume_medium_window: int = 20

    volume_long_window: int = 60

    volume_recent_weight: float = 0.50

    volume_medium_weight: float = 0.50

    # ==========================
    # Final Score
    # ==========================

    delivery_weight: float = 1.00

    volume_weight: float = 0.00

    # ==========================
    # Output
    # ==========================

    top_n: int = 10