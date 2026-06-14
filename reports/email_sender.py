# -*- coding: utf-8 -*-
"""
Created on Thu May 14 21:47:48 2026

@author: mohak
"""
from __future__ import annotations

import os
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import (
    MIMEMultipart
)

from email.mime.application import (
    MIMEApplication
)

from openpyxl.utils import (
    get_column_letter
)

from pathlib import Path
import pandas as pd

# =========================================================
# EMAIL CONFIGURATION
# =========================================================

SENDER_EMAIL = os.getenv(
    "SENDER_EMAIL"
)
# SENDER_EMAIL = "mohak.wagle@gmail.com"


EMAIL_PASSWORD = os.getenv(
    "EMAIL_PASSWORD"
)
# EMAIL_PASSWORD = "qeuk bfni brne glib"

RECEIVER_EMAILS = [
    "mohak.wagle@gmail.com",
    "prasadwagle08@gmail.com"
]

# =========================================================
# SEND EMAIL REPORT
# =========================================================

def send_email_report(
    oversold_dataframe: pd.DataFrame
) -> None:
    """
    Send RSI scanner report to all receivers.

    Args:
        oversold_dataframe:
            Dataframe containing oversold stocks.
    """

    # =====================================================
    # BUILD EMAIL BODY
    # =====================================================

    if oversold_dataframe.empty:

        body = (
            "No oversold stocks found today."
        )

    else:

        body = (
            "Oversold Stocks Detected\n\n"
        )

        for _, row in (
            oversold_dataframe.iterrows()
        ):

            body += (
                f"Stock: {row['Stock']}\n"
                f"RSI 9: {row['RSI_9']}\n"
                f"RSI 14: {row['RSI_14']}\n"
                "--------------------------\n"
            )

    # =====================================================
    # CREATE SMTP SESSION
    # =====================================================

    with smtplib.SMTP(
        "smtp.gmail.com",
        587
    ) as server:

        # =================================================
        # SECURE CONNECTION
        # =================================================

        server.starttls()

        # =================================================
        # LOGIN
        # =================================================

        server.login(
            SENDER_EMAIL,
            EMAIL_PASSWORD
        )

        # =================================================
        # SEND MAIL TO ALL RECEIVERS
        # =================================================

        for receiver in RECEIVER_EMAILS:

            # =============================================
            # CREATE FRESH EMAIL MESSAGE
            # =============================================

            message = MIMEText(body)

            message["Subject"] = (
                "Daily RSI Scanner Report"
            )

            message["From"] = (
                SENDER_EMAIL
            )

            message["To"] = (
                receiver
            )

            # =============================================
            # SEND EMAIL
            # =============================================

            server.sendmail(
                SENDER_EMAIL,
                receiver,
                message.as_string()
            )

            print(
                f"Email sent to: {receiver}"
            )

    print(
        "\nAll email reports sent successfully."
    )
    
# =========================================================
# SEND MARKET WARNING EMAIL
# =========================================================

def send_market_warning_email(
    market_dataframe: pd.DataFrame,
    market_status: str
) -> None:

    # =====================================================
    # EMAIL BODY
    # =====================================================

    body = (
        "MARKET WARNING\n\n"
    )

    body += (
        f"Current Market Status: "
        f"{market_status}\n\n"
    )

    body += (
        "Broader market conditions "
        "appear weak.\n"
    )

    body += (
        "New buying positions are "
        "not recommended currently.\n\n"
    )

    body += (
        "Market RSI Summary:\n\n"
    )

    for _, row in (
        market_dataframe.iterrows()
    ):

        body += (
            f"{row['Market']} | "
            f"RSI9: {row['RSI_9']} | "
            f"RSI14: {row['RSI_14']}\n"
        )

    # =====================================================
    # SMTP SESSION
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

        for receiver in RECEIVER_EMAILS:

            message = MIMEText(body)

            message["Subject"] = (
                "Market Panic Warning"
            )

            message["From"] = (
                SENDER_EMAIL
            )

            message["To"] = (
                receiver
            )

            server.sendmail(
                SENDER_EMAIL,
                receiver,
                message.as_string()
            )

    print(
        "Market warning email sent."
    )
    
# =========================================================
# SEND NO WEAK SECTOR EMAIL
# =========================================================

def send_no_sector_email() -> None:

    body = (

        "No weak sectors detected "
        "today.\n\n"

        "Market conditions do not "
        "currently satisfy the "
        "sector weakness criteria."
    )

    message = MIMEText(body)

    message["Subject"] = (
        "No Weak Sectors Today"
    )

    message["From"] = (
        SENDER_EMAIL
    )

    message["To"] = (
        ", ".join(RECEIVER_EMAILS)
    )

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
        "No sector email sent."
    )
    
# =========================================================
# SEND NO STOCK EMAIL
# =========================================================

def send_no_stock_email() -> None:

    body = (

        "Weak sectors were detected, "
        "but no stocks satisfied "
        "the stock filtering criteria."
    )

    message = MIMEText(body)

    message["Subject"] = (
        "No Weak Stocks Today"
    )

    message["From"] = (
        SENDER_EMAIL
    )

    message["To"] = (
        ", ".join(RECEIVER_EMAILS)
    )

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
        "No stock email sent."
    )
    
# =========================================================
# SEND FINAL STOCK REPORT
# =========================================================

def send_stock_report_email(
    weak_stock_dataframe: pd.DataFrame
) -> None:

    # =====================================================
    # EMAIL BODY
    # =====================================================

    body = (

        "Daily stock scanner report "
        "attached.\n\n"

        "Please check the attached "
        "Excel file for shortlisted "
        "stocks."
    )

    # =====================================================
    # MULTIPART MESSAGE
    # =====================================================

    message = MIMEMultipart()

    message["Subject"] = (
        "Daily Stock Scanner Report"
    )

    message["From"] = (
        SENDER_EMAIL
    )

    message["To"] = (
        ", ".join(RECEIVER_EMAILS)
    )

    # =====================================================
    # ATTACH BODY
    # =====================================================

    message.attach(
        MIMEText(body)
    )

    # =====================================================
    # CREATE EXCEL IN MEMORY
    # =====================================================

    excel_buffer = BytesIO()

    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl"
    ) as writer:

        weak_stock_dataframe.to_excel(
            writer,
            sheet_name="Shortlisted Stocks",
            index=False
        )

        worksheet = writer.sheets[
            "Shortlisted Stocks"
        ]

        # =================================================
        # AUTO ADJUST COLUMN WIDTH
        # =================================================

        for column_cells in worksheet.columns:

            max_length = max(

                len(str(cell.value))
                if cell.value is not None
                else 0

                for cell in column_cells
            )

            column_letter = (
                get_column_letter(
                    column_cells[0].column
                )
            )

            worksheet.column_dimensions[
                column_letter
            ].width = max_length + 4

    excel_buffer.seek(0)

    # =====================================================
    # ATTACH EXCEL
    # =====================================================

    attachment = MIMEApplication(
        excel_buffer.read(),
        _subtype="xlsx"
    )

    attachment.add_header(

        "Content-Disposition",

        "attachment",

        filename="daily_scan_report.xlsx"
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
        "\nFinal report email sent."
    )
    

