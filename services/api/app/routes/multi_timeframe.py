
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user
from app.db.mongo import get_database

from analysis.multi_timeframe import (
    MultiTimeframeError,
    analyze_multi_timeframe,
)


router = APIRouter(
    prefix="/api/v1/analysis",
    tags=["Multi-Timeframe Analysis"],
)

Timeframe = Literal["M5", "M15", "M30", "H1", "H4", "D1"]

SUPPORTED_TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]


@router.get("/multi-timeframe")
async def get_multi_timeframe_analysis(
    symbol: str = Query(
        ...,
        min_length=3,
        max_length=30,
        pattern=r"^[A-Za-z0-9._-]+$",
    ),
    limit: int = Query(default=500, ge=50, le=500),
    minimum_candles: int = Query(default=50, ge=2, le=500),
    current_user: dict = Depends(get_current_user),
):
    """
    Analyse a market instrument across M5, M15, M30, H1, H4 and D1.

    Requires an authenticated user.
    Uses closed candles only.
    Does not execute trades.
    """

    symbol = symbol.strip().upper()

    try:
        database = get_database()

        candles_by_timeframe = {}

        for timeframe in SUPPORTED_TIMEFRAMES:

            cursor = (
                database.market_candles.find(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                    },
                    {
                        "_id": 0,
                    },
                )
                .sort("timestamp", -1)
                .limit(limit)
            )

            candles = await cursor.to_list(length=limit)

            # The analysis engine expects chronological candles.
            candles.reverse()

            candles_by_timeframe[timeframe] = candles

        result = analyze_multi_timeframe(
            candles_by_timeframe=candles_by_timeframe,
            symbol=symbol,
            minimum_candles=minimum_candles,
        )

        return {
            "success": True,
            "message": "Multi-timeframe analysis completed.",
            "analysis": result,
        }

    except MultiTimeframeError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        # Keep internal database and implementation details out
        # of the response sent to the client.
        raise HTTPException(
            status_code=500,
            detail="Unable to complete multi-timeframe analysis.",
        ) from exc
