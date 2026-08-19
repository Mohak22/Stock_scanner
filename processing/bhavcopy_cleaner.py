# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 11:03:40 2026

@author: mohak
"""

"""
Bhavcopy Cleaner

Responsibilities:
    - Read raw NSE Bhavcopy files.
    - Detect old NSE format or new UDiFF format.
    - Convert both formats into one canonical schema.
    - Keep only EQ series.
    - Save the cleaned Bhavcopy as Parquet.

IMPORTANT:
    Delivery quantity and delivery percentage are NOT part of Bhavcopy.

    They come from the separate NSE MTO file and will be processed
    separately.

Canonical output columns:

    SYMBOL
    SERIES
    OPEN
    HIGH
    LOW
    CLOSE
    LAST
    PREVCLOSE
    TOTTRDQTY
    TOTTRDVAL
    TIMESTAMP
    TOTALTRADES
    ISIN
"""


from pathlib import Path

import pandas as pd

from reports.excel_report_generator import (
    save_output
)


class BhavcopyCleaner:

    # ==================================================================
    # CANONICAL OUTPUT SCHEMA
    # ==================================================================

    OUTPUT_COLUMNS = (
        "SYMBOL",
        "SERIES",
        "OPEN",
        "HIGH",
        "LOW",
        "CLOSE",
        "LAST",
        "PREVCLOSE",
        "TOTTRDQTY",
        "TOTTRDVAL",
        "TIMESTAMP",
        "TOTALTRADES",
        "ISIN"
    )


    # ==================================================================
    # OLD NSE BHAVCOPY FORMAT
    # ==================================================================

    OLD_FORMAT_MAPPING = {

        "DATE1": "TIMESTAMP",

        "CLOSE_PRICE": "CLOSE",

        "TTL_TRD_QNTY": "TOTTRDQTY",

        "TURNOVER_LACS": "TOTTRDVAL"

    }


    # ==================================================================
    # NEW NSE UDIFF FORMAT
    # ==================================================================

    UDIFF_FORMAT_MAPPING = {

        "TradDt": "TIMESTAMP",

        "TckrSymb": "SYMBOL",

        "SctySrs": "SERIES",

        "OpnPric": "OPEN",

        "HghPric": "HIGH",

        "LwPric": "LOW",

        "ClsPric": "CLOSE",

        "LastPric": "LAST",

        "PrvsClsgPric": "PREVCLOSE",

        "TtlTradgVol": "TOTTRDQTY",

        "TtlTrfVal": "TOTTRDVAL",

        "TtlNbOfTxsExctd": "TOTALTRADES",

        "ISIN": "ISIN"

    }


    # ==================================================================
    # REQUIRED RAW/CANONICAL FIELDS
    # ==================================================================

    REQUIRED_COLUMNS = (
        "SYMBOL",
        "SERIES",
        "OPEN",
        "HIGH",
        "LOW",
        "CLOSE",
        "LAST",
        "PREVCLOSE",
        "TOTTRDQTY",
        "TOTTRDVAL",
        "TIMESTAMP",
        "TOTALTRADES",
        "ISIN"
    )


    # ==================================================================
    # INITIALIZATION
    # ==================================================================

    def __init__(
        self,
        processed_directory: Path
    ):

        self.processed_directory = (
            processed_directory
        )

        self.processed_directory.mkdir(
            parents=True,
            exist_ok=True
        )


    # ==================================================================
    # READ RAW FILE
    # ==================================================================

    def _read_raw_file(
        self,
        raw_file_path: Path
    ) -> pd.DataFrame:

        print(
            f"\nReading : {raw_file_path.name}"
        )

        dataframe = pd.read_csv(
            raw_file_path,
            low_memory=False
        )

        dataframe.columns = (
            dataframe.columns
            .astype(str)
            .str.strip()
        )

        return dataframe


    # ==================================================================
    # DETECT FORMAT
    # ==================================================================

    def _detect_format(
        self,
        dataframe: pd.DataFrame
    ) -> str:

        columns = set(
            dataframe.columns
        )

        # --------------------------------------------------------------
        # OLD FORMAT
        # --------------------------------------------------------------

        old_format_columns = {
            "SYMBOL",
            "SERIES",
            "OPEN",
            "HIGH",
            "LOW",
            "CLOSE",
            "PREVCLOSE",
            "TOTTRDQTY",
            "TOTTRDVAL",
            "TIMESTAMP"
        }

        if old_format_columns.issubset(
            columns
        ):

            return "OLD"


        # --------------------------------------------------------------
        # UDIFF FORMAT
        # --------------------------------------------------------------

        udiff_format_columns = {
            "TradDt",
            "TckrSymb",
            "SctySrs",
            "OpnPric",
            "HghPric",
            "LwPric",
            "ClsPric",
            "PrvsClsgPric",
            "TtlTradgVol",
            "TtlTrfVal"
        }

        if udiff_format_columns.issubset(
            columns
        ):

            return "UDIFF"


        # --------------------------------------------------------------
        # UNKNOWN
        # --------------------------------------------------------------

        raise ValueError(
            "\nUnsupported NSE Bhavcopy format.\n"
            f"File : {dataframe.shape}\n"
            f"Columns : {list(dataframe.columns)}"
        )


    # ==================================================================
    # NORMALIZE OLD FORMAT
    # ==================================================================

    def _normalize_old_format(
        self,
        dataframe: pd.DataFrame
    ) -> pd.DataFrame:

        dataframe = dataframe.rename(
            columns=self.OLD_FORMAT_MAPPING
        )

        # --------------------------------------------------------------
        # Some old files already contain canonical names.
        # Therefore we only rename fields that require conversion.
        # --------------------------------------------------------------

        return dataframe


    # ==================================================================
    # NORMALIZE UDIFF FORMAT
    # ==================================================================

    def _normalize_udiff_format(
        self,
        dataframe: pd.DataFrame
    ) -> pd.DataFrame:

        dataframe = dataframe.rename(
            columns=self.UDIFF_FORMAT_MAPPING
        )

        return dataframe


    # ==================================================================
    # NORMALIZE FORMAT
    # ==================================================================

    def _normalize_dataframe(
        self,
        dataframe: pd.DataFrame
    ) -> pd.DataFrame:

        file_format = (
            self._detect_format(
                dataframe
            )
        )

        print(
            f"Detected Bhavcopy format : "
            f"{file_format}"
        )


        if file_format == "OLD":

            dataframe = (
                self._normalize_old_format(
                    dataframe
                )
            )


        elif file_format == "UDIFF":

            dataframe = (
                self._normalize_udiff_format(
                    dataframe
                )
            )


        else:

            raise ValueError(
                f"Unsupported format : "
                f"{file_format}"
            )


        return dataframe


    # ==================================================================
    # VALIDATE COLUMNS
    # ==================================================================

    def _validate_columns(
        self,
        dataframe: pd.DataFrame
    ):

        missing_columns = [

            column

            for column in self.REQUIRED_COLUMNS

            if column not in dataframe.columns

        ]


        if missing_columns:

            raise ValueError(

                "Missing canonical Bhavcopy "
                f"columns : {missing_columns}"

            )


    # ==================================================================
    # CLEAN DATAFRAME
    # ==================================================================

    def _clean_dataframe(
        self,
        dataframe: pd.DataFrame
    ) -> pd.DataFrame:

        # --------------------------------------------------------------
        # Keep only canonical columns
        # --------------------------------------------------------------

        dataframe = dataframe[
            list(self.REQUIRED_COLUMNS)
        ].copy()


        # --------------------------------------------------------------
        # Strip strings
        # --------------------------------------------------------------

        string_columns = (
            dataframe
            .select_dtypes(
                include="object"
            )
            .columns
        )


        dataframe[
            string_columns
        ] = dataframe[
            string_columns
        ].apply(
            lambda column:
            column.astype(str)
            .str.strip()
        )


        # --------------------------------------------------------------
        # Keep EQ series only
        # --------------------------------------------------------------

        dataframe = dataframe[
            dataframe["SERIES"]
            .str.upper()
            .eq("EQ")
        ].copy()


        if dataframe.empty:

            raise ValueError(
                "No EQ series found in "
                "Bhavcopy."
            )


        # --------------------------------------------------------------
        # Timestamp
        # --------------------------------------------------------------

        dataframe["TIMESTAMP"] = (
            pd.to_datetime(
                dataframe["TIMESTAMP"],
                errors="coerce"
            )
        )


        # --------------------------------------------------------------
        # Numeric columns
        # --------------------------------------------------------------

        numeric_columns = (

            "OPEN",

            "HIGH",

            "LOW",

            "CLOSE",

            "LAST",

            "PREVCLOSE",

            "TOTTRDQTY",

            "TOTTRDVAL",

            "TOTALTRADES"

        )


        dataframe[
            list(numeric_columns)
        ] = dataframe[
            list(numeric_columns)
        ].apply(
            pd.to_numeric,
            errors="coerce"
        )


        # --------------------------------------------------------------
        # Remove invalid rows
        # --------------------------------------------------------------

        dataframe = dataframe.dropna(

            subset=[

                "SYMBOL",

                "TIMESTAMP",

                "CLOSE",

                "TOTTRDQTY",

                "TOTTRDVAL"

            ]

        )


        # --------------------------------------------------------------
        # Remove duplicate rows
        # --------------------------------------------------------------

        dataframe = (
            dataframe
            .drop_duplicates()
        )


        # --------------------------------------------------------------
        # Sort
        # --------------------------------------------------------------

        dataframe = (
            dataframe
            .sort_values(
                by=[
                    "SYMBOL",
                    "TIMESTAMP"
                ]
            )
        )


        # --------------------------------------------------------------
        # Reset index
        # --------------------------------------------------------------

        dataframe = (
            dataframe
            .reset_index(
                drop=True
            )
        )


        return dataframe


    # ==================================================================
    # SAVE
    # ==================================================================

    def _save_processed_file(
        self,
        dataframe: pd.DataFrame,
        raw_file_path: Path
    ) -> Path:

        file_name = (
            raw_file_path
            .with_suffix(
                ".parquet"
            )
            .name
        )


        save_output(

            dataframe=dataframe,

            folder_name="processed/bhavcopy",

            file_name=file_name,

            save_output=True

        )


        return (
            self.processed_directory
            / file_name
        )


    # ==================================================================
    # PUBLIC CLEAN FUNCTION
    # ==================================================================

    def clean_file(
        self,
        raw_file_path: Path
    ) -> Path:

        output_path = (
            self.processed_directory
            / raw_file_path
            .with_suffix(
                ".parquet"
            )
            .name
        )


        # --------------------------------------------------------------
        # Already processed
        # --------------------------------------------------------------

        if output_path.exists():

            print(
                "\nProcessed file already exists : "
                f"{output_path.name}"
            )

            return output_path


        # --------------------------------------------------------------
        # READ
        # --------------------------------------------------------------

        dataframe = (
            self._read_raw_file(
                raw_file_path
            )
        )


        # --------------------------------------------------------------
        # NORMALIZE
        # --------------------------------------------------------------

        dataframe = (
            self._normalize_dataframe(
                dataframe
            )
        )


        # --------------------------------------------------------------
        # VALIDATE
        # --------------------------------------------------------------

        self._validate_columns(
            dataframe
        )


        # --------------------------------------------------------------
        # CLEAN
        # --------------------------------------------------------------

        dataframe = (
            self._clean_dataframe(
                dataframe
            )
        )


        # --------------------------------------------------------------
        # SAVE
        # --------------------------------------------------------------

        output_path = (
            self._save_processed_file(
                dataframe,
                raw_file_path
            )
        )


        print(
            "\nProcessed Bhavcopy saved : "
            f"{output_path}"
        )


        return output_path