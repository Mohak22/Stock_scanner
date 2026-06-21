# -*- coding: utf-8 -*-
"""
Created on Sat Jun 20 22:57:53 2026

@author: mohak
"""

import requests


def download_pdf(
    pdf_url: str
) -> bytes:
    """
    Download MMTC PDF and return
    the PDF content as bytes.
    """

    response = requests.get(
        pdf_url,
        timeout=30
    )

    response.raise_for_status()

    return response.content