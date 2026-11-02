# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 23:36:53 2026

@author: mohak
"""

import pandas as pd

from research.engine.feature_engine import calculate_features


def test_raw_ohlc_features_are_supported():
    data = pd.DataFrame({
        "SYMBOL": ["ABC", "ABC"],
        "TIMESTAMP": pd.to_datetime([
            "2025-01-01",
            "2025-01-02",
        ]),
        "OPEN": [100, 105],
        "HIGH": [110, 115],
        "LOW": [95, 102],
        "CLOSE": [108, 112],
    })

    features = [
        {"type": "open"},
        {"type": "high"},
        {"type": "low"},
        {"type": "close"},
    ]

    result = calculate_features(data, features)

    assert result["OPEN"].tolist() == [100, 105]
    assert result["HIGH"].tolist() == [110, 115]
    assert result["LOW"].tolist() == [95, 102]
    assert result["CLOSE"].tolist() == [108, 112]