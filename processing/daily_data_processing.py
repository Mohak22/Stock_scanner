# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 14:35:51 2026

@author: mohak
"""

"""
Daily Data Preparation

Responsibilities
----------------
Central data-ingestion and data-preparation pipeline.

Purpose
-------
Maintain the STOCK_SCANNER_DATA repository with complete historical
data up to a fixed cutoff date.

The cutoff is always supplied explicitly through `data_as_of`.

Example:

    data_as_of = 2026-08-16

means:

    No dataset is intentionally fetched beyond 2026-08-16.

This module is responsible ONLY for data acquisition and preparation.

It does NOT:
    - calculate research features
    - calculate RSI / EMA / ATR
    - perform research filtering
    - run backtests
    - run strategies
    - generate recommendations
    - run Streamlit
"""


from datetime import date


# ======================================================================
# NSE RAW DATA
# ======================================================================

from fetch.nse_report_downloader import (
    NSEReportDownloader
)

from fetch.history_synchronizer import (
    HistorySynchronizer
)


# ======================================================================
# BHAVCOPY PROCESSING
# ======================================================================

from processing.bhavcopy_cleaner import (
    BhavcopyCleaner
)

from processing.history_processor import (
    HistoryProcessor
)

from processing.master_universe_builder import (
    build_master_universe
)


# ======================================================================
# PATHS
# ======================================================================

from config.paths import (
    RAW_BHAVCOPY_DIRECTORY,
    PROCESSED_BHAVCOPY_DIRECTORY
)


# ======================================================================
# RESEARCH MARKET DATA
# ======================================================================

from research.market_data.market_context_collector import (
    MarketContextCollector
)


# ======================================================================
# RESEARCH UNIVERSE
# ======================================================================

from research.reference_data.nse_equity_security_master import (
    NSEEquitySecurityMasterCollector
)


# ======================================================================
# RESEARCH STOCK MARKET DATA
# ======================================================================

from backtesting.market_data.historical_market_data import (
    main as update_historical_stock_data
)


# ======================================================================
# DAILY DATA PREPARATION
# ======================================================================

class Daily_Data_Preparation:

    """
    Central data-preparation pipeline.

    Every external data collector receives the same `data_as_of`
    cutoff wherever that collector requires it.

    Example:

        data_as_of = 2026-08-16

    The pipeline is therefore designed to maintain data only
    through 2026-08-16.
    """


    # ==================================================================
    # RUN COMPLETE PIPELINE
    # ==================================================================

    def run(
        self,
        data_as_of: date
    ):

        """
        Execute the complete data-preparation pipeline.

        Parameters
        ----------
        data_as_of : date
            Latest date for which data may be downloaded or saved.
        """


        # ==============================================================
        # VALIDATION
        # ==============================================================

        if not isinstance(
            data_as_of,
            date
        ):

            raise TypeError(
                "data_as_of must be a datetime.date object."
            )


        # ==============================================================
        # HEADER
        # ==============================================================

        print(
            "\n"
            + "=" * 70
        )

        print(
            "DAILY DATA PREPARATION"
        )

        print(
            "=" * 70
        )

        print(
            f"\nData cutoff : "
            f"{data_as_of.strftime('%d-%m-%Y')}"
        )

        print(
            "All datasets must remain at or before this date."
        )


        # ==============================================================
        # STEP 1
        # NSE RAW DATA
        #
        # Bhavcopy
        # MTO / Delivery
        # ==============================================================

        self._synchronize_nse_history(
            data_as_of=data_as_of
        )


        # ==============================================================
        # STEP 2
        # PROCESS NSE HISTORY
        #
        # Raw Bhavcopy -> Processed Parquet
        # ==============================================================

        self._process_history(
            data_as_of=data_as_of
        )


        # ==============================================================
        # STEP 3
        # MASTER UNIVERSE
        # ==============================================================

        self._build_master_universe()


        # ==============================================================
        # STEP 4
        # HISTORICAL STOCK MARKET DATA
        #
        # Per-stock historical OHLCV
        # ==============================================================

        self._update_historical_stock_data(
            data_as_of=data_as_of
        )


        # ==============================================================
        # STEP 5
        # MARKET + SECTOR INDEX DATA
        #
        # NIFTY 50
        # NIFTY 500
        # Sector indices
        # ==============================================================

        self._update_market_context(
            data_as_of=data_as_of
        )


        # ==============================================================
        # STEP 6
        # RESEARCH UNIVERSE
        #
        # Must be LAST because it depends on the latest
        # master_universe.csv.
        # ==============================================================

        self._update_research_universe()


        # ==============================================================
        # COMPLETE
        # ==============================================================

        print(
            "\n"
            + "=" * 70
        )

        print(
            "DAILY DATA PREPARATION COMPLETED"
        )

        print(
            "=" * 70
        )

        print(
            f"\nData maintained through : "
            f"{data_as_of.strftime('%d-%m-%Y')}"
        )


    # ==================================================================
    # STEP 1
    # NSE RAW HISTORY
    # ==================================================================

    def _synchronize_nse_history(
        self,
        data_as_of: date
    ):

        """
        Synchronize NSE raw historical data.

        Responsible for:

            - Bhavcopy
            - MTO / delivery data

        HistorySynchronizer handles:

            - old/new NSE formats
            - weekends
            - holidays
            - unavailable dates
            - incremental synchronization
            - cutoff enforcement
        """


        print(
            "\n"
            + "-" * 70
        )

        print(
            "STEP 1 : NSE RAW HISTORY"
        )

        print(
            "-" * 70
        )

        print(
            f"Data cutoff : "
            f"{data_as_of.strftime('%d-%m-%Y')}"
        )


        # --------------------------------------------------------------
        # DOWNLOADER
        # --------------------------------------------------------------

        downloader = NSEReportDownloader(
            RAW_BHAVCOPY_DIRECTORY
        )


        # --------------------------------------------------------------
        # SYNCHRONIZER
        # --------------------------------------------------------------

        synchronizer = HistorySynchronizer(
            downloader=downloader,
            data_as_of=data_as_of
        )


        synchronizer.synchronize_history()


    # ==================================================================
    # STEP 2
    # PROCESS BHAVCOPY HISTORY
    # ==================================================================

    def _process_history(
        self,
        data_as_of: date
    ):

        """
        Process all raw NSE Bhavcopy files available through
        the supplied cutoff date.

        Already processed files are skipped.
        """


        print(
            "\n"
            + "-" * 70
        )

        print(
            "STEP 2 : PROCESS BHAVCOPY HISTORY"
        )

        print(
            "-" * 70
        )

        print(
            f"Processing through : "
            f"{data_as_of.strftime('%d-%m-%Y')}"
        )


        # --------------------------------------------------------------
        # CLEANER
        # --------------------------------------------------------------

        cleaner = BhavcopyCleaner(
            processed_directory=(
                PROCESSED_BHAVCOPY_DIRECTORY
            )
        )


        # --------------------------------------------------------------
        # PROCESSOR
        # --------------------------------------------------------------

        processor = HistoryProcessor(

            cleaner=cleaner,

            raw_directory=(
                RAW_BHAVCOPY_DIRECTORY
            ),

            processed_directory=(
                PROCESSED_BHAVCOPY_DIRECTORY
            ),

            data_as_of=data_as_of

        )


        processor.process_history()


    # ==================================================================
    # STEP 3
    # MASTER UNIVERSE
    # ==================================================================

    def _build_master_universe(
        self
    ):

        """
        Build/update the current master universe.

        master_universe.csv remains the broad liquidity/price
        universe.

        It is NOT the same as the Research Universe.
        """


        print(
            "\n"
            + "-" * 70
        )

        print(
            "STEP 3 : BUILD MASTER UNIVERSE"
        )

        print(
            "-" * 70
        )


        build_master_universe(

            processed_directory=(
                PROCESSED_BHAVCOPY_DIRECTORY
            ),

            save_output_flag=True

        )


    # ==================================================================
    # STEP 4
    # HISTORICAL STOCK MARKET DATA
    # ==================================================================

    def _update_historical_stock_data(
        self,
        data_as_of: date
    ):

        """
        Update per-stock historical market data.

        The historical stock collector receives the exact same
        cutoff used by the overall data-preparation pipeline.

        It must never intentionally retain data after `data_as_of`.
        """


        print(
            "\n"
            + "-" * 70
        )

        print(
            "STEP 4 : HISTORICAL STOCK MARKET DATA"
        )

        print(
            "-" * 70
        )

        print(
            f"Stock data cutoff : "
            f"{data_as_of.strftime('%d-%m-%Y')}"
        )


        update_historical_stock_data(
            data_as_of=data_as_of
        )


        print(
            "Historical stock market data "
            "update completed."
        )


    # ==================================================================
    # STEP 5
    # MARKET + SECTOR CONTEXT
    # ==================================================================

    def _update_market_context(
        self,
        data_as_of: date
    ):

        """
        Update NIFTY and sector index history.

        The market-context collector receives the same cutoff
        as the rest of the data-preparation pipeline.
        """


        print(
            "\n"
            + "-" * 70
        )

        print(
            "STEP 5 : MARKET + SECTOR CONTEXT"
        )

        print(
            "-" * 70
        )

        print(
            f"Market data cutoff : "
            f"{data_as_of.strftime('%d-%m-%Y')}"
        )


        collector = MarketContextCollector(
            today=data_as_of
        )


        results = (
            collector.collect_all()
        )


        print(
            "\nMarket context collection summary:"
        )


        for result in results:

            print(
                f"  {result['index_name']}: "
                f"{result['status']}"
            )


    # ==================================================================
    # STEP 6
    # RESEARCH UNIVERSE
    # ==================================================================

    def _update_research_universe(
        self
    ):

        """
        Refresh the Research Cockpit universe.

        This is intentionally the FINAL step.

        Flow:

            master_universe.csv
                    |
                    v
            NSE EQUITY_L.csv
                    |
                    v
            Resolve valid NSE equities
                    |
                    v
            Fetch NSE industry classification
                    |
                    v
            research_universe.csv

        IMPORTANT:

            - master_universe.csv is NOT modified.
            - ETFs/unresolved symbols are excluded.
            - research_universe.csv is overwritten daily.
            - Sector / industry columns are generated by
              NSEEquitySecurityMasterCollector.
        """


        print(
            "\n"
            + "-" * 70
        )

        print(
            "STEP 6 : RESEARCH UNIVERSE"
        )

        print(
            "-" * 70
        )

        print(
            "Refreshing Research Cockpit universe..."
        )


        # --------------------------------------------------------------
        # COLLECTOR
        # --------------------------------------------------------------

        collector = (
            NSEEquitySecurityMasterCollector()
        )


        # --------------------------------------------------------------
        # BUILD + SAVE RESEARCH UNIVERSE
        #
        # IMPORTANT:
        #
        # Do NOT manually construct research_universe.csv here.
        #
        # The collector now:
        #
        #   1. downloads EQUITY_L.csv
        #   2. resolves the master universe
        #   3. fetches NSE classification
        #   4. saves research_universe.csv
        #
        # --------------------------------------------------------------

        collector.collect_and_validate()


# ======================================================================
# STANDALONE TEST
# ======================================================================

if __name__ == "__main__":

    from datetime import timedelta


    # --------------------------------------------------------------
    # IMPORTANT
    #
    # Always use YESTERDAY.
    #
    # Never use date.today() directly as the data cutoff.
    #
    # Example:
    #
    # Today       = 17-Aug-2026
    # data_as_of  = 16-Aug-2026
    #
    # Since 16-Aug-2026 is Sunday, the latest actual trading
    # observation will normally be 14-Aug-2026.
    #
    # --------------------------------------------------------------

    data_as_of = (

        date.today()
        - timedelta(days=1)

    )


    preparation = (
        Daily_Data_Preparation()
    )


    preparation.run(
        data_as_of=data_as_of
    )