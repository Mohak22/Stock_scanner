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
#SENDER_EMAIL = "mohak.wagle@gmail.com"
SENDER_EMAIL = os.getenv(
   "SENDER_EMAIL"
)
#EMAIL_PASSWORD = "qeuk bfni brne glib"
EMAIL_PASSWORD = os.getenv(
    "EMAIL_PASSWORD"
)

RECEIVER_EMAILS = [
    "mohak.wagle@gmail.com",
    "prasadwagle08@gmail.com"
]

# =========================================================
# SEND EMAIL
# =========================================================

def send_email_report(
    oversold_dataframe: pd.DataFrame
) -> None:

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
                f"{row['Stock']} | "
                f"RSI9: {row['RSI_9']} | "
                f"RSI14: {row['RSI_14']}\n"
            )

    message = MIMEText(body)

    message["Subject"] = (
        "Daily RSI Scanner Report"
    )

    message["From"] = SENDER_EMAIL

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

            message["To"] = receiver

            server.sendmail(
                SENDER_EMAIL,
                receiver,
                message.as_string()
            )

    print(
        "Email report sent successfully."
    )