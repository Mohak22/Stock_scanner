# -*- coding: utf-8 -*-
"""
Created on Sun Jul  5 17:24:04 2026

@author: mohak
"""

from datetime import date, timedelta
from pathlib import Path

import requests

from fetch.nse_report_downloader import NSEReportDownloader

class HistorySynchronizer:

    FILE_PREFIX = "sec_bhavdata_full_"

    FILE_EXTENSION = ".csv"

    def __init__(
        self,
        downloader: NSEReportDownloader,
        recommendation_date: date,
        history_window: int
    ):
    
        self.downloader = downloader
    
        self.recommendation_date = recommendation_date
    
        self.history_window = history_window
        
    def _build_filename(
        self,
        trading_date: date
    ) -> str:
    
        return (
    
            self.FILE_PREFIX
    
            + trading_date.strftime("%d%m%Y")
    
            + self.FILE_EXTENSION
    
        )

    def _local_file_exists(
        self,
        file_name: str
    ) -> bool:
    
        file_path = (
            self.downloader.raw_data_dir
            / file_name
        )
    
        print(f"Checking : {file_path}")
    
        print(f"Exists   : {file_path.exists()}")
    
        return file_path.exists()
    
    def _download_if_available(
        self,
        file_name: str
    ) -> bool:
    
        metadata = self.downloader.download_raw_file(
    
            file_name=file_name
    
        )
    
        return metadata is not None

    def synchronize_history(
        self
    ):
    
        start_date = (
            self.recommendation_date
            - timedelta(days=1)
        )
    
        history_count = 0
    
        current_date = start_date
    
        print("\nSynchronizing Raw History...")
    
        while history_count < self.history_window:
    
            # Skip Saturday and Sunday
            if current_date.weekday() >= 5:
    
                print(
                    f"Skipping weekend : {current_date.strftime('%d-%m-%Y')}"
                )
    
                current_date -= timedelta(days=1)
    
                continue
    
            file_name = self._build_filename(
                current_date
            )
    
            if self._local_file_exists(
                file_name
            ):
    
                history_count += 1
    
            else:
    
                downloaded = self._download_if_available(
                    file_name
                )
    
                if downloaded:
    
                    history_count += 1
    
                else:
    
                    print(
                        f"Skipping : {file_name}"
                    )
    
            current_date -= timedelta(days=1)
    
        print(
            f"\n{history_count} trading days available."
        )