"""
FastAPI entry point for the Research Cockpit.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from api.data.github_data import ResearchDataRepository

from api.schemas import (
    DateRangeResponse,
    HealthResponse,
)

from api.research.features import get_feature_registry
from api.research.universe import get_research_universe
from api.research.dataset import get_dataset_info
from api.research.models import ResearchRequest

from research.engine.feature_engine import calculate_features

from research.engine.market_data_loader import load_market_index

from research.engine.market_return_engine import (
    calculate_market_forward_returns,
)

from research.engine.research_engine import (
    run_research,
    build_research_diagnostics,
    analyze_by_market_regime,
)

from research.engine.regime_engine import (
    calculate_market_regime,
)

from config.paths import RESEARCH_MARKET_CONTEXT_INDICES_FOLDER


# ======================================================================
# APPLICATION
# ======================================================================

app = FastAPI(
    title="Stock Scanner Research Cockpit API",
    version="0.1.0",
    description=(
        "Read-only research API backed by the "
        "STOCK_SCANNER_DATA GitHub repository."
    ),
)

repository = ResearchDataRepository()


# ======================================================================
# SYSTEM
# ======================================================================

@app.get(
    "/",
    tags=["system"],
)
def root() -> dict[str, str]:
    return {
        "name": "Stock Scanner Research Cockpit API",
        "version": "0.1.0",
        "mode": "research-only",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
)
def health() -> HealthResponse:

    status = repository.health()

    return HealthResponse(
        status=(
            "ok"
            if status["reachable"]
            else "error"
        ),
        data_repository=status["repository"],
        branch=status["branch"],
        data_repository_reachable=status["reachable"],
        error=status["error"],
    )


# ======================================================================
# DATA
# ======================================================================

@app.get(
    "/data/dates",
    response_model=DateRangeResponse,
    tags=["data"],
)
def available_dates() -> DateRangeResponse:

    try:

        dates = [
            date.fromisoformat(value)
            for value in repository.list_bhavcopy_dates()
        ]

    except RuntimeError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return DateRangeResponse(
        available_dates=dates,
    )


@app.get(
    "/data/bhavcopy",
    tags=["data"],
)
def bhavcopy(
    start_date: date = Query(...),
    end_date: date = Query(...),
    limit: int = Query(
        default=1000,
        ge=1,
        le=10000,
    ),
) -> dict:

    try:

        dataframe = repository.load_bhavcopy(
            start_date.isoformat(),
            end_date.isoformat(),
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

    if dataframe.empty:

        return {
            "start_date": start_date,
            "end_date": end_date,
            "rows": [],
            "total_rows": 0,
        }

    dataframe = (
        dataframe
        .head(limit)
        .copy()
    )

    dataframe = dataframe.where(
        dataframe.notna(),
        None,
    )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "rows": dataframe.to_dict(
            orient="records"
        ),
        "total_rows": len(dataframe),
    }


# ======================================================================
# RESEARCH FEATURES
# ======================================================================

@app.get(
    "/research/features",
    tags=["research"],
)
def research_features() -> dict:

    return {
        "features": get_feature_registry(),
    }


# ======================================================================
# RESEARCH UNIVERSE
# ======================================================================

@app.get(
    "/research/universe",
    tags=["research"],
)
def research_universe() -> dict:

    return get_research_universe()


# ======================================================================
# RESEARCH DATASET INFORMATION
# ======================================================================

@app.get(
    "/research/dataset-info",
    tags=["research"],
)
def research_dataset_info(
    start_date: date,
    end_date: date,
) -> dict:

    if start_date > end_date:

        raise HTTPException(
            status_code=400,
            detail=(
                "start_date must be on or before "
                "end_date"
            ),
        )

    return get_dataset_info(
        start_date=start_date,
        end_date=end_date,
    )


# ======================================================================
# RESEARCH RUN
# ======================================================================

@app.post(
    "/research/run",
)
def run_research_api(
    request: ResearchRequest,
):

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
        feature_periods,
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
    )

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
    # 9. APPLY UNIVERSE
    # ----------------------------------------------------------

    if request.universe.type == "symbols":

        symbols = {
            symbol.upper().strip()
            for symbol in request.universe.symbols
        }

        if not symbols:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Universe type 'symbols' "
                    "requires at least one symbol."
                ),
            )

        data = data[
            data["SYMBOL"].isin(symbols)
        ].copy()

    elif request.universe.type != "all_stocks":

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported universe type. "
                "Use 'all_stocks' or 'symbols'."
            ),
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
    # 12. LOAD MARKET BENCHMARK
    #
    # NIFTY 50 is the default market benchmark.
    #
    # The market dataset uses the SAME extended
    # date range as the stock research.
    # ----------------------------------------------------------

    market_file = (
        RESEARCH_MARKET_CONTEXT_INDICES_FOLDER
        / "nifty_50.parquet"
    )

    try:

        market_data = load_market_index(
            file_path=market_file,
            start_date=data_start,
            end_date=data_end,
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
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
                "Market benchmark contains "
                "no data for the requested range."
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
    )

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

    # ----------------------------------------------------------
    # 13. CALCULATE MARKET FORWARD RETURNS
    # ----------------------------------------------------------

    try:

        market_returns = (
            calculate_market_forward_returns(
                market_dataframe=market_data,
                horizons=horizons,
            )
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "Market return calculation "
                f"failed: {exc}"
            ),
        ) from exc

    # Normalize market return timestamp.
    if "TIMESTAMP" not in market_returns.columns:

        if "Date" in market_returns.columns:

            market_returns = market_returns.rename(
                columns={
                    "Date": "TIMESTAMP",
                }
            )

        else:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Market forward-return data "
                    "does not contain TIMESTAMP."
                ),
            )

    market_returns["TIMESTAMP"] = pd.to_datetime(
        market_returns["TIMESTAMP"],
        errors="coerce",
    )

    market_returns = (
        market_returns
        .dropna(subset=["TIMESTAMP"])
        .sort_values("TIMESTAMP")
        .drop_duplicates(
            subset=["TIMESTAMP"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    # ----------------------------------------------------------
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
    # 15. RUN STOCK RESEARCH ON FULL DATASET
    #
    # Forward stock returns MUST be calculated across
    # the complete extended dataset before splitting.
    # ----------------------------------------------------------

    try:

        full_result = run_research(
            dataframe=data,
            features=features,
            conditions=conditions,
            horizons=horizons,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "Research execution failed: "
                f"{exc}"
            ),
        ) from exc

    full_signals = (
        full_result["signals"]
        .copy()
    )

    # ----------------------------------------------------------
    # 16. ENRICH SIGNALS
    #
    # Add:
    #   - market forward returns
    #   - excess returns
    #   - causal market trailing return
    #   - causal market regime
    # ----------------------------------------------------------

    if not full_signals.empty:

        full_signals["TIMESTAMP"] = pd.to_datetime(
            full_signals["TIMESTAMP"],
            errors="coerce",
        )

        full_signals = (
            full_signals
            .dropna(subset=["TIMESTAMP"])
            .sort_values(
                [
                    "SYMBOL",
                    "TIMESTAMP",
                ]
            )
            .reset_index(drop=True)
        )

        # ------------------------------------------------------
        # MARKET FORWARD RETURNS
        # ------------------------------------------------------

        full_signals = (
            full_signals.merge(
                market_returns,
                on="TIMESTAMP",
                how="left",
            )
        )

        # ------------------------------------------------------
        # EXCESS RETURNS
        # ------------------------------------------------------

        for horizon in horizons:

            horizon = int(horizon)

            stock_column = (
                f"RETURN_T{horizon}"
            )

            market_column = (
                f"MARKET_RETURN_T{horizon}"
            )

            excess_column = (
                f"EXCESS_RETURN_T{horizon}"
            )

            if (
                stock_column in full_signals.columns
                and market_column in full_signals.columns
            ):

                full_signals[excess_column] = (
                    full_signals[stock_column]
                    - full_signals[market_column]
                )

        # ------------------------------------------------------
        # CAUSAL MARKET REGIME
        # ------------------------------------------------------

        regime_merge_data = (
            market_regime_data[
                [
                    "TIMESTAMP",
                    "MARKET_TRAILING_RETURN",
                    "MARKET_REGIME",
                ]
            ]
            .copy()
        )

        full_signals = (
            full_signals.merge(
                regime_merge_data,
                on="TIMESTAMP",
                how="left",
            )
        )

    # ----------------------------------------------------------
    # 17. BUILD SPLIT RESULTS
    # ----------------------------------------------------------

    def build_split_result(
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
        # Select signals in split
        # ------------------------------------------------------

        if full_signals.empty:

            signal_data = (
                full_signals.copy()
            )

        else:

            signal_data = (
                full_signals[
                    (
                        full_signals["TIMESTAMP"]
                        >= split_start
                    )
                    & (
                        full_signals["TIMESTAMP"]
                        < split_end_exclusive
                    )
                ].copy()
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
                testing_start,
                testing_end,
            )
        )

    # ----------------------------------------------------------
    # 21. CLEAN JSON RESULT
    # ----------------------------------------------------------

    def clean_result(
        result,
    ):

        if result is None:
            return None

        signals = (
            result["signals"]
            .head(100)
            .copy()
        )

        if not signals.empty:

            signals["TIMESTAMP"] = (
                pd.to_datetime(
                    signals["TIMESTAMP"],
                    errors="coerce",
                )
                .dt.strftime("%Y-%m-%d")
            )

            signals = signals.where(
                signals.notna(),
                None,
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