# -*- coding: utf-8 -*-
"""
Created on Sun Jun 21 22:00:40 2026

@author: mohak
"""

import smtplib

from email.mime.text import MIMEText


def send_email(
    subject: str,
    body: str,
    sender_email: str,
    email_password: str,
    receiver_emails: list[str]
) -> None:

    message = MIMEText(
        body
    )

    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = ", ".join(
        receiver_emails
    )

    with smtplib.SMTP(
        "smtp.gmail.com",
        587
    ) as server:

        server.starttls()

        server.login(
            sender_email,
            email_password
        )

        server.sendmail(
            sender_email,
            receiver_emails,
            message.as_string()
        )