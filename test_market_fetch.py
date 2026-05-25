# -*- coding: utf-8 -*-
"""
Created on Sun May 24 11:23:18 2026

@author: mohak
"""

from fetch.market_data_fetching import (
    fetch_market_data
)

from indicators.rsi_engine import (
    calculate_rsi
)

# =========================================================
# FETCH DATA
# =========================================================

market_data = fetch_market_data()

print("\n")

# =========================================================
# CALCULATE RSI
# =========================================================

for market_name, close_prices in (
    market_data.items()
):

    rsi_9 = calculate_rsi(
        close_prices,
        9
    )

    rsi_14 = calculate_rsi(
        close_prices,
        14
    )

    print(
        f"{market_name}"
    )

    print(
        f"RSI 9  : {rsi_9}"
    )

    print(
        f"RSI 14 : {rsi_14}"
    )

    print(
        "\n====================\n"
    )