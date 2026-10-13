# -*- coding: utf-8 -*-
"""
Created on Thu May 14 21:47:48 2026

@author: mohak
"""

from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path

import pandas as pd


# =========================================================
# EMAIL CONFIGURATION
# =========================================================

SENDER_EMAIL = os.getenv(
    "SENDER_EMAIL"
)

EMAIL_PASSWORD = os.getenv(
    "EMAIL_PASSWORD"
)

RECEIVER_EMAILS = [
    email.strip()
    for email in os.getenv("RECEIVER_EMAILS", "").split(",")
    if email.strip()
]


# =========================================================
# GENERIC EMAIL SENDER
# =========================================================

def send_email(

    subject: str,

    body: str,

    attachment_path: Path | None = None

) -> None:

    if not RECEIVER_EMAILS:
        raise RuntimeError(
            "RECEIVER_EMAILS environment variable is not configured."
        )

    try:

        # =====================================================
        # CREATE MESSAGE
        # =====================================================

        message = MIMEMultipart()

        message["Subject"] = subject

        message["From"] = (
            SENDER_EMAIL
        )

        message["To"] = (
            ", ".join(
                RECEIVER_EMAILS
            )
        )


        # =====================================================
        # ATTACH BODY
        # =====================================================

        message.attach(
            MIMEText(body)
        )


        # =====================================================
        # ATTACH FILE
        # =====================================================

        if attachment_path is not None:

            with open(
                attachment_path,
                "rb"
            ) as file:

                attachment = MIMEApplication(
                    file.read(),
                    _subtype="xlsx"
                )

            attachment.add_header(

                "Content-Disposition",

                "attachment",

                filename=attachment_path.name

            )

            message.attach(
                attachment
            )


        # =====================================================
        # SEND EMAIL
        # =====================================================

        with smtplib.SMTP(
            "smtp.gmail.com",
            587
        ) as server:

            server.starttls()

            server.login(
                SENDER_EMAIL,
                EMAIL_PASSWORD
            )

            server.sendmail(

                SENDER_EMAIL,

                RECEIVER_EMAILS,

                message.as_string()

            )


        print(
            "\nEmail sent successfully."
        )


    finally:

        # =====================================================
        # DELETE TEMPORARY ATTACHMENT
        # =====================================================

        if (

            attachment_path is not None

            and

            attachment_path.exists()

        ):

            attachment_path.unlink()

            print(
                "Temporary workbook deleted."
            )


# =========================================================
# RESOLVE STOCK SYMBOL COLUMN
# =========================================================

def _get_stock_symbol(
    row: pd.Series
) -> str:

    """
    Resolve the stock symbol from strategy output.

    Different strategy/report layers may use different
    naming conventions. Keep the email layer tolerant
    of those differences.
    """

    possible_columns = [

        "stock_symbol",

        "STOCK_SYMBOL",

        "symbol",

        "SYMBOL",

        "stock",

        "STOCK"

    ]


    for column in possible_columns:

        if column in row.index:

            value = row[column]

            if pd.notna(value):

                return str(value)


    return "UNKNOWN"


# =========================================================
# RESOLVE SECTOR
# =========================================================

def _get_sector(
    row: pd.Series
) -> str:

    """
    Resolve sector if available.

    Sector is optional because not every strategy output
    necessarily contains sector information.
    """

    possible_columns = [

        "sector",

        "SECTOR",

        "sector_name",

        "SECTOR_NAME"

    ]


    for column in possible_columns:

        if column in row.index:

            value = row[column]

            if pd.notna(value):

                return str(value)


    return "N/A"


# =========================================================
# SEND FINAL STOCK REPORT
# =========================================================

def send_stock_report_email(

    recommendations: pd.DataFrame,

    workbook_path: Path

) -> None:

    # =====================================================
    # EMAIL BODY
    # =====================================================

    body = (

        "Final stock recommendations "
        "have been generated for today.\n\n"

        "The attached workbook contains:\n\n"

        "• Sheet 1 : FINAL_RECOMMENDATIONS\n"

        "• Remaining sheets : Individual "
        "strategy outputs generated today.\n\n"

        "The strategy sheets are attached "
        "for research and hypothesis testing."

    )


    # =====================================================
    # APPEND RECOMMENDATIONS
    # =====================================================

    if not recommendations.empty:

        body += (
            "\n\nToday's Final Recommendations:\n\n"
        )


        for _, row in recommendations.iterrows():

            stock_symbol = _get_stock_symbol(
                row
            )

            sector = _get_sector(
                row
            )


            body += (

                f"{stock_symbol}"

                f" | "

                f"{sector}"

                f"\n"

            )


    # =====================================================
    # SEND EMAIL
    # =====================================================

    send_email(

        subject=(

            "Daily Stock Scanner | "

            "Final Recommendations Available"

        ),

        body=body,

        attachment_path=workbook_path

    )


    print(
        "\nFinal recommendation email sent."
    )


# =========================================================
# SEND STRATEGY OUTPUT EMAIL
# =========================================================

def send_strategy_output_email(

    workbook_path: Path

) -> None:

    # =====================================================
    # EMAIL BODY
    # =====================================================

    body = (

        "No FINAL RECOMMENDATIONS were "
        "generated today.\n\n"

        "However, one or more strategies "
        "generated candidate stocks.\n\n"

        "The attached workbook contains:\n\n"

        "• Sheet 1 : FINAL_RECOMMENDATIONS "
        "(No recommendations today)\n"

        "• Remaining sheets : Individual "
        "strategy outputs generated today.\n\n"

        "These strategy outputs are shared "
        "only for research and hypothesis "
        "testing purposes.\n\n"

        "They should not be interpreted "
        "as final investment recommendations."

    )


    # =====================================================
    # SEND EMAIL
    # =====================================================

    send_email(

        subject=(

            "Daily Stock Scanner | "

            "No Final Recommendation | "

            "Strategy Outputs Attached"

        ),

        body=body,

        attachment_path=workbook_path

    )


    print(
        "\nStrategy output email sent."
    )


# =========================================================
# SEND NO RECOMMENDATION EMAIL
# =========================================================

def send_no_stock_email() -> None:

    # =====================================================
    # EMAIL BODY
    # =====================================================

    body = (

        "No recommendations were generated "
        "today.\n\n"

        "None of the available strategies "
        "produced any qualifying stocks "
        "based on their respective "
        "selection criteria.\n\n"

        "Therefore:\n"

        "• No FINAL RECOMMENDATIONS were generated.\n"

        "• No strategy output workbook has been attached."

    )


    # =====================================================
    # SEND EMAIL
    # =====================================================

    send_email(

        subject=(

            "Daily Stock Scanner | "

            "No Recommendations Today"

        ),

        body=body

    )


    print(
        "\nNo recommendation email sent."
    )
