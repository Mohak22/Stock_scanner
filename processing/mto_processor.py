# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 13:24:48 2026

@author: mohak
"""

"""
NSE MTO Processor

Responsibilities:
    - Find raw NSE MTO .DAT files.
    - Process only files up to the supplied data_as_of date.
    - Identify MTO files that have not yet been processed.
    - Parse NSE Security Wise Delivery Position files.
    - Save processed MTO data as Parquet.

Canonical MTO output:

    SYMBOL
    TIMESTAMP
    MTO_QTY_TRADED
    DELIV_QTY
    DELIV_PER

This module does NOT:
    - Download data.
    - Process Bhavcopy.
    - Calculate strategy indicators.
    - Run strategies.
"""


from datetime import date
from pathlib import Path
import re

import pandas as pd


# ======================================================================
# MTO PROCESSOR
# ======================================================================

class MTOProcessor:

    FILE_PATTERN = re.compile(
        r"^MTO_(\d{2})(\d{2})(\d{4})\.DAT$",
        re.IGNORECASE
    )


    OUTPUT_COLUMNS = [
        "SYMBOL",
        "TIMESTAMP",
        "MTO_QTY_TRADED",
        "DELIV_QTY",
        "DELIV_PER"
    ]


    # ==================================================================
    # INITIALIZATION
    # ==================================================================

    def __init__(
        self,
        raw_directory: Path,
        processed_directory: Path,
        data_as_of: date,
    ) -> None:

        self.raw_directory = (
            raw_directory
        )

        self.processed_directory = (
            processed_directory
        )

        self.data_as_of = (
            data_as_of
        )


        self.processed_directory.mkdir(
            parents=True,
            exist_ok=True
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
    # GET RAW MTO FILES
    # ==================================================================

    def _get_raw_files(
        self
    ) -> list[Path]:

        if not self.raw_directory.exists():

            return []


        valid_files = []


        for raw_file in self.raw_directory.glob(
            "MTO_*.DAT"
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

            if file_date > self.data_as_of:

                print(
                    f"Skipping future MTO : "
                    f"{raw_file.name}"
                )

                continue


            valid_files.append(
                raw_file
            )


        # --------------------------------------------------------------
        # CHRONOLOGICAL ORDER
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
    # BUILD PROCESSED FILE PATH
    # ==================================================================

    def _processed_path(
        self,
        raw_file: Path
    ) -> Path:

        return (

            self.processed_directory

            / raw_file.with_suffix(
                ".parquet"
            ).name

        )


    # ==================================================================
    # CHECK WHETHER FILE IS ALREADY PROCESSED
    # ==================================================================

    def _is_processed(
        self,
        raw_file: Path
    ) -> bool:

        return (

            self._processed_path(
                raw_file
            ).exists()

        )


    # ==================================================================
    # PARSE ONE MTO FILE
    # ==================================================================

    def _parse_file(
        self,
        raw_file: Path
    ) -> pd.DataFrame:

        file_date = (
            self._extract_file_date(
                raw_file
            )
        )


        if file_date is None:

            raise ValueError(

                "Unable to determine date "
                f"from MTO file: {raw_file.name}"

            )


        rows = []


        # --------------------------------------------------------------
        # READ RAW DAT FILE
        # --------------------------------------------------------------

        with open(

            raw_file,

            "r",

            encoding="utf-8",

            errors="replace"

        ) as file:


            for line in file:

                line = line.strip()


                if not line:

                    continue


                # ------------------------------------------------------
                # MTO DATA RECORDS
                #
                # Actual security records begin with:
                #
                # 20,...
                #
                # Example:
                #
                # 20,1,0MOFSL26,N1,50,50,100.00
                #
                # ------------------------------------------------------

                if not line.startswith(
                    "20,"
                ):

                    continue


                fields = [

                    field.strip()

                    for field in line.split(",")

                ]


                # ------------------------------------------------------
                # EXPECTED FORMAT
                #
                # 0 = Record Type
                # 1 = Sr No
                # 2 = Name of Security
                # 3 = Settlement Type
                # 4 = Quantity Traded
                # 5 = Deliverable Quantity
                # 6 = Delivery %
                #
                # Therefore minimum fields = 7
                # ------------------------------------------------------

                if len(fields) < 7:

                    continue


                symbol = fields[2]


                if not symbol:

                    continue


                # ------------------------------------------------------
                # QUANTITY TRADED
                # ------------------------------------------------------

                try:

                    quantity_traded = int(

                        fields[4]
                        .replace(",", "")
                        .strip()

                    )

                except (
                    ValueError,
                    TypeError
                ):

                    continue


                # ------------------------------------------------------
                # DELIVERABLE QUANTITY
                # ------------------------------------------------------

                try:

                    deliverable_quantity = int(

                        fields[5]
                        .replace(",", "")
                        .strip()

                    )

                except (
                    ValueError,
                    TypeError
                ):

                    continue


                # ------------------------------------------------------
                # DELIVERY PERCENTAGE
                # ------------------------------------------------------

                try:

                    delivery_percentage = float(

                        fields[6]
                        .replace(",", "")
                        .replace("%", "")
                        .strip()

                    )

                except (
                    ValueError,
                    TypeError
                ):

                    continue


                rows.append(

                    (

                        symbol.upper(),

                        file_date,

                        quantity_traded,

                        deliverable_quantity,

                        delivery_percentage

                    )

                )


        # ==================================================================
        # BUILD DATAFRAME
        # ==================================================================

        dataframe = pd.DataFrame(

            rows,

            columns=self.OUTPUT_COLUMNS

        )


        if dataframe.empty:

            return dataframe


        # ==================================================================
        # NORMALIZE TYPES
        # ==================================================================

        dataframe["SYMBOL"] = (

            dataframe["SYMBOL"]

            .astype(str)

            .str.strip()

            .str.upper()

        )


        dataframe["TIMESTAMP"] = (

            pd.to_datetime(

                dataframe["TIMESTAMP"]

            ).dt.date

        )


        dataframe["MTO_QTY_TRADED"] = (

            pd.to_numeric(

                dataframe[
                    "MTO_QTY_TRADED"
                ],

                errors="coerce"

            )

        )


        dataframe["DELIV_QTY"] = (

            pd.to_numeric(

                dataframe[
                    "DELIV_QTY"
                ],

                errors="coerce"

            )

        )


        dataframe["DELIV_PER"] = (

            pd.to_numeric(

                dataframe[
                    "DELIV_PER"
                ],

                errors="coerce"

            )

        )


        # ==================================================================
        # REMOVE INVALID RECORDS
        # ==================================================================

        dataframe = (

            dataframe

            .dropna(

                subset=[

                    "SYMBOL",

                    "MTO_QTY_TRADED",

                    "DELIV_QTY",

                    "DELIV_PER"

                ]

            )

        )


        # ==================================================================
        # REMOVE DUPLICATES
        # ==================================================================

        dataframe = (

            dataframe

            .drop_duplicates(

                subset=[

                    "SYMBOL",

                    "TIMESTAMP"

                ],

                keep="last"

            )

        )


        # ==================================================================
        # SORT
        # ==================================================================

        dataframe = (

            dataframe

            .sort_values(

                [

                    "TIMESTAMP",

                    "SYMBOL"

                ]

            )

            .reset_index(

                drop=True

            )

        )


        return dataframe


    # ==================================================================
    # PROCESS ONE FILE
    # ==================================================================

    def process_file(
        self,
        raw_file: Path
    ) -> Path:

        print(

            f"\nReading MTO : "
            f"{raw_file.name}"

        )


        dataframe = self._parse_file(
            raw_file
        )


        output_file = (
            self._processed_path(
                raw_file
            )
        )


        dataframe.to_parquet(

            output_file,

            index=False

        )


        print(

            f"Saved : "
            f"{output_file}"

        )


        print(

            f"Rows   : "
            f"{len(dataframe)}"

        )


        return output_file


    # ==================================================================
    # PROCESS HISTORY
    # ==================================================================

    def process_history(
        self
    ) -> None:

        print(

            "\n"
            + "=" * 70

        )


        print(
            "PROCESSING NSE MTO HISTORY"
        )


        print(
            "=" * 70
        )


        print(

            f"Data cutoff : "
            f"{self.data_as_of}"

        )


        # --------------------------------------------------------------
        # GET RAW FILES
        # --------------------------------------------------------------

        raw_files = (
            self._get_raw_files()
        )


        print(

            f"\nRaw MTO files available "
            f"through cutoff : "
            f"{len(raw_files)}"

        )


        if not raw_files:

            print(

                "\nNo eligible raw MTO "
                "files found."

            )

            return


        # --------------------------------------------------------------
        # FIND UNPROCESSED FILES
        # --------------------------------------------------------------

        unprocessed_files = [

            raw_file

            for raw_file in raw_files

            if not self._is_processed(
                raw_file
            )

        ]


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

                "\nAll eligible MTO files "
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

                self.process_file(
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
            "NSE MTO HISTORY PROCESSING COMPLETE"
        )


        print(
            "=" * 70
        )


        print(

            f"Data cutoff        : "
            f"{self.data_as_of}"

        )


        print(

            f"Eligible files     : "
            f"{len(raw_files)}"

        )


        print(

            f"Already processed  : "
            f"{already_processed}"

        )


        print(

            f"New files processed: "
            f"{processed_count}"

        )


        print(
            "=" * 70
        )