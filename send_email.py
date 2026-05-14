# -*- coding: utf-8 -*-
"""
Created on Thu May 14 21:47:48 2026

@author: mohak
"""
import smtplib
from email.mime.text import MIMEText
import os

# Sender
sender_email = os.getenv("SENDER_EMAIL")

# Multiple receivers
receiver_emails = [
    "mohak.wagle@gmail.com",
    "prasadwagle08@gmail.com"
]

# Gmail app password
app_password = os.getenv("EMAIL_PASSWORD")

# Email content
subject = "Test Mail"
body = "SMTP email system is working successfully."

msg = MIMEText(body)

msg["Subject"] = subject
msg["From"] = sender_email
msg["To"] = ", ".join(receiver_emails)

try:

    # Connect to Gmail SMTP server
    server = smtplib.SMTP("smtp.gmail.com", 587)

    server.starttls()

    # Login
    server.login(sender_email, app_password)

    # Send email
    server.sendmail(
        sender_email,
        receiver_emails,
        msg.as_string()
    )

    print("Email sent successfully!")

    server.quit()

except Exception as e:

    print("Error:", e)