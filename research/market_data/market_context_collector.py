"""Incrementally maintain raw research market-context index history.

This module intentionally stores only raw index OHLC data.  It does not
calculate indicators, classify stocks, or join index data to stock data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import time

import pandas as pd
import yfinance as yf

from config.paths import (
    RESEARCH_MARKET_CONTEXT_INDICES_FOLDER,
    RESEARCH_MARKET_CONTEXT_LOGS_FOLDER,
    RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER,
)


START_DATE = "2016-01-01"
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 2
REQUEST_DELAY_SECONDS = 0.5


@dataclass(frozen=True)
class IndexDefinition:
    """A Yahoo Finance-backed Nifty index maintained by this collector."""

    name: str
    ticker: str | None
    output_folder: Path
    is_sector: bool = False
    unavailable_reason: str | None = None

    @property
    def output_file(self) -> Path:
        return self.output_folder / f"{self.name}.parquet"


# Yahoo Finance symbols are used because yfinance is already the project's
# proven NIFTY 50 source.  These are published Nifty indices, not baskets of
# current stock constituents.
CORE_INDICES = (
    IndexDefinition("nifty_50", "^NSEI", RESEARCH_MARKET_CONTEXT_INDICES_FOLDER),
    IndexDefinition("nifty_500", "^CRSLDX", RESEARCH_MARKET_CONTEXT_INDICES_FOLDER),
)

SECTOR_INDICES = (
    IndexDefinition("auto", "^CNXAUTO", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("bank", "^NSEBANK", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("fmcg", "^CNXFMCG", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("it", "^CNXIT", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("media", "^CNXMEDIA", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("metal", "^CNXMETAL", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("pharma", "^CNXPHARMA", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("realty", "^CNXREALTY", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("energy", "^CNXENERGY", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("infra", "^CNXINFRA", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("psubank", "^CNXPSUBANK", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("privatebank", "NIFTY_PVT_BANK.NS", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("finance", "NIFTY_FIN_SERVICE.NS", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
    IndexDefinition("pse", "^CNXPSE", RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER, True),
)

ALL_INDICES = CORE_INDICES + SECTOR_INDICES
LOG_FILE = RESEARCH_MARKET_CONTEXT_LOGS_FOLDER / "market_context_collection.csv"
REQUIRED_COLUMNS = ("Date", "Open", "High", "Low", "Close")


class MarketContextCollector:
    """Download each supported index independently and maintain its cache."""

    def __init__(self, today: date | None = None) -> None:
        self.today = pd.Timestamp(today or date.today()).normalize()
        for directory in (
            RESEARCH_MARKET_CONTEXT_INDICES_FOLDER,
            RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER,
            RESEARCH_MARKET_CONTEXT_LOGS_FOLDER,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def collect_all(self) -> list[dict]:
        """Collect all supported indices, logging and reporting every result."""
        results = []
        for index_definition in ALL_INDICES:
            result = self.collect_index(index_definition)
            self._append_log(result)
            results.append(result)
            print(self._result_message(result))
            time.sleep(REQUEST_DELAY_SECONDS)
        return results

    def collect_index_by_name(self, index_name: str) -> dict:
        """Collect one named index; useful for a focused first run in Spyder."""
        matching_indices = [item for item in ALL_INDICES if item.name == index_name]
        if not matching_indices:
            supported_names = ", ".join(item.name for item in ALL_INDICES)
            raise ValueError(f"Unsupported index '{index_name}'. Supported: {supported_names}")

        result = self.collect_index(matching_indices[0])
        self._append_log(result)
        print(self._result_message(result))
        return result

    def collect_index(self, index_definition: IndexDefinition) -> dict:
        """Incrementally maintain one index without affecting other indices."""
        try:
            if index_definition.unavailable_reason:
                return self._unavailable_result(index_definition, index_definition.unavailable_reason)

            existing_data = self._load_existing_data(index_definition.output_file)
            rows_before = len(existing_data)
            fetch_start = (
                pd.Timestamp(START_DATE)
                if existing_data.empty
                else existing_data["Date"].max() + pd.Timedelta(days=1)
            )

            if fetch_start > self.today:
                return self._result(index_definition, "up_to_date", existing_data, rows_before, 0)

            new_data = self._fetch_history(index_definition, fetch_start, self.today)
            if new_data.empty:
                if existing_data.empty:
                    raise ValueError("No data returned for the requested historical range.")
                return self._result(index_definition, "no_new_data", existing_data, rows_before, 0)

            combined_data = self._merge_data(existing_data, new_data)
            combined_data.to_parquet(index_definition.output_file, index=False)
            return self._result(
                index_definition,
                "success",
                combined_data,
                rows_before,
                len(combined_data) - rows_before,
            )
        except Exception as error:
            if index_definition.is_sector:
                return self._unavailable_result(
                    index_definition,
                    str(error),
                    locals().get("existing_data"),
                )
            return self._failure_result(index_definition, locals().get("existing_data"), str(error))

    def _load_existing_data(self, file_path: Path) -> pd.DataFrame:
        if not file_path.exists():
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
        return self._prepare_data(pd.read_parquet(file_path))

    def _fetch_history(
        self,
        index_definition: IndexDefinition,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
    ) -> pd.DataFrame:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(
                    f"Fetching {index_definition.name} ({index_definition.ticker}): "
                    f"{start_date.date()} -> {end_date.date()} (attempt {attempt})"
                )
                downloaded_data = yf.download(
                    tickers=index_definition.ticker,
                    start=start_date.date(),
                    end=(end_date + pd.Timedelta(days=1)).date(),
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                )
                if downloaded_data.empty:
                    raise ValueError("Yahoo Finance returned no data.")
                prepared_data = self._prepare_data(downloaded_data)
                if prepared_data.empty:
                    raise ValueError("Yahoo Finance returned no usable OHLC data.")
                if (
                    end_date - start_date >= pd.Timedelta(days=30)
                    and len(prepared_data) < 2
                ):
                    raise ValueError(
                        "Yahoo Finance returned insufficient history for the requested range."
                    )
                return prepared_data
            except Exception as error:
                if attempt == MAX_RETRIES:
                    raise RuntimeError(
                        f"Download failed after {MAX_RETRIES} attempts: {error}"
                    ) from error
                print(f"  Attempt {attempt} failed: {error}. Retrying...")
                time.sleep(RETRY_DELAY_SECONDS)
        raise RuntimeError("Unreachable retry state.")

    @staticmethod
    def _prepare_data(data: pd.DataFrame) -> pd.DataFrame:
        prepared = data.copy()
        if isinstance(prepared.columns, pd.MultiIndex):
            prepared.columns = prepared.columns.get_level_values(0)
        if "Date" not in prepared.columns:
            prepared = prepared.reset_index()
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in prepared.columns]
        if missing_columns:
            raise ValueError(f"Index data is missing required columns: {missing_columns}")

        selected_columns = list(REQUIRED_COLUMNS)
        if "Adj Close" in prepared.columns:
            selected_columns.append("Adj Close")
        prepared = prepared[selected_columns].copy()
        prepared["Date"] = pd.to_datetime(prepared["Date"], errors="coerce")
        if getattr(prepared["Date"].dt, "tz", None) is not None:
            prepared["Date"] = prepared["Date"].dt.tz_localize(None)
        prepared["Date"] = prepared["Date"].dt.normalize()
        prepared = prepared.dropna(subset=REQUIRED_COLUMNS)
        return (
            prepared.sort_values("Date")
            .drop_duplicates(subset=["Date"], keep="last")
            .reset_index(drop=True)
        )

    @staticmethod
    def _merge_data(existing_data: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
        return MarketContextCollector._prepare_data(
            pd.concat([existing_data, new_data], ignore_index=True)
        )

    @staticmethod
    def _result(
        index_definition: IndexDefinition,
        status: str,
        data: pd.DataFrame,
        rows_before: int,
        rows_added: int,
    ) -> dict:
        return {
            "index_name": index_definition.name,
            "ticker": index_definition.ticker,
            "status": status,
            "rows_before": rows_before,
            "rows_added": rows_added,
            "rows_after": len(data),
            "first_date": MarketContextCollector._date_or_none(data, "min"),
            "last_date": MarketContextCollector._date_or_none(data, "max"),
            "error": "",
        }

    @staticmethod
    def _failure_result(
        index_definition: IndexDefinition,
        existing_data: pd.DataFrame | None,
        error: str,
    ) -> dict:
        data = existing_data if isinstance(existing_data, pd.DataFrame) else pd.DataFrame()
        return {
            "index_name": index_definition.name,
            "ticker": index_definition.ticker,
            "status": "failed",
            "rows_before": len(data),
            "rows_added": 0,
            "rows_after": len(data),
            "first_date": MarketContextCollector._date_or_none(data, "min"),
            "last_date": MarketContextCollector._date_or_none(data, "max"),
            "error": error,
        }

    @staticmethod
    def _unavailable_result(
        index_definition: IndexDefinition,
        error: str,
        existing_data: pd.DataFrame | None = None,
    ) -> dict:
        """Record an unavailable sector without stopping the full collection."""
        result = MarketContextCollector._failure_result(
            index_definition,
            existing_data,
            error,
        )
        result["status"] = "unavailable"
        return result

    @staticmethod
    def _date_or_none(data: pd.DataFrame, operation: str) -> str | None:
        if data.empty or "Date" not in data.columns:
            return None
        value = getattr(data["Date"], operation)()
        return None if pd.isna(value) else str(value.date())

    @staticmethod
    def _result_message(result: dict) -> str:
        message = (
            f"{result['index_name']}: {result['status']} "
            f"(before={result['rows_before']}, added={result['rows_added']}, "
            f"after={result['rows_after']})"
        )
        return f"{message} - {result['error']}" if result["error"] else message

    @staticmethod
    def _append_log(result: dict) -> None:
        pd.DataFrame([result]).to_csv(
            LOG_FILE,
            mode="a",
            index=False,
            header=not LOG_FILE.exists(),
        )


def main() -> list[dict]:
    """Run the complete research market-context collection."""
    return MarketContextCollector().collect_all()


if __name__ == "__main__":
    main()
