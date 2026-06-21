# -*- coding: utf-8 -*-
"""
Created on Sat Jun 20 22:58:32 2026

@author: mohak
"""

from config import PDF_URL, PRICE_HISTORY_FILE, BAND_SIZE, STATE_FILE, SENDER_EMAIL, EMAIL_PASSWORD, RECEIVER_EMAILS

from fetchers.pdf_downloader import download_pdf

from extractors.silver_price_extractor import extract_pdf_text, extract_silver_price

from storage.price_history_manager import save_price

from storage.state_manager import load_last_band, save_last_band

from alerts.band_checker import get_band, band_changed

from alerts.email_checker import send_email


def main():

    pdf_content = download_pdf(
        pdf_url=PDF_URL
    )

    pdf_text = extract_pdf_text(
        pdf_content=pdf_content
    )

    silver_price = extract_silver_price(
        pdf_text=pdf_text
    )

    save_price(
        file_path=PRICE_HISTORY_FILE,
        price=silver_price
    )

    current_band = get_band(
        price=silver_price,
        band_size=BAND_SIZE
    )

    previous_band = load_last_band(
        STATE_FILE
    )

    if band_changed(
        current_band=current_band,
        previous_band=previous_band
    ):

        direction = (
            "UP ↑"
            if current_band > previous_band
            else "DOWN ↓"
        )

        subject = (
            "Silver Price Alert"
        )

        body = (
            f"MMTC Silver 1000g Casted Bar\n\n"
            f"Current Price: ₹{silver_price:,}\n"
            f"Direction: {direction}"
        )

        send_email(
            subject=subject,
            body=body,
            sender_email=SENDER_EMAIL,
            email_password=EMAIL_PASSWORD,
            receiver_emails=RECEIVER_EMAILS
        )

        print(
            "Alert email sent."
        )

    save_last_band(
        state_file=STATE_FILE,
        band=current_band
    )

    print(
        f"Silver Price: ₹{silver_price:,}"
    )

    print(
        "Price saved successfully."
    )


if __name__ == "__main__":

    main()