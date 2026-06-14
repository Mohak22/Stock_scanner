# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 12:20:25 2026

@author: mohak
"""


from pathlib import Path

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

GITHUB_DATA_REPO = (
    PROJECT_ROOT
    / "STOCK_SCANNER_DATA"
)

LOCAL_DATA_REPO = (
    PROJECT_ROOT.parent
    / "STOCK_SCANNER_DATA"
)

if GITHUB_DATA_REPO.exists():

    DATA_REPO = (
        GITHUB_DATA_REPO
    )

elif LOCAL_DATA_REPO.exists():

    DATA_REPO = (
        LOCAL_DATA_REPO
    )

else:

    raise FileNotFoundError(
        "STOCK_SCANNER_DATA repository not found."
    )


FINAL_RECOMMENDATIONS_FOLDER = (
    DATA_REPO / "final_recommendations"
)

STRATEGIES_FOLDER = (
    DATA_REPO / "strategies"
)

REPORT_FOLDER = (
    DATA_REPO / "analysis" / "reports"
)



