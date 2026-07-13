# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 14:35:51 2026

@author: mohak
"""

"""
Prepares all daily data required by strategies.

Daily Pipeline

1. Synchronize Raw History
2. Process Raw History
3. Build Master Universe
"""

from datetime import date

from fetch.nse_report_downloader import NSEReportDownloader
from fetch.history_synchronizer import HistorySynchronizer

from processing.bhavcopy_cleaner import BhavcopyCleaner
from processing.history_processor import HistoryProcessor
from processing.master_universe_builder import (
    build_master_universe
)

from config.paths import (
    RAW_BHAVCOPY_DIRECTORY,
    PROCESSED_BHAVCOPY_DIRECTORY,
    MASTER_UNIVERSE_FILE
)


class Daily_Data_Preparation:

    def run(
        self,
        recommendation_date: date,
        history_window: int
    ):

        print("\n" + "=" * 70)
        print("Preparing Daily Data")
        print("=" * 70)

        self._synchronize_history(

            recommendation_date=recommendation_date,

            history_window=history_window

        )

        self._process_history(

            history_window=history_window

        )

        self._build_master_universe()

        print("\nDaily Data Preparation Completed.")

    def _synchronize_history(
        self,
        recommendation_date: date,
        history_window: int
    ):

        downloader = NSEReportDownloader(

            RAW_BHAVCOPY_DIRECTORY

        )

        synchronizer = HistorySynchronizer(

            downloader=downloader,

            recommendation_date=recommendation_date,

            history_window=history_window

        )

        synchronizer.synchronize_history()

    def _process_history(
        self,
        history_window: int
    ):

        cleaner = BhavcopyCleaner(

            processed_directory=PROCESSED_BHAVCOPY_DIRECTORY

        )

        processor = HistoryProcessor(

            cleaner=cleaner,

            raw_directory=RAW_BHAVCOPY_DIRECTORY,

            history_window=history_window

        )

        processor.process_history()

    def _build_master_universe(
        self
    ):

        build_master_universe(
        
            processed_directory=PROCESSED_BHAVCOPY_DIRECTORY,
        
            save_output_flag=True
        )