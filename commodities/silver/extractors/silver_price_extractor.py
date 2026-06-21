# -*- coding: utf-8 -*-
"""
Created on Sat Jun 20 23:00:55 2026

@author: mohak
"""

import io
import re
import pdfplumber


def extract_pdf_text(
    pdf_content: bytes
) -> str:
    """
    Extract all text from PDF.
    """

    pdf_bytes = io.BytesIO(
        pdf_content
    )

    full_text = ""

    with pdfplumber.open(
        pdf_bytes
    ) as pdf:

        for page in pdf.pages:

            page_text = (
                page.extract_text()
                or ""
            )

            full_text += (
                page_text
                + "\n"
            )

    return full_text



def extract_silver_price(
    pdf_text: str
) -> int:
    """
    Extract 1000g Casted Bar
    inclusive tax price.
    """

    pattern = (
        r"Casted\s+Bar.*?1000.*?"
        r"(\d[\d,]*)\s+"
        r"(\d[\d,]*)"
    )

    match = re.search(
        pattern,
        pdf_text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if not match:

        raise ValueError(
            "1000g Casted Bar not found."
        )

    inclusive_price = (
        match.group(2)
        .replace(",", "")
    )

    return int(
        inclusive_price
    )