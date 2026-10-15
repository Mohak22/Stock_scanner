# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 23:17:36 2026

@author: mohak
"""


"""Transparent, configurable transaction-cost estimates for NSE equity delivery."""

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TransactionCostModel:
    # Rates are decimal fractions, not percentages.
    brokerage_rate: float = 0.0
    stt_rate: float = 0.001              # 0.1% on both sides
    exchange_rate: float = 0.0000307     # NSE: 0.00307%
    sebi_rate: float = 10 / 10_000_000   # ₹10 per crore, per side
    stamp_duty_rate: float = 0.00015     # 0.015%, buy side only
    gst_rate: float = 0.18
    slippage_bps_per_side: float = 5.0   # Explicit modelling assumption


DEFAULT_COST_MODEL = TransactionCostModel()


def _side_cost_rates(
    model: TransactionCostModel,
) -> tuple[float, float]:
    """Return effective buy and sell cost rates as fractions of turnover."""

    service_charge_base = (
        model.brokerage_rate
        + model.exchange_rate
        + model.sebi_rate
    )
    gst = model.gst_rate * service_charge_base
    slippage = model.slippage_bps_per_side / 10_000

    buy_rate = (
        model.brokerage_rate
        + model.stt_rate
        + model.exchange_rate
        + model.sebi_rate
        + model.stamp_duty_rate
        + gst
        + slippage
    )

    sell_rate = (
        model.brokerage_rate
        + model.stt_rate
        + model.exchange_rate
        + model.sebi_rate
        + gst
        + slippage
    )

    return buy_rate, sell_rate


def apply_transaction_costs(
    signal_data: pd.DataFrame,
    horizons: list[int],
    model: TransactionCostModel = DEFAULT_COST_MODEL,
) -> tuple[pd.DataFrame, dict]:
    """
    Preserve gross returns and add estimated net returns.

    Net return accounts for estimated buy-side and sell-side costs.
    Only rows marked OUTCOME_ELIGIBLE are included in net summaries.
    All returns/costs expressed in output columns are percentages.
    """

    result = signal_data.copy()
    buy_rate, sell_rate = _side_cost_rates(model)
    horizon_summary = {}

    for horizon in sorted(set(int(h) for h in horizons)):
        suffix = f"T{horizon}"

        entry = pd.to_numeric(
            result.get(
                "ENTRY_PRICE",
                pd.Series(np.nan, index=result.index),
            ),
            errors="coerce",
        )
        exit_price = pd.to_numeric(
            result.get(
                f"OUTCOME_PRICE_{suffix}",
                pd.Series(np.nan, index=result.index),
            ),
            errors="coerce",
        )
        gross = pd.to_numeric(
            result.get(
                f"RETURN_{suffix}",
                pd.Series(np.nan, index=result.index),
            ),
            errors="coerce",
        )
        eligible = result.get(
            f"OUTCOME_ELIGIBLE_{suffix}",
            pd.Series(False, index=result.index),
        ).fillna(False).astype(bool)

        eligible &= (
            entry.gt(0)
            & exit_price.gt(0)
            & gross.notna()
        )

        net = pd.Series(np.nan, index=result.index, dtype=float)
        estimated_cost = pd.Series(
            np.nan, index=result.index, dtype=float
        )

        # Model effective execution prices after slippage and fees.
        net.loc[eligible] = (
            (
                exit_price.loc[eligible] * (1 - sell_rate)
                / (entry.loc[eligible] * (1 + buy_rate))
            ) - 1
        ) * 100

        estimated_cost.loc[eligible] = (
            gross.loc[eligible] - net.loc[eligible]
        )

        result[f"NET_RETURN_{suffix}"] = net
        result[f"ESTIMATED_COST_PCT_{suffix}"] = estimated_cost

        market_return = pd.to_numeric(
            result.get(
                f"MARKET_RETURN_{suffix}",
                pd.Series(np.nan, index=result.index),
            ),
            errors="coerce",
        )
        result[f"NET_EXCESS_RETURN_{suffix}"] = net - market_return

        valid_net = net.dropna()
        valid_gross = gross.loc[valid_net.index].dropna()
        valid_cost = estimated_cost.dropna()

        horizon_summary[f"T+{horizon}"] = {
            "observations": int(valid_net.size),
            "average_gross_return_pct": (
                float(valid_gross.mean())
                if not valid_gross.empty else None
            ),
            "average_net_return_pct": (
                float(valid_net.mean())
                if not valid_net.empty else None
            ),
            "median_net_return_pct": (
                float(valid_net.median())
                if not valid_net.empty else None
            ),
            "positive_net_return_pct": (
                float((valid_net > 0).mean() * 100)
                if not valid_net.empty else None
            ),
            "average_estimated_cost_pct": (
                float(valid_cost.mean())
                if not valid_cost.empty else None
            ),
        }

    return result, {
        "model": "NSE equity delivery estimate",
        "assumptions": {
            **asdict(model),
            "exchange_rate_pct": model.exchange_rate * 100,
            "sebi_rate_description": "₹10 per crore per side, modelled proportionally",
            "slippage_description": (
                "Assumed adverse execution-price movement on each side; "
                "not estimated from historical bid-ask data."
            ),
        },
        "effective_buy_cost_pct": buy_rate * 100,
        "effective_sell_cost_pct": sell_rate * 100,
        "excluded_costs": [
            "Per-scrip DP/depository charges",
            "IPFT and minimum/rounded rupee charges",
            "Broker-specific deviations from the assumed schedule",
        ],
        "by_horizon": horizon_summary,
    }
