# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 16:09:41 2026

@author: mohak
"""

from pathlib import Path


def get_strategy_folders(
    strategies_folder: Path
) -> list[Path]:

    return [
        folder
        for folder in strategies_folder.iterdir()
        if folder.is_dir()
    ]