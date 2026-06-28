# -*- coding: utf-8 -*-
"""
Created on Mon May 18 15:47:53 2026

@author: mohak
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from typing import Dict

from fetch.market_data_fetching import fetch_market_data

from fetch.sector_data_fetching import (
    fetch_sector_data,
    load_master_universe
)

from fetch.stock_data_fetching import (
    fetch_stock_data
)

from indicators.rsi_engine import (
    calculate_rsi, calculate_rsi_series
)

from indicators.ema_engine import (
    calculate_ema
) 

from strategies.strategy1.filters.market_filter import (
    analyze_market_condition
)

from strategies.strategy1.filters.sector_filter import (
    filter_weak_sectors
)

from strategies.strategy1.filters.stock_filter import (
    filter_weak_stocks
)

from reports.excel_report_generator import (
    save_output
)

# =========================================================
# CONFIG
# =========================================================

STRATEGY_NAME = "strategy_1"

DATA_PERIOD = "3mo"

MARKET_INDEX_MAP = {

    "NIFTY50": "^NSEI",

    "MIDCAP":
        "NIFTY_MIDCAP_100.NS",

    "BANKNIFTY":
        "^NSEBANK"
}

RSI_SHORT_PERIOD = 9

RSI_LONG_PERIOD = 14

EMA_PERIOD = 50
# =========================================================
# BUILD MARKET DATAFRAME
# =========================================================

def build_market_dataframe(
    market_data: Dict[str, pd.Series]
) -> pd.DataFrame:

    rows = []

    for market_name, close_prices in market_data.items():

        rows.append({

            "Market":
                market_name,

            "close_price":
                round(
                    close_prices.iloc[-1],
                    2
                ),

            "RSI_9":
                calculate_rsi(
                    close_prices,
                    RSI_SHORT_PERIOD
                ),
            
            "RSI_14":
                calculate_rsi(
                    close_prices,
                    RSI_LONG_PERIOD
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
    sector_data: Dict[str, pd.Series]
) -> pd.DataFrame:

    rows = []

    for sector_name, close_prices in sector_data.items():

        rows.append({

            "Sector":
                sector_name,

            "close_price":
                round(
                    close_prices.iloc[-1],
                    2
                ),

            "RSI_9":
                calculate_rsi(
                    close_prices,
                    RSI_SHORT_PERIOD
                ),
            
            "RSI_14":
                calculate_rsi(
                    close_prices,
                    RSI_LONG_PERIOD
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

    master_lookup = (
    
        master_dataframe
    
        .drop_duplicates(
            subset="Symbol",
            keep="first"
        )
    
        .set_index("Symbol")
    
        .to_dict(
            orient="index"
        )
    )

    sector_lookup = (
    
        sector_dataframe
    
        .drop_duplicates(
            subset="Sector",
            keep="first"
        )
    
        .set_index("Sector")
    
        .to_dict(
            orient="index"
        )
    )

    for stock_name, stock_dataframe_raw  in stock_data.items():
        
        close_prices = (stock_dataframe_raw["Close"])
        
        stock_information = (
            master_lookup.get(
                stock_name
            )
        )

        sector_name = (
            stock_information["sector"]
        )
        
        matching_sector = (
            sector_lookup.get(
                sector_name
            )
        )

        if matching_sector is None:
        
            continue

        sector_rsi_14 = (
            matching_sector["RSI_14"]
        )

        nifty_50_price = (

            market_dataframe[
                market_dataframe["Market"]
                == "NIFTY50"
            ]

            .iloc[0]["close_price"]
        )

        sector_price = (
            matching_sector["close_price"]
        )

        rsi_14_series = calculate_rsi_series(
            close_prices,
            RSI_LONG_PERIOD
        )

        if len(rsi_14_series) < 2:

            print(
                f"RSI history is insufficient."
            )

            continue
        current_rsi_14 = round(
            rsi_14_series.iloc[-1],
            2
        )

        previous_rsi_14 = round(
            rsi_14_series.iloc[-2],
            2
        )
        
        current_volume = (
            stock_dataframe_raw["Volume"]
            .iloc[-1])

        avg_20_volume = (stock_dataframe_raw["Volume"].rolling(20).mean().iloc[-1])

        if avg_20_volume <= 0:
        
            volume_ratio = None
        
        else:
        
            volume_ratio = round(
                current_volume /
                avg_20_volume,
                2
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
                calculate_rsi(
                    close_prices,
                    RSI_SHORT_PERIOD
                ),

            "rsi_14":
                current_rsi_14,

            "previous_rsi_14":
                previous_rsi_14,

            "volume_ratio":
                volume_ratio,
                
            "ema_50":
                round(
                    calculate_ema(
                        close_prices,
                        EMA_PERIOD
                    ).iloc[-1],
                    2
                ),

            "entry_close_price":
                round(
                    close_prices.iloc[-1],
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

    market_data = fetch_market_data(
        market_index_map=MARKET_INDEX_MAP,
        period=DATA_PERIOD
    )

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
    
    for sector_name, close_prices in sector_data.items():

       print(
        sector_name,
        type(close_prices)
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

    weak_sectors = (
        weak_sector_dataframe["Sector"]
        .tolist()
    )
    
    filtered_dataframe = (
    
        master_dataframe[
    
            master_dataframe["sector"]
            .isin(weak_sectors)
        ]
    )
    
    symbols = (
    
        filtered_dataframe["Symbol"]
    
        .dropna()
    
        .unique()
    
        .tolist()
    )
    
    stock_data = fetch_stock_data(
    
        symbols=symbols,
    
        period=DATA_PERIOD,
    
        auto_adjust=False,
    
        exchange_suffix=".NS"
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

