# -*- coding: utf-8 -*-
"""
Created on Sun Sep 27 22:19:01 2026

@author: mohak
"""

import hashlib
import os
import sys

import requests
from dotenv import load_dotenv


load_dotenv()


KITE_SESSION_URL = (
    "https://api.kite.trade/session/token"
)


def main() -> None:
    api_key = os.getenv(
        "ZERODHA_API_KEY",
        "",
    ).strip()

    api_secret = os.getenv(
        "ZERODHA_API_SECRET",
        "",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "ZERODHA_API_KEY is not configured."
        )

    if not api_secret:
        raise RuntimeError(
            "ZERODHA_API_SECRET is not configured."
        )

    if len(sys.argv) > 1:
        request_token = sys.argv[1].strip()
    else:
        request_token = input(
            "Enter Zerodha request_token: "
        ).strip()

    if not request_token:
        raise RuntimeError(
            "request_token is required."
        )

    checksum = hashlib.sha256(
        (
            f"{api_key}"
            f"{request_token}"
            f"{api_secret}"
        ).encode("utf-8")
    ).hexdigest()

    response = requests.post(
        KITE_SESSION_URL,
        data={
            "api_key": api_key,
            "request_token": request_token,
            "checksum": checksum,
        },
        timeout=20,
    )

    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(
            f"Unexpected Zerodha response: "
            f"{response.text}"
        )

    if not response.ok:
        message = payload.get(
            "message",
            "Zerodha session request failed.",
        )

        raise RuntimeError(
            f"Zerodha session error "
            f"({response.status_code}): {message}"
        )

    data = payload.get("data", {})

    access_token = data.get("access_token")

    if not access_token:
        raise RuntimeError(
            "Zerodha did not return an access token."
        )

    print()
    print("Zerodha session created successfully.")
    print()
    print(
        "ZERODHA_ACCESS_TOKEN="
        f"{access_token}"
    )
    print(
        "USER_ID="
        f"{data.get('user_id', '')}"
    )
    print(
        "LOGIN_TIME="
        f"{data.get('login_time', '')}"
    )
    print()


if __name__ == "__main__":
    main()