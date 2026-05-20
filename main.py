# -*- coding: utf-8 -*-
"""
Created on Mon May 18 15:47:53 2026

@author: mohak
"""

import logging

from fetch.stock_data_fetching import (
    fetch_all_stock_data,
    load_master_universe
)

from indicators.stock_rsi_engine import (
    calculate_stock_rsi,
    filter_oversold_stocks
)

from reports.email_sender import (
    send_email_report
)

# =========================================================
# LOGGING CONFIGURATION
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# =========================================================
# MAIN PIPELINE
# =========================================================

def main() -> None:

    logger.info(
        "Starting RSI Scanner..."
    )

    # =====================================================
    # LOAD UNIVERSE
    # =====================================================

    master_dataframe = (
        load_master_universe(
            "config/master_universe.csv"
        )
    )

    # =====================================================
    # FETCH STOCK DATA
    # =====================================================

    stock_data = (
        fetch_all_stock_data(
            master_dataframe
        )
    )

    logger.info(
        "Stock data fetched successfully."
    )

    # =====================================================
    # CALCULATE RSI
    # =====================================================

    rsi_dataframe = (
        calculate_stock_rsi(
            stock_data
        )
    )

    logger.info(
        "RSI calculation completed."
    )

    # =====================================================
    # FILTER OVERSOLD STOCKS
    # =====================================================

    oversold_dataframe = (
        filter_oversold_stocks(
            rsi_dataframe
        )
    )

    logger.info(
        "Oversold stocks found: %s",
        len(oversold_dataframe)
    )

    print("\n========================")
    print("OVERSOLD STOCKS")
    print("========================\n")

    print(oversold_dataframe)

    # =====================================================
    # SEND EMAIL REPORT
    # =====================================================

    send_email_report(
        oversold_dataframe
    )

# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()