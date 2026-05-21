# -*- coding: utf-8 -*-
"""
Created on Thu May 14 21:47:48 2026

@author: mohak
"""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText

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