# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 11:07:09 2026

@author: mohak
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
from fastapi import HTTPException

from api.data.github_data import ResearchDataRepository
from api.research.models import ResearchRequest
from api.research.universe import load_research_universe_dataframe

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


ProgressCallback = Callable[[int, str], None]


def execute_research(
    request: ResearchRequest,
    *,
    repository: ResearchDataRepository,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """
    Execute the existing Research Cockpit research pipeline.

    This is intentionally the same pipeline that previously lived inside
    POST /research/run. The HTTP layer will later call this function from
    a background job.
    """

    def report(progress: int, stage: str) -> None:
        if progress_callback is not None:
            progress_callback(progress, stage)


    # ----------------------------------------------------------
    # 1. VALIDATE DATE RANGE
    # ----------------------------------------------------------

    if request.training_start > request.training_end:
        raise HTTPException(
            status_code=400,
            detail=(
                "Training start date must be "
                "before training end date."
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
        request.testing_start is not None
        and request.testing_end is not None
        and request.testing_start > request.testing_end
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Testing start date must be "
                "before testing end date."
            ),
        )

    # ----------------------------------------------------------
    # 2. CONVERT REQUEST DATES
    # ----------------------------------------------------------

    training_start = pd.Timestamp(
        request.training_start
    )

    training_end = pd.Timestamp(
        request.training_end
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

    testing_start = (
        pd.Timestamp(request.testing_start)
        if request.testing_start is not None
        else None
    )

    testing_end = (
        pd.Timestamp(request.testing_end)
        if request.testing_end is not None
        else None
    )

    # ----------------------------------------------------------
    # 3. CONVERT REQUEST MODELS
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

    if not horizons:

        raise HTTPException(
            status_code=400,
            detail=(
                "At least one evaluation "
                "horizon is required."
            ),
        )

    if any(horizon <= 0 for horizon in horizons):

        raise HTTPException(
            status_code=400,
            detail=(
                "Evaluation horizons must be "
                "positive integers."
            ),
        )

    # Remove duplicate horizons while preserving order.
    horizons = list(dict.fromkeys(horizons))

    # ----------------------------------------------------------
    # 4. DETERMINE REQUESTED RANGE
    # ----------------------------------------------------------

    requested_dates = [
        training_start,
        training_end,
    ]

    if validation_start is not None:
        requested_dates.append(validation_start)

    if validation_end is not None:
        requested_dates.append(validation_end)

    if testing_start is not None:
        requested_dates.append(testing_start)

    if testing_end is not None:
        requested_dates.append(testing_end)

    requested_start = min(requested_dates)
    requested_end = max(requested_dates)

    # ----------------------------------------------------------
    # 5. FEATURE LOOKBACK
    # ----------------------------------------------------------

    # Feature requirements are expressed as observations.  The data source is
    # date-addressed, so the existing calendar buffer remains a conservative
    # retrieval buffer rather than a statement of indicator semantics.
    try:
        lookback_requirements = feature_lookback_requirements(features)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    feature_periods = []

    for feature in features:

        period = feature.get("period")

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

            feature_periods.append(period)

    max_feature_period = max(
        [*feature_periods, *lookback_requirements.values()],
        default=1,
    )

    lookback_days = max(
        30,
        max_feature_period * 3,
    )

    data_start = (
        requested_start
        - pd.Timedelta(days=lookback_days)
    )

    # ----------------------------------------------------------
    # 6. FORWARD-RETURN BUFFER
    # ----------------------------------------------------------

    max_horizon = max(horizons)

    forward_buffer_days = max(
        15,
        max_horizon * 3 + 10,
    )

    data_end = (
        requested_end
        + pd.Timedelta(days=forward_buffer_days)
    )

    # ----------------------------------------------------------
    report(10, "Loading historical data")
    # 7. LOAD STOCK HISTORICAL DATA
    # ----------------------------------------------------------

    try:

        data = repository.load_bhavcopy(
            data_start.date().isoformat(),
            data_end.date().isoformat(),
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

    # ----------------------------------------------------------
    # 8. VALIDATE / NORMALIZE STOCK DATA
    # ----------------------------------------------------------

    if data.empty:

        raise HTTPException(
            status_code=400,
            detail=(
                "No historical data available "
                "for the requested range."
            ),
        )

    if "TIMESTAMP" not in data.columns:

        raise HTTPException(
            status_code=400,
            detail=(
                "Historical data does not "
                "contain TIMESTAMP."
            ),
        )

    data["TIMESTAMP"] = pd.to_datetime(
        data["TIMESTAMP"],
        errors="coerce",
    ).dt.normalize()

    data = (
        data
        .dropna(subset=["TIMESTAMP"])
        .copy()
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

    # ----------------------------------------------------------
    report(20, "Applying universe")
    # 9. APPLY UNIVERSE
    # ----------------------------------------------------------

    if request.universe.type == "all_stocks":
        try:
            research_universe = load_research_universe_dataframe()
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

        research_universe_symbols = set(
            research_universe["SYMBOL"]
        )

        data = data[
            data["SYMBOL"].isin(research_universe_symbols)
        ].copy()

    elif request.universe.type in {
        "macro_sector",
        "sector",
        "industry",
        "basic_industry",
    }:
        try:
            research_universe = load_research_universe_dataframe()
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
            "macro_sector": "MACRO_ECONOMIC_SECTOR",
            "sector": "SECTOR",
            "industry": "INDUSTRY",
            "basic_industry": "BASIC_INDUSTRY",
        }

        column = column_map[request.universe.type]
        selected_value = (request.universe.value or "").strip()

        if not selected_value:
            raise HTTPException(
                status_code=400,
                detail=f"A value is required for {request.universe.type}.",
            )

        selected_symbols = set(
            research_universe.loc[
                research_universe[column].astype(str).str.strip()
                == selected_value,
                "SYMBOL",
            ]
        )

        data = data[
            data["SYMBOL"].isin(selected_symbols)
        ].copy()

    elif request.universe.type == "symbols":
        symbols = {
            symbol.upper().strip()
            for symbol in request.universe.symbols
            if symbol.strip()
        }

        if not symbols:
            raise HTTPException(
                status_code=400,
                detail="At least one symbol is required.",
            )

        data = data[
            data["SYMBOL"].isin(symbols)
        ].copy()

    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported universe type.",
        )

    if data.empty:

        raise HTTPException(
            status_code=400,
            detail=(
                "No historical data available "
                "for the selected universe."
            ),
        )

    # ----------------------------------------------------------
    # 10. SORT STOCK DATA
    # ----------------------------------------------------------

    data = (
        data
        .sort_values(
            [
                "SYMBOL",
                "TIMESTAMP",
            ]
        )
        .reset_index(drop=True)
    )

    # ----------------------------------------------------------
    report(35, "Calculating features")
    # 11. CALCULATE FEATURES
    # ----------------------------------------------------------

    try:

        data = calculate_features(
            dataframe=data,
            features=features,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "Feature calculation failed: "
                f"{exc}"
            ),
        ) from exc

    # ----------------------------------------------------------
    report(45, "Loading market benchmark")
    # 12. LOAD MARKET BENCHMARK FROM GITHUB
    #
    # GitHub STOCK_SCANNER_DATA/main is the
    # single source of truth for research data.
    # ----------------------------------------------------------

    market_data_path = (
        "research/market_context/indices/"
        "nifty_50.parquet"
    )

    try:

        market_dataframe = (
            repository.load_parquet(
                market_data_path
            )
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

    # ----------------------------------------------------------
    # 12A. NORMALIZE MARKET DATA
    #
    # The market loader may return Date while the
    # regime engine expects TIMESTAMP.
    # ----------------------------------------------------------

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

    market_data["TIMESTAMP"] = pd.to_datetime(
        market_data["TIMESTAMP"],
        errors="coerce",
    ).dt.normalize()

    market_data = (
        market_data
        .dropna(subset=["TIMESTAMP"])
        .sort_values("TIMESTAMP")
        .drop_duplicates(
            subset=["TIMESTAMP"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    report(60, "Calculating market regime")
    # 14. CALCULATE CAUSAL MARKET REGIME
    #
    # IMPORTANT:
    #
    # The regime uses only market prices available
    # on or before each signal date.
    #
    # It does NOT use forward returns.
    # ----------------------------------------------------------

    try:

        market_regime_data = calculate_market_regime(
            market_dataframe=market_data,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "Market regime calculation "
                f"failed: {exc}"
            ),
        ) from exc

    # ----------------------------------------------------------
    report(70, "Generating causal signals")
    # Conditions are evaluated once, after causal feature calculation and
    # before any entry/outcome evaluation.
    # ----------------------------------------------------------
    try:
        signal_mask = generate_signal_mask(data, conditions)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Signal generation failed: {exc}",
        ) from exc

    regime_merge_data = market_regime_data[
        ["TIMESTAMP", "MARKET_TRAILING_RETURN", "MARKET_REGIME"]
    ].copy()

    # ----------------------------------------------------------
    report(85, "Building split analysis")
    # 17. BUILD SPLIT RESULTS
    # ----------------------------------------------------------

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
            + pd.Timedelta(days=1)
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
        # Evaluate entries and outcomes against this stage.  The evaluator
        # retains a signal but marks each horizon independently ineligible
        # when its entry/outcome would cross the boundary.
        # ------------------------------------------------------
        stage = TemporalStage.create(split_name, split_start, split_end)
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
        # Build diagnostics + A3 analysis
        #
        # IMPORTANT:
        #
        # We pass features here so A3 feature analysis
        # is calculated for the actual split.
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
        # A3.3 MARKET REGIME ANALYSIS
        #
        # Regime is attached before splitting and therefore
        # remains causal.
        # ------------------------------------------------------

        analysis = (
            split_result.get(
                "analysis",
                {},
            )
            or {}
        )

        if signal_data.empty:

            analysis["by_market_regime"] = {}

        else:

            try:

                analysis["by_market_regime"] = (
                    analyze_by_market_regime(
                        signal_data=signal_data,
                        horizons=horizons,
                    )
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
            "summary": split_result["summary"],
            "performance": split_result["performance"],
            "diagnostics": split_result["diagnostics"],
            "analysis": analysis,
            "warnings": split_result["warnings"],
            "signals": signal_data,
        }

    # ----------------------------------------------------------
    # 18. TRAINING
    # ----------------------------------------------------------

    training_result = (
        build_split_result(
            "training",
            training_start,
            training_end,
        )
    )

    # ----------------------------------------------------------
    # 19. VALIDATION
    # ----------------------------------------------------------

    validation_result = None

    if (
        validation_start is not None
        and validation_end is not None
    ):

        validation_result = (
            build_split_result(
                "validation",
                validation_start,
                validation_end,
            )
        )

    # ----------------------------------------------------------
    # 20. TESTING
    # ----------------------------------------------------------

    testing_result = None

    if (
        testing_start is not None
        and testing_end is not None
    ):

        testing_result = (
            build_split_result(
                "testing",
                testing_start,
                testing_end,
            )
        )

    # ----------------------------------------------------------
    report(95, "Finalizing results")
    # 21. CLEAN JSON RESULT
    # ----------------------------------------------------------

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
                if column.endswith("_DATE") or "_DATE_T" in column or column == "TIMESTAMP":
                    signals[column] = pd.to_datetime(
                        signals[column], errors="coerce"
                    ).dt.strftime("%Y-%m-%d")

            signals = (
                signals
                .astype(object)
                .where(
                    signals.notna(),
                    None,
                )
            )

        return {
            "summary": result["summary"],
            "performance": result["performance"],
            "diagnostics": result["diagnostics"],
            "analysis": result.get(
                "analysis",
                {},
            ),
            "warnings": result["warnings"],
            "signals": signals.to_dict(
                orient="records"
            ),
        }

    # ----------------------------------------------------------
    report(100, "Complete")
    # 22. FINAL RESPONSE
    # ----------------------------------------------------------

    return {
        "research_config": {
            "training_start": request.training_start,
            "training_end": request.training_end,
            "validation_start": request.validation_start,
            "validation_end": request.validation_end,
            "testing_start": request.testing_start,
            "testing_end": request.testing_end,
            "universe": request.universe.model_dump(),
            "features": features,
            "entry_conditions": conditions,
            "evaluation_horizons": horizons,
            "temporal_convention": TEMPORAL_CONVENTION,
            "feature_lookback_requirements": lookback_requirements,
            "reproducibility_hooks": {
                "data_revision": None,
                "universe_revision": None,
                "engine_version": None,
            },
            "universe_membership_note": (
                "research_universe.csv is a current-universe snapshot; "
                "it is not point-in-time historical membership."
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
                    "20-trading-day trailing NIFTY 50 return "
                    "at the signal date"
                ),
            },
        },

        "training": clean_result(
            training_result
        ),

        "validation": clean_result(
            validation_result
        ),

        "testing": clean_result(
            testing_result
        ),
    }
