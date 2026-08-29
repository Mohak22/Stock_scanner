"""Read-only access to the private GitHub STOCK_SCANNER_DATA repository."""

from __future__ import annotations

import json
import os
from datetime import date
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


DATA_REPOSITORY_OWNER = "Mohak22"
DATA_REPOSITORY_NAME = "STOCK_SCANNER_DATA"
DATA_REPOSITORY_BRANCH = "main"
GITHUB_API_BASE_URL = "https://api.github.com"


class ResearchDataRepository:
    """Read-only access to research files stored in private GitHub."""

    def __init__(self) -> None:
        self.repository = (
            f"{DATA_REPOSITORY_OWNER}/{DATA_REPOSITORY_NAME}"
        )
        self.token = os.getenv("STOCK_SCANNER_DATA_TOKEN")

    def _request(self, url: str) -> bytes:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Stock-Scanner-Research-Cockpit",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = Request(url, headers=headers)

        try:
            with urlopen(request, timeout=60) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code == 401:
                raise RuntimeError(
                    "GitHub authentication failed. Check "
                    "STOCK_SCANNER_DATA_TOKEN."
                ) from exc
            if exc.code == 403:
                raise RuntimeError(
                    "GitHub access denied. Check the token permissions."
                ) from exc
            if exc.code == 404:
                raise RuntimeError(
                    f"GitHub resource not found: {url}"
                ) from exc
            raise RuntimeError(
                f"GitHub data request failed ({exc.code}): {url}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Could not reach GitHub: {exc.reason}"
            ) from exc

    def health(self) -> dict:
        """Verify authenticated access to the private data repository."""
        url = (
            f"{GITHUB_API_BASE_URL}/repos/"
            f"{self.repository}"
        )

        try:
            payload = json.loads(self._request(url).decode("utf-8"))
            reachable = payload.get("full_name") == self.repository
            error = None if reachable else "Unexpected GitHub repository response."
        except RuntimeError as exc:
            reachable = False
            error = str(exc)

        return {
            "repository": self.repository,
            "branch": DATA_REPOSITORY_BRANCH,
            "reachable": reachable,
            "error": error,
        }

    def _tree(self) -> list[dict]:
        url = (
            f"{GITHUB_API_BASE_URL}/repos/{self.repository}/git/trees/"
            f"{DATA_REPOSITORY_BRANCH}?recursive=1"
        )
        payload = json.loads(self._request(url).decode("utf-8"))
        return payload.get("tree", [])

    def list_bhavcopy_dates(self) -> list[str]:
        dates: list[str] = []
        prefix = "processed/bhavcopy/sec_bhavdata_full_"

        for item in self._tree():
            path = item.get("path", "")
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
        start = pd.Timestamp(start_date).date()
        end = pd.Timestamp(end_date).date()

        if start > end:
            raise ValueError("start_date must be on or before end_date")

        frames: list[pd.DataFrame] = []

        for date_value in pd.date_range(start, end, freq="D"):
            current = date_value.date()
            filename = f"sec_bhavdata_full_{current:%d%m%Y}.parquet"
            path = f"processed/bhavcopy/{filename}"

            url = (
                f"{GITHUB_API_BASE_URL}/repos/{self.repository}/contents/{path}"
                f"?ref={DATA_REPOSITORY_BRANCH}"
            )

            try:
                payload = json.loads(self._request(url).decode("utf-8"))
            except RuntimeError as exc:
                if "not found" in str(exc).lower():
                    continue
                raise

            import base64
            content = base64.b64decode(payload["content"])
            frames.append(pd.read_parquet(BytesIO(content)))

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
