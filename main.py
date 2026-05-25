# -*- coding: utf-8 -*-
"""
Created on Mon May 18 15:47:53 2026

@author: mohak
"""

from __future__ import annotations

import pandas as pd

from fetch.market_data_fetching import (
    fetch_market_data
)

from fetch.sector_data_fetching import (
    fetch_sector_data,
    load_master_universe
)

from fetch.stock_data_fetching import (
    fetch_stock_data
)

from indicators.rsi_engine import (
    calculate_rsi
)

from filters.market_filter import (
    analyze_market_condition
)

from filters.sector_filter import (
    filter_weak_sectors
)

from filters.stock_filter import (
    filter_weak_stocks
)

from reports.excel_report_generator import (
    generate_excel_report
)

from reports.email_sender import (
    send_market_warning_email,
    send_no_sector_email,
    send_no_stock_email,
    send_stock_report_email
)

# =========================================================
# BUILD MARKET DATAFRAME
# =========================================================

def build_market_dataframe(
    market_data: dict
) -> pd.DataFrame:

    market_rows = []

    for (
        market_name,
        close_prices
    ) in market_data.items():

        market_rows.append({

            "Market":
                market_name,

            "RSI_9":
                calculate_rsi(
                    close_prices,
                    9
                ),

            "RSI_14":
                calculate_rsi(
                    close_prices,
                    14
                )
        })

    market_dataframe = pd.DataFrame(
        market_rows
    )

    return (

        market_dataframe

        .sort_values(
            by="RSI_14"
        )

        .reset_index(
            drop=True
        )
    )

# =========================================================
# BUILD SECTOR DATAFRAME
# =========================================================

def build_sector_dataframe(
    sector_data: dict
) -> pd.DataFrame:

    sector_rows = []

    for (
        sector_name,
        close_prices
    ) in sector_data.items():

        sector_rows.append({

            "Sector":
                sector_name,

            "RSI_9":
                calculate_rsi(
                    close_prices,
                    9
                ),

            "RSI_14":
                calculate_rsi(
                    close_prices,
                    14
                )
        })

    sector_dataframe = pd.DataFrame(
        sector_rows
    )

    return (

        sector_dataframe

        .sort_values(
            by="RSI_14"
        )

        .reset_index(
            drop=True
        )
    )

# =========================================================
# BUILD STOCK DATAFRAME
# =========================================================

def build_stock_dataframe(
    stock_data: dict,
    master_dataframe: pd.DataFrame,
    sector_dataframe: pd.DataFrame
) -> pd.DataFrame:

    stock_rows = []

    for (
        stock_name,
        close_prices
    ) in stock_data.items():

        stock_information = (

            master_dataframe[

                master_dataframe["Symbol"]
                == stock_name
            ]

            .iloc[0]
        )

        sector_name = (
            stock_information["sector"]
        )

        sector_rsi_14 = (

            sector_dataframe[

                sector_dataframe["Sector"]
                == sector_name
            ]

            .iloc[0]["RSI_14"]
        )

        stock_rows.append({

            "Stock":
                stock_name,

            "Sector":
                sector_name,

            "Industry":
                stock_information["Industry"],

            "Sector_RSI_14":
                round(
                    sector_rsi_14,
                    2
                ),

            "RSI_9":
                round(
                    calculate_rsi(
                        close_prices,
                        9
                    ),
                    2
                ),

            "RSI_14":
                round(
                    calculate_rsi(
                        close_prices,
                        14
                    ),
                    2
                )
        })

    stock_dataframe = pd.DataFrame(
        stock_rows
    )

    return (

        stock_dataframe

        .sort_values(
            by=[
                "Sector_RSI_14",
                "RSI_14"
            ]
        )

        .reset_index(
            drop=True
        )
    )

# =========================================================
# MAIN
# =========================================================

def main() -> None:

    # =====================================================
    # LOAD MASTER UNIVERSE
    # =====================================================

    master_dataframe = (
        load_master_universe(
            "config/master_universe.csv"
        )
    )

    # =====================================================
    # MARKET ANALYSIS
    # =====================================================

    market_data = (
        fetch_market_data()
    )

    market_dataframe = (
        build_market_dataframe(
            market_data
        )
    )

    market_status = (
        analyze_market_condition(
            market_dataframe
        )
    )

    print(
        "\nMarket Analysis:\n"
    )

    print(
        market_dataframe
    )

    print(
        f"\nMarket Status: "
        f"{market_status}"
    )

    # =====================================================
    # PANIC MARKET EXIT
    # =====================================================

    if market_status == "PANIC":

        send_market_warning_email(
            market_dataframe,
            market_status
        )

        return

    # =====================================================
    # SECTOR ANALYSIS
    # =====================================================

    sector_data = (
        fetch_sector_data(
            master_dataframe
        )
    )

    sector_dataframe = (
        build_sector_dataframe(
            sector_data
        )
    )

    weak_sector_dataframe = (
        filter_weak_sectors(
            sector_dataframe
        )
    )

    print(
        "\nWeak Sectors:\n"
    )

    print(
        weak_sector_dataframe
    )

    # =====================================================
    # NO WEAK SECTORS
    # =====================================================

    if weak_sector_dataframe.empty:

        send_no_sector_email()

        return

    # =====================================================
    # STOCK ANALYSIS
    # =====================================================

    stock_data = (
        fetch_stock_data(
            weak_sector_dataframe,
            master_dataframe
        )
    )

    stock_dataframe = (
        build_stock_dataframe(
            stock_data,
            master_dataframe,
            sector_dataframe
        )
    )

    weak_stock_dataframe = (
        filter_weak_stocks(
            stock_dataframe
        )
    )

    print(
        "\nWeak Stocks:\n"
    )

    print(
        weak_stock_dataframe
    )
    
    # =====================================================
    # NO WEAK STOCKS
    # =====================================================

    if weak_stock_dataframe.empty:

        send_no_stock_email()

        return

    # =====================================================
    # GENERATE EXCEL REPORT
    # =====================================================

    generate_excel_report(
        weak_stock_dataframe
    )

    # =====================================================
    # SEND FINAL EMAIL
    # =====================================================

    send_stock_report_email(
        weak_stock_dataframe
    )
# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()