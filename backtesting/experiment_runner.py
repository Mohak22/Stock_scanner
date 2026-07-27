# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 10:43:35 2026

@author: mohak
"""

from time import perf_counter

import pandas as pd

from datetime import timedelta

import json 

from analysis.calculators.return_calculator import (
    calculate_returns
)

from backtesting.backtest_experiment import (
    Experiment
)

from backtesting.backtest_result import (
    ExperimentResult
)

from backtesting.metrics_calculator import (
    MetricsCalculator
)

class ExperimentRunner:

    def __init__(
        self,
        historical_data_repository,
        trading_calendar,
        strategy_runner,
        recommendation_repository,
        nifty_data_repository
    ):

        self.historical_data_repository = (
            historical_data_repository
        )

        self.trading_calendar = (
            trading_calendar
        )

        self.strategy_runner = (
            strategy_runner
        )

        self.recommendation_repository = (
            recommendation_repository
        )

        self.nifty_data_repository = (
            nifty_data_repository
        )

    def run(
        self,
        experiment: Experiment
    ) -> ExperimentResult:

        start_time = perf_counter()

        # ==========================================
        # LOAD STRATEGY HISTORY
        #
        # Used only for recommendation generation.
        # Includes required history before the
        # experiment.
        # ==========================================

        history = (
            self.historical_data_repository.load(

                start_date=experiment.start_date,

                end_date=experiment.end_date,

                history_window=(
                    experiment.config.history_window
                )

            )
        )

        # ==========================================
        # GET RECOMMENDATION DATES
        #
        # Only dates inside experiment period.
        # ==========================================

        recommendation_dates = (
            self.trading_calendar.get_recommendation_dates(

                history=history,

                start_date=experiment.start_date,

                end_date=experiment.end_date

            )
        )

        # ==========================================
        # RUN STRATEGY
        # ==========================================

        recommendations = (
            self.strategy_runner.run(

                experiment=experiment,

                history=history,

                recommendation_dates=(
                    recommendation_dates
                )

            )
        )

        # ==========================================
        # SAVE RECOMMENDATIONS
        # ==========================================

        self.recommendation_repository.save(

            experiment=experiment,

            recommendations=recommendations

        )

        # ==========================================
        # HANDLE EMPTY RECOMMENDATIONS
        # ==========================================

        if recommendations.empty:

            analysis = pd.DataFrame()

            self._save_analysis(

                experiment=experiment,

                analysis=analysis

            )

            execution_time = (
                perf_counter()
                - start_time
            )

            return ExperimentResult(

                experiment=experiment,

                metrics={},

                execution_time=execution_time,

                recommendation_count=0

            )

        # ==========================================
        # DETERMINE ANALYSIS END DATE
        #
        # 14D means 14 calendar days.
        # Extra days allow for weekends / holidays
        # after the 14-day target.
        # ==========================================
        
        analysis_end_date = (
        
            experiment.end_date
            + timedelta(
                days=21
            )
        
        )

        # ==========================================
        # LOAD RAW MARKET DATA
        #
        # Raw NSE bhavcopy contains:
        # OPEN / HIGH / LOW / CLOSE
        #
        # This data is used only for evaluating
        # recommendations.
        # ==========================================

        market_data = (
            self.historical_data_repository
            .load_market_data(
        
                start_date=experiment.start_date,
        
                end_date=analysis_end_date
        
            )
        )

        # ==========================================
        # KEEP ONLY RECOMMENDED STOCKS
        #
        # Avoid keeping unnecessary stock histories
        # in the dictionary used by analysis.
        # ==========================================

        if "stock_symbol" in recommendations.columns:

            recommended_symbols = (
                recommendations[
                    "stock_symbol"
                ]
                .dropna()
                .unique()
            )

        elif "SYMBOL" in recommendations.columns:

            recommended_symbols = (
                recommendations[
                    "SYMBOL"
                ]
                .dropna()
                .unique()
            )

        else:

            raise ValueError(

                "Recommendations do not contain "
                "'stock_symbol' or 'SYMBOL'."

            )

        market_data = market_data[

            market_data["SYMBOL"].isin(
                recommended_symbols
            )

        ].copy()

        # ==========================================
        # PREPARE STOCK PRICE HISTORY
        #
        # Generic structure expected by
        # calculate_returns().
        # ==========================================

        historical_prices = {

            symbol: stock_history.copy()

            for symbol, stock_history

            in market_data.groupby(
                "SYMBOL"
            )

        }

        # ==========================================
        # LOAD NIFTY DATA ONCE
        #
        # Same analysis horizon as stock prices.
        # ==========================================

        nifty_prices = (
            self.nifty_data_repository.load(
        
                start_date=experiment.start_date,
        
                end_date=analysis_end_date
        
            )
        )

        # ==========================================
        # ANALYZE RECOMMENDATIONS
        #
        # Universal return calculator:
        #
        # BTST  -> next trading session HIGH
        # 7D    -> 7 calendar days
        # 14D   -> 14 calendar days
        #
        # Stock prices -> raw NSE bhavcopy
        # Benchmark    -> NIFTY cache
        # ==========================================
        print("\n==========================================")
        print("BACKTEST ANALYSIS DEBUG")
        print("==========================================")
        
        print(
            "Recommendations:",
            len(recommendations)
        )
        
        print(
            "Market data rows:",
            len(market_data)
        )
        
        print(
            "Historical price symbols:",
            len(historical_prices)
        )
        
        print(
            "NIFTY rows:",
            len(nifty_prices)
        )
        
        print("\nRecommendation columns:")
        print(
            recommendations.columns.tolist()
        )
        
        print("\nMarket data columns:")
        print(
            market_data.columns.tolist()
        )
        
        print("\nFirst recommendation:")
        print(
            recommendations.head(1).T
        )
        
        print("\nMarket date range:")
        
        if not market_data.empty:
        
            print(
                market_data["TIMESTAMP"].min(),
                "->",
                market_data["TIMESTAMP"].max()
            )
        
        print("\nNIFTY date range:")
        
        if not nifty_prices.empty:
        
            print(
                nifty_prices["Date"].min(),
                "->",
                nifty_prices["Date"].max()
            )
        
        print("\n==========================================")
        analysis = calculate_returns(

            recommendations_df=(
                recommendations
            ),

            historical_prices=(
                historical_prices
            ),

            nifty_prices=(
                nifty_prices
            )

        )

        # ==========================================
        # SAVE ANALYSIS
        # ==========================================

        self._save_analysis(

            experiment=experiment,

            analysis=analysis

        )

        # ==========================================
        # CALCULATE EXPERIMENT METRICS
        # ==========================================
        
        metrics_calculator = (
            MetricsCalculator()
        )
        
        metrics = (
            metrics_calculator.calculate(
                analysis
            )
        )
        
        # ==========================================
        # SAVE EXPERIMENT METRICS
        # ==========================================
        
        self._save_metrics(
        
            experiment=experiment,
        
            metrics=metrics
        
        )

        # ==========================================
        # RESULT
        # ==========================================

        execution_time = (

            perf_counter()
            - start_time

        )

        return ExperimentResult(

            experiment=experiment,

            metrics=metrics,

            execution_time=execution_time,

            recommendation_count=len(
                recommendations
            )

        )

    def _save_analysis(
        self,
        experiment: Experiment,
        analysis: pd.DataFrame
    ) -> None:

        experiment_directory = (

            self.recommendation_repository
            .strategy_directory

            / experiment.experiment_id

        )

        experiment_directory.mkdir(

            parents=True,

            exist_ok=True

        )

        analysis_file = (

            experiment_directory
            / "analysis.csv"

        )

        analysis.to_csv(

            analysis_file,

            index=False

        )
        
    def _save_metrics(
        self,
        experiment: Experiment,
        metrics: dict
    ) -> None:
    
        experiment_directory = (
    
            self.recommendation_repository
            .strategy_directory
    
            / experiment.experiment_id
    
        )
    
        experiment_directory.mkdir(
    
            parents=True,
    
            exist_ok=True
    
        )
    
        metrics_file = (
    
            experiment_directory
            / "metrics.json"
    
        )
    
        with open(
    
            metrics_file,
    
            "w",
    
            encoding="utf-8"
    
        ) as file:
    
            json.dump(
    
                metrics,
    
                file,
    
                indent=4
    
            )