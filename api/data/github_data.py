"""Read-only access to the GitHub STOCK_SCANNER_DATA repository.

Research Cockpit V1 has no server or database. During local development the
API downloads the required Parquet files directly from the public GitHub data
repository. The local STOCK_SCANNER_DATA checkout is deliberately ignored.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


DATA_REPOSITORY_OWNER = "Mohak22"
DATA_REPOSITORY_NAME = "STOCK_SCANNER_DATA"
DATA_REPOSITORY_BRANCH = "main"

RAW_GITHUB_BASE_URL = (
    "https://raw.githubusercontent.com/"
    f"{DATA_REPOSITORY_OWNER}/{DATA_REPOSITORY_NAME}/"
    f"{DATA_REPOSITORY_BRANCH}/"
)


class ResearchDataRepository:
    """Read-only access to research files stored in GitHub."""

    def __init__(self) -> None:
        self.repository = (
            f"{DATA_REPOSITORY_OWNER}/{DATA_REPOSITORY_NAME}"
        )

    @staticmethod
    def _download(url: str) -> bytes:
        request = Request(
            url,
            headers={"User-Agent": "Stock-Scanner-Research-Cockpit"},
        )

        try:
            with urlopen(request, timeout=60) as response:
                return response.read()
        except HTTPError as exc:
            raise RuntimeError(
                f"GitHub data request failed ({exc.code}): {url}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Could not reach GitHub data repository: {exc.reason}"
            ) from exc

    def health(self) -> dict:
        """Verify that the configured GitHub data repository is reachable."""
        url = RAW_GITHUB_BASE_URL + "master_universe.csv"

        try:
            self._download(url)
            reachable = True
            error = None
        except RuntimeError as exc:
            reachable = False
            error = str(exc)

        return {
            "repository": self.repository,
            "branch": DATA_REPOSITORY_BRANCH,
            "reachable": reachable,
            "error": error,
        }

    def list_bhavcopy_dates(self) -> list[str]:
        """Return available processed Bhavcopy dates from GitHub.

        GitHub's raw-content endpoint cannot list a directory, so the date
        catalogue is intentionally obtained from the Git tree API.
        """
        import json

        url = (
            "https://api.github.com/repos/"
            f"{DATA_REPOSITORY_OWNER}/{DATA_REPOSITORY_NAME}/git/trees/"
            f"{DATA_REPOSITORY_BRANCH}?recursive=1"
        )

        payload = json.loads(self._download(url).decode("utf-8"))
        dates: list[str] = []

        for item in payload.get("tree", []):
            path = item.get("path", "")
            prefix = "processed/bhavcopy/sec_bhavdata_full_"

            if not path.startswith(prefix) or not path.endswith(".parquet"):
                continue

            suffix = path[len(prefix):-len(".parquet")]

            if len(suffix) != 8 or not suffix.isdigit():
                continue

            try:
                parsed = pd.to_datetime(suffix, format="%d%m%Y")
            except ValueError:
                continue

            dates.append(parsed.strftime("%Y-%m-%d"))

        return sorted(set(dates), reverse=True)

    def load_bhavcopy(
        self,
        start_date: str | date,
        end_date: str | date,
    ) -> pd.DataFrame:
        """Load processed Bhavcopy Parquets directly from GitHub."""
        start = pd.Timestamp(start_date).date()
        end = pd.Timestamp(end_date).date()

        if start > end:
            raise ValueError("start_date must be on or before end_date")

        frames: list[pd.DataFrame] = []

        for date_value in pd.date_range(start, end, freq="D"):
            current = date_value.date()
            filename = (
                f"sec_bhavdata_full_{current:%d%m%Y}.parquet"
            )
            relative_path = f"processed/bhavcopy/{filename}"
            url = RAW_GITHUB_BASE_URL + relative_path

            try:
                content = self._download(url)
            except RuntimeError as exc:
                # Weekends and market holidays normally have no Bhavcopy.
                if "(404)" in str(exc):
                    continue
                raise

            frames.append(
                pd.read_parquet(BytesIO(content))
            )

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
