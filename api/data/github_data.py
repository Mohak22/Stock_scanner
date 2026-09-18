"""
Read-only access to the private GitHub STOCK_SCANNER_DATA repository.
"""

from __future__ import annotations

import base64
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


DATA_REPOSITORY_OWNER = "Mohak22"
DATA_REPOSITORY_NAME = "STOCK_SCANNER_DATA"
DATA_REPOSITORY_BRANCH = "main"

GITHUB_API_BASE_URL = "https://api.github.com"

MAX_DOWNLOAD_WORKERS = 8


class ResearchDataRepository:

    def __init__(self) -> None:

        self.repository = (
            f"{DATA_REPOSITORY_OWNER}/{DATA_REPOSITORY_NAME}"
        )

        self.token = os.getenv(
            "STOCK_SCANNER_DATA_TOKEN"
        )

    # ==========================================================
    # GITHUB REQUEST
    # ==========================================================

    def _request(
        self,
        url: str,
        accept: str = "application/vnd.github+json",
    ) -> bytes:

        headers = {
            "Accept": accept,
            "User-Agent": "Stock-Scanner-Research-Cockpit",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if self.token:

            headers["Authorization"] = (
                f"Bearer {self.token}"
            )

        request = Request(
            url,
            headers=headers,
        )

        try:

            with urlopen(
                request,
                timeout=60,
            ) as response:

                return response.read()

        except HTTPError as exc:

            error_body = (
                exc.read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            print(
                "\n========== GITHUB ERROR =========="
            )
            print("Status:", exc.code)
            print("URL:", url)
            print("Response:", error_body)
            print(
                "==================================\n"
            )

            if exc.code == 401:

                raise RuntimeError(
                    "GitHub authentication failed. "
                    "Check STOCK_SCANNER_DATA_TOKEN."
                ) from exc

            if exc.code == 403:

                raise RuntimeError(
                    "GitHub access denied or API "
                    "rate limit exceeded. "
                    "Check the token and permissions."
                ) from exc

            if exc.code == 404:

                raise RuntimeError(
                    f"GitHub resource not found: {url}"
                ) from exc

            raise RuntimeError(
                f"GitHub data request failed "
                f"({exc.code}): {url}"
            ) from exc

        except URLError as exc:

            raise RuntimeError(
                f"Could not reach GitHub: "
                f"{exc.reason}"
            ) from exc

    # ==========================================================
    # HEALTH
    # ==========================================================

    def health(self) -> dict:

        url = (
            f"{GITHUB_API_BASE_URL}"
            f"/repos/{self.repository}"
        )

        try:

            payload = json.loads(
                self._request(url)
                .decode("utf-8")
            )

            reachable = (
                payload.get("full_name")
                == self.repository
            )

            error = (
                None
                if reachable
                else
                "Unexpected GitHub repository response."
            )

        except RuntimeError as exc:

            reachable = False
            error = str(exc)

        return {
            "repository": self.repository,
            "branch": DATA_REPOSITORY_BRANCH,
            "reachable": reachable,
            "error": error,
        }

    # ==========================================================
    # CSV
    # ==========================================================

    def load_csv(
        self,
        path: str,
    ) -> pd.DataFrame:

        url = (
            f"{GITHUB_API_BASE_URL}"
            f"/repos/{self.repository}"
            f"/contents/{path}"
            f"?ref={DATA_REPOSITORY_BRANCH}"
        )

        payload = json.loads(
            self._request(url)
            .decode("utf-8")
        )

        if "content" not in payload:

            raise RuntimeError(
                f"GitHub file content missing for: {path}"
            )

        content = base64.b64decode(
            payload["content"]
        )

        return pd.read_csv(
            BytesIO(content)
        )

    # ==========================================================
    # PARQUET
    #
    # Always fetched directly from GitHub.
    # No local cache.
    # ==========================================================

    def load_parquet(
        self,
        path: str,
    ) -> pd.DataFrame:

        url = (
            f"{GITHUB_API_BASE_URL}"
            f"/repos/{self.repository}"
            f"/contents/{path}"
            f"?ref={DATA_REPOSITORY_BRANCH}"
        )

        content = self._request(
            url,
            accept="application/vnd.github.raw+json",
        )

        return pd.read_parquet(
            BytesIO(content)
        )

    # ==========================================================
    # GITHUB TREE
    # ==========================================================

    def _tree(self) -> list[dict]:

        url = (
            f"{GITHUB_API_BASE_URL}"
            f"/repos/{self.repository}"
            f"/git/trees/{DATA_REPOSITORY_BRANCH}"
            f"?recursive=1"
        )

        payload = json.loads(
            self._request(url)
            .decode("utf-8")
        )

        return payload.get(
            "tree",
            [],
        )

    # ==========================================================
    # AVAILABLE BHAVCOPY DATES
    # ==========================================================

    def list_bhavcopy_dates(
        self,
    ) -> list[str]:

        dates = []

        prefix = (
            "processed/bhavcopy/"
            "sec_bhavdata_full_"
        )

        for item in self._tree():

            path = item.get(
                "path",
                "",
            )

            if not path.startswith(prefix):
                continue

            if not path.endswith(".parquet"):
                continue

            suffix = path[
                len(prefix):-len(".parquet")
            ]

            if (
                len(suffix) != 8
                or not suffix.isdigit()
            ):
                continue

            try:

                parsed = pd.to_datetime(
                    suffix,
                    format="%d%m%Y",
                )

            except ValueError:

                continue

            dates.append(
                parsed.strftime(
                    "%Y-%m-%d"
                )
            )

        return sorted(
            set(dates),
            reverse=True,
        )

    # ==========================================================
    # DOWNLOAD ONE BHAVCOPY FILE
    #
    # IMPORTANT:
    # No local cache.
    # Every call downloads the current GitHub version.
    # ==========================================================

    def _download_bhavcopy_file(
        self,
        file_date: date,
        path: str,
    ) -> pd.DataFrame:

        url = (
            f"{GITHUB_API_BASE_URL}"
            f"/repos/{self.repository}"
            f"/contents/{path}"
            f"?ref={DATA_REPOSITORY_BRANCH}"
        )

        content = self._request(
            url,
            accept="application/vnd.github.raw+json",
        )

        return pd.read_parquet(
            BytesIO(content)
        )

    # ==========================================================
    # LOAD BHAVCOPY
    #
    # GitHub is the source of truth.
    # No local data dependency.
    # ==========================================================

    def load_bhavcopy(
        self,
        start_date: str | date,
        end_date: str | date,
    ) -> pd.DataFrame:

        start = pd.Timestamp(
            start_date
        ).date()

        end = pd.Timestamp(
            end_date
        ).date()

        if start > end:

            raise ValueError(
                "start_date must be on or before end_date"
            )

        # ------------------------------------------------------
        # GET CURRENT GITHUB TREE
        # ------------------------------------------------------

        tree = self._tree()

        prefix = (
            "processed/bhavcopy/"
            "sec_bhavdata_full_"
        )

        selected_paths = []

        for item in tree:

            path = item.get(
                "path",
                "",
            )

            if not path.startswith(prefix):
                continue

            if not path.endswith(".parquet"):
                continue

            filename = path.rsplit(
                "/",
                1
            )[-1]

            date_text = filename[
                len("sec_bhavdata_full_"):
                -len(".parquet")
            ]

            if (
                len(date_text) != 8
                or not date_text.isdigit()
            ):
                continue

            try:

                file_date = pd.to_datetime(
                    date_text,
                    format="%d%m%Y",
                ).date()

            except ValueError:

                continue

            if start <= file_date <= end:

                selected_paths.append(
                    (
                        file_date,
                        path,
                    )
                )

        selected_paths.sort(
            key=lambda item: item[0]
        )

        if not selected_paths:

            return pd.DataFrame()

        # ------------------------------------------------------
        # DOWNLOAD CURRENT GITHUB FILES
        # ------------------------------------------------------

        with ThreadPoolExecutor(
            max_workers=MAX_DOWNLOAD_WORKERS
        ) as executor:

            future_map = {
                executor.submit(
                    self._download_bhavcopy_file,
                    file_date,
                    path,
                ): file_date
                for file_date, path
                in selected_paths
            }

            results = []

            for future in as_completed(
                future_map
            ):

                file_date = future_map[
                    future
                ]

                try:

                    dataframe = future.result()

                    results.append(
                        (
                            file_date,
                            dataframe,
                        )
                    )

                except Exception as exc:

                    raise RuntimeError(
                        "Failed to load bhavcopy "
                        f"for {file_date}: {exc}"
                    ) from exc

        # ------------------------------------------------------
        # RESTORE CHRONOLOGICAL ORDER
        # ------------------------------------------------------

        results.sort(
            key=lambda item: item[0]
        )

        frames = [
            dataframe
            for _, dataframe
            in results
        ]

        if not frames:

            return pd.DataFrame()

        # ------------------------------------------------------
        # COMBINE
        # ------------------------------------------------------

        result = pd.concat(
            frames,
            ignore_index=True,
        )

        # ------------------------------------------------------
        # NORMALIZE
        # ------------------------------------------------------

        if "TIMESTAMP" in result.columns:

            result["TIMESTAMP"] = (
                pd.to_datetime(
                    result["TIMESTAMP"],
                    errors="coerce",
                )
            )

        if "SYMBOL" in result.columns:

            result["SYMBOL"] = (
                result["SYMBOL"]
                .astype(str)
                .str.strip()
                .str.upper()
            )

        # ------------------------------------------------------
        # FINAL DATE FILTER
        # ------------------------------------------------------

        if "TIMESTAMP" in result.columns:

            result = result[
                (
                    result["TIMESTAMP"]
                    >= pd.Timestamp(start)
                )
                &
                (
                    result["TIMESTAMP"]
                    <
                    pd.Timestamp(end)
                    + pd.Timedelta(days=1)
                )
            ].copy()

        # ------------------------------------------------------
        # SORT
        # ------------------------------------------------------

        if (
            "SYMBOL" in result.columns
            and "TIMESTAMP" in result.columns
        ):

            result = (
                result
                .sort_values(
                    [
                        "SYMBOL",
                        "TIMESTAMP",
                    ]
                )
                .reset_index(drop=True)
            )

        return result