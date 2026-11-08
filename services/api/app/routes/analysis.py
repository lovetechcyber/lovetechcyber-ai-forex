from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user
from app.db.mongo import get_database
from starlette.concurrency import run_in_threadpool
from analysis.unified_analysis import analyze_market
from datetime import datetime, timezone
from indicators.technical_indicators import (
    IndicatorError,
    calculate_technical_indicators,
)
from pydantic import BaseModel
from typing import Optional, Any

from services.ai_analysis import (
    AIAnalysisError,
    analyze_with_ai,
)


router = APIRouter(
    prefix="/api/v1/analysis",
    tags=["Analysis"],
)


Timeframe = Literal["M5", "M15", "M30", "H1", "H4", "D1"]


@router.get("/indicators")
async def get_technical_indicators(
    symbol: str = Query(
        ...,
        min_length=3,
        max_length=30,
        pattern=r"^[A-Za-z0-9._-]+$",
    ),
    timeframe: Timeframe = Query(...),
    limit: int = Query(default=500, ge=2, le=500),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve stored MT5 candles and calculate technical indicators.
    Requires an authenticated user.
    """

    symbol = symbol.strip().upper()

    try:
        database = get_database()

        cursor = (
            database.market_candles
            .find(
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

        # MongoDB returns newest first. The indicator engine
        # requires chronological order.
        candles = await cursor.to_list(length=limit)
        candles.reverse()

        if len(candles) < 2:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Insufficient market data for "
                    f"{symbol} {timeframe}."
                ),
            )

        result = calculate_technical_indicators(
            candles=candles,
            symbol=symbol,
            timeframe=timeframe,
            exclude_forming_candle=True,
        )

        return {
            "success": True,
            "message": "Technical analysis completed.",
            "analysis": result,
        }

    except IndicatorError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        # Log the full exception server-side in production.
        raise HTTPException(
            status_code=500,
            detail="Unable to calculate technical indicators.",
        ) from exc
        
@router.get("/unified")
async def get_unified_analysis(
    symbol: str = Query(
        ...,
        min_length=3,
        max_length=30,
        pattern=r"^[A-Za-z0-9._-]+$",
    ),
    timeframe: Timeframe = Query(...),
    limit: int = Query(default=500, ge=2, le=500),
    _current_user: dict = Depends(get_current_user),
):
    """
    Run unified market analysis using stored MT5 candles.

    Includes:
    - Technical indicators
    - Market structure
    - BOS and CHoCH
    - Liquidity sweeps and zones
    - Fair value gaps
    - Order blocks
    - Confluences and risk factors

    This endpoint provides analysis only.
    It does not execute trades.
    """

    symbol = symbol.strip().upper()

    try:
        database = get_database()

        cursor = (
            database.market_candles
            .find(
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

        # The analysis engine requires chronological order.
        candles.reverse()

        if not candles:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No market data found for "
                    f"{symbol} {timeframe}."
                ),
            )

        result = await run_in_threadpool(
            analyze_market,
            candles=candles,
            symbol=symbol,
            timeframe=timeframe,
        )

        return {
            "success": True,
            "message": "Unified market analysis completed.",
            "analysis": result,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Keep internal exception details out of API responses.
        # Add server-side logging before production deployment.
        raise HTTPException(
            status_code=500,
            detail="Unable to complete unified market analysis.",
        ) from exc
        

class AIAnalysisRequest(BaseModel):
    market_analysis: dict[str, Any]
    multi_timeframe_analysis: Optional[dict[str, Any]] = None


@router.post("/ai")
async def get_ai_analysis(
    payload: AIAnalysisRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Interpret actual results from the existing market analysis engine
    and persist the completed AI analysis in MongoDB.
    """

    try:
        result = await analyze_with_ai(
            market_analysis=payload.market_analysis,
            multi_timeframe_analysis=payload.multi_timeframe_analysis,
        )

        interpretation = result["interpretation"]

        raw_symbol = payload.market_analysis.get("symbol")
        raw_timeframe = payload.market_analysis.get("timeframe")

        symbol = (
            str(raw_symbol).strip().upper()
            if raw_symbol
            else "UNKNOWN"
        )

        timeframe = (
            str(raw_timeframe).strip().upper()
            if raw_timeframe
            else "UNKNOWN"
        )

        analyzed_at = datetime.now(timezone.utc)

        database = get_database()

        saved_record = {
            "user_id": current_user["_id"],
            "symbol": symbol,
            "timeframe": timeframe,
            "analyzed_at": analyzed_at,
            "directional_bias": interpretation["market_bias"],
            "confidence": interpretation["confidence"],
            "summary": interpretation["summary"],
            "market_analysis": payload.market_analysis,
            "multi_timeframe_analysis": (
                payload.multi_timeframe_analysis
            ),
            "ai_result": result,
            "human_confirmation_required": True,
            "execution_enabled": False,
        }

        insert_result = await database.analysis_history.insert_one(
            saved_record
        )

        return {
            **result,
            "symbol": symbol,
            "timeframe": timeframe,
            "requested_by": str(current_user["_id"]),
            "history_id": str(insert_result.inserted_id),
            "analyzed_at": analyzed_at.isoformat(),
        }

    except AIAnalysisError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Do not expose database or internal exception details.
        # Log the exception server-side when production logging is configured.
        raise HTTPException(
            status_code=500,
            detail="AI analysis could not be completed or saved.",
        ) from exc