# -*- coding: utf-8 -*-
"""
Created on Mon Jun  8 13:47:34 2026

@author: mohak
"""

from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent)
)

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from reports.email_sender import send_analysis_report


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

PIPELINE_ROOT = (
    PROJECT_ROOT.parent
)

DATA_REPO = (
    PIPELINE_ROOT
    / "STOCK_SCANNER_DATA"
)

FINAL_RECOMMENDATIONS_FOLDER = (
    DATA_REPO / "final_recommendations"
)

STRATEGY_1_FOLDER = (
    DATA_REPO / "strategies" / "strategy_1"
)

REPORT_FOLDER = (
    DATA_REPO / "analysis" / "reports"
)

REPORT_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

print("PROJECT_ROOT =", PROJECT_ROOT)
print("PROJECT_ROOT EXISTS =", PROJECT_ROOT.exists())

print(
    "PROJECT_ROOT/STOCK_SCANNER_DATA =",
    (PROJECT_ROOT / "STOCK_SCANNER_DATA").exists()
)

print(
    "PROJECT_ROOT.parent/STOCK_SCANNER_DATA =",
    (PROJECT_ROOT.parent / "STOCK_SCANNER_DATA").exists()
)

def load_recommendations(
    folder_path: Path,
    prefix: str,
    target_date: date
) -> pd.DataFrame:

    file_name = (
        f"{prefix}_{target_date}.csv"
    )

    file_path = folder_path / file_name

    
    print(file_path)
    print(file_path.exists())
    
    return pd.read_csv(file_path)


def calculate_returns(
    recommendations_df: pd.DataFrame
) -> pd.DataFrame:

    analysis_rows = []

    today = date.today()

    for _, row in recommendations_df.iterrows():

        symbol = row["stock_symbol"]
        ticker = f"{symbol}.NS"

        entry_price = row["entry_close_price"]

        recommendation_date = pd.to_datetime(
            row["recommendation_date"]
        )

        price_df = yf.download(
            tickers=ticker,
            start=recommendation_date.date(),
            end=today + timedelta(days=1),
            progress=False,
            auto_adjust=False
        )

        if isinstance(
            price_df.columns,
            pd.MultiIndex
        ):
            price_df.columns = (
                price_df.columns
                .get_level_values(0)
            )
            
        if len(price_df) < 2:
            continue

        price_df = price_df.reset_index()

        btst_high = price_df.iloc[1]["High"]

        btst_return = (
            (btst_high - entry_price)
            / entry_price
        ) * 100

        if len(price_df) >= 4:
            day_3_close = price_df.iloc[3]["Close"]

            return_3d = (
                (day_3_close - entry_price)
                / entry_price
            ) * 100
        else:
            return_3d = None

        latest_close = price_df.iloc[-1]["Close"]

        return_till_today = (
            (latest_close - entry_price)
            / entry_price
        ) * 100

        highest_high = (
            price_df["High"].max()
        )

        highest_return = (
            (highest_high - entry_price)
            / entry_price
        ) * 100

        lowest_low = (
            price_df["Low"].min()
        )

        lowest_return = (
            (lowest_low - entry_price)
            / entry_price
        ) * 100

        analysis_row = row.to_dict()

        analysis_row.update(
            {    
                "recommendation_date": recommendation_date,
                "analysis_date": today,
                "btst_return_pct": round(
                    btst_return, 2
                ),
                "return_3d_pct": (
                    round(return_3d, 2)
                    if return_3d is not None
                    else None
                ),
                "return_till_today_pct": round(
                    return_till_today, 2
                ),
                "highest_return_pct": round(
                    highest_return, 2
                ),
                "lowest_return_pct": round(
                    lowest_return, 2
                ),
            }
        )

        analysis_rows.append(
            analysis_row
        )

    return pd.DataFrame(
        analysis_rows
    )

def create_summary(
    analysis_df: pd.DataFrame,
    strategy_name: str
) -> pd.DataFrame:

    return pd.DataFrame(
        {
            "strategy_name": [strategy_name],
            "total_picks": [len(analysis_df)],
            "avg_btst_return_pct": [
                round(
                    analysis_df[
                        "btst_return_pct"
                    ].mean(),
                    2
                )
            ],
            "avg_3d_return_pct": [
                round(
                    analysis_df[
                        "return_3d_pct"
                    ].mean(),
                    2
                )
            ],
            "avg_current_return_pct": [
                round(
                    analysis_df[
                        "return_till_today_pct"
                    ].mean(),
                    2
                )
            ],
            "avg_highest_return_pct": [
                round(
                    analysis_df[
                        "highest_return_pct"
                    ].mean(),
                    2
                )
            ],
            "avg_lowest_return_pct": [
                round(
                    analysis_df[
                        "lowest_return_pct"
                    ].mean(),
                    2
                )
            ],
            "win_rate_pct": [
                round(
                    (
                        analysis_df[
                            "return_till_today_pct"
                        ] > 0
                    ).mean()
                    * 100,
                    2
                )
            ]
        }
    )

def generate_excel_report(
    final_df: pd.DataFrame,
    strategy_1_df: pd.DataFrame
) -> Path:

    report_path = (
        REPORT_FOLDER
        / f"analysis_report_{date.today()}.xlsx"
    )

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    summary_df = pd.concat(
        [
            create_summary(
                final_df,
                "final_recommendations"
            ),
            create_summary(
                strategy_1_df,
                "strategy_1"
            )
        ],
        ignore_index=True
    )

    with pd.ExcelWriter(
        report_path,
        engine="openpyxl"
    ) as writer:

        summary_df.to_excel(
            writer,
            sheet_name="Summary",
            index=False
        )

        final_df.to_excel(
            writer,
            sheet_name="Final_Recommendations",
            index=False
        )

        strategy_1_df.to_excel(
            writer,
            sheet_name="Strategy_1",
            index=False
        )

    return report_path

from pathlib import Path
from datetime import date


def save_analysis(
    analysis_df: pd.DataFrame,
    strategy_name: str
) -> None:

    output_folder = (
        DATA_REPO
        / "analysis"
        / strategy_name
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_folder
        / f"analysis_{date.today()}.xlsx"
    )

    analysis_df.to_excel(
        output_file,
        index=False
    )

    print(
        f"Saved: {output_file}"
    )
    

    
    
def main():

    target_date = (
        date.today()
        - timedelta(days=7)
    )

    final_recommendations_df = (
        load_recommendations(
            FINAL_RECOMMENDATIONS_FOLDER,
            "final_recommendations",
            target_date
        )
    )

    strategy_1_df = (
        load_recommendations(
            STRATEGY_1_FOLDER,
            "strategy_1",
            target_date
        )
    )

    final_analysis_df = (
        calculate_returns(
            final_recommendations_df
        )
    )

    strategy_1_analysis_df = (
        calculate_returns(
            strategy_1_df
        )
    )

    save_analysis(
        final_analysis_df,
        "final_recommendations"
    )

    save_analysis(
        strategy_1_analysis_df,
        "strategy_1"
    )
    
    report_path = generate_excel_report(
        final_analysis_df,
        strategy_1_analysis_df
    )

    send_analysis_report(
        report_path
    )


if __name__ == "__main__":
    main()