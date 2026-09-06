# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 13:17:33 2026

@author: mohak
"""

"""
Research Feature Registry

Purpose:
    Define the features that the Strategy Inventor can use.

Important:
    This is a FEATURE REGISTRY, not the actual feature calculation engine.

    It tells the frontend:
        - what features exist
        - what category they belong to
        - what parameters they accept
        - what type of value they produce

    Actual calculation of features will be handled later.
"""


# ======================================================================
# FEATURE REGISTRY
# ======================================================================

FEATURE_REGISTRY = [

    # ------------------------------------------------------------------
    # PRICE
    # ------------------------------------------------------------------

    {
        "id": "open",
        "name": "Open",
        "category": "price",
        "type": "numeric",
        "parameters": []
    },

    {
        "id": "high",
        "name": "High",
        "category": "price",
        "type": "numeric",
        "parameters": []
    },

    {
        "id": "low",
        "name": "Low",
        "category": "price",
        "type": "numeric",
        "parameters": []
    },

    {
        "id": "close",
        "name": "Close",
        "category": "price",
        "type": "numeric",
        "parameters": []
    },


    # ------------------------------------------------------------------
    # VOLUME
    # ------------------------------------------------------------------

    {
        "id": "volume",
        "name": "Volume",
        "category": "volume",
        "type": "numeric",
        "parameters": []
    },


    # ------------------------------------------------------------------
    # DELIVERY
    # ------------------------------------------------------------------

    {
        "id": "delivery_quantity",
        "name": "Delivery Quantity",
        "category": "delivery",
        "type": "numeric",
        "parameters": []
    },

    {
        "id": "delivery_percentage",
        "name": "Delivery %",
        "category": "delivery",
        "type": "numeric",
        "parameters": []
    },


    # ------------------------------------------------------------------
    # RSI
    # ------------------------------------------------------------------

    {
        "id": "rsi",
        "name": "RSI",
        "category": "technical",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 14,
                "minimum": 1,
                "maximum": 200
            }
        ]
    },


    # ------------------------------------------------------------------
    # EMA
    # ------------------------------------------------------------------

    {
        "id": "ema",
        "name": "EMA",
        "category": "technical",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "maximum": 500
            }
        ]
    },


    # ------------------------------------------------------------------
    # SMA
    # ------------------------------------------------------------------

    {
        "id": "sma",
        "name": "SMA",
        "category": "technical",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "maximum": 500
            }
        ]
    },


    # ------------------------------------------------------------------
    # RETURNS
    # ------------------------------------------------------------------

    {
        "id": "return",
        "name": "Return",
        "category": "returns",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 1,
                "minimum": 1,
                "maximum": 500
            }
        ]
    },


    # ------------------------------------------------------------------
    # VOLUME AVERAGE
    # ------------------------------------------------------------------

    {
        "id": "volume_average",
        "name": "Average Volume",
        "category": "volume",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "maximum": 500
            }
        ]
    },


    # ------------------------------------------------------------------
    # DELIVERY AVERAGE
    # ------------------------------------------------------------------

    {
        "id": "delivery_percentage_average",
        "name": "Average Delivery %",
        "category": "delivery",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "maximum": 500
            }
        ]
    }

]


# ======================================================================
# GET ALL FEATURES
# ======================================================================

def get_feature_registry() -> list:

    return FEATURE_REGISTRY