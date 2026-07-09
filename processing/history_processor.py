# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 11:32:40 2026

@author: mohak
"""

from pathlib import Path

from processing.bhavcopy_cleaner import BhavcopyCleaner


class HistoryProcessor:

    def __init__(
        self,
        cleaner: BhavcopyCleaner,
        raw_directory: Path,
        history_window: int
    ):

        self.cleaner = cleaner

        self.raw_directory = raw_directory

        self.history_window = history_window

    def _get_raw_files(
        self
    ) -> list[Path]:

        return sorted(

            self.raw_directory.glob(
                "*.csv"
            ),

            reverse=True

        )

    def _select_history(
        self,
        raw_files: list[Path]
    ) -> list[Path]:

        return raw_files[
            :self.history_window
        ]

    def process_history(
        self
    ):

        print("\nProcessing Raw History...")

        raw_files = self._get_raw_files()

        history = self._select_history(
            raw_files
        )

        for raw_file in history:
        
            try:
        
                self.cleaner.clean_file(
                    raw_file
                )
        
            except Exception as error:
        
                print(f"\nError while processing {raw_file.name}")
                print(error)
                raise

        print(
            f"\nProcessed {len(history)} trading days."
        )