# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 13:44:23 2026

@author: mohak
"""

"""
Research Dataset API

Purpose:
    Provide information about the historical dataset available
    for a requested research period.

This endpoint does NOT run a strategy.

It answers questions such as:

    - Is data available for this period?
    - How many trading dates are available?
    - What is the first available date?
    - What is the last available date?

The actual strategy execution will be built later.
"""

from datetime import date

from api.data.github_data import (
    ResearchDataRepository
)


# ======================================================================
# GET DATASET INFORMATION
# ======================================================================

def get_dataset_info(
    start_date: date,
    end_date: date
) -> dict:

    # ------------------------------------------------------------------
    # VALIDATE DATE RANGE
    # ------------------------------------------------------------------

    if start_date > end_date:

        raise ValueError(
            "start_date must be on or before end_date"
        )


    # ------------------------------------------------------------------
    # CONNECT TO GITHUB DATA REPOSITORY
    # ------------------------------------------------------------------

    repository = ResearchDataRepository()


    # ------------------------------------------------------------------
    # GET AVAILABLE BHAVCOPY DATES
    # ------------------------------------------------------------------

    available_dates = (
        repository.list_bhavcopy_dates()
    )


    # ------------------------------------------------------------------
    # FILTER DATES
    # ------------------------------------------------------------------

    selected_dates = [

        current_date

        for current_date in available_dates

        if (
            str(start_date)
            <= current_date
            <= str(end_date)
        )

    ]


    # ------------------------------------------------------------------
    # SORT CHRONOLOGICALLY
    # ------------------------------------------------------------------

    selected_dates.sort()


    # ------------------------------------------------------------------
    # BUILD RESPONSE
    # ------------------------------------------------------------------

    if not selected_dates:

        return {

            "start_date": str(start_date),

            "end_date": str(end_date),

            "data_available": False,

            "trading_days": 0,

            "first_available_date": None,

            "last_available_date": None

        }


    return {

        "start_date": str(start_date),

        "end_date": str(end_date),

        "data_available": True,

        "trading_days": len(
            selected_dates
        ),

        "first_available_date": (
            selected_dates[0]
        ),

        "last_available_date": (
            selected_dates[-1]
        )

    }