# -*- coding: utf-8 -*-
"""
Created on Thu Jul  2 22:08:26 2026

@author: mohak
"""

from dataclasses import dataclass
from pathlib import Path
import time
import requests

@dataclass
class ReportMetadata:

    file_name: str

    file_path: Path

    trading_date: str

    display_name: str

    file_size: str

    downloaded: bool
    
class ReportNotFoundError(Exception):

    """Raised when the requested report is not present in NSE catalogue."""

    pass


class NSEReportDownloader:
    """
    Downloads NSE reports and stores raw files
    in the STOCK_SCANNER_DATA repository.
    """
    REPORT_API = "https://www.nseindia.com/api/daily-reports"

    ARCHIVE_BASE_URL = (
        "https://nsearchives.nseindia.com/products/content/"
    )

    DEFAULT_SEGMENT = "CM"

    DEFAULT_REPORT_DAY = "PreviousDay"

    SECURITY_BHAVCOPY_FILE_KEY = "CM-BHAVDATA-FULL"

    def __init__(
        self,
        raw_data_dir: Path
    ):
    
        self.raw_data_dir = raw_data_dir
    
        self.raw_data_dir.mkdir(
            parents=True,
            exist_ok=True
        )
    
        self.session = requests.Session()
    
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.nseindia.com/all-reports"
            }
        )
    
    def _fetch_report_catalogue(
        self,
        segment: str
    ) -> dict:
    
        print("\nFetching report catalogue...")
    
        api_url = (
            f"{self.REPORT_API}?key={segment}"
        )
    
        response = self.session.get(
            api_url,
            timeout=30
        )
    
        response.raise_for_status()
    
        return response.json()

    def _find_report(
        self,
        reports: list,
        file_key: str
    ) -> dict:
    
        report = next(
            (
                report
                for report in reports
                if report["fileKey"] == file_key
            ),
            None
        )
    
        if report is None:
    
            raise ReportNotFoundError(
                f"Report '{file_key}' not found."
            )
    
        return report

    def _build_download_url(
        self,
        report: dict
    ) -> str:
    
        return (
            report["filePath"]
            + report["fileActlName"]
        )

    def _download_file(
        self,
        download_url: str,
        file_name: str,
        trading_date: str = "",
        display_name: str = "",
        file_size: str = ""
    ) -> ReportMetadata:
    
        output_path = (
            self.raw_data_dir
            / file_name
        )
    
        if output_path.exists():
    
            print(
                f"\nRaw file already exists : {file_name}"
            )
    
            return ReportMetadata(
                file_name=file_name,
                file_path=output_path,
                trading_date=trading_date,
                display_name=display_name,
                file_size=file_size,
                downloaded=False
            )
    
        print(
            f"\nDownloading : {file_name}"
        )
    
        max_attempts = 3
    
        for attempt in range(1, max_attempts + 1):
    
            try:
    
                response = self.session.get(
                    download_url,
                    timeout=60
                )
    
                response.raise_for_status()
    
                output_path.write_bytes(
                    response.content
                )
    
                print(
                    f"Downloaded : {output_path}"
                )
    
                return ReportMetadata(
                    file_name=file_name,
                    file_path=output_path,
                    trading_date=trading_date,
                    display_name=display_name,
                    file_size=file_size,
                    downloaded=True
                )
    
            except requests.exceptions.ReadTimeout:
    
                print(
                    f"\nAttempt {attempt} of {max_attempts} timed out."
                )
    
                if attempt == max_attempts:
    
                    raise
    
                print(
                    "Retrying in 5 seconds..."
                )
    
                time.sleep(5)

    def download_report(
        self,
        file_key: str,
        report_day: str = DEFAULT_REPORT_DAY,
        segment: str = DEFAULT_SEGMENT
    ) -> ReportMetadata:
    
        data = self._fetch_report_catalogue(
            segment
        )
    
        reports = data[report_day]
    
        report = self._find_report(
            reports,
            file_key
        )
    
        download_url = self._build_download_url(
            report
        )
    
        return self._download_file(
    
            download_url=download_url,
    
            file_name=report["fileActlName"],
    
            trading_date=report["tradingDate"],
    
            display_name=report["displayName"],
    
            file_size=report["fileSize"]
        )

    def download_security_bhavcopy(
        self
    ) -> ReportMetadata:
    
        return self.download_report(
    
            file_key=self.SECURITY_BHAVCOPY_FILE_KEY
    
        )
    
    def download_raw_file(
        self,
        file_name: str
    ) -> ReportMetadata:
    
        download_url = (
            self.ARCHIVE_BASE_URL
            + file_name
        )
    
        return self._download_file(
    
            download_url=download_url,
    
            file_name=file_name
    
        )
