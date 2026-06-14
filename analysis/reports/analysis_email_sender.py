# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 15:17:58 2026

@author: mohak
"""

from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import (
    MIMEMultipart
)

from email.mime.application import MIMEApplication

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


def send_analysis_report(
    report_path: Path,
    strategy_names: list[str]
) -> None:

    body = (
        "Stock Scanner Analysis Report\n\n"
        f"Analysis Date: "
        f"{pd.Timestamp.today().date()}\n\n"
        "Sheets Included:\n"
        "- Summary\n"
        "- Final Recommendations\n"
    )

    for strategy_name in strategy_names:

        body += (
            f"- {strategy_name}\n"
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

        message = MIMEMultipart()

        message["Subject"] = (
            "Stock Scanner Analysis Report"
        )

        message["From"] = (
            SENDER_EMAIL
        )

        message["To"] = (
            ", ".join(RECEIVER_EMAILS)
        )

        message.attach(
            MIMEText(body)
        )

        with open(
            report_path,
            "rb"
        ) as file:

            attachment = (
                MIMEApplication(
                    file.read(),
                    _subtype="xlsx"
                )
            )

        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=report_path.name
        )

        message.attach(
            attachment
        )

        server.sendmail(
            SENDER_EMAIL,
            RECEIVER_EMAILS,
            message.as_string()
        )

    print(
        "\nAnalysis report sent successfully."
    )
    
    
    
def send_no_analysis_report() -> None:

    body = (
        "No recommendation files "
        "were found for analysis today.\n\n"
        "Possible reasons:\n"
        "- No stocks were recommended\n"
        "- Recommendation files "
        "were not generated\n"
        "- Recommendation files "
        "were not saved"
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

        message = MIMEText(
            body
        )

        message["Subject"] = (
            "Stock Scanner "
            "Analysis Report"
        )

        message["From"] = (
            SENDER_EMAIL
        )

        message["To"] = (
            ", ".join(
                RECEIVER_EMAILS
            )
        )

        server.sendmail(
            SENDER_EMAIL,
            RECEIVER_EMAILS,
            message.as_string()
        )

    print(
        "\nNo-analysis report "
        "sent successfully."
    )