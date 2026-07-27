# -*- coding: utf-8 -*-
"""
Created on Sun Jul 26 23:08:50 2026

@author: mohak
"""

import pandas as pd


class MetricsCalculator:

    def calculate(
        self,
        analysis: pd.DataFrame
    ) -> dict:

        if analysis is None or analysis.empty:

            return {
                "recommendation_count": 0
            }

        metrics = {
            "recommendation_count": len(
                analysis
            )
        }

        # ==========================================
        # BTST
        # ==========================================

        metrics.update(

            self._calculate_period_metrics(

                analysis=analysis,

                return_column="btst_return_pct",

                outperformance_column=(
                    "btst_outperformance_pct"
                ),

                prefix="btst"

            )

        )

        # ==========================================
        # 7 CALENDAR DAYS
        # ==========================================

        metrics.update(

            self._calculate_period_metrics(

                analysis=analysis,

                return_column="return_7d_pct",

                outperformance_column=(
                    "outperformance_7d_pct"
                ),

                prefix="7d"

            )

        )

        # ==========================================
        # 14 CALENDAR DAYS
        # ==========================================

        metrics.update(

            self._calculate_period_metrics(

                analysis=analysis,

                return_column="return_14d_pct",

                outperformance_column=(
                    "outperformance_14d_pct"
                ),

                prefix="14d"

            )

        )

        # ==========================================
        # HIGHEST / LOWEST RETURN
        # ==========================================

        metrics.update(

            self._calculate_risk_metrics(
                analysis
            )

        )

        return metrics

    def _calculate_period_metrics(
        self,
        analysis: pd.DataFrame,
        return_column: str,
        outperformance_column: str,
        prefix: str
    ) -> dict:

        # ==========================================
        # RETURN DATA
        # ==========================================

        returns = pd.to_numeric(

            analysis[
                return_column
            ],

            errors="coerce"

        ).dropna()

        # ==========================================
        # OUTPERFORMANCE DATA
        # ==========================================

        outperformance = pd.to_numeric(

            analysis[
                outperformance_column
            ],

            errors="coerce"

        ).dropna()

        # ==========================================
        # NO VALID RETURN OBSERVATIONS
        # ==========================================

        if returns.empty:

            return {

                f"{prefix}_valid_count": 0,

                f"{prefix}_mean_return_pct": None,

                f"{prefix}_median_return_pct": None,

                f"{prefix}_positive_pct": None,

                f"{prefix}_mean_outperformance_pct": None,

                f"{prefix}_outperformance_positive_pct": None

            }

        # ==========================================
        # RETURN METRICS
        # ==========================================

        mean_return = (
            returns.mean()
        )

        median_return = (
            returns.median()
        )

        positive_pct = (

            (
                returns > 0
            ).mean()

            * 100

        )

        # ==========================================
        # OUTPERFORMANCE METRICS
        # ==========================================

        if outperformance.empty:

            mean_outperformance = None

            outperformance_positive_pct = None

        else:

            mean_outperformance = (
                outperformance.mean()
            )

            outperformance_positive_pct = (

                (
                    outperformance > 0
                ).mean()

                * 100

            )

        # ==========================================
        # RESULT
        # ==========================================

        return {

            f"{prefix}_valid_count":
                int(
                    len(returns)
                ),

            f"{prefix}_mean_return_pct":
                self._round(
                    mean_return
                ),

            f"{prefix}_median_return_pct":
                self._round(
                    median_return
                ),

            f"{prefix}_positive_pct":
                self._round(
                    positive_pct
                ),

            f"{prefix}_mean_outperformance_pct":
                self._round(
                    mean_outperformance
                ),

            f"{prefix}_outperformance_positive_pct":
                self._round(
                    outperformance_positive_pct
                )

        }

    def _calculate_risk_metrics(
        self,
        analysis: pd.DataFrame
    ) -> dict:

        highest_returns = pd.to_numeric(

            analysis[
                "highest_return_pct"
            ],

            errors="coerce"

        ).dropna()

        lowest_returns = pd.to_numeric(

            analysis[
                "lowest_return_pct"
            ],

            errors="coerce"

        ).dropna()

        return {

            "mean_highest_return_pct":
                self._round(
                    highest_returns.mean()
                    if not highest_returns.empty
                    else None
                ),

            "median_highest_return_pct":
                self._round(
                    highest_returns.median()
                    if not highest_returns.empty
                    else None
                ),

            "mean_lowest_return_pct":
                self._round(
                    lowest_returns.mean()
                    if not lowest_returns.empty
                    else None
                ),

            "median_lowest_return_pct":
                self._round(
                    lowest_returns.median()
                    if not lowest_returns.empty
                    else None
                )

        }

    def _round(
        self,
        value
    ):

        if value is None:

            return None

        if pd.isna(value):

            return None

        return round(
            float(value),
            2
        )