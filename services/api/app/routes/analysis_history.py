from datetime import datetime, timezone
import re

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user
from app.db.mongo import get_database


router = APIRouter(
    prefix="/api/v1/analysis/history",
    tags=["Analysis History"],
)


def serialize_history_record(record: dict) -> dict:
    """Convert MongoDB values into JSON-safe response values."""

    analyzed_at = record.get("analyzed_at")

    if isinstance(analyzed_at, datetime):
        analyzed_at = analyzed_at.isoformat()

    return {
        "id": str(record["_id"]),
        "symbol": record.get("symbol"),
        "timeframe": record.get("timeframe"),
        "analyzed_at": analyzed_at,
        "directional_bias": record.get("directional_bias"),
        "confidence": record.get("confidence"),
        "summary": record.get("summary"),
        "human_confirmation_required": record.get(
            "human_confirmation_required", True
        ),
    }


@router.get("")
async def list_analysis_history(
    symbol: str | None = Query(default=None, max_length=30),
    timeframe: str | None = Query(default=None, max_length=10),
    bias: str | None = Query(default=None, max_length=20),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    List the authenticated user's saved AI analysis records.
    Supports filtering and pagination.
    """

    database = get_database()

    filters = {
        "user_id": current_user["_id"],
    }

    if symbol:
        filters["symbol"] = symbol.strip().upper()

    if timeframe:
        normalized_timeframe = timeframe.strip().upper()

        if normalized_timeframe not in {
            "M5", "M15", "M30", "H1", "H4", "D1"
        }:
            raise HTTPException(
                status_code=422,
                detail="Unsupported timeframe.",
            )

        filters["timeframe"] = normalized_timeframe

    if bias:
        normalized_bias = bias.strip().lower()

        if normalized_bias not in {
            "bullish", "bearish", "neutral", "uncertain"
        }:
            raise HTTPException(
                status_code=422,
                detail="Unsupported directional bias.",
            )

        filters["directional_bias"] = normalized_bias

    if search:
        escaped_search = re.escape(search.strip())

        if escaped_search:
            filters["$or"] = [
                {"symbol": {"$regex": escaped_search, "$options": "i"}},
                {"summary": {"$regex": escaped_search, "$options": "i"}},
            ]

    collection = database.analysis_history

    total = await collection.count_documents(filters)

    cursor = (
        collection.find(
            filters,
            {
                "market_analysis": 0,
                "multi_timeframe_analysis": 0,
                "ai_result": 0,
            },
        )
        .sort("analyzed_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    records = await cursor.to_list(length=limit)

    return {
        "success": True,
        "items": [
            serialize_history_record(record)
            for record in records
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


@router.get("/{record_id}")
async def get_analysis_history_detail(
    record_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve one saved analysis belonging to the authenticated user."""

    if not ObjectId.is_valid(record_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid analysis history ID.",
        )

    database = get_database()

    record = await database.analysis_history.find_one(
        {
            "_id": ObjectId(record_id),
            "user_id": current_user["_id"],
        }
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis history record not found.",
        )

    record["id"] = str(record.pop("_id"))
    record["user_id"] = str(record["user_id"])

    if isinstance(record.get("analyzed_at"), datetime):
        record["analyzed_at"] = record["analyzed_at"].isoformat()

    return {
        "success": True,
        "record": record,
    }