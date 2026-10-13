from __future__ import annotations

# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 11:07:09 2026

@author: mohak
"""

from typing import Any, Callable
import threading
import time

import pandas as pd
from fastapi import HTTPException
from datetime import datetime, timezone

from api.data.github_data import ResearchDataRepository
from api.research.models import ResearchRequest
from api.research.universe import (
    apply_research_universe,
    load_research_universe_dataframe,
    validate_bhavcopy_session_coverage,
)

from research.engine.feature_engine import calculate_features
from research.engine.market_data_loader import load_market_index
from research.engine.research_engine import (
    build_research_diagnostics,
    analyze_by_market_regime,
)
from research.engine.regime_engine import calculate_market_regime
from research.engine.temporal_evaluation import (
    TEMPORAL_CONVENTION,
    TemporalStage,
    evaluate_temporal_stage,
    feature_lookback_requirements,
    generate_signal_mask,
)


RESEARCH_ENGINE_VERSION = "1.0.0"

ProgressCallback = Callable[[int, str], None]


# ============================================================
# GRANULAR PROGRESS SYSTEM
# ============================================================

class ProgressTracker:
    """
    Duration-aware progress tracker.

    Each expensive research operation receives its own progress range.

    Example:

        Loading historical data
        5% -------------------------- 34%
                         actual work
        completed -> 35%

    The displayed title remains unchanged while the progress
    slowly advances inside the allocated range.

    The progress is intentionally capped before the actual
    operation finishes. This prevents the UI from showing
    100% while the backend is still working.
    """

    def __init__(
        self,
        callback: ProgressCallback | None = None,
    ) -> None:
        self.callback = callback
        self._lock = threading.Lock()
        self._last_progress = 0

    def report(
        self,
        progress: float,
        stage: str,
    ) -> None:
        """
        Report progress while guaranteeing that progress never
        moves backwards.
        """

        if self.callback is None:
            return

        progress = max(0.0, min(100.0, progress))

        with self._lock:
            progress = max(
                progress,
                float(self._last_progress),
            )

            integer_progress = int(round(progress))

            if integer_progress < self._last_progress:
                return

            self._last_progress = integer_progress

        self.callback(
            integer_progress,
            stage,
        )

    def run(
        self,
        *,
        start: int,
        end: int,
        stage: str,
        function,
        expected_duration: float,
        minimum_tick: float = 0.25,
        easing: str = "ease_out",
    ):
        """
        Execute a blocking function while gradually advancing
        progress through the allocated range.

        `expected_duration` is only used for visual progress.
        The actual function controls when the stage completes.

        The progress never reaches `end` until the real function
        has returned.
        """

        start = int(start)
        end = int(end)

        if end <= start:
            return function()

        # The maximum progress while the real function is still
        # running. Keep a small safety margin so we never show
        # the stage as completed prematurely.
        visual_end = max(
            start,
            end - 1,
        )

        result_holder: dict[str, Any] = {}
        error_holder: dict[str, BaseException] = {}
        finished = threading.Event()

        def worker() -> None:
            try:
                result_holder["result"] = function()
            except BaseException as exc:
                error_holder["error"] = exc
            finally:
                finished.set()

        worker_thread = threading.Thread(
            target=worker,
            daemon=True,
        )

        worker_thread.start()

        # ----------------------------------------------------
        # INITIAL STAGE PROGRESS
        # ----------------------------------------------------

        self.report(
            start,
            stage,
        )

        # ----------------------------------------------------
        # DURATION-AWARE VISUAL PROGRESS
        # ----------------------------------------------------

        expected_duration = max(
            float(expected_duration),
            1.0,
        )

        start_time = time.monotonic()

        while not finished.is_set():

            elapsed = time.monotonic() - start_time

            ratio = elapsed / expected_duration

            # Never visually finish the stage before the real
            # operation finishes.
            ratio = min(
                ratio,
                0.97,
            )

            if easing == "ease_out":
                # Fast initial movement, then increasingly slower.
                # This resembles real progress better than a
                # perfectly linear fake timer.
                eased_ratio = 1.0 - ((1.0 - ratio) ** 2)
            elif easing == "ease_in_out":
                if ratio < 0.5:
                    eased_ratio = 2.0 * ratio * ratio
                else:
                    eased_ratio = (
                        1.0
                        - ((-2.0 * ratio + 2.0) ** 2) / 2.0
                    )
            else:
                eased_ratio = ratio

            current_progress = (
                start
                + ((visual_end - start) * eased_ratio)
            )

            self.report(
                current_progress,
                stage,
            )

            # The progress ticker itself should not hammer the
            # SSE endpoint.
            finished.wait(
                timeout=max(
                    minimum_tick,
                    0.25,
                )
            )

        worker_thread.join()

        # ----------------------------------------------------
        # REAL OPERATION FAILED
        # ----------------------------------------------------

        if "error" in error_holder:
            raise error_holder["error"]

        # ----------------------------------------------------
        # REAL OPERATION FINISHED
        # ----------------------------------------------------

        self.report(
            end,
            stage,
        )

        return result_holder.get("result")


# ============================================================
# MAIN RESEARCH EXECUTOR
# ============================================================

def execute_research(
    request: ResearchRequest,
    *,
    repository: ResearchDataRepository,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """
    Execute the existing Research Cockpit research pipeline.

    Progress is intentionally granular and duration-aware.

    The actual research computation remains synchronous from the
    caller's perspective. Long-running operations are wrapped in
    ProgressTracker so the frontend receives realistic intermediate
    progress while the operation is executing.
    """

    tracker = ProgressTracker(
        callback=progress_callback,
    )

    # ----------------------------------------------------------
    # 0. START
    # ----------------------------------------------------------

    tracker.report(
        1,
        "Starting research",
    )

    # ----------------------------------------------------------
    # 1. REPRODUCIBILITY METADATA
    # ----------------------------------------------------------

    data_revision = repository.get_revision()

    tracker.report(
        2,
        "Starting research",
    )

    universe_revision = (
        None
        if request.universe.membership_basis == "point_in_time"
        else repository.get_file_revision(
            "research_universe.csv",
            ref=data_revision,
        )
    )

    tracker.report(
        3,
        "Starting research",
    )

    run_timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    # ----------------------------------------------------------
    # PROGRESS HELPER
    # ----------------------------------------------------------

    def report(
        progress: int,
        stage: str,
    ) -> None:
        tracker.report(
            progress,
            stage,
        )

    # ----------------------------------------------------------
    # 2. VALIDATE DATE RANGE
    # ----------------------------------------------------------

    report(
        4,
        "Validating research configuration",
    )

    if request.development_start > request.development_end:
        raise HTTPException(
            status_code=400,
            detail=(
                "Development start date must be "
                "before development end date."
            ),
        )

    if (
        request.validation_start is not None
        and request.validation_end is not None
        and request.validation_start > request.validation_end
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Validation start date must be "
                "before validation end date."
            ),
        )

    if (
        request.holdout_start is not None
        and request.holdout_end is not None
        and request.holdout_start > request.holdout_end
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Final holdout start date must be "
                "before final holdout end date."
            ),
        )

    report(
        5,
        "Validating research configuration",
    )

    # ----------------------------------------------------------
    # 3. CONVERT REQUEST DATES
    # ----------------------------------------------------------

    development_start = pd.Timestamp(
        request.development_start
    )

    development_end = pd.Timestamp(
        request.development_end
    )

    validation_start = (
        pd.Timestamp(request.validation_start)
        if request.validation_start is not None
        else None
    )

    validation_end = (
        pd.Timestamp(request.validation_end)
        if request.validation_end is not None
        else None
    )

    holdout_start = (
        pd.Timestamp(request.holdout_start)
        if request.holdout_start is not None
        else None
    )

    holdout_end = (
        pd.Timestamp(request.holdout_end)
        if request.holdout_end is not None
        else None
    )

    report(
        6,
        "Preparing research configuration",
    )

    # ----------------------------------------------------------
    # 4. CONVERT REQUEST MODELS
    # ----------------------------------------------------------

    features = [
        feature.model_dump()
        for feature in request.features
    ]

    conditions = [
        condition.model_dump()
        for condition in request.entry_conditions
    ]

    horizons = [
        int(horizon)
        for horizon in request.evaluation_horizons
    ]

    membership_basis = (
        request.universe.membership_basis
    )

    if not horizons:
        raise HTTPException(
            status_code=400,
            detail=(
                "At least one evaluation "
                "horizon is required."
            ),
        )

    if any(
        horizon <= 0
        for horizon in horizons
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Evaluation horizons must be "
                "positive integers."
            ),
        )

    # Remove duplicate horizons while preserving order.
    horizons = list(
        dict.fromkeys(horizons)
    )

    report(
        7,
        "Preparing research configuration",
    )

    # ----------------------------------------------------------
    # 5. DETERMINE REQUESTED RANGE
    # ----------------------------------------------------------

    requested_dates = [
        development_start,
        development_end,
    ]

    if validation_start is not None:
        requested_dates.append(
            validation_start
        )

    if validation_end is not None:
        requested_dates.append(
            validation_end
        )

    if holdout_start is not None:
        requested_dates.append(
            holdout_start
        )

    if holdout_end is not None:
        requested_dates.append(
            holdout_end
        )

    requested_start = min(
        requested_dates
    )

    requested_end = max(
        requested_dates
    )

    report(
        8,
        "Preparing research period",
    )

    # ----------------------------------------------------------
    # 6. FEATURE LOOKBACK
    # ----------------------------------------------------------

    try:
        lookback_requirements = (
            feature_lookback_requirements(
                features
            )
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    feature_periods = []

    for feature in features:

        parameters = dict(feature.get("parameters") or {})
        if feature.get("period") is not None and "period" not in parameters:
            parameters["period"] = feature["period"]

        period = parameters.get("period")

        if period is not None:

            try:
                period = int(period)

            except (
                TypeError,
                ValueError,
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Invalid feature "
                        f"period: {period}"
                    ),
                )

            if period <= 0:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Feature period must "
                        f"be positive: {period}"
                    ),
                )

            feature_periods.append(
                period
            )

    max_feature_period = max(
        [
            *feature_periods,
            *lookback_requirements.values(),
        ],
        default=1,
    )

    lookback_days = max(
        30,
        max_feature_period * 3,
    )

    data_start = (
        requested_start
        - pd.Timedelta(
            days=lookback_days
        )
    )

    report(
        9,
        "Preparing historical data range",
    )

    # ----------------------------------------------------------
    # 7. FORWARD-RETURN BUFFER
    # ----------------------------------------------------------

    max_horizon = max(
        horizons
    )

    forward_buffer_days = max(
        15,
        max_horizon * 3 + 10,
    )

    data_end = (
        requested_end
        + pd.Timedelta(
            days=forward_buffer_days
        )
    )

    report(
        10,
        "Preparing historical data range",
    )

    # ==========================================================
    # 8. LOAD STOCK HISTORICAL DATA
    # ==========================================================

    try:

        data = tracker.run(
            start=11,
            end=35,
            stage="Loading historical data",
            expected_duration=25.0,
            minimum_tick=0.35,
            easing="ease_out",
            function=lambda: repository.load_bhavcopy(
                data_start.date().isoformat(),
                data_end.date().isoformat(),
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    # ==========================================================
    # 9. VALIDATE / NORMALIZE STOCK DATA
    # ==========================================================

    report(
        36,
        "Validating historical data",
    )

    if data.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "No historical data available "
                "for the requested range."
            ),
        )

    report(
        37,
        "Validating historical data",
    )

    if "TIMESTAMP" not in data.columns:
        raise HTTPException(
            status_code=400,
            detail=(
                "Historical data does not "
                "contain TIMESTAMP."
            ),
        )

    report(
        38,
        "Normalizing historical data",
    )

    data["TIMESTAMP"] = pd.to_datetime(
        data["TIMESTAMP"],
        errors="coerce",
    ).dt.normalize()

    data = (
        data
        .dropna(
            subset=["TIMESTAMP"]
        )
        .copy()
    )

    report(
        39,
        "Normalizing historical data",
    )

    if "SYMBOL" not in data.columns:
        raise HTTPException(
            status_code=400,
            detail=(
                "Historical data does not "
                "contain SYMBOL."
            ),
        )

    data["SYMBOL"] = (
        data["SYMBOL"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    report(
        40,
        "Historical data ready",
    )

    # Preserve dates from the full historical dataset before any
    # universe filter can remove rows.
    observed_bhavcopy_sessions = set(
        data["TIMESTAMP"]
        .dropna()
        .dt.normalize()
        .unique()
    )

    # ==========================================================
    # 10. APPLY UNIVERSE
    # ==========================================================

    report(
        41,
        "Applying universe",
    )

    if request.universe.type == "all_stocks":

        try:

            data = apply_research_universe(
                data,
                membership_basis,
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except RuntimeError as exc:

            raise HTTPException(
                status_code=502,
                detail=str(exc),
            ) from exc

    elif request.universe.type in {
        "macro_sector",
        "sector",
        "industry",
        "basic_industry",
    }:

        try:

            research_universe = (
                load_research_universe_dataframe()
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=500,
                detail=str(exc),
            ) from exc

        except RuntimeError as exc:

            raise HTTPException(
                status_code=502,
                detail=str(exc),
            ) from exc

        column_map = {
            "macro_sector":
                "MACRO_ECONOMIC_SECTOR",
            "sector":
                "SECTOR",
            "industry":
                "INDUSTRY",
            "basic_industry":
                "BASIC_INDUSTRY",
        }

        column = column_map[
            request.universe.type
        ]

        selected_value = (
            request.universe.value or ""
        ).strip()

        if not selected_value:
            raise HTTPException(
                status_code=400,
                detail=(
                    "A value is required for "
                    f"{request.universe.type}."
                ),
            )

        selected_symbols = set(
            research_universe.loc[
                research_universe[column]
                .astype(str)
                .str.strip()
                == selected_value,
                "SYMBOL",
            ]
        )

        data = data[
            data["SYMBOL"].isin(
                selected_symbols
            )
        ].copy()

    elif request.universe.type == "major_stocks":

        try:
            from api.research.universe import (
                apply_major_stocks_universe,
            )

            data = apply_major_stocks_universe(
                data
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except RuntimeError as exc:

            raise HTTPException(
                status_code=502,
                detail=str(exc),
            ) from exc
            
    elif request.universe.type == "symbols":

        symbols = {
            symbol.upper().strip()
            for symbol in request.universe.symbols
            if symbol.strip()
        }

        if not symbols:
            raise HTTPException(
                status_code=400,
                detail=(
                    "At least one symbol "
                    "is required."
                ),
            )

        data = data[
            data["SYMBOL"].isin(
                symbols
            )
        ].copy()

    else:

        raise HTTPException(
            status_code=400,
            detail="Unsupported universe type.",
        )

    report(
        44,
        "Universe applied",
    )

    if data.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "No historical data available "
                "for the selected universe."
            ),
        )

    # ==========================================================
    # 11. LOAD DELIVERY DATA WHEN REQUIRED
    # ==========================================================

    delivery_requested = any(
        feature.get("type", "").lower()
        in {
            "delivery_percentage",
            "average_delivery_percentage",
        }
        for feature in features
    )

    if delivery_requested:
        try:
            mto_data = tracker.run(
                start=45,
                end=48,
                stage="Loading delivery data",
                expected_duration=15.0,
                minimum_tick=0.35,
                easing="ease_out",
                function=lambda: repository.load_mto(
                    data_start.date().isoformat(),
                    data_end.date().isoformat(),
                ),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=502,
                detail=str(exc),
            ) from exc

        if mto_data.empty:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Delivery data was requested, but no "
                    "NSE MTO data was found for the research range."
                ),
            )

        mto_data = mto_data.copy()

        mto_data["SYMBOL"] = (
            mto_data["SYMBOL"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        mto_data["TIMESTAMP"] = (
            pd.to_datetime(
                mto_data["TIMESTAMP"],
                errors="coerce",
            )
            .dt.normalize()
        )

        selected_symbols = set(
            data["SYMBOL"].unique()
        )

        mto_data = mto_data[
            mto_data["SYMBOL"].isin(
                selected_symbols
            )
        ].copy()

        for column in [
            "MTO_QTY_TRADED",
            "DELIV_QTY",
            "DELIV_PER",
        ]:
            if column in data.columns:
                data = data.drop(
                    columns=[column]
                )

        data = data.merge(
            mto_data[
                [
                    "SYMBOL",
                    "TIMESTAMP",
                    "MTO_QTY_TRADED",
                    "DELIV_QTY",
                    "DELIV_PER",
                ]
            ],
            on=[
                "SYMBOL",
                "TIMESTAMP",
            ],
            how="left",
        )

    else:
        report(
            48,
            "Delivery data not required",
        )

    # ==========================================================
    # 12. SORT STOCK DATA
    # ==========================================================


    report(
        49,
        "Sorting research data",
    )

    data = (
        data
        .sort_values(
            [
                "SYMBOL",
                "TIMESTAMP",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    report(
        50,
        "Research data sorted",
    )

    # ==========================================================
    # 12. CALCULATE FEATURES
    # ==========================================================

    try:

        data = tracker.run(
            start=51,
            end=66,
            stage="Calculating indicators",
            expected_duration=18.0,
            minimum_tick=0.35,
            easing="ease_out",
            function=lambda: calculate_features(
                dataframe=data,
                features=features,
            ),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "Feature calculation failed: "
                f"{exc}"
            ),
        ) from exc

    # ==========================================================
    # 13. LOAD MARKET BENCHMARK
    # ==========================================================

    report(
        67,
        "Loading NIFTY benchmark",
    )

    market_data_path = (
        "research/market_context/indices/"
        "nifty_50.parquet"
    )

    try:

        market_dataframe = tracker.run(
            start=68,
            end=74,
            stage="Loading NIFTY benchmark",
            expected_duration=7.0,
            minimum_tick=0.35,
            easing="ease_out",
            function=lambda: repository.load_parquet(
                market_data_path
            ),
        )

        market_data = load_market_index(
            source=market_dataframe,
            start_date=data_start,
            end_date=data_end,
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Failed to load NIFTY 50 "
                f"from GitHub: {exc}"
            ),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "Market benchmark data error: "
                f"{exc}"
            ),
        ) from exc

    if market_data.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "NIFTY 50 benchmark contains "
                "no data for the requested range "
                "in GitHub STOCK_SCANNER_DATA."
            ),
        )

    # ==========================================================
    # 14. NORMALIZE MARKET DATA
    # ==========================================================

    report(
        75,
        "Normalizing NIFTY benchmark",
    )

    market_data = market_data.copy()

    if "TIMESTAMP" not in market_data.columns:

        if "Date" in market_data.columns:

            market_data = market_data.rename(
                columns={
                    "Date": "TIMESTAMP",
                }
            )

        else:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Market benchmark data must "
                    "contain TIMESTAMP or Date."
                ),
            )

    report(
        76,
        "Normalizing NIFTY benchmark",
    )

    market_data["TIMESTAMP"] = (
        pd.to_datetime(
            market_data["TIMESTAMP"],
            errors="coerce",
        ).dt.normalize()
    )

    market_data = (
        market_data
        .dropna(
            subset=["TIMESTAMP"]
        )
        .sort_values("TIMESTAMP")
        .drop_duplicates(
            subset=["TIMESTAMP"],
            keep="last",
        )
        .reset_index(
            drop=True
        )
    )

    report(
        77,
        "NIFTY benchmark ready",
    )

    # A missing bhavcopy session can silently bias historical research.
    # Use the benchmark's available trading sessions as a reference.
    if membership_basis == "point_in_time":
        try:
            validate_bhavcopy_session_coverage(
                observed_dates=observed_bhavcopy_sessions,
                expected_dates=market_data["TIMESTAMP"],
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Historical bhavcopy coverage validation failed: "
                    f"{exc}"
                ),
            ) from exc
        
    # ==========================================================
    # 15. CALCULATE CAUSAL MARKET REGIME
    # ==========================================================

    try:

        market_regime_data = tracker.run(
            start=78,
            end=83,
            stage="Calculating market regime",
            expected_duration=6.0,
            minimum_tick=0.35,
            easing="ease_out",
            function=lambda: calculate_market_regime(
                market_dataframe=market_data,
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "Market regime calculation "
                f"failed: {exc}"
            ),
        ) from exc

    # ==========================================================
    # 16. GENERATE CAUSAL SIGNALS
    # ==========================================================

    report(
        84,
        "Generating signals",
    )

    try:

        signal_mask = tracker.run(
            start=84,
            end=88,
            stage="Generating signals",
            expected_duration=5.0,
            minimum_tick=0.35,
            easing="ease_out",
            function=lambda: generate_signal_mask(
                data,
                conditions,
            ),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "Signal generation failed: "
                f"{exc}"
            ),
        ) from exc

    regime_merge_data = market_regime_data[
        [
            "TIMESTAMP",
            "MARKET_TRAILING_RETURN",
            "MARKET_REGIME",
        ]
    ].copy()

    # ==========================================================
    # 17. BUILD SPLIT ANALYSIS
    # ==========================================================

    report(
        89,
        "Evaluating outcomes",
    )

    def build_split_result(
        split_name: str,
        split_start: pd.Timestamp,
        split_end: pd.Timestamp,
    ) -> dict:

        # ------------------------------------------------------
        # Split date range
        # ------------------------------------------------------

        split_end_exclusive = (
            split_end
            + pd.Timedelta(
                days=1
            )
        )

        split_mask = (
            (data["TIMESTAMP"] >= split_start)
            & (
                data["TIMESTAMP"]
                < split_end_exclusive
            )
        )

        split_data = (
            data.loc[
                split_mask
            ].copy()
        )

        # ------------------------------------------------------
        # Evaluate entries and outcomes
        # ------------------------------------------------------

        stage = TemporalStage.create(
            split_name,
            split_start,
            split_end,
        )

        signal_data = evaluate_temporal_stage(
            dataframe=data,
            signal_mask=signal_mask,
            stage=stage,
            horizons=horizons,
            market_dataframe=market_data,
        )

        if not signal_data.empty:

            signal_data = signal_data.merge(
                regime_merge_data,
                on="TIMESTAMP",
                how="left",
            )

        # ------------------------------------------------------
        # Diagnostics + A3 analysis
        # ------------------------------------------------------

        split_result = (
            build_research_diagnostics(
                dataframe=split_data,
                signal_data=signal_data,
                horizons=horizons,
                features=features,
            )
        )

        # ------------------------------------------------------
        # Market regime analysis
        # ------------------------------------------------------

        analysis = (
            split_result.get(
                "analysis",
                {},
            )
            or {}
        )

        if signal_data.empty:

            analysis[
                "by_market_regime"
            ] = {}

        else:

            try:

                analysis[
                    "by_market_regime"
                ] = analyze_by_market_regime(
                    signal_data=signal_data,
                    horizons=horizons,
                )

            except ValueError as exc:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Market regime analysis "
                        f"failed: {exc}"
                    ),
                ) from exc

        return {
            "summary": split_result[
                "summary"
            ],
            "performance": split_result[
                "performance"
            ],
            "diagnostics": split_result[
                "diagnostics"
            ],
            "analysis": analysis,
            "warnings": split_result[
                "warnings"
            ],
            "signals": signal_data,
        }

    # ==========================================================
    # 18. DEVELOPMENT
    # ==========================================================

    development_result = tracker.run(
        start=89,
        end=93,
        stage="Evaluating development",
        expected_duration=5.0,
        minimum_tick=0.35,
        easing="ease_out",
        function=lambda: build_split_result(
            "development",
            development_start,
            development_end,
        ),
    )

    # ==========================================================
    # 19. VALIDATION
    # ==========================================================

    validation_result = None

    if (
        validation_start is not None
        and validation_end is not None
    ):

        validation_result = tracker.run(
            start=93,
            end=95,
            stage="Evaluating validation",
            expected_duration=3.0,
            minimum_tick=0.35,
            easing="ease_out",
            function=lambda: build_split_result(
                "validation",
                validation_start,
                validation_end,
            ),
        )

    else:

        report(
            95,
            "Validation skipped",
        )

    # ==========================================================
    # 20. FINAL HOLDOUT
    # ==========================================================

    holdout_result = None

    if (
        holdout_start is not None
        and holdout_end is not None
    ):

        holdout_result = tracker.run(
            start=95,
            end=97,
            stage="Evaluating final testing",
            expected_duration=3.0,
            minimum_tick=0.35,
            easing="ease_out",
            function=lambda: build_split_result(
                "final_holdout",
                holdout_start,
                holdout_end,
            ),
        )

    else:

        report(
            97,
            "Final testing skipped",
        )

    # ==========================================================
    # 21. CLEAN JSON RESULT
    # ==========================================================

    report(
        98,
        "Building analysis",
    )

    def clean_result(
        result,
    ):

        if result is None:
            return None

        signals = (
            result["signals"]
            .copy()
        )

        if not signals.empty:

            for column in signals.columns:

                if (
                    column.endswith("_DATE")
                    or "_DATE_T" in column
                    or column == "TIMESTAMP"
                ):

                    signals[column] = (
                        pd.to_datetime(
                            signals[column],
                            errors="coerce",
                        ).dt.strftime(
                            "%Y-%m-%d"
                        )
                    )

            signals = (
                signals
                .astype(object)
                .where(
                    signals.notna(),
                    None,
                )
            )

        return {
            "summary": result[
                "summary"
            ],
            "performance": result[
                "performance"
            ],
            "diagnostics": result[
                "diagnostics"
            ],
            "analysis": result.get(
                "analysis",
                {},
            ),
            "warnings": result[
                "warnings"
            ],
            "signals": signals.to_dict(
                orient="records"
            ),
        }

    # ==========================================================
    # 22. FINALIZE
    # ==========================================================

    report(
        99,
        "Finalizing results",
    )

    final_result = {
        "research_config": {
            "research_schema_version": "2",
            "development_start":
                request.development_start,
            "development_end":
                request.development_end,
            "validation_start":
                request.validation_start,
            "validation_end":
                request.validation_end,
            "holdout_start":
                request.holdout_start,
            "holdout_end":
                request.holdout_end,
            "signal_timing":
                request.signal_timing.model_dump(),
            "outcome_definition": (
                request.outcome_definition.model_dump()
                if request.outcome_definition
                is not None
                else {
                    "anchor": "signal_date",
                    "price_basis": "CLOSE",
                    "horizons": horizons,
                }
            ),
            "universe":
                request.universe.model_dump(),
            "universe_membership_basis":
                membership_basis,
            "features":
                features,
            "entry_conditions":
                conditions,
            "evaluation_horizons":
                horizons,
            "temporal_convention":
                TEMPORAL_CONVENTION,
            "feature_lookback_requirements":
                lookback_requirements,
            "reproducibility_hooks": {
                "data_revision":
                    data_revision,
                "universe_revision":
                    universe_revision,
                "engine_version":
                    RESEARCH_ENGINE_VERSION,
                "run_timestamp":
                    run_timestamp,
            },
            "universe_membership_note": (
                (
                    "Point-in-time all-stocks universe is derived from symbol/date "
                    "records in the archived historical NSE bhavcopy files. "
                    "Today's research_universe.csv is not used to filter these "
                    "historical rows. Validity depends on completeness of the "
                    "archived bhavcopy files and their historical symbol coverage."
                )
                if membership_basis == "point_in_time"
                else
                (
                    "research_universe.csv is a current-universe snapshot; "
                    "it is not point-in-time historical membership. Results may "
                    "be affected by survivorship bias."
                )
            ),
            "market_benchmark": {
                "name": "NIFTY 50",
                "file": "nifty_50.parquet",
            },
            "market_regime": {
                "lookback": 20,
                "bear_threshold": -5.0,
                "bull_threshold": 5.0,
                "definition": (
                    "20-trading-day trailing NIFTY "
                    "50 return at the signal date"
                ),
            },
        },

        "development":
            clean_result(
                development_result
            ),

        "validation":
            clean_result(
                validation_result
            ),

        "final_holdout":
            clean_result(
                holdout_result
            ),
    }

    report(
        100,
        "Complete",
    )

    return final_result