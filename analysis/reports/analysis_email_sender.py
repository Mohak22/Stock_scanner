# -*- coding: utf-8 -*-
"""
Email notifications for Stock Scanner analysis reports.

Email is an optional notification channel. Missing email configuration must
not fail the analysis pipeline; report generation and persistence are separate
from notification delivery.
"""

from __future__ import annotations

import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd


# =========================================================
# EMAIL CONFIGURATION
# =========================================================

SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip()
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "").strip()

RECEIVER_EMAILS = [
    email.strip()
    for email in os.getenv("RECEIVER_EMAILS", "").split(",")
    if email.strip()
]


def _email_is_configured() -> bool:
    """Return whether all required SMTP settings are present."""
    missing = []

    if not SENDER_EMAIL:
        missing.append("SENDER_EMAIL")
    if not EMAIL_PASSWORD:
        missing.append("EMAIL_PASSWORD")
    if not RECEIVER_EMAILS:
        missing.append("RECEIVER_EMAILS")

    if missing:
        print(
            "Email notification skipped; missing configuration: "
            + ", ".join(missing)
        )
        return False

    return True


def send_analysis_report(
    report_path: Path,
    strategy_names: list[str],
) -> None:
    """Email the generated analysis workbook when SMTP is configured."""
    if not _email_is_configured():
        return

    body = (
        "Stock Scanner Analysis Report\n\n"
        f"Analysis Date: {pd.Timestamp.today().date()}\n\n"
        "Sheets Included:\n"
        "- Summary\n"
        "- Final Recommendations\n"
    )

    for strategy_name in strategy_names:
        body += f"- {strategy_name}\n"

    message = MIMEMultipart()
    message["Subject"] = "Stock Scanner Analysis Report"
    message["From"] = SENDER_EMAIL
    message["To"] = ", ".join(RECEIVER_EMAILS)
    message.attach(MIMEText(body))

    with open(report_path, "rb") as file:
        attachment = MIMEApplication(file.read(), _subtype="xlsx")

    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=report_path.name,
    )
    message.attach(attachment)

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.sendmail(
            SENDER_EMAIL,
            RECEIVER_EMAILS,
            message.as_string(),
        )

    print("\nAnalysis report sent successfully.")


def send_no_analysis_report() -> None:
    """Notify recipients when no recommendations exist, if configured."""
    if not _email_is_configured():
        print(
            "No-analysis notification was not sent. "
            "The pipeline will finish without email."
        )
        return

    body = (
        "No recommendation files were found for the target analysis date.\n\n"
        "Possible reasons:\n"
        "- No stocks were recommended\n"
        "- Recommendation files were not generated\n"
        "- Recommendation files were not saved\n"
        "- The target date has no corresponding recommendation files"
    )

    message = MIMEText(body)
    message["Subject"] = "Stock Scanner Analysis Report"
    message["From"] = SENDER_EMAIL
    message["To"] = ", ".join(RECEIVER_EMAILS)

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.sendmail(
            SENDER_EMAIL,
            RECEIVER_EMAILS,
            message.as_string(),
        )

    print("\nNo-analysis report sent successfully.")
