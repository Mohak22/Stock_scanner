# -*- coding: utf-8 -*-
"""
Created on Mon May 18 15:47:53 2026

@author: mohak
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from fetch.market_data_fetching import fetch_market_data

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
    save_output
)

# =========================================================
# CONFIG
# =========================================================

STRATEGY_NAME = "strategy_1"


# =========================================================
# BUILD MARKET DATAFRAME
# =========================================================

def build_market_dataframe(
    market_data: dict
) -> pd.DataFrame:

    rows = []

    for market_name, close_prices in market_data.items():

        rows.append({

            "Market":
                market_name,

            "close_price":
                round(
                    close_prices.iloc[0],
                    2
                ),

            "RSI_9":
                round(
                    calculate_rsi(close_prices, 9),
                    2
                ),

            "RSI_14":
                round(
                    calculate_rsi(close_prices, 14),
                    2
                )
        })

    return (

        pd.DataFrame(rows)

        .sort_values(
            by="RSI_14"
        )

        .reset_index(drop=True)
    )

# =========================================================
# BUILD SECTOR DATAFRAME
# =========================================================

def build_sector_dataframe(
    sector_data: dict
) -> pd.DataFrame:

    rows = []

    for sector_name, close_prices in sector_data.items():

        rows.append({

            "Sector":
                sector_name,

            "close_price":
                round(
                    close_prices.iloc[0],
                    2
                ),

            "RSI_9":
                round(
                    calculate_rsi(close_prices, 9),
                    2
                ),

            "RSI_14":
                round(
                    calculate_rsi(close_prices, 14),
                    2
                )
        })

    return (

        pd.DataFrame(rows)

        .sort_values(
            by="RSI_14"
        )

        .reset_index(drop=True)
    )


# =========================================================
# BUILD STOCK DATAFRAME
# =========================================================

def build_stock_dataframe(
    stock_data: dict,
    master_dataframe: pd.DataFrame,
    market_dataframe: pd.DataFrame,
    sector_dataframe: pd.DataFrame
) -> pd.DataFrame:

    rows = []

    for stock_name, close_prices in stock_data.items():

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
        
        nifty_50_price = (

            market_dataframe[
            market_dataframe["Market"]
            == "NIFTY50"
            ]

            .iloc[0]["close_price"]
        )

        sector_price = (

            sector_dataframe[
                sector_dataframe["Sector"]
                == sector_name
            ]

            .iloc[0]["close_price"]
        )

        rows.append({

            "recommendation_date":
                datetime.now().strftime(
                    "%Y-%m-%d"
                ),

            "strategy_name":
                STRATEGY_NAME,

            "stock_symbol":
                stock_name,

            "sector":
                sector_name,

            "industry":
                stock_information["Industry"],

            "sector_rsi_14":
                round(
                    sector_rsi_14,
                    2
                ),

            "rsi_9":
                round(
                    calculate_rsi(
                        close_prices,
                        9
                    ),
                    2
                ),

            "rsi_14":
                round(
                    calculate_rsi(
                        close_prices,
                        14
                    ),
                    2
                ),

            "entry_close_price":
                round(
                    close_prices.iloc[0],
                    2
                ),

            "nifty_50_price":
                round(
                    nifty_50_price,
                    2
                ),

            "sector_price":
                round(
                    sector_price,
                    2
                )
        })

    dataframe = pd.DataFrame(rows)

    dataframe = (

        dataframe

        .sort_values(
            by=[
                "sector_rsi_14",
                "rsi_14"
            ]
        )

        .reset_index(drop=True)
    )


    return dataframe


# =========================================================
# RUN STRATEGY
# =========================================================

def run_strategy_1(
    save_output_flag: bool
) -> dict:

    master_dataframe = load_master_universe(
        "config/master_universe.csv"
    )

    # =====================================================
    # MARKET ANALYSIS
    # =====================================================

    market_data = fetch_market_data()

    market_dataframe = build_market_dataframe(
        market_data
    )

    market_status = analyze_market_condition(
        market_dataframe
    )

    print("\nMarket Analysis:\n")
    print(market_dataframe)

    print(
        f"\nMarket Status: {market_status}"
    )

    # =====================================================
    # PANIC MARKET EXIT
    # =====================================================

    if market_status == "PANIC":

        print(
            "\nPANIC market detected."
        )

        return {

            "market_status":
                market_status,

            "market_dataframe":
                market_dataframe,

            "sector_dataframe":
                pd.DataFrame(),

            "recommendations":
                pd.DataFrame()
        }

    # =====================================================
    # SECTOR ANALYSIS
    # =====================================================

    sector_data = fetch_sector_data(
        master_dataframe
    )

    sector_dataframe = build_sector_dataframe(
        sector_data
    )

    weak_sector_dataframe = filter_weak_sectors(
        sector_dataframe
    )

    print("\nWeak Sectors:\n")
    print(weak_sector_dataframe)

    # =====================================================
    # NO WEAK SECTORS
    # =====================================================

    if weak_sector_dataframe.empty:

        print(
            "\nNo weak sectors found."
        )

        return {

            "market_status":
                market_status,

            "market_dataframe":
                market_dataframe,

            "sector_dataframe":
                sector_dataframe,

            "recommendations":
                pd.DataFrame()
        }

    # =====================================================
    # STOCK ANALYSIS
    # =====================================================

    stock_data = fetch_stock_data(
        weak_sector_dataframe,
        master_dataframe
    )

    stock_dataframe = build_stock_dataframe(
        stock_data,
        master_dataframe,
        market_dataframe,
        sector_dataframe
    )

    weak_stock_dataframe = filter_weak_stocks(
        stock_dataframe
    )

    print("\nWeak Stocks:\n")
    print(weak_stock_dataframe)

    # =====================================================
    # NO WEAK STOCKS
    # =====================================================

    if weak_stock_dataframe.empty:

        print(
            "\nNo weak stocks found."
        )

        return {

            "market_status":
                market_status,

            "market_dataframe":
                market_dataframe,

            "sector_dataframe":
                sector_dataframe,

            "recommendations":
                pd.DataFrame()
        }

    # =====================================================
    # SAVE OUTPUT
    # =====================================================

    current_date = datetime.now().strftime(
        "%Y-%m-%d"
    )

    save_output(

        dataframe=weak_stock_dataframe,

        folder_name=(
            f"strategies/{STRATEGY_NAME}"
        ),

        file_name=(
            f"{STRATEGY_NAME}_{current_date}.csv"
        ),

        save_output=save_output_flag
    )

    # =====================================================
    # RETURN OUTPUT
    # =====================================================

    return {

        "market_status":
            market_status,

        "market_dataframe":
            market_dataframe,

        "sector_dataframe":
            sector_dataframe,

        "recommendations":
            weak_stock_dataframe
    }

