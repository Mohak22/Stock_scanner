"""Read-only access to the STOCK_SCANNER_DATA repository.

The Research Cockpit currently has no server-side database. The API runs
against a local checkout of STOCK_SCANNER_DATA, which is the same repository
used by GitHub Actions and local development.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.paths import DATA_REPOSITORY


class ResearchDataRepository:
    """Read-only data access for research endpoints."""

    def __init__(self, data_root: Path | None = None) -> None:
        self.data_root = Path(data_root or DATA_REPOSITORY)

    @property
    def processed_bhavcopy(self) -> Path:
        return self.data_root / "processed" / "bhavcopy"

    @property
    def research_market_context(self) -> Path:
        return self.data_root / "research" / "market_context"

    @property
    def historical_market_data(self) -> Path:
        return self.data_root / "research" / "historical_market_data"

    @property
    def reference_data(self) -> Path:
        return self.data_root / "research" / "reference_data"

    def health(self) -> dict:
        return {
            "data_repository": str(self.data_root),
            "exists": self.data_root.exists(),
            "processed_bhavcopy_exists": self.processed_bhavcopy.exists(),
            "market_context_exists": self.research_market_context.exists(),
            "historical_market_data_exists": self.historical_market_data.exists(),
            "reference_data_exists": self.reference_data.exists(),
        }

    def list_bhavcopy_dates(self) -> list[str]:
        """Return available processed Bhavcopy dates, newest first."""
        dates: list[str] = []

        if not self.processed_bhavcopy.exists():
            return dates

        for file in self.processed_bhavcopy.glob("sec_bhavdata_full_*.parquet"):
            suffix = file.stem.removeprefix("sec_bhavdata_full_")
            if len(suffix) != 8 or not suffix.isdigit():
                continue

            try:
                parsed = pd.to_datetime(suffix, format="%d%m%Y")
            except ValueError:
                continue

            dates.append(parsed.strftime("%Y-%m-%d"))

        return sorted(set(dates), reverse=True)

    def load_bhavcopy(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Load processed Bhavcopy files overlapping the requested date range."""
        start = pd.Timestamp(start_date).date()
        end = pd.Timestamp(end_date).date()

        if start > end:
            raise ValueError("start_date must be on or before end_date")

        frames: list[pd.DataFrame] = []

        for file in self.processed_bhavcopy.glob("sec_bhavdata_full_*.parquet"):
            suffix = file.stem.removeprefix("sec_bhavdata_full_")
            if len(suffix) != 8 or not suffix.isdigit():
                continue

            try:
                file_date = pd.to_datetime(suffix, format="%d%m%Y").date()
            except ValueError:
                continue

            if start <= file_date <= end:
                frames.append(pd.read_parquet(file))

        if not frames:
            return pd.DataFrame()

        result = pd.concat(frames, ignore_index=True)

        if "TIMESTAMP" in result.columns:
            result["TIMESTAMP"] = pd.to_datetime(
                result["TIMESTAMP"], errors="coerce"
            ).dt.date

        if "SYMBOL" in result.columns:
            result["SYMBOL"] = (
                result["SYMBOL"].astype(str).str.strip().str.upper()
            )

        return result
