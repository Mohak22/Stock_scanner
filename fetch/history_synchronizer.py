# -*- coding: utf-8 -*-
"""
Created on Sun Jul  5 17:24:04 2026

@author: mohak
"""

"""
NSE historical data synchronizer.

Responsible for:

    - Finding the latest locally available Bhavcopy.
    - Finding the latest locally available MTO.
    - Starting from the next calendar date after the latest
      available file.
    - Starting from 01-Jan-2016 when no history exists.
    - Walking forward through calendar dates.
    - Skipping weekends.
    - Skipping NSE holidays / unavailable dates.
    - Downloading the correct historical Bhavcopy format through
      NSEReportDownloader.
    - Downloading the corresponding historical MTO / delivery file.
    - Never downloading data after the supplied data_as_of date.

IMPORTANT
---------
This class does NOT use date.today() to determine the download cutoff.

The caller supplies:

    data_as_of

Example:

    data_as_of = 2026-08-16

The synchronizer will never intentionally request:

    2026-08-17
    or any later date.
"""


from datetime import date, timedelta
import re


from fetch.nse_report_downloader import (
    NSEReportDownloader
)


class HistorySynchronizer:

    # ==================================================================
    # STANDARD LOCAL FILE NAMING
    # ==================================================================

    BHAVCOPY_FILE_PREFIX = (
        "sec_bhavdata_full_"
    )

    BHAVCOPY_FILE_EXTENSION = (
        ".csv"
    )


    MTO_FILE_PREFIX = (
        "mto_"
    )

    MTO_FILE_EXTENSION = (
        ".dat"
    )


    # ==================================================================
    # HISTORICAL START DATE
    # ==================================================================

    HISTORICAL_START_DATE = date(
        2016,
        1,
        1
    )


    # ==================================================================
    # FILE PATTERNS
    # ==================================================================

    BHAVCOPY_FILE_PATTERN = re.compile(
        r"^sec_bhavdata_full_"
        r"(\d{2})(\d{2})(\d{4})"
        r"\.csv$"
    )


    MTO_FILE_PATTERN = re.compile(
        r"^mto_"
        r"(\d{2})(\d{2})(\d{4})"
        r"\.dat$",
        re.IGNORECASE
    )


    # ==================================================================
    # INITIALIZATION
    # ==================================================================

    def __init__(
        self,
        downloader: NSEReportDownloader,
        data_as_of: date
    ):

        self.downloader = (
            downloader
        )

        self.data_as_of = (
            data_as_of
        )


    # ==================================================================
    # BHAVCOPY FILENAME
    # ==================================================================

    def _build_bhavcopy_filename(
        self,
        trading_date: date
    ) -> str:

        return (
            self.BHAVCOPY_FILE_PREFIX
            + trading_date.strftime(
                "%d%m%Y"
            )
            + self.BHAVCOPY_FILE_EXTENSION
        )


    # ==================================================================
    # MTO FILENAME
    # ==================================================================

    def _build_mto_filename(
        self,
        trading_date: date
    ) -> str:

        return (
            self.MTO_FILE_PREFIX
            + trading_date.strftime(
                "%d%m%Y"
            )
            + self.MTO_FILE_EXTENSION
        )


    # ==================================================================
    # FIND LATEST LOCAL BHAVCOPY
    # ==================================================================

    def _find_latest_local_bhavcopy_date(
        self
    ) -> date | None:

        raw_dir = (
            self.downloader.raw_data_dir
        )

        if not raw_dir.exists():

            return None


        latest_date = None


        for file_path in raw_dir.iterdir():

            if not file_path.is_file():

                continue


            match = (
                self.BHAVCOPY_FILE_PATTERN
                .match(
                    file_path.name
                )
            )


            if not match:

                continue


            day, month, year = (
                match.groups()
            )


            try:

                file_date = date(
                    int(year),
                    int(month),
                    int(day)
                )

            except ValueError:

                continue


            if (
                latest_date is None
                or file_date > latest_date
            ):

                latest_date = (
                    file_date
                )


        return latest_date


    # ==================================================================
    # FIND LATEST LOCAL MTO
    # ==================================================================

    def _find_latest_local_mto_date(
        self
    ) -> date | None:

        raw_dir = (
            self.downloader.raw_data_dir
        )

        if not raw_dir.exists():

            return None


        latest_date = None


        for file_path in raw_dir.iterdir():

            if not file_path.is_file():

                continue


            match = (
                self.MTO_FILE_PATTERN
                .match(
                    file_path.name
                )
            )


            if not match:

                continue


            day, month, year = (
                match.groups()
            )


            try:

                file_date = date(
                    int(year),
                    int(month),
                    int(day)
                )

            except ValueError:

                continue


            if (
                latest_date is None
                or file_date > latest_date
            ):

                latest_date = (
                    file_date
                )


        return latest_date


    # ==================================================================
    # DOWNLOAD BHAVCOPY FOR ONE DATE
    # ==================================================================

    def _download_bhavcopy_date(
        self,
        trading_date: date
    ) -> bool:

        file_name = (
            self._build_bhavcopy_filename(
                trading_date
            )
        )


        file_path = (
            self.downloader.raw_data_dir
            / file_name
        )


        # --------------------------------------------------------------
        # ALREADY EXISTS
        # --------------------------------------------------------------

        if file_path.exists():

            print(
                f"{trading_date} : "
                "Bhavcopy already exists"
            )

            return True


        # --------------------------------------------------------------
        # DOWNLOAD
        # --------------------------------------------------------------

        metadata = (
            self.downloader
            .download_historical_bhavcopy(
                trading_date=trading_date
            )
        )


        if metadata is not None:

            print(
                f"{trading_date} : "
                "Bhavcopy downloaded"
            )

            return True


        print(
            f"{trading_date} : "
            "Bhavcopy not available"
        )

        return False


    # ==================================================================
    # DOWNLOAD MTO FOR ONE DATE
    # ==================================================================

    def _download_mto_date(
        self,
        trading_date: date
    ) -> bool:

        file_name = (
            self._build_mto_filename(
                trading_date
            )
        )


        file_path = (
            self.downloader.raw_data_dir
            / file_name
        )


        # --------------------------------------------------------------
        # ALREADY EXISTS
        # --------------------------------------------------------------

        if file_path.exists():

            print(
                f"{trading_date} : "
                "MTO already exists"
            )

            return True


        # --------------------------------------------------------------
        # DOWNLOAD
        # --------------------------------------------------------------

        metadata = (
            self.downloader
            .download_historical_mto(
                trading_date=trading_date
            )
        )


        if metadata is not None:

            print(
                f"{trading_date} : "
                "MTO downloaded"
            )

            return True


        print(
            f"{trading_date} : "
            "MTO not available"
        )

        return False


    # ==================================================================
    # SYNCHRONIZE
    # ==================================================================

    def synchronize_history(
        self
    ):

        # ==============================================================
        # FIND LOCAL HISTORY
        # ==============================================================

        latest_bhavcopy_date = (
            self._find_latest_local_bhavcopy_date()
        )


        latest_mto_date = (
            self._find_latest_local_mto_date()
        )


        # ==============================================================
        # DETERMINE COMMON START DATE
        # ==============================================================

        latest_local_dates = [
            current_date
            for current_date in [
                latest_bhavcopy_date,
                latest_mto_date
            ]
            if current_date is not None
        ]


        if not latest_local_dates:

            current_date = (
                self.HISTORICAL_START_DATE
            )

            print(
                "\nNo local NSE history found."
            )

            print(
                "Starting historical backfill from : "
                f"{current_date}"
            )

        else:

            latest_local_date = min(
                latest_local_dates
            )

            current_date = (
                latest_local_date
                + timedelta(days=1)
            )

            print(
                "\nLatest local Bhavcopy : "
                f"{latest_bhavcopy_date}"
            )

            print(
                "Latest local MTO      : "
                f"{latest_mto_date}"
            )

            print(
                "Synchronization starts from : "
                f"{current_date}"
            )


        # ==============================================================
        # CUTOFF CHECK
        # ==============================================================

        if current_date > self.data_as_of:

            print(
                "\nNSE raw history is already "
                "up to date."
            )

            print(
                f"Latest required date : "
                f"{self.data_as_of}"
            )

            return


        # ==============================================================
        # SUMMARY COUNTERS
        # ==============================================================

        bhavcopy_downloaded = 0
        bhavcopy_unavailable = 0

        mto_downloaded = 0
        mto_unavailable = 0


        # ==============================================================
        # FORWARD SYNCHRONIZATION
        # ==============================================================

        print(
            "\nSynchronizing NSE raw history..."
        )

        print(
            f"From : {current_date}"
        )

        print(
            f"To   : {self.data_as_of}"
        )


        while current_date <= self.data_as_of:

            # ----------------------------------------------------------
            # WEEKEND
            # ----------------------------------------------------------

            if current_date.weekday() >= 5:

                print(
                    "Skipping weekend : "
                    f"{current_date.strftime('%d-%m-%Y')}"
                )

                current_date += timedelta(
                    days=1
                )

                continue


            # ----------------------------------------------------------
            # PROCESS DATE
            # ----------------------------------------------------------

            print(
                "\n"
                + "-" * 60
            )

            print(
                "Processing trading date : "
                f"{current_date}"
            )

            print(
                "-" * 60
            )


            # ----------------------------------------------------------
            # BHAVCOPY
            # ----------------------------------------------------------

            bhavcopy_success = (
                self._download_bhavcopy_date(
                    current_date
                )
            )


            if bhavcopy_success:

                bhavcopy_downloaded += 1

            else:

                bhavcopy_unavailable += 1


            # ----------------------------------------------------------
            # MTO
            # ----------------------------------------------------------

            mto_success = (
                self._download_mto_date(
                    current_date
                )
            )


            if mto_success:

                mto_downloaded += 1

            else:

                mto_unavailable += 1


            # ----------------------------------------------------------
            # NEXT CALENDAR DATE
            # ----------------------------------------------------------

            current_date += timedelta(
                days=1
            )


        # ==============================================================
        # SUMMARY
        # ==============================================================

        print(
            "\n"
            + "=" * 70
        )

        print(
            "NSE RAW HISTORY SYNCHRONIZATION COMPLETE"
        )

        print(
            "=" * 70
        )

        print(
            f"Data cutoff             : "
            f"{self.data_as_of}"
        )

        print(
            f"Bhavcopy downloaded/found : "
            f"{bhavcopy_downloaded}"
        )

        print(
            f"Bhavcopy unavailable       : "
            f"{bhavcopy_unavailable}"
        )

        print(
            f"MTO downloaded/found      : "
            f"{mto_downloaded}"
        )

        print(
            f"MTO unavailable            : "
            f"{mto_unavailable}"
        )