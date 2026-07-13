# -*- coding: utf-8 -*-
"""
Created on Sun Jul 12 09:25:48 2026

@author: mohak
"""

from dataclasses import dataclass


@dataclass
class Strategy2Config:

    history_window: int = 60

    ema_fast_period: int = 20

    ema_slow_period: int = 50

    delivery_short_window: int = 5

    delivery_medium_window: int = 20

    delivery_long_window: int = 60

    volume_short_window: int = 5

    volume_medium_window: int = 20

    volume_long_window: int = 60

    delivery_recent_weight: float = 0.50

    delivery_medium_weight: float = 0.50

    volume_recent_weight: float = 0.50

    volume_medium_weight: float = 0.50

    delivery_weight: float = 0.50

    volume_weight: float = 0.50

    top_n: int = 25