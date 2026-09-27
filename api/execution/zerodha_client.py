# -*- coding: utf-8 -*-
"""
Created on Sun Sep 27 22:17:16 2026

@author: mohak
"""

import os
from typing import Any

import requests


KITE_API_BASE = "https://api.kite.trade"
KITE_LOGIN_BASE = "https://kite.zerodha.com/connect/login"


class ZerodhaClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("ZERODHA_API_KEY", "").strip()
        self.access_token = os.getenv(
            "ZERODHA_ACCESS_TOKEN",
            "",
        ).strip()

        self.timeout = int(
            os.getenv(
                "ZERODHA_TIMEOUT_SECONDS",
                "20",
            )
        )

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError(
                "ZERODHA_API_KEY is not configured."
            )

        if not self.access_token:
            raise RuntimeError(
                "ZERODHA_ACCESS_TOKEN is not configured."
            )

        return {
            "X-Kite-Version": "3",
            "Authorization": (
                f"token {self.api_key}:{self.access_token}"
            ),
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Any = None,
        data: Any = None,
    ) -> dict[str, Any]:
        url = f"{KITE_API_BASE}{path}"

        response = requests.request(
            method=method,
            url=url,
            headers=self._headers(),
            params=params,
            data=data,
            timeout=self.timeout,
        )

        try:
            payload = response.json()
        except ValueError:
            payload = {
                "status": "error",
                "message": response.text,
            }

        if not response.ok:
            message = payload.get(
                "message",
                "Zerodha API request failed.",
            )

            raise RuntimeError(
                f"Zerodha API error "
                f"({response.status_code}): {message}"
            )

        return payload

    def login_url(self) -> str:
        if not self.api_key:
            raise RuntimeError(
                "ZERODHA_API_KEY is not configured."
            )

        return (
            f"{KITE_LOGIN_BASE}"
            f"?v=3&api_key={self.api_key}"
        )

    def profile(self) -> dict[str, Any]:
        return self._request(
            "GET",
            "/user/profile",
        )

    def ltp(
        self,
        instruments: list[str],
    ) -> dict[str, Any]:
        if not instruments:
            raise ValueError(
                "At least one instrument is required."
            )

        if len(instruments) > 1000:
            raise ValueError(
                "Zerodha LTP supports at most "
                "1000 instruments per request."
            )

        params = [
            ("i", instrument)
            for instrument in instruments
        ]

        return self._request(
            "GET",
            "/quote/ltp",
            params=params,
        )

    def quote(
        self,
        instruments: list[str],
    ) -> dict[str, Any]:
        if not instruments:
            raise ValueError(
                "At least one instrument is required."
            )

        if len(instruments) > 500:
            raise ValueError(
                "Zerodha quote supports at most "
                "500 instruments per request."
            )

        params = [
            ("i", instrument)
            for instrument in instruments
        ]

        return self._request(
            "GET",
            "/quote",
            params=params,
        )

    def orders(self) -> dict[str, Any]:
        return self._request(
            "GET",
            "/orders",
        )

    def order_history(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/orders/{order_id}",
        )

    def trades(self) -> dict[str, Any]:
        return self._request(
            "GET",
            "/trades",
        )

    def positions(self) -> dict[str, Any]:
        return self._request(
            "GET",
            "/portfolio/positions",
        )

    def holdings(self) -> dict[str, Any]:
        return self._request(
            "GET",
            "/portfolio/holdings",
        )

    def place_order(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/orders/regular",
            data=payload,
        )