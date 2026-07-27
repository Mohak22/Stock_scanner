# -*- coding: utf-8 -*-
"""
Created on Mon Jul 27 13:24:31 2026

@author: mohak
"""

"""
Strategy 2 hyperparameter experiment plan.

The first tuning stage is diagnostic:
- Keep windows fixed at 5 / 20 / 60
- Keep EMA and RSI fixed
- Keep top_n fixed at 10
- Test Delivery vs Volume contribution
- Test internal recent vs medium weighting

This intentionally avoids a large Cartesian grid.
"""

from dataclasses import replace

from strategies.strategy2.strategy2_config import (
    Strategy2Config
)


def generate_strategy2_experiments(
) -> list[tuple[str, Strategy2Config]]:

    # =====================================================
    # BASELINE
    # =====================================================

    baseline = Strategy2Config(

        history_window=60,

        rsi_period=14,

        ema_fast_period=20,
        ema_slow_period=50,

        delivery_short_window=5,
        delivery_medium_window=20,
        delivery_long_window=60,

        delivery_recent_weight=0.50,
        delivery_medium_weight=0.50,

        volume_short_window=5,
        volume_medium_window=20,
        volume_long_window=60,

        volume_recent_weight=0.50,
        volume_medium_weight=0.50,

        delivery_weight=0.50,
        volume_weight=0.50,

        top_n=10

    )

    experiments = [

        # =================================================
        # STAGE 1
        # DELIVERY vs VOLUME
        # =================================================

        (
            "s2_001_delivery_only",

            replace(
                baseline,
                delivery_weight=1.00,
                volume_weight=0.00
            )
        ),

        (
            "s2_002_delivery_75_volume_25",

            replace(
                baseline,
                delivery_weight=0.75,
                volume_weight=0.25
            )
        ),

        (
            "s2_003_equal_weight",

            baseline
        ),

        (
            "s2_004_delivery_25_volume_75",

            replace(
                baseline,
                delivery_weight=0.25,
                volume_weight=0.75
            )
        ),

        (
            "s2_005_volume_only",

            replace(
                baseline,
                delivery_weight=0.00,
                volume_weight=1.00
            )
        ),

        # =================================================
        # STAGE 2
        # DELIVERY INTERNAL WEIGHTING
        #
        # Final Delivery/Volume remains 50/50.
        # Volume internal weighting remains 50/50.
        # =================================================

        (
            "s2_006_delivery_recent_70",

            replace(
                baseline,
                delivery_recent_weight=0.70,
                delivery_medium_weight=0.30
            )
        ),

        (
            "s2_007_delivery_recent_30",

            replace(
                baseline,
                delivery_recent_weight=0.30,
                delivery_medium_weight=0.70
            )
        ),

        # =================================================
        # STAGE 3
        # VOLUME INTERNAL WEIGHTING
        #
        # Final Delivery/Volume remains 50/50.
        # Delivery internal weighting remains 50/50.
        # =================================================

        (
            "s2_008_volume_recent_70",

            replace(
                baseline,
                volume_recent_weight=0.70,
                volume_medium_weight=0.30
            )
        ),

        (
            "s2_009_volume_recent_30",

            replace(
                baseline,
                volume_recent_weight=0.30,
                volume_medium_weight=0.70
            )
        )

    ]

    return experiments