# -*- coding: utf-8 -*-
"""
Created on Sun Sep 27 22:18:15 2026

@author: mohak
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from api.data.github_data import ResearchDataRepository
from api.execution.models import OrderRequest
from api.execution.zerodha_client import ZerodhaClient


router = APIRouter(
    prefix="/execution",
    tags=["execution"],
)

store = ResearchDataRepository()

EXECUTION_PREFIX = "research/execution/"


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def execution_mode() -> str:
    mode = os.getenv(
        "TRADING_EXECUTION_MODE",
        "paper",
    ).strip().lower()

    if mode not in {"paper", "live"}:
        raise RuntimeError(
            "TRADING_EXECUTION_MODE must be "
            "'paper' or 'live'."
        )

    return mode


def load_locked_strategy(
    strategy_slug: str,
    version: int,
) -> dict[str, Any]:
    path = (
        f"research/strategies/"
        f"{strategy_slug}/v{version}.json"
    )

    try:
        strategy = store.read_json(path)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail="Strategy could not be found.",
        ) from exc

    if strategy.get("status") != "LOCKED":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only LOCKED strategies can be used "
                "for execution."
            ),
        )

    return strategy


def strategy_fingerprint(
    strategy: dict[str, Any],
) -> str:
    existing = strategy.get(
        "strategy_fingerprint"
    )

    if existing:
        return str(existing)

    canonical = json.dumps(
        strategy,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def execution_path(
    strategy_slug: str,
    version: int,
    execution_id: str,
) -> str:
    return (
        f"{EXECUTION_PREFIX}"
        f"{strategy_slug}/"
        f"v{version}/"
        f"{execution_id}.json"
    )


def build_audit_record(
    *,
    execution_id: str,
    mode: str,
    status: str,
    request: OrderRequest,
    strategy: dict[str, Any],
    order_payload: dict[str, Any],
    zerodha_response: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "execution_id": execution_id,
        "created_at": now(),
        "mode": mode,
        "status": status,
        "signal_id": request.signal_id,
        "strategy": {
            "strategy_slug": strategy.get(
                "strategy_slug"
            ),
            "version": strategy.get("version"),
            "strategy_fingerprint": (
                strategy_fingerprint(strategy)
            ),
            "source_experiment_id": strategy.get(
                "source_experiment_id"
            ),
            "source_experiment_sha": strategy.get(
                "source_experiment_sha"
            ),
            "strategy_sha": strategy.get(
                "strategy_sha"
            ),
        },
        "order": order_payload,
        "notes": request.notes,
        "zerodha_response": zerodha_response,
        "error": error,
    }


def save_execution_audit(
    strategy_slug: str,
    version: int,
    execution_id: str,
    record: dict[str, Any],
) -> None:
    path = execution_path(
        strategy_slug,
        version,
        execution_id,
    )

    store.write_json(
        path,
        record,
    )


@router.get("/status")
def execution_status() -> dict[str, Any]:
    return {
        "execution_mode": execution_mode(),
        "zerodha_api_key_configured": bool(
            os.getenv("ZERODHA_API_KEY", "").strip()
        ),
        "zerodha_access_token_configured": bool(
            os.getenv(
                "ZERODHA_ACCESS_TOKEN",
                "",
            ).strip()
        ),
    }


@router.get("/login-url")
def login_url() -> dict[str, str]:
    client = ZerodhaClient()

    try:
        url = client.login_url()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return {
        "login_url": url,
    }


@router.get("/profile")
def profile() -> dict[str, Any]:
    client = ZerodhaClient()

    try:
        return client.profile()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@router.get("/ltp")
def ltp(
    instruments: str = Query(
        ...,
        description=(
            "Comma-separated instruments, "
            "for example NSE:INFY,NSE:TCS"
        ),
    ),
) -> dict[str, Any]:
    parsed = [
        item.strip()
        for item in instruments.split(",")
        if item.strip()
    ]

    if not parsed:
        raise HTTPException(
            status_code=400,
            detail="At least one instrument is required.",
        )

    client = ZerodhaClient()

    try:
        return client.ltp(parsed)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@router.get("/orders")
def orders() -> dict[str, Any]:
    client = ZerodhaClient()

    try:
        return client.orders()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@router.get("/positions")
def positions() -> dict[str, Any]:
    client = ZerodhaClient()

    try:
        return client.positions()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@router.get("/holdings")
def holdings() -> dict[str, Any]:
    client = ZerodhaClient()

    try:
        return client.holdings()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@router.post(
    "/strategies/{strategy_slug}/v{version}/order"
)
def place_strategy_order(
    strategy_slug: str,
    version: int,
    request: OrderRequest,
) -> dict[str, Any]:
    strategy = load_locked_strategy(
        strategy_slug,
        version,
    )

    mode = execution_mode()

    if mode == "live" and not request.confirm_live:
        raise HTTPException(
            status_code=409,
            detail=(
                "Live execution requires "
                "confirm_live=true."
            ),
        )

    execution_id = uuid.uuid4().hex

    order_payload: dict[str, Any] = {
        "exchange": request.exchange,
        "tradingsymbol": request.tradingsymbol,
        "transaction_type": request.transaction_type,
        "quantity": request.quantity,
        "order_type": request.order_type,
        "product": request.product,
        "validity": request.validity,
        "market_protection": (
            request.market_protection
        ),
        "tag": f"SS{version:03d}"[:20],
    }

    if request.price is not None:
        order_payload["price"] = request.price

    if mode == "paper":
        paper_order_id = (
            f"PAPER-{execution_id[:12].upper()}"
        )

        record = build_audit_record(
            execution_id=execution_id,
            mode="paper",
            status="PAPER_CREATED",
            request=request,
            strategy=strategy,
            order_payload=order_payload,
            zerodha_response={
                "paper_order_id": paper_order_id,
            },
        )

        try:
            save_execution_audit(
                strategy_slug,
                version,
                execution_id,
                record,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Paper execution was created, "
                    "but the audit record could not "
                    "be saved: "
                    f"{exc}"
                ),
            ) from exc

        return {
            "execution_id": execution_id,
            "mode": "paper",
            "status": "PAPER_CREATED",
            "paper_order_id": paper_order_id,
            "strategy_fingerprint": (
                strategy_fingerprint(strategy)
            ),
            "order": order_payload,
        }

    client = ZerodhaClient()

    try:
        zerodha_response = client.place_order(
            order_payload
        )
    except RuntimeError as exc:
        record = build_audit_record(
            execution_id=execution_id,
            mode="live",
            status="REJECTED",
            request=request,
            strategy=strategy,
            order_payload=order_payload,
            error=str(exc),
        )

        try:
            save_execution_audit(
                strategy_slug,
                version,
                execution_id,
                record,
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    order_id = (
        zerodha_response
        .get("data", {})
        .get("order_id")
    )

    record = build_audit_record(
        execution_id=execution_id,
        mode="live",
        status="SUBMITTED",
        request=request,
        strategy=strategy,
        order_payload=order_payload,
        zerodha_response=zerodha_response,
    )

    try:
        save_execution_audit(
            strategy_slug,
            version,
            execution_id,
            record,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "The Zerodha order was processed, "
                "but the execution audit could not "
                f"be saved: {exc}"
            ),
        ) from exc

    return {
        "execution_id": execution_id,
        "mode": "live",
        "status": "SUBMITTED",
        "zerodha_order_id": order_id,
        "strategy_fingerprint": (
            strategy_fingerprint(strategy)
        ),
        "order": order_payload,
    }