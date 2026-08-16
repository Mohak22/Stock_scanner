"""Collect and validate the current NSE equity security-master snapshot.

This module resolves the dynamic research universe from SYMBOL to current NSE
identity fields only.  Sector and industry collection are intentionally out of
scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.paths import PROJECT_ROOT


NSE_EQUITY_SECURITY_MASTER_URL = (
    "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
)
RESEARCH_DATA_REPOSITORY = PROJECT_ROOT.parent / "STOCK_SCANNER_DATA"
MASTER_UNIVERSE_FILE = RESEARCH_DATA_REPOSITORY / "master_universe.csv"
OUTPUT_DIRECTORY = RESEARCH_DATA_REPOSITORY / "research" / "reference_data"
OUTPUT_FILE = OUTPUT_DIRECTORY / "nse_equity_security_master.parquet"

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


@dataclass
class IdentityValidationResult:
    """Resolved identities and explicit exceptions for the research universe."""

    security_master: pd.DataFrame
    resolved_identities: pd.DataFrame
    missing_symbols: list[str]
    duplicate_master_symbols: list[str]
    duplicate_universe_symbols: list[str]
    total_security_master_rows: int
    total_universe_rows: int
    total_universe_symbols: int

    def summary(self) -> dict[str, int]:
        return {
            "total_nse_security_master_rows": self.total_security_master_rows,
            "total_research_universe_rows": self.total_universe_rows,
            "unique_research_universe_symbols": self.total_universe_symbols,
            "matched_symbols": len(self.resolved_identities),
            "unresolved_symbols": len(self.missing_symbols),
            "duplicate_master_symbols": len(self.duplicate_master_symbols),
            "duplicate_universe_symbols": len(self.duplicate_universe_symbols),
        }


class NSEEquitySecurityMasterCollector:
    """Download the NSE equity list and resolve the current research universe."""

    def __init__(
        self,
        universe_file: Path = MASTER_UNIVERSE_FILE,
        output_file: Path = OUTPUT_FILE,
        timeout_seconds: int = 30,
    ) -> None:
        self.universe_file = universe_file
        self.output_file = output_file
        self.timeout_seconds = timeout_seconds
        self.session = self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
                "Accept": "text/csv,text/plain,*/*",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        retry_policy = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
        adapter = HTTPAdapter(max_retries=retry_policy)
        session.mount("https://", adapter)
        return session

    def download_security_master(self) -> pd.DataFrame:
        """Download and validate the current official NSE security list."""
        response = self.session.get(
            NSE_EQUITY_SECURITY_MASTER_URL,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        if not response.content.strip():
            raise ValueError("NSE EQUITY_L.csv download was empty.")

        source_data = pd.read_csv(StringIO(response.text), dtype=str)
        return self._normalize_security_master(source_data)

    @staticmethod
    def _normalize_security_master(source_data: pd.DataFrame) -> pd.DataFrame:
        data = source_data.copy()
        data.columns = data.columns.astype(str).str.strip()

        missing_columns = [
            column for column in SOURCE_COLUMNS if column not in data.columns
        ]
        if missing_columns:
            raise ValueError(
                "NSE EQUITY_L.csv schema changed; missing expected columns: "
                f"{missing_columns}"
            )

        data = data.loc[:, SOURCE_COLUMNS].rename(
            columns={
                "NAME OF COMPANY": "COMPANY_NAME",
                "DATE OF LISTING": "DATE_OF_LISTING",
                "ISIN NUMBER": "ISIN",
            }
        )

        for column in ("SYMBOL", "COMPANY_NAME", "SERIES", "ISIN"):
            data[column] = data[column].fillna("").astype(str).str.strip()

        data["SYMBOL"] = data["SYMBOL"].str.upper()
        data["SERIES"] = data["SERIES"].str.upper()
        data["ISIN"] = data["ISIN"].str.upper()
        data["DATE_OF_LISTING"] = pd.to_datetime(
            data["DATE_OF_LISTING"],
            format="%d-%b-%Y",
            errors="coerce",
        ).dt.normalize()

        data = data[data["SYMBOL"] != ""].copy()
        if data.empty:
            raise ValueError("NSE EQUITY_L.csv contains no usable SYMBOL values.")

        return data.loc[:, NORMALIZED_COLUMNS].reset_index(drop=True)

    def load_research_universe(self) -> pd.DataFrame:
        """Load and normalize the dynamic research universe without modifying it."""
        if not self.universe_file.exists():
            raise FileNotFoundError(
                f"Research master universe not found: {self.universe_file}"
            )

        universe = pd.read_csv(self.universe_file, dtype=str)
        universe.columns = universe.columns.astype(str).str.strip()
        if "SYMBOL" not in universe.columns:
            raise ValueError(
                f"Research master universe is missing SYMBOL: {self.universe_file}"
            )

        universe = universe.loc[:, ["SYMBOL"]].copy()
        universe["SYMBOL"] = universe["SYMBOL"].fillna("").astype(str).str.strip().str.upper()
        universe = universe[universe["SYMBOL"] != ""].reset_index(drop=True)
        if universe.empty:
            raise ValueError("Research master universe contains no usable SYMBOL values.")
        return universe

    @staticmethod
    def validate_universe(
        security_master: pd.DataFrame,
        universe: pd.DataFrame,
    ) -> IdentityValidationResult:
        """Resolve unambiguous NSE equity-list identities for the research universe."""
        universe_symbols = universe["SYMBOL"]
        duplicate_universe_symbols = sorted(
            universe_symbols[universe_symbols.duplicated(keep=False)].unique().tolist()
        )
        unique_universe_symbols = sorted(universe_symbols.unique().tolist())

        master_symbol_counts = security_master["SYMBOL"].value_counts()
        duplicate_master_symbols = sorted(
            master_symbol_counts[master_symbol_counts > 1].index.tolist()
        )

        unambiguous_master = security_master[
            ~security_master["SYMBOL"].isin(duplicate_master_symbols)
        ].copy()
        resolved_identities = (
            pd.DataFrame({"SYMBOL": unique_universe_symbols})
            .merge(unambiguous_master, on="SYMBOL", how="inner", validate="one_to_one")
            .sort_values("SYMBOL")
            .reset_index(drop=True)
        )

        resolved_symbols = set(resolved_identities["SYMBOL"])
        duplicate_symbol_set = set(duplicate_master_symbols)
        missing_symbols = sorted(
            symbol
            for symbol in unique_universe_symbols
            if symbol not in resolved_symbols and symbol not in duplicate_symbol_set
        )

        return IdentityValidationResult(
            security_master=security_master,
            resolved_identities=resolved_identities,
            missing_symbols=missing_symbols,
            duplicate_master_symbols=duplicate_master_symbols,
            duplicate_universe_symbols=duplicate_universe_symbols,
            total_security_master_rows=len(security_master),
            total_universe_rows=len(universe),
            total_universe_symbols=len(unique_universe_symbols),
        )

    def collect_and_validate(self) -> IdentityValidationResult:
        """Download, save the normalized snapshot, and validate research identities."""
        security_master = self.download_security_master()
        universe = self.load_research_universe()
        result = self.validate_universe(security_master, universe)

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        security_master.to_parquet(self.output_file, index=False)
        self._print_result(result)
        return result

    @staticmethod
    def _print_result(result: IdentityValidationResult) -> None:
        print("\nNSE equity security-master identity validation")
        for label, count in result.summary().items():
            print(f"{label}: {count}")
        print("unresolved_symbols:")
        print(", ".join(result.missing_symbols)
            if result.missing_symbols
            else "None"
        )
        print("duplicate_master_symbols:")
        print(", ".join(result.duplicate_master_symbols)
            if result.duplicate_master_symbols
            else "None"
        )
        print("duplicate_universe_symbols:")
        print(", ".join(result.duplicate_universe_symbols)
            if result.duplicate_universe_symbols
            else "None"
        )


def main() -> IdentityValidationResult:
    """Run the current NSE equity identity validation."""
    return NSEEquitySecurityMasterCollector().collect_and_validate()


if __name__ == "__main__":
    main()
