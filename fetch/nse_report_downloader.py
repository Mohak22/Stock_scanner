# -*- coding: utf-8 -*-
"""
Created on Thu Jul  2 22:08:26 2026

@author: mohak
"""

"""
NSE report downloader.

Responsibilities:   
    - Download current NSE Full Bhavcopy files.
    - Download historical NSE Bhavcopy files.
    - Handle the pre-July-2024 historical archive format.
    - Handle the post-July-2024 UDiFF historical format.
    - Download NSE Security-wise Delivery Position (MTO).
    - Preserve the existing raw filename convention.
    - Validate downloaded content before saving.
    - Keep raw files exactly as downloaded by NSE.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import io
import time
import zipfile

import requests


# ======================================================================
# METADATA
# ======================================================================

@dataclass
class ReportMetadata:

    file_name: str

    file_path: Path

    trading_date: str

    display_name: str

    file_size: str

    downloaded: bool


# ======================================================================
# EXCEPTIONS
# ======================================================================

class ReportNotFoundError(Exception):

    """Raised when the requested report is not available."""

    pass


# ======================================================================
# DOWNLOADER
# ======================================================================

class NSEReportDownloader:
    """
    Downloads NSE reports and stores raw files in STOCK_SCANNER_DATA.

    Bhavcopy files:

        raw/nse/bhavcopy/

    MTO files:

        raw/nse/mto/

    Historical Bhavcopy filename:

        sec_bhavdata_full_DDMMYYYY.csv

    Historical MTO filename:

        MTO_DDMMYYYY.DAT

    Raw NSE contents are preserved.
    Normalization belongs to the processing layer.
    """

    # ==================================================================
    # CURRENT NSE REPORT API
    # ==================================================================

    REPORT_API = (
        "https://www.nseindia.com/api/daily-reports"
    )

    ARCHIVE_BASE_URL = (
        "https://nsearchives.nseindia.com/products/content/"
    )

    # ==================================================================
    # HISTORICAL BHAVCOPY
    # ==================================================================

    HISTORICAL_BASE_URL = (
        "https://nsearchives.nseindia.com/content/"
        "historical/EQUITIES/"
    )

    # Old CM Bhavcopy was discontinued from 08-Jul-2024.
    HISTORICAL_FORMAT_END_DATE = date(
        2024,
        7,
        7
    )

    # ==================================================================
    # HISTORICAL MTO
    # ==================================================================

    MTO_HISTORICAL_BASE_URL = (
        "https://nsearchives.nseindia.com/"
        "archives/equities/mto/"
    )

    # ==================================================================
    # DEFAULT SETTINGS
    # ==================================================================

    DEFAULT_SEGMENT = "CM"

    DEFAULT_REPORT_DAY = "PreviousDay"

    SECURITY_BHAVCOPY_FILE_KEY = (
        "CM-BHAVDATA-FULL"
    )

    MTO_FILE_KEY = (
        "CM-SECWISE-DELIVERY-POSITION"
    )

    # ==================================================================
    # RETRY SETTINGS
    # ==================================================================

    MAX_RETRIES = 3

    RETRY_DELAY_SECONDS = 2

    # ==================================================================
    # EXPECTED CURRENT FULL BHAVCOPY COLUMNS
    # ==================================================================

    CURRENT_REQUIRED_COLUMNS = {

        "SYMBOL",
        "SERIES",
        "DATE1",
        "PREV_CLOSE",
        "OPEN_PRICE",
        "HIGH_PRICE",
        "LOW_PRICE",
        "LAST_PRICE",
        "CLOSE_PRICE",
        "AVG_PRICE",
        "TTL_TRD_QNTY",
        "TURNOVER_LACS",
        "NO_OF_TRADES",
        "DELIV_QTY",
        "DELIV_PER",

    }

    # ==================================================================
    # OLD BHAVCOPY COLUMNS
    # ==================================================================

    OLD_REQUIRED_COLUMNS = {

        "SYMBOL",
        "SERIES",
        "OPEN",
        "HIGH",
        "LOW",
        "CLOSE",
        "TOTTRDQTY",

    }

    # ==================================================================
    # MTO VALIDATION
    # ==================================================================

    MTO_REQUIRED_TEXT = (
        b"Security Wise Delivery Position"
    )

    # ==================================================================
    # INITIALIZATION
    # ==================================================================

    def __init__(
        self,
        raw_data_dir: Path,
        mto_data_dir: Path | None = None
    ):

        # --------------------------------------------------------------
        # BHAVCOPY DIRECTORY
        # --------------------------------------------------------------

        self.raw_data_dir = raw_data_dir

        self.raw_data_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # --------------------------------------------------------------
        # MTO DIRECTORY
        # --------------------------------------------------------------

        if mto_data_dir is None:

            self.mto_data_dir = (
                self.raw_data_dir.parent
                / "mto"
            )

        else:

            self.mto_data_dir = (
                mto_data_dir
            )

        self.mto_data_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # --------------------------------------------------------------
        # NSE SESSION
        # --------------------------------------------------------------

        self.session = requests.Session()

        self.session.headers.update({

            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/138.0.0.0 "
                "Safari/537.36"
            ),

            "Accept": "*/*",

            "Accept-Language": (
                "en-US,en;q=0.9"
            ),

            "Referer": (
                "https://www.nseindia.com/all-reports"
            ),

            "Connection": "keep-alive"

        })

    # ==================================================================
    # GENERAL HELPERS
    # ==================================================================

    @staticmethod
    def _normalise_columns(
        columns
    ) -> set:

        return {

            str(column)
            .strip()
            .upper()

            for column in columns

        }

    @staticmethod
    def _is_html_response(
        content: bytes
    ) -> bool:

        sample = (
            content[:500]
            .lower()
        )

        return (

            b"<html" in sample

            or b"<!doctype" in sample

            or b"<head" in sample

        )

    # ==================================================================
    # CSV VALIDATION
    # ==================================================================

    def _validate_csv_content(
        self,
        content: bytes,
        required_columns: set,
        format_name: str
    ) -> bool:
        """
        Validate downloaded CSV content without modifying it.
        """

        if not content:

            print(
                "Invalid Bhavcopy: "
                "empty response."
            )

            return False

        if self._is_html_response(
            content
        ):

            print(
                "Invalid Bhavcopy: "
                "HTML/error response received."
            )

            return False

        try:

            first_line = (

                content
                .splitlines()[0]
                .decode(
                    "utf-8-sig",
                    errors="replace"
                )

            )

        except Exception as error:

            print(
                "Invalid Bhavcopy: "
                f"unable to read header - {error}"
            )

            return False

        columns = (
            self._normalise_columns(
                first_line.split(",")
            )
        )

        missing_columns = (
            required_columns
            - columns
        )

        if missing_columns:

            print(
                f"Invalid {format_name} Bhavcopy."
            )

            print(
                "Missing columns:"
            )

            print(
                sorted(missing_columns)
            )

            print(
                "Received columns:"
            )

            print(
                sorted(columns)
            )

            return False

        return True

    # ==================================================================
    # MTO VALIDATION
    # ==================================================================

    def _validate_mto_content(
        self,
        content: bytes
    ) -> bool:
        """
        Validate NSE MTO content.

        MTO is a DAT text file rather than CSV.
        """

        if not content:

            print(
                "Invalid MTO: "
                "empty response."
            )

            return False

        if self._is_html_response(
            content
        ):

            print(
                "Invalid MTO: "
                "HTML/error response received."
            )

            return False

        sample = (
            content[:2000]
        )

        if (
            self.MTO_REQUIRED_TEXT
            not in sample
        ):

            print(
                "Invalid MTO: "
                "expected NSE Security Wise "
                "Delivery Position header "
                "not found."
            )

            return False

        return True

    # ==================================================================
    # CURRENT NSE REPORT CATALOGUE
    # ==================================================================

    def _fetch_report_catalogue(
        self,
        segment: str
    ) -> dict:

        print(
            "\nFetching report catalogue..."
        )

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

                if report.get(
                    "fileKey"
                ) == file_key

            ),

            None

        )

        if report is None:

            raise ReportNotFoundError(
                f"Report '{file_key}' "
                "not found."
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

    # ==================================================================
    # SAVE RAW CONTENT
    # ==================================================================

    def _save_raw_content(
        self,
        content: bytes,
        file_name: str,
        output_dir: Path,
        trading_date: str = "",
        display_name: str = "",
        file_size: str = ""
    ) -> ReportMetadata | None:

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        output_path = (
            output_dir
            / file_name
        )

        if output_path.exists():

            print(
                f"\nRaw file already exists : "
                f"{file_name}"
            )

            return ReportMetadata(

                file_name=file_name,

                file_path=output_path,

                trading_date=trading_date,

                display_name=display_name,

                file_size=file_size,

                downloaded=False

            )

        output_path.write_bytes(
            content
        )

        print(
            f"Downloaded : "
            f"{output_path}"
        )

        return ReportMetadata(

            file_name=file_name,

            file_path=output_path,

            trading_date=trading_date,

            display_name=display_name,

            file_size=file_size,

            downloaded=True

        )

    # ==================================================================
    # GENERIC BHAVCOPY DOWNLOAD
    # ==================================================================

    def _download_file(
        self,
        download_url: str,
        file_name: str,
        trading_date: str = "",
        display_name: str = "",
        file_size: str = "",
        required_columns: set | None = None,
        format_name: str = "Full"
    ) -> ReportMetadata | None:

        output_path = (
            self.raw_data_dir
            / file_name
        )

        if output_path.exists():

            print(
                f"\nRaw file already exists : "
                f"{file_name}"
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
            f"\nDownloading : "
            f"{file_name}"
        )

        print(
            f"Download URL : "
            f"{download_url}"
        )

        for attempt in range(

            1,

            self.MAX_RETRIES + 1

        ):

            try:

                response = self.session.get(

                    download_url,

                    timeout=60

                )

                print(
                    f"Status: "
                    f"{response.status_code}"
                )

                response.raise_for_status()

                content = (
                    response.content
                )

                if required_columns is not None:

                    if not self._validate_csv_content(

                        content,

                        required_columns,

                        format_name

                    ):

                        raise ValueError(

                            "Downloaded response is "
                            f"not a valid "
                            f"{format_name} "
                            "Bhavcopy."

                        )

                return self._save_raw_content(

                    content=content,

                    file_name=file_name,

                    output_dir=self.raw_data_dir,

                    trading_date=trading_date,

                    display_name=display_name,

                    file_size=file_size

                )

            except Exception as error:

                print(

                    f"{file_name} : "
                    f"attempt {attempt} "
                    f"failed - {error}"

                )

                if attempt < self.MAX_RETRIES:

                    time.sleep(
                        self.RETRY_DELAY_SECONDS
                    )

                else:

                    print(

                        f"{file_name} : "
                        f"giving up after "
                        f"{self.MAX_RETRIES} "
                        "attempts"

                    )

        return None

    # ==================================================================
    # CURRENT FULL BHAVCOPY
    # ==================================================================

    def download_report(
        self,
        file_key: str,
        report_day: str = DEFAULT_REPORT_DAY,
        segment: str = DEFAULT_SEGMENT
    ) -> ReportMetadata | None:

        data = (
            self._fetch_report_catalogue(
                segment
            )
        )

        reports = data.get(
            report_day,
            []
        )

        report = self._find_report(
            reports,
            file_key
        )

        download_url = (
            self._build_download_url(
                report
            )
        )

        return self._download_file(

            download_url=download_url,

            file_name=report[
                "fileActlName"
            ],

            trading_date=report.get(
                "tradingDate",
                ""
            ),

            display_name=report.get(
                "displayName",
                ""
            ),

            file_size=report.get(
                "fileSize",
                ""
            ),

            required_columns=(
                self.CURRENT_REQUIRED_COLUMNS
            ),

            format_name="Current Full"

        )

    def download_security_bhavcopy(
        self
    ) -> ReportMetadata | None:

        return self.download_report(

            file_key=(
                self.SECURITY_BHAVCOPY_FILE_KEY
            )

        )

    # ==================================================================
    # CURRENT ARCHIVE FILE
    # ==================================================================

    def download_raw_file(
        self,
        file_name: str
    ) -> ReportMetadata | None:

        download_url = (
            self.ARCHIVE_BASE_URL
            + file_name
        )

        return self._download_file(

            download_url=download_url,

            file_name=file_name

        )

    # ==================================================================
    # CURRENT MTO
    # ==================================================================

    def download_mto_report(
        self
    ) -> ReportMetadata | None:
        """
        Download the current NSE Security-wise
        Delivery Position report.
        """

        data = (
            self._fetch_report_catalogue(
                self.DEFAULT_SEGMENT
            )
        )

        reports = data.get(
            self.DEFAULT_REPORT_DAY,
            []
        )

        report = self._find_report(

            reports,

            self.MTO_FILE_KEY

        )

        download_url = (
            self._build_download_url(
                report
            )
        )

        file_name = (
            report["fileActlName"]
        )

        output_path = (
            self.mto_data_dir
            / file_name
        )

        if output_path.exists():

            print(
                f"\nMTO already exists : "
                f"{file_name}"
            )

            return ReportMetadata(

                file_name=file_name,

                file_path=output_path,

                trading_date=report.get(
                    "tradingDate",
                    ""
                ),

                display_name=report.get(
                    "displayName",
                    ""
                ),

                file_size=report.get(
                    "fileSize",
                    ""
                ),

                downloaded=False

            )

        print(
            f"\nDownloading MTO : "
            f"{file_name}"
        )

        print(
            f"Download URL : "
            f"{download_url}"
        )

        for attempt in range(

            1,

            self.MAX_RETRIES + 1

        ):

            try:

                response = self.session.get(

                    download_url,

                    timeout=60

                )

                print(
                    f"Status: "
                    f"{response.status_code}"
                )

                response.raise_for_status()

                content = (
                    response.content
                )

                if not self._validate_mto_content(
                    content
                ):

                    raise ValueError(
                        "Downloaded response is "
                        "not a valid NSE MTO report."
                    )

                return self._save_raw_content(

                    content=content,

                    file_name=file_name,

                    output_dir=self.mto_data_dir,

                    trading_date=report.get(
                        "tradingDate",
                        ""
                    ),

                    display_name=report.get(
                        "displayName",
                        ""
                    ),

                    file_size=report.get(
                        "fileSize",
                        ""
                    )

                )

            except Exception as error:

                print(

                    f"MTO {file_name} : "
                    f"attempt {attempt} "
                    f"failed - {error}"

                )

                if attempt < self.MAX_RETRIES:

                    time.sleep(
                        self.RETRY_DELAY_SECONDS
                    )

                else:

                    print(

                        f"MTO {file_name} : "
                        f"giving up after "
                        f"{self.MAX_RETRIES} "
                        "attempts"

                    )

        return None

    # ==================================================================
    # HISTORICAL BHAVCOPY FILENAME
    # ==================================================================

    @staticmethod
    def _build_standard_filename(
        trading_date: date
    ) -> str:

        return (

            "sec_bhavdata_full_"

            + trading_date.strftime(
                "%d%m%Y"
            )

            + ".csv"

        )

    # ==================================================================
    # HISTORICAL MTO FILENAME
    # ==================================================================

    @staticmethod
    def _build_mto_filename(
        trading_date: date
    ) -> str:

        return (

            "MTO_"

            + trading_date.strftime(
                "%d%m%Y"
            )

            + ".DAT"

        )

    # ==================================================================
    # OLD HISTORICAL BHAVCOPY URL
    # ==================================================================

    @staticmethod
    def _build_old_historical_url(
        trading_date: date
    ) -> str:

        year = (
            trading_date.strftime(
                "%Y"
            )
        )

        month = (
            trading_date.strftime(
                "%b"
            ).upper()
        )

        day = (
            trading_date.strftime(
                "%d"
            )
        )

        file_name = (

            f"cm{day}"
            f"{month}"
            f"{year}"
            "bhav.csv.zip"

        )

        return (

            "https://nsearchives.nseindia.com/"
            "content/historical/EQUITIES/"
            f"{year}/{month}/{file_name}"

        )

    # ==================================================================
    # NEW UDIFF BHAVCOPY URL
    # ==================================================================

    @staticmethod
    def _build_new_udiff_url(
        trading_date: date
    ) -> str:

        date_string = (
            trading_date.strftime(
                "%Y%m%d"
            )
        )

        return (

            "https://nsearchives.nseindia.com/"
            "content/cm/"
            "BhavCopy_NSE_CM_0_0_0_"
            f"{date_string}"
            "_F_0000.csv.zip"

        )

    # ==================================================================
    # HISTORICAL MTO URL
    # ==================================================================

    @staticmethod
    def _build_historical_mto_url(
        trading_date: date
    ) -> str:

        file_name = (
            "MTO_"
            + trading_date.strftime(
                "%d%m%Y"
            )
            + ".DAT"
        )

        return (

            "https://nsearchives.nseindia.com/"
            "archives/equities/mto/"
            + file_name

        )

    # ==================================================================
    # EXTRACT ZIP CSV
    # ==================================================================

    def _extract_zip_csv(
        self,
        content: bytes
    ) -> bytes:

        if not content:

            raise ValueError(
                "Empty ZIP response."
            )

        with zipfile.ZipFile(

            io.BytesIO(
                content
            )

        ) as archive:

            members = [

                name

                for name
                in archive.namelist()

                if not name.endswith("/")

            ]

            if not members:

                raise ValueError(
                    "ZIP archive contains no files."
                )

            csv_members = [

                name

                for name
                in members

                if name.lower().endswith(
                    ".csv"
                )

            ]

            member = (

                csv_members[0]

                if csv_members

                else members[0]

            )

            print(
                f"Extracting : "
                f"{member}"
            )

            return archive.read(
                member
            )

    # ==================================================================
    # OLD HISTORICAL BHAVCOPY
    # ==================================================================

    def _download_historical_old_format(
        self,
        trading_date: date,
        output_file_name: str
    ) -> ReportMetadata | None:

        url = (
            self._build_old_historical_url(
                trading_date
            )
        )

        print(
            f"{trading_date} : "
            "old historical source"
        )

        for attempt in range(

            1,

            self.MAX_RETRIES + 1

        ):

            try:

                response = self.session.get(

                    url,

                    timeout=60

                )

                if response.status_code == 404:

                    print(

                        f"{trading_date} : "
                        "old archive not available"

                    )

                    return None

                response.raise_for_status()

                csv_content = (
                    self._extract_zip_csv(
                        response.content
                    )
                )

                if not self._validate_csv_content(

                    csv_content,

                    self.OLD_REQUIRED_COLUMNS,

                    "Historical Old"

                ):

                    raise ValueError(

                        "Historical old-format "
                        "file failed validation."

                    )

                return self._save_raw_content(

                    content=csv_content,

                    file_name=output_file_name,

                    output_dir=self.raw_data_dir,

                    trading_date=(
                        trading_date.isoformat()
                    ),

                    display_name=(
                        "Historical CM Bhavcopy"
                    ),

                    file_size=str(
                        len(csv_content)
                    )

                )

            except Exception as error:

                print(

                    f"{trading_date} : "
                    f"old format attempt "
                    f"{attempt} failed - "
                    f"{error}"

                )

                if attempt < self.MAX_RETRIES:

                    time.sleep(
                        self.RETRY_DELAY_SECONDS
                    )

        return None

    # ==================================================================
    # NEW UDIFF HISTORICAL BHAVCOPY
    # ==================================================================

    def _download_historical_new_format(
        self,
        trading_date: date,
        output_file_name: str
    ) -> ReportMetadata | None:

        url = (
            self._build_new_udiff_url(
                trading_date
            )
        )

        print(
            f"{trading_date} : "
            "UDiFF historical source"
        )

        for attempt in range(

            1,

            self.MAX_RETRIES + 1

        ):

            try:

                response = self.session.get(

                    url,

                    timeout=60

                )

                if response.status_code == 404:

                    print(

                        f"{trading_date} : "
                        "UDiFF archive not available"

                    )

                    return None

                response.raise_for_status()

                csv_content = (
                    self._extract_zip_csv(
                        response.content
                    )
                )

                first_line = (

                    csv_content
                    .splitlines()[0]
                    .decode(
                        "utf-8-sig",
                        errors="replace"
                    )

                )

                columns = (
                    self._normalise_columns(
                        first_line.split(",")
                    )
                )

                required_udiff = {

                    "TCKRSYMB",
                    "TRADDT",
                    "OPNPRIC",
                    "HGHPRIC",
                    "LWPRIC",
                    "CLSPRIC",
                    "TTLTRADGVOL",

                }

                missing = (
                    required_udiff
                    - columns
                )

                if missing:

                    raise ValueError(

                        "UDiFF file missing "
                        "expected columns: "
                        f"{sorted(missing)}"

                    )

                return self._save_raw_content(

                    content=csv_content,

                    file_name=output_file_name,

                    output_dir=self.raw_data_dir,

                    trading_date=(
                        trading_date.isoformat()
                    ),

                    display_name=(
                        "UDiFF Common Bhavcopy"
                    ),

                    file_size=str(
                        len(csv_content)
                    )

                )

            except Exception as error:

                print(

                    f"{trading_date} : "
                    f"UDiFF attempt "
                    f"{attempt} failed - "
                    f"{error}"

                )

                if attempt < self.MAX_RETRIES:

                    time.sleep(
                        self.RETRY_DELAY_SECONDS
                    )

        return None

    # ==================================================================
    # HISTORICAL BHAVCOPY
    # ==================================================================

    def download_historical_bhavcopy(
        self,
        trading_date: date
    ) -> ReportMetadata | None:
        """
        Download NSE Bhavcopy for a specific date.

        Pre-08-Jul-2024:
            Old historical CM Bhavcopy ZIP.

        08-Jul-2024 onward:
            UDiFF Common Bhavcopy ZIP.
        """

        output_file_name = (
            self._build_standard_filename(
                trading_date
            )
        )

        output_path = (
            self.raw_data_dir
            / output_file_name
        )

        if output_path.exists():

            print(

                f"{trading_date} : "
                "local file already exists"

            )

            return ReportMetadata(

                file_name=output_file_name,

                file_path=output_path,

                trading_date=(
                    trading_date.isoformat()
                ),

                display_name=(
                    "Existing NSE Bhavcopy"
                ),

                file_size=str(
                    output_path.stat().st_size
                ),

                downloaded=False

            )

        if (

            trading_date
            <= self.HISTORICAL_FORMAT_END_DATE

        ):

            return (
                self._download_historical_old_format(

                    trading_date=trading_date,

                    output_file_name=(
                        output_file_name
                    )

                )
            )

        return (
            self._download_historical_new_format(

                trading_date=trading_date,

                output_file_name=(
                    output_file_name
                )

            )
        )

    # ==================================================================
    # HISTORICAL MTO
    # ==================================================================

    def download_historical_mto(
        self,
        trading_date: date
    ) -> ReportMetadata | None:
        """
        Download historical NSE Security-wise
        Delivery Position (MTO) for a specific date.

        Filename:

            MTO_DDMMYYYY.DAT

        Example:

            MTO_04012016.DAT
            MTO_14082026.DAT
        """

        file_name = (
            self._build_mto_filename(
                trading_date
            )
        )

        output_path = (
            self.mto_data_dir
            / file_name
        )

        # --------------------------------------------------------------
        # LOCAL FILE
        # --------------------------------------------------------------

        if output_path.exists():

            print(

                f"{trading_date} : "
                "MTO already exists"

            )

            return ReportMetadata(

                file_name=file_name,

                file_path=output_path,

                trading_date=(
                    trading_date.isoformat()
                ),

                display_name=(
                    "Existing NSE MTO"
                ),

                file_size=str(
                    output_path.stat().st_size
                ),

                downloaded=False

            )

        # --------------------------------------------------------------
        # URL
        # --------------------------------------------------------------

        url = (
            self._build_historical_mto_url(
                trading_date
            )
        )

        print(
            f"{trading_date} : "
            "historical MTO source"
        )

        print(
            f"URL : {url}"
        )

        # --------------------------------------------------------------
        # DOWNLOAD
        # --------------------------------------------------------------

        for attempt in range(

            1,

            self.MAX_RETRIES + 1

        ):

            try:

                response = self.session.get(

                    url,

                    timeout=60

                )

                print(
                    f"Status: "
                    f"{response.status_code}"
                )

                # ------------------------------------------------------
                # NSE HOLIDAY / NOT AVAILABLE
                # ------------------------------------------------------

                if response.status_code == 404:

                    print(

                        f"{trading_date} : "
                        "MTO not available"

                    )

                    return None

                response.raise_for_status()

                content = (
                    response.content
                )

                # ------------------------------------------------------
                # VALIDATE
                # ------------------------------------------------------

                if not self._validate_mto_content(
                    content
                ):

                    raise ValueError(

                        "Downloaded response is "
                        "not a valid NSE MTO report."

                    )

                # ------------------------------------------------------
                # SAVE
                # ------------------------------------------------------

                return self._save_raw_content(

                    content=content,

                    file_name=file_name,

                    output_dir=self.mto_data_dir,

                    trading_date=(
                        trading_date.isoformat()
                    ),

                    display_name=(
                        "Historical NSE "
                        "Security-wise "
                        "Delivery Position"
                    ),

                    file_size=str(
                        len(content)
                    )

                )

            except Exception as error:

                print(

                    f"{trading_date} : "
                    f"MTO attempt "
                    f"{attempt} failed - "
                    f"{error}"

                )

                if attempt < self.MAX_RETRIES:

                    time.sleep(
                        self.RETRY_DELAY_SECONDS
                    )

                else:

                    print(

                        f"{trading_date} : "
                        "MTO download failed"

                    )

        return None