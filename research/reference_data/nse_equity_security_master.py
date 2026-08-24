# -*- coding: utf-8 -*-
"""
NSE Equity Security Master + Research Universe Builder

Responsibilities:

1. Download official NSE EQUITY_L.csv
2. Resolve master_universe.csv against NSE securities
3. Exclude unresolved instruments such as ETFs
4. Fetch NSE Industry Classification for resolved equities
5. Build the final research_universe.csv
6. Save the normalized NSE security-master snapshot

Research Universe columns:

    SYMBOL
    COMPANY_NAME
    SERIES
    DATE_OF_LISTING
    ISIN
    MACRO_ECONOMIC_SECTOR
    SECTOR
    INDUSTRY
    BASIC_INDUSTRY
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
import time

import pandas as pd
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yfinance as yf

from config.paths import (
    MASTER_UNIVERSE_FILE,
    RESEARCH_REFERENCE_DATA_FOLDER,
    NSE_EQUITY_SECURITY_MASTER_FILE,
    RESEARCH_UNIVERSE_FILE
)


# ======================================================================
# PATHS
# ======================================================================

NSE_EQUITY_SECURITY_MASTER_URL = (
    "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
)

NSE_EQUITY_QUOTE_URL = (
    "https://www.nseindia.com/api/quote-equity"
)

OUTPUT_DIRECTORY = (
    RESEARCH_REFERENCE_DATA_FOLDER
)

OUTPUT_FILE = (
    NSE_EQUITY_SECURITY_MASTER_FILE
)

# ======================================================================
# CONFIGURATION
# ======================================================================

REQUEST_TIMEOUT_SECONDS = 30

# ======================================================================
# NSE EQUITY_L COLUMNS
# ======================================================================

SOURCE_COLUMNS = (
    "SYMBOL",
    "NAME OF COMPANY",
    "SERIES",
    "DATE OF LISTING",
    "ISIN NUMBER",
)


NORMALIZED_COLUMNS = (
    "SYMBOL",
    "COMPANY_NAME",
    "SERIES",
    "DATE_OF_LISTING",
    "ISIN",
)


# ======================================================================
# FINAL RESEARCH UNIVERSE COLUMNS
# ======================================================================

RESEARCH_UNIVERSE_COLUMNS = (
    "SYMBOL",
    "COMPANY_NAME",
    "SERIES",
    "DATE_OF_LISTING",
    "ISIN",
    "MACRO_ECONOMIC_SECTOR",
    "SECTOR",
    "INDUSTRY",
    "BASIC_INDUSTRY",
)


# ======================================================================
# RESULT OBJECT
# ======================================================================

@dataclass
class IdentityValidationResult:

    security_master: pd.DataFrame

    resolved_identities: pd.DataFrame

    missing_symbols: list[str]

    duplicate_master_symbols: list[str]

    duplicate_universe_symbols: list[str]

    total_security_master_rows: int

    total_universe_rows: int

    total_universe_symbols: int

    def summary(
        self
    ) -> dict[str, int]:

        return {

            "total_nse_security_master_rows":
                self.total_security_master_rows,

            "total_research_universe_rows":
                self.total_universe_rows,

            "unique_research_universe_symbols":
                self.total_universe_symbols,

            "matched_symbols":
                len(self.resolved_identities),

            "unresolved_symbols":
                len(self.missing_symbols),

            "duplicate_master_symbols":
                len(self.duplicate_master_symbols),

            "duplicate_universe_symbols":
                len(self.duplicate_universe_symbols),

        }


# ======================================================================
# COLLECTOR
# ======================================================================

class NSEEquitySecurityMasterCollector:

    def __init__(
        self,
        universe_file: Path = MASTER_UNIVERSE_FILE,
        output_file: Path = OUTPUT_FILE,
        research_universe_file: Path = RESEARCH_UNIVERSE_FILE,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:

        self.universe_file = universe_file

        self.output_file = output_file

        self.research_universe_file = (
            research_universe_file
        )

        self.timeout_seconds = (
            timeout_seconds
        )

        self.session = (
            self._build_session()
        )


    # ==================================================================
    # SESSION
    # ==================================================================

    @staticmethod
    def _build_session() -> requests.Session:

        session = requests.Session()

        session.headers.update(

            {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/138.0.0.0 "
                    "Safari/537.36"
                ),

                "Accept": (
                    "text/html,"
                    "application/xhtml+xml,"
                    "application/xml;q=0.9,"
                    "image/avif,"
                    "image/webp,"
                    "*/*;q=0.8"
                ),

                "Accept-Language":
                    "en-US,en;q=0.9",

                "Referer":
                    "https://www.nseindia.com/",
            }

        )

        retry_policy = Retry(

            total=3,

            connect=3,

            read=3,

            backoff_factor=1,

            status_forcelist=(
                429,
                500,
                502,
                503,
                504
            ),

            allowed_methods=frozenset(
                {"GET"}
            ),
        )

        adapter = HTTPAdapter(
            max_retries=retry_policy
        )

        session.mount(
            "https://",
            adapter
        )

        return session


    # ==================================================================
    # NSE EQUITY_L
    # ==================================================================

    def download_security_master(
        self
    ) -> pd.DataFrame:

        response = self.session.get(

            NSE_EQUITY_SECURITY_MASTER_URL,

            timeout=self.timeout_seconds

        )

        response.raise_for_status()

        if not response.content.strip():

            raise ValueError(
                "NSE EQUITY_L.csv download was empty."
            )

        source_data = pd.read_csv(

            StringIO(
                response.text
            ),

            dtype=str

        )

        return (
            self._normalize_security_master(
                source_data
            )
        )


    # ==================================================================
    # NORMALIZE EQUITY_L
    # ==================================================================

    @staticmethod
    def _normalize_security_master(
        source_data: pd.DataFrame
    ) -> pd.DataFrame:

        data = source_data.copy()

        data.columns = (
            data.columns
            .astype(str)
            .str.strip()
        )

        missing_columns = [

            column

            for column in SOURCE_COLUMNS

            if column not in data.columns

        ]

        if missing_columns:

            raise ValueError(

                "NSE EQUITY_L.csv schema changed; "
                f"missing expected columns: "
                f"{missing_columns}"

            )

        data = (
            data
            .loc[:, SOURCE_COLUMNS]
            .rename(
                columns={
                    "NAME OF COMPANY":
                        "COMPANY_NAME",

                    "DATE OF LISTING":
                        "DATE_OF_LISTING",

                    "ISIN NUMBER":
                        "ISIN",
                }
            )
        )

        for column in (
            "SYMBOL",
            "COMPANY_NAME",
            "SERIES",
            "ISIN"
        ):

            data[column] = (

                data[column]

                .fillna("")

                .astype(str)

                .str.strip()

            )

        data["SYMBOL"] = (
            data["SYMBOL"]
            .str.upper()
        )

        data["SERIES"] = (
            data["SERIES"]
            .str.upper()
        )

        data["ISIN"] = (
            data["ISIN"]
            .str.upper()
        )

        data["DATE_OF_LISTING"] = (

            pd.to_datetime(

                data["DATE_OF_LISTING"],

                format="%d-%b-%Y",

                errors="coerce"

            )

            .dt.normalize()

        )

        data = data[
            data["SYMBOL"] != ""
        ].copy()

        if data.empty:

            raise ValueError(
                "NSE EQUITY_L.csv contains "
                "no usable SYMBOL values."
            )

        return (

            data

            .loc[:, NORMALIZED_COLUMNS]

            .reset_index(drop=True)

        )


    # ==================================================================
    # LOAD MASTER UNIVERSE
    # ==================================================================

    def load_research_universe(
        self
    ) -> pd.DataFrame:

        if not self.universe_file.exists():

            raise FileNotFoundError(

                "Research master universe not found: "
                f"{self.universe_file}"

            )

        universe = pd.read_csv(

            self.universe_file,

            dtype=str

        )

        universe.columns = (

            universe.columns

            .astype(str)

            .str.strip()

        )

        if "SYMBOL" not in universe.columns:

            raise ValueError(

                "Research master universe is missing "
                f"SYMBOL: {self.universe_file}"

            )

        universe = (

            universe

            .loc[:, ["SYMBOL"]]

            .copy()

        )

        universe["SYMBOL"] = (

            universe["SYMBOL"]

            .fillna("")

            .astype(str)

            .str.strip()

            .str.upper()

        )

        universe = universe[

            universe["SYMBOL"] != ""

        ].reset_index(
            drop=True
        )

        if universe.empty:

            raise ValueError(
                "Research master universe "
                "contains no usable SYMBOL values."
            )

        return universe


    # ==================================================================
    # VALIDATE UNIVERSE
    # ==================================================================

    @staticmethod
    def validate_universe(

        security_master: pd.DataFrame,

        universe: pd.DataFrame,

    ) -> IdentityValidationResult:

        universe_symbols = (
            universe["SYMBOL"]
        )

        duplicate_universe_symbols = sorted(

            universe_symbols[

                universe_symbols
                .duplicated(
                    keep=False
                )

            ]

            .unique()

            .tolist()

        )

        unique_universe_symbols = sorted(

            universe_symbols
            .unique()
            .tolist()

        )

        master_symbol_counts = (

            security_master["SYMBOL"]
            .value_counts()

        )

        duplicate_master_symbols = sorted(

            master_symbol_counts[

                master_symbol_counts > 1

            ]

            .index

            .tolist()

        )

        unambiguous_master = (

            security_master[

                ~security_master["SYMBOL"]
                .isin(
                    duplicate_master_symbols
                )

            ]

            .copy()

        )

        resolved_identities = (

            pd.DataFrame(
                {
                    "SYMBOL":
                        unique_universe_symbols
                }
            )

            .merge(

                unambiguous_master,

                on="SYMBOL",

                how="inner",

                validate="one_to_one"

            )

            .sort_values(
                "SYMBOL"
            )

            .reset_index(
                drop=True
            )

        )

        resolved_symbols = set(

            resolved_identities[
                "SYMBOL"
            ]

        )

        duplicate_symbol_set = set(

            duplicate_master_symbols

        )

        missing_symbols = sorted(

            symbol

            for symbol
            in unique_universe_symbols

            if (
                symbol
                not in resolved_symbols
                and
                symbol
                not in duplicate_symbol_set
            )

        )

        return IdentityValidationResult(

            security_master=
                security_master,

            resolved_identities=
                resolved_identities,

            missing_symbols=
                missing_symbols,

            duplicate_master_symbols=
                duplicate_master_symbols,

            duplicate_universe_symbols=
                duplicate_universe_symbols,

            total_security_master_rows=
                len(security_master),

            total_universe_rows=
                len(universe),

            total_universe_symbols=
                len(unique_universe_symbols),

        )


    # ==================================================================
    # YAHOO FINANCE SECTOR / INDUSTRY
    # ==================================================================

    @staticmethod
    def _get_industry_classification(
        symbol: str
    ) -> dict:

        yahoo_symbol = f"{symbol}.NS"

        try:

            ticker = yf.Ticker(
                yahoo_symbol
            )

            info = ticker.info

            sector = (
                str(
                    info.get(
                        "sector",
                        ""
                    )
                )
                .strip()
            )

            industry = (
                str(
                    info.get(
                        "industry",
                        ""
                    )
                )
                .strip()
            )

            return {

                "MACRO_ECONOMIC_SECTOR":
                    "",

                "SECTOR":
                    sector,

                "INDUSTRY":
                    industry,

                "BASIC_INDUSTRY":
                    "",

            }

        except Exception as error:

            print(
                f"  {symbol}: "
                f"Yahoo classification failed - "
                f"{error}"
            )

            return {

                "MACRO_ECONOMIC_SECTOR":
                    "",

                "SECTOR":
                    "",

                "INDUSTRY":
                    "",

                "BASIC_INDUSTRY":
                    "",

            }


    # ==================================================================
    # BUILD RESEARCH UNIVERSE
    # ==================================================================

    def build_research_universe(
        self,
        resolved_identities: pd.DataFrame
    ) -> pd.DataFrame:

        research_universe = (
            resolved_identities.copy()
        )

        # --------------------------------------------------------------
        # LOAD EXISTING CLASSIFICATIONS
        # --------------------------------------------------------------

        existing_classifications = {}

        if self.research_universe_file.exists():

            try:

                existing = pd.read_csv(
                    self.research_universe_file,
                    dtype=str
                )

                if "SYMBOL" in existing.columns:

                    existing["SYMBOL"] = (
                        existing["SYMBOL"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .str.upper()
                    )

                    for column in (
                        "MACRO_ECONOMIC_SECTOR",
                        "SECTOR",
                        "INDUSTRY",
                        "BASIC_INDUSTRY"
                    ):

                        if column not in existing.columns:

                            existing[column] = ""

                        existing[column] = (
                            existing[column]
                            .fillna("")
                            .astype(str)
                            .str.strip()
                        )

                    for _, row in existing.iterrows():

                        symbol = row["SYMBOL"]

                        if not symbol:
                            continue

                        existing_classifications[
                            symbol
                        ] = {

                            "MACRO_ECONOMIC_SECTOR":
                                row[
                                    "MACRO_ECONOMIC_SECTOR"
                                ],

                            "SECTOR":
                                row["SECTOR"],

                            "INDUSTRY":
                                row["INDUSTRY"],

                            "BASIC_INDUSTRY":
                                row["BASIC_INDUSTRY"],

                        }

            except Exception as error:

                print(
                    "Warning: could not load "
                    "existing classifications: "
                    f"{error}"
                )

        # --------------------------------------------------------------
        # DETERMINE WHICH SYMBOLS NEED YAHOO LOOKUP
        # --------------------------------------------------------------

        symbols = (
            research_universe[
                "SYMBOL"
            ]
            .astype(str)
            .str.strip()
            .str.upper()
            .tolist()
        )

        symbols_requiring_lookup = [

            symbol

            for symbol in symbols

            if (
                symbol
                not in existing_classifications
            )

        ]

        print(
            "\n"
            + "=" * 70
        )

        print(
            "RESEARCH UNIVERSE CLASSIFICATION"
        )

        print(
            "=" * 70
        )

        print(
            f"Total resolved stocks : "
            f"{len(symbols)}"
        )

        print(
            f"Already classified    : "
            f"{len(symbols) - len(symbols_requiring_lookup)}"
        )

        print(
            f"Yahoo lookups required : "
            f"{len(symbols_requiring_lookup)}"
        )

        # --------------------------------------------------------------
        # YAHOO LOOKUP ONLY FOR NEW SYMBOLS
        # --------------------------------------------------------------

        for position, symbol in enumerate(
            symbols_requiring_lookup,
            start=1
        ):

            print(
                f"[{position}/"
                f"{len(symbols_requiring_lookup)}] "
                f"{symbol}"
            )

            classification = (
                self._get_industry_classification(
                    symbol
                )
            )

            existing_classifications[
                symbol
            ] = classification

        # --------------------------------------------------------------
        # APPLY CLASSIFICATIONS
        # --------------------------------------------------------------

        classification_rows = []

        for symbol in symbols:

            classification = (
                existing_classifications.get(
                    symbol,
                    {
                        "MACRO_ECONOMIC_SECTOR": "",
                        "SECTOR": "",
                        "INDUSTRY": "",
                        "BASIC_INDUSTRY": "",
                    }
                )
            )

            classification_rows.append(
                {
                    "SYMBOL": symbol,

                    "MACRO_ECONOMIC_SECTOR":
                        classification[
                            "MACRO_ECONOMIC_SECTOR"
                        ],

                    "SECTOR":
                        classification[
                            "SECTOR"
                        ],

                    "INDUSTRY":
                        classification[
                            "INDUSTRY"
                        ],

                    "BASIC_INDUSTRY":
                        classification[
                            "BASIC_INDUSTRY"
                        ],
                }
            )

        classification_dataframe = (
            pd.DataFrame(
                classification_rows
            )
        )

        research_universe = (
            research_universe
            .merge(
                classification_dataframe,
                on="SYMBOL",
                how="left",
                validate="one_to_one"
            )
        )

        for column in (
            "MACRO_ECONOMIC_SECTOR",
            "SECTOR",
            "INDUSTRY",
            "BASIC_INDUSTRY"
        ):

            research_universe[column] = (
                research_universe[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        research_universe = (
            research_universe
            .loc[
                :,
                RESEARCH_UNIVERSE_COLUMNS
            ]
            .sort_values(
                "SYMBOL"
            )
            .reset_index(
                drop=True
            )
        )

        return research_universe


    # ==================================================================
    # SAVE RESEARCH UNIVERSE
    # ==================================================================

    def save_research_universe(
        self,
        research_universe: pd.DataFrame
    ) -> Path:

        self.research_universe_file.parent.mkdir(

            parents=True,

            exist_ok=True

        )

        research_universe.to_csv(

            self.research_universe_file,

            index=False

        )

        return (
            self.research_universe_file
        )


    # ==================================================================
    # MAIN COLLECTION
    # ==================================================================

    def collect_and_validate(
        self
    ) -> IdentityValidationResult:

        # --------------------------------------------------------------
        # 1. DOWNLOAD EQUITY_L
        # --------------------------------------------------------------

        security_master = (
            self.download_security_master()
        )

        # --------------------------------------------------------------
        # 2. LOAD MASTER UNIVERSE
        # --------------------------------------------------------------

        universe = (
            self.load_research_universe()
        )

        # --------------------------------------------------------------
        # 3. RESOLVE 1614 -> 1499
        # --------------------------------------------------------------

        result = (
            self.validate_universe(

                security_master=

                    security_master,

                universe=

                    universe,

            )
        )

        # --------------------------------------------------------------
        # 4. SAVE SECURITY MASTER
        # --------------------------------------------------------------

        self.output_file.parent.mkdir(

            parents=True,

            exist_ok=True

        )

        security_master.to_parquet(

            self.output_file,

            index=False

        )

        self._print_result(
            result
        )

        # --------------------------------------------------------------
        # 5. FETCH SECTOR / INDUSTRY
        # --------------------------------------------------------------

        research_universe = (

            self.build_research_universe(

                result.resolved_identities

            )

        )

        # --------------------------------------------------------------
        # 6. SAVE FINAL RESEARCH UNIVERSE
        # --------------------------------------------------------------

        research_universe_path = (

            self.save_research_universe(

                research_universe

            )

        )

        # --------------------------------------------------------------
        # 7. SUMMARY
        # --------------------------------------------------------------

        print(
            "\n"
            + "=" * 70
        )

        print(
            "RESEARCH UNIVERSE UPDATED"
        )

        print(
            "=" * 70
        )

        print(
            f"Research universe size : "
            f"{len(research_universe)}"
        )

        print(
            f"Unresolved symbols     : "
            f"{len(result.missing_symbols)}"
        )

        print(
            f"Output file            : "
            f"{research_universe_path}"
        )

        print(
            "\nResearch Universe columns:"
        )

        print(
            research_universe.columns.tolist()
        )

        return result


    # ==================================================================
    # PRINT VALIDATION
    # ==================================================================

    @staticmethod
    def _print_result(
        result: IdentityValidationResult
    ) -> None:

        print(
            "\nNSE equity security-master "
            "identity validation"
        )

        for label, count in (
            result.summary().items()
        ):

            print(
                f"{label}: {count}"
            )

        print(
            "unresolved_symbols:"
        )

        print(

            ", ".join(
                result.missing_symbols
            )

            if result.missing_symbols

            else "None"

        )

        print(
            "duplicate_master_symbols:"
        )

        print(

            ", ".join(
                result.duplicate_master_symbols
            )

            if result.duplicate_master_symbols

            else "None"

        )

        print(
            "duplicate_universe_symbols:"
        )

        print(

            ", ".join(
                result.duplicate_universe_symbols
            )

            if result.duplicate_universe_symbols

            else "None"

        )


# ======================================================================
# MAIN
# ======================================================================

def main() -> IdentityValidationResult:

    return (
        NSEEquitySecurityMasterCollector()
        .collect_and_validate()
    )


if __name__ == "__main__":

    main()