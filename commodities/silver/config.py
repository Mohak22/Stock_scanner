# -*- coding: utf-8 -*-
"""
Created on Sat Jun 20 22:41:04 2026

@author: mohak
"""

from pathlib import Path
import os

DATA_REPO_PATH = Path(
    "STOCK_SCANNER_DATA"
)

COMMODITY_FOLDER = (
    DATA_REPO_PATH
    / "commodity"
)

SILVER_FOLDER = (
    COMMODITY_FOLDER
    / "silver"
)

PDF_URL = (
    "https://cem-cms-data.s3.ap-south-1.amazonaws.com/"
    "today_price_list.pdf"
)

PRICE_HISTORY_FILE = (
    SILVER_FOLDER
    / "price_history.csv"
)

TRACK_PRICE_TYPE = (
    "incl_tax"
)

BAND_SIZE = 10000

STATE_FILE = (
    SILVER_FOLDER
    / "state.json"
)

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