# -*- coding: utf-8 -*-
"""
Created on Sun Jun 21 21:47:55 2026

@author: mohak
"""

def get_band(
    price: int,
    band_size: int
) -> int:

    return (
        price // band_size
    )


def band_changed(
    current_band: int,
    previous_band: int | None
) -> bool:

    if previous_band is None:

        return False

    return (
        current_band
        != previous_band
    )