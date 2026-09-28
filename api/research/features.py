# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 13:17:33 2026

@author: mohak
"""

# -*- coding: utf-8 -*-

"""
Research Feature Registry

The registry must contain only features supported by
research.engine.feature_engine.calculate_features().
"""

FEATURE_REGISTRY = [

    {
        "id": "volume",
        "name": "Volume",
        "category": "volume",
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

    {
        "id": "average_volume",
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

    {
        "id": "average_delivery_percentage",
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


def get_feature_registry() -> list:
    return FEATURE_REGISTRY