# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 12:28:48 2026

@author: mohak
"""

from datetime import date, timedelta

import pandas as pd
import yfinance as yf


def calculate_returns(
    recommendations_df: pd.DataFrame,
    historical_prices: dict[str, pd.DataFrame] | None = None,
    nifty_prices: pd.DataFrame | None = None
) -> pd.DataFrame:
    """
    Calculate recommendation performance.

    Horizons
    --------
    BTST:
        Next trading session HIGH.

    7D:
        7 calendar days after recommendation.
        If target date is not a trading day, use the latest
        trading session on or before the target date.

    14D:
        14 calendar days after recommendation.
        If target date is not a trading day, use the latest
        trading session on or before the target date.

    Production
    ----------
    historical_prices=None
    nifty_prices=None

    Data is downloaded from yfinance.

    Backtesting
    -----------
    Supply:

        historical_prices = {
            "RELIANCE": DataFrame,
            "TCS": DataFrame,
            ...
        }

        nifty_prices = DataFrame

    Stock historical prices can come directly from NSE bhavcopy.
    """

    if recommendations_df.empty:

        return pd.DataFrame()

    analysis_rows = []

    # =====================================================
    # PREPARE NIFTY ONCE FOR BACKTESTING
    # =====================================================

    prepared_nifty_prices = None

    if nifty_prices is not None:

        prepared_nifty_prices = (
            _prepare_price_dataframe(
                nifty_prices
            )
        )

    # =====================================================
    # PROCESS RECOMMENDATIONS
    # =====================================================

    for _, row in recommendations_df.iterrows():

        # =================================================
        # RECOMMENDATION INFORMATION
        # =================================================

        symbol = _get_value(

            row=row,

            primary_column="stock_symbol",

            fallback_column="SYMBOL"

        )

        entry_price = float(

            _get_value(

                row=row,

                primary_column="entry_close_price",

                fallback_column="CLOSE"

            )

        )

        recommendation_date = pd.Timestamp(

            _get_value(

                row=row,

                primary_column="recommendation_date",

                fallback_column="TIMESTAMP"

            )

        ).normalize()

        target_7d = (
            recommendation_date
            + pd.Timedelta(days=7)
        )

        target_14d = (
            recommendation_date
            + pd.Timedelta(days=14)
        )

        # =================================================
        # STOCK PRICE DATA
        # =================================================

        if historical_prices is None:

            ticker = f"{symbol}.NS"

            price_df = yf.download(

                tickers=ticker,

                start=recommendation_date.date(),

                # yfinance end is exclusive
                end=(
                    target_14d.date()
                    + timedelta(days=1)
                ),

                progress=False,

                auto_adjust=False

            )

            price_df = _prepare_price_dataframe(
                price_df
            )

        else:

            if symbol not in historical_prices:

                continue

            price_df = _prepare_price_dataframe(

                historical_prices[
                    symbol
                ]

            )

            price_df = _filter_price_period(

                price_df=price_df,

                start_date=recommendation_date,

                end_date=target_14d

            )

        # =================================================
        # NIFTY PRICE DATA
        # =================================================

        if prepared_nifty_prices is None:

            nifty_df = yf.download(

                tickers="^NSEI",

                start=recommendation_date.date(),

                end=(
                    target_14d.date()
                    + timedelta(days=1)
                ),

                progress=False,

                auto_adjust=False

            )

            nifty_df = _prepare_price_dataframe(
                nifty_df
            )

        else:

            nifty_df = _filter_price_period(

                price_df=prepared_nifty_prices,

                start_date=recommendation_date,

                end_date=target_14d

            )

        # =================================================
        # BASIC VALIDATION
        # =================================================

        if len(price_df) < 2:

            continue

        if len(nifty_df) < 2:

            continue

        # =================================================
        # NIFTY ENTRY PRICE
        # =================================================

        nifty_entry_price = _get_optional_value(

            row=row,

            column="nifty_50_price"

        )

        if (
            nifty_entry_price is None
            or
            pd.isna(nifty_entry_price)
        ):

            nifty_entry_row = (
                _get_price_on_or_before(
                    price_df=nifty_df,
                    target_date=recommendation_date
                )
            )

            if nifty_entry_row is None:

                continue

            nifty_entry_price = float(
                nifty_entry_row["Close"]
            )

        else:

            nifty_entry_price = float(
                nifty_entry_price
            )

        # =================================================
        # BTST
        # =================================================

        next_stock_session = (
            _get_next_trading_session(
                price_df=price_df,
                recommendation_date=(
                    recommendation_date
                )
            )
        )

        next_nifty_session = (
            _get_next_trading_session(
                price_df=nifty_df,
                recommendation_date=(
                    recommendation_date
                )
            )
        )

        if (
            next_stock_session is None
            or
            next_nifty_session is None
        ):

            continue

        btst_high = float(
            next_stock_session["High"]
        )

        nifty_btst_high = float(
            next_nifty_session["High"]
        )

        btst_return = (

            (
                btst_high
                - entry_price
            )

            / entry_price

        ) * 100

        nifty_btst_return = (

            (
                nifty_btst_high
                - nifty_entry_price
            )

            / nifty_entry_price

        ) * 100

        btst_outperformance = (

            btst_return
            - nifty_btst_return

        )

        # =================================================
        # 7 CALENDAR DAY RETURN
        # =================================================

        stock_7d_row = (
            _get_price_on_or_before(

                price_df=price_df,

                target_date=target_7d

            )
        )

        nifty_7d_row = (
            _get_price_on_or_before(

                price_df=nifty_df,

                target_date=target_7d

            )
        )

        if (
            stock_7d_row is not None
            and
            nifty_7d_row is not None
        ):

            stock_7d_close = float(
                stock_7d_row["Close"]
            )

            nifty_7d_close = float(
                nifty_7d_row["Close"]
            )

            return_7d = (

                (
                    stock_7d_close
                    - entry_price
                )

                / entry_price

            ) * 100

            nifty_7d_return = (

                (
                    nifty_7d_close
                    - nifty_entry_price
                )

                / nifty_entry_price

            ) * 100

            outperformance_7d = (

                return_7d
                - nifty_7d_return

            )

        else:

            return_7d = None

            outperformance_7d = None

        # =================================================
        # 14 CALENDAR DAY RETURN
        # =================================================

        stock_14d_row = (
            _get_price_on_or_before(

                price_df=price_df,

                target_date=target_14d

            )
        )

        nifty_14d_row = (
            _get_price_on_or_before(

                price_df=nifty_df,

                target_date=target_14d

            )
        )

        # Do not pretend we have a 14D result if the
        # available data has not yet reached target_14d.

        stock_has_14d_data = (

            not price_df.empty
            and
            price_df["Date"].max()
            >= target_14d

        )

        nifty_has_14d_data = (

            not nifty_df.empty
            and
            nifty_df["Date"].max()
            >= target_14d

        )

        if (
            stock_14d_row is not None
            and
            nifty_14d_row is not None
            and
            stock_has_14d_data
            and
            nifty_has_14d_data
        ):

            stock_14d_close = float(
                stock_14d_row["Close"]
            )

            nifty_14d_close = float(
                nifty_14d_row["Close"]
            )

            return_14d = (

                (
                    stock_14d_close
                    - entry_price
                )

                / entry_price

            ) * 100

            nifty_14d_return = (

                (
                    nifty_14d_close
                    - nifty_entry_price
                )

                / nifty_entry_price

            ) * 100

            outperformance_14d = (

                return_14d
                - nifty_14d_return

            )

        else:

            return_14d = None

            outperformance_14d = None

        # =================================================
        # HIGHEST / LOWEST RETURN
        #
        # Horizon:
        # recommendation date -> 14 calendar day target
        # =================================================

        evaluation_period = price_df[

            (
                price_df["Date"]
                >= recommendation_date
            )

            &

            (
                price_df["Date"]
                <= target_14d
            )

        ]

        if evaluation_period.empty:

            highest_return = None

            lowest_return = None

        else:

            highest_high = float(
                evaluation_period[
                    "High"
                ].max()
            )

            lowest_low = float(
                evaluation_period[
                    "Low"
                ].min()
            )

            highest_return = (

                (
                    highest_high
                    - entry_price
                )

                / entry_price

            ) * 100

            lowest_return = (

                (
                    lowest_low
                    - entry_price
                )

                / entry_price

            ) * 100

        # =================================================
        # OUTPUT
        # =================================================

        analysis_row = (
            row.to_dict()
        )

        analysis_row.update(
            {

                "recommendation_date":
                    recommendation_date,

                "analysis_date":
                    date.today(),

                "btst_return_pct":
                    round(
                        btst_return,
                        2
                    ),

                "btst_outperformance_pct":
                    round(
                        btst_outperformance,
                        2
                    ),

                "return_7d_pct":
                    (
                        round(
                            return_7d,
                            2
                        )

                        if return_7d is not None

                        else None
                    ),

                "outperformance_7d_pct":
                    (
                        round(
                            outperformance_7d,
                            2
                        )

                        if outperformance_7d is not None

                        else None
                    ),

                "return_14d_pct":
                    (
                        round(
                            return_14d,
                            2
                        )

                        if return_14d is not None

                        else None
                    ),

                "outperformance_14d_pct":
                    (
                        round(
                            outperformance_14d,
                            2
                        )

                        if outperformance_14d is not None

                        else None
                    ),

                "highest_return_pct":
                    (
                        round(
                            highest_return,
                            2
                        )

                        if highest_return is not None

                        else None
                    ),

                "lowest_return_pct":
                    (
                        round(
                            lowest_return,
                            2
                        )

                        if lowest_return is not None

                        else None
                    )

            }
        )

        analysis_rows.append(
            analysis_row
        )

    return pd.DataFrame(
        analysis_rows
    )


def _prepare_price_dataframe(
    price_df: pd.DataFrame
) -> pd.DataFrame:

    if price_df is None:

        return pd.DataFrame()

    if price_df.empty:

        return pd.DataFrame()

    price_df = price_df.copy()

    # =====================================================
    # YFINANCE MULTIINDEX
    # =====================================================

    if isinstance(
        price_df.columns,
        pd.MultiIndex
    ):

        price_df.columns = (
            price_df.columns
            .get_level_values(0)
        )

    # =====================================================
    # DATE COLUMN
    # =====================================================

    if "Date" not in price_df.columns:

        if "TIMESTAMP" in price_df.columns:

            price_df["Date"] = (
                pd.to_datetime(
                    price_df["TIMESTAMP"],
                    dayfirst=True,
                    errors="coerce"
                )
            )

        else:

            price_df = (
                price_df.reset_index()
            )

            if "Date" not in price_df.columns:

                first_column = (
                    price_df.columns[0]
                )

                price_df = (
                    price_df.rename(
                        columns={
                            first_column:
                                "Date"
                        }
                    )
                )

    price_df["Date"] = (
        pd.to_datetime(
            price_df["Date"],
            errors="coerce"
        )
    )

    price_df = price_df.dropna(
        subset=["Date"]
    )

    price_df["Date"] = (
        price_df["Date"]
        .dt.normalize()
    )

    # =====================================================
    # NORMALISE OHLC COLUMN NAMES
    # =====================================================

    rename_columns = {}

    for column in price_df.columns:

        upper_column = (
            str(column).upper()
        )

        if upper_column == "OPEN":

            rename_columns[
                column
            ] = "Open"

        elif upper_column == "HIGH":

            rename_columns[
                column
            ] = "High"

        elif upper_column == "LOW":

            rename_columns[
                column
            ] = "Low"

        elif upper_column == "CLOSE":

            rename_columns[
                column
            ] = "Close"

    price_df = price_df.rename(
        columns=rename_columns
    )

    required_columns = [
        "Date",
        "High",
        "Low",
        "Close"
    ]

    missing_columns = [

        column

        for column in required_columns

        if column not in price_df.columns

    ]

    if missing_columns:

        raise ValueError(

            "Price dataframe missing columns: "
            f"{missing_columns}"

        )

    price_df = (
        price_df
        .sort_values("Date")
        .drop_duplicates(
            subset=["Date"],
            keep="last"
        )
        .reset_index(drop=True)
    )

    return price_df


def _filter_price_period(
    price_df: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp
) -> pd.DataFrame:

    filtered_df = price_df[

        (
            price_df["Date"]
            >= start_date
        )

        &

        (
            price_df["Date"]
            <= end_date
        )

    ].copy()

    return (
        filtered_df
        .sort_values("Date")
        .reset_index(drop=True)
    )


def _get_next_trading_session(
    price_df: pd.DataFrame,
    recommendation_date: pd.Timestamp
):

    future_sessions = price_df[

        price_df["Date"]
        > recommendation_date

    ]

    if future_sessions.empty:

        return None

    return future_sessions.iloc[0]


def _get_price_on_or_before(
    price_df: pd.DataFrame,
    target_date: pd.Timestamp
):

    eligible_prices = price_df[

        price_df["Date"]
        <= target_date

    ]

    if eligible_prices.empty:

        return None

    return eligible_prices.iloc[-1]


def _get_value(
    row: pd.Series,
    primary_column: str,
    fallback_column: str
):

    if primary_column in row.index:

        value = row[
            primary_column
        ]

        if not pd.isna(value):

            return value

    if fallback_column in row.index:

        value = row[
            fallback_column
        ]

        if not pd.isna(value):

            return value

    raise KeyError(

        f"Neither '{primary_column}' "
        f"nor '{fallback_column}' "
        f"contains a valid value."

    )


def _get_optional_value(
    row: pd.Series,
    column: str
):

    if column not in row.index:

        return None

    return row[
        column
    ]