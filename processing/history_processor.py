# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 11:32:40 2026

@author: mohak
"""

# -*- coding: utf-8 -*-
"""
History Processor

Responsibilities:
    - Find raw NSE Bhavcopy files.
    - Process only files up to the supplied data_as_of date.
    - Identify files that have not yet been processed.
    - Send each new raw file to BhavcopyCleaner.
    - Preserve the existing raw/processed filename relationship.

This module does NOT:
    - Download data.
    - Calculate indicators.
    - Merge MTO data.
    - Run strategies.
"""


from datetime import date
from pathlib import Path
import re

from processing.bhavcopy_cleaner import (
    BhavcopyCleaner
)


class HistoryProcessor:

    FILE_PATTERN = re.compile(
        r"^sec_bhavdata_full_(\d{2})(\d{2})(\d{4})\.csv$"
    )


    def __init__(
        self,
        cleaner: BhavcopyCleaner,
        raw_directory: Path,
        processed_directory: Path,
        data_as_of: date
    ):

        self.cleaner = cleaner

        self.raw_directory = (
            raw_directory
        )

        self.processed_directory = (
            processed_directory
        )

        self.data_as_of = (
            data_as_of
        )


    # ==================================================================
    # EXTRACT DATE FROM FILENAME
    # ==================================================================

    def _extract_file_date(
        self,
        raw_file: Path
    ) -> date | None:

        match = self.FILE_PATTERN.match(
            raw_file.name
        )

        if not match:

            return None

        day, month, year = (
            match.groups()
        )

        try:

            return date(
                int(year),
                int(month),
                int(day)
            )

        except ValueError:

            return None


    # ==================================================================
    # GET RAW BHAVCOPY FILES
    # ==================================================================

    def _get_raw_files(
        self
    ) -> list[Path]:

        if not self.raw_directory.exists():

            return []


        valid_files = []


        for raw_file in self.raw_directory.glob(
            "sec_bhavdata_full_*.csv"
        ):

            if not raw_file.is_file():

                continue


            file_date = (
                self._extract_file_date(
                    raw_file
                )
            )


            if file_date is None:

                continue


            # ----------------------------------------------------------
            # SAFETY CUTOFF
            # ----------------------------------------------------------
            #
            # Never process data after data_as_of.
            #

            if file_date > self.data_as_of:

                print(
                    f"Skipping future Bhavcopy : "
                    f"{raw_file.name}"
                )

                continue


            valid_files.append(
                raw_file
            )


        # --------------------------------------------------------------
        # SORT CHRONOLOGICALLY
        # --------------------------------------------------------------

        valid_files.sort(
            key=lambda file: (
                self._extract_file_date(
                    file
                )
            )
        )


        return valid_files


    # ==================================================================
    # CHECK WHETHER FILE IS ALREADY PROCESSED
    # ==================================================================

    def _is_processed(
        self,
        raw_file: Path
    ) -> bool:

        processed_file = (

            self.processed_directory

            / raw_file.with_suffix(
                ".parquet"
            ).name

        )


        return processed_file.exists()


    # ==================================================================
    # GET ONLY UNPROCESSED FILES
    # ==================================================================

    def _get_unprocessed_files(
        self,
        raw_files: list[Path]
    ) -> list[Path]:

        return [

            raw_file

            for raw_file in raw_files

            if not self._is_processed(
                raw_file
            )

        ]


    # ==================================================================
    # PROCESS HISTORY
    # ==================================================================

    def process_history(
        self
    ):

        print(
            "\n"
            + "=" * 70
        )

        print(
            "PROCESSING NSE BHAVCOPY HISTORY"
        )

        print(
            "=" * 70
        )

        print(
            f"Data cutoff : "
            f"{self.data_as_of}"
        )


        # --------------------------------------------------------------
        # RAW FILES
        # --------------------------------------------------------------

        raw_files = (
            self._get_raw_files()
        )


        print(
            f"\nRaw Bhavcopy files available "
            f"through cutoff : "
            f"{len(raw_files)}"
        )


        if not raw_files:

            print(
                "\nNo eligible raw Bhavcopy "
                "files found."
            )

            return


        # --------------------------------------------------------------
        # UNPROCESSED FILES
        # --------------------------------------------------------------

        unprocessed_files = (
            self._get_unprocessed_files(
                raw_files
            )
        )


        already_processed = (
            len(raw_files)
            - len(unprocessed_files)
        )


        print(
            f"Already processed : "
            f"{already_processed}"
        )

        print(
            f"Requiring processing : "
            f"{len(unprocessed_files)}"
        )


        if not unprocessed_files:

            print(
                "\nAll eligible Bhavcopy files "
                "are already processed."
            )

            return


        # --------------------------------------------------------------
        # PROCESS
        # --------------------------------------------------------------

        processed_count = 0


        for raw_file in unprocessed_files:

            print(
                "\n"
                + "-" * 70
            )

            print(
                f"Processing : "
                f"{raw_file.name}"
            )

            print(
                "-" * 70
            )


            try:

                self.cleaner.clean_file(
                    raw_file
                )

                processed_count += 1


            except Exception as error:

                print(
                    "\nError while processing "
                    f"{raw_file.name}"
                )

                print(
                    error
                )

                raise


        # --------------------------------------------------------------
        # SUMMARY
        # --------------------------------------------------------------

        print(
            "\n"
            + "=" * 70
        )

        print(
            "BHAVCOPY HISTORY PROCESSING COMPLETE"
        )

        print(
            "=" * 70
        )

        print(
            f"Data cutoff            : "
            f"{self.data_as_of}"
        )

        print(
            f"Eligible raw files     : "
            f"{len(raw_files)}"
        )

        print(
            f"Already processed      : "
            f"{already_processed}"
        )

        print(
            f"New files processed    : "
            f"{processed_count}"
        )

        print(
            "=" * 70
        )