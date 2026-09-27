# -*- coding: utf-8 -*-
"""
Created on Sun Sep 27 22:16:32 2026

@author: mohak
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class OrderRequest(BaseModel):
    signal_id: str = Field(
        min_length=1,
        max_length=100,
    )

    exchange: Literal["NSE", "BSE"] = "NSE"

    tradingsymbol: str = Field(
        min_length=1,
        max_length=50,
    )

    transaction_type: Literal["BUY", "SELL"]

    quantity: int = Field(
        gt=0,
        le=1_000_000,
    )

    order_type: Literal["MARKET", "LIMIT"] = "MARKET"

    product: Literal["CNC", "MIS"] = "CNC"

    price: float | None = Field(
        default=None,
        gt=0,
    )

    validity: Literal["DAY", "IOC"] = "DAY"

    market_protection: int = Field(
        default=-1,
        ge=-1,
        le=100,
    )

    confirm_live: bool = False

    notes: str | None = Field(
        default=None,
        max_length=500,
    )

    @field_validator("tradingsymbol")
    @classmethod
    def normalize_tradingsymbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("price")
    @classmethod
    def validate_price(
        cls,
        value: float | None,
        info,
    ) -> float | None:
        if (
            info.data.get("order_type") == "LIMIT"
            and value is None
        ):
            raise ValueError(
                "price is required for LIMIT orders."
            )

        return value