# -*- coding: utf-8 -*-
"""
Created on Sun Jun 21 21:46:19 2026

@author: mohak
"""

import json


def load_last_band(
    state_file
) -> int | None:

    try:

        with open(
            state_file,
            "r"
        ) as file:

            state = json.load(
                file
            )

        return state.get(
            "last_band"
        )

    except FileNotFoundError:

        return None


def save_last_band(
    state_file,
    band: int
) -> None:

    state_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        state_file,
        "w"
    ) as file:

        json.dump(
            {
                "last_band": band
            },
            file,
            indent=4
        )