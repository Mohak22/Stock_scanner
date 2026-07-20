# -*- coding: utf-8 -*-
"""
Created on Sun Jul 12 15:28:58 2026

@author: mohak
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class Experiment:

    experiment_id: str

    strategy: object

    config: object

    start_date: date

    end_date: date