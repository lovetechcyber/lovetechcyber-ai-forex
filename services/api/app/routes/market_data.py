
import math
import re
import secrets
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from pymongo import UpdateOne
from pymongo.errors import PyMongoError

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.mongo import get_database
from app.routes.auth import limiter
from app.routes.market_data_schemas import (
    MarketDataBatch,
    MarketDataResponse,
)


router = APIRouter(
    prefix="/market-data",
    tags=["Market Data"],
)

SUPPORTED_TIMEFRAMES = {
    "M5", "M15", "M30", "H1", "H4", "D1"
}

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9._-]{3,30}$")


def verify_mt5_agent(api_key: str | None) -> None:
    configured_key = settings.mt5_ingest_api_key

    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MT5 ingestion is not configured",
        )

    if not api_key or not secrets.compare_digest(
        api_key,
        configured_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MT5 agent credentials",
        )


def validate_candles(candles) -> None:
    """Validate candle integrity before database ingestion."""

    timestamps = set()

    for candle in candles:
        timestamp = candle.timestamp

        if timestamp in timestamps:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate candle timestamp: {timestamp}",
            )

        timestamps.add(timestamp)

        prices = (
            candle.open,
            candle.high,
            candle.low,
            candle.close,
        )

        if not all(math.isfinite(price) for price in prices):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Candle contains a non-finite price",
            )

        if candle.high < max(candle.open, candle.close):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid candle high at timestamp {timestamp}",
            )

        if candle.low > min(candle.open, candle.close):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid candle low at timestamp {timestamp}",
            )

        if candle.high < candle.low:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid candle range at timestamp {timestamp}",
            )


@router.post(
    "/ingest",
    response_model=MarketDataResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(settings.market_data_rate_limit)
async def ingest_market_data(
    request: Request,
    payload: MarketDataBatch,
    x_mt5_api_key: str | None = Header(
        default=None,
        alias="X-MT5-API-Key",
    ),
):
    # Authenticate MT5 independently of user authentication.
    verify_mt5_agent(x_mt5_api_key)

    symbol = payload.symbol.strip().upper()
    timeframe = payload.timeframe.strip().upper()

    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid market symbol",
        )

    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported timeframe",
        )

    if len(payload.candles) > settings.max_market_data_candles:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Too many candles in one request",
        )

    validate_candles(payload.candles)

    database = get_database()
    collection = database.market_candles

    received_at = datetime.now(timezone.utc)

    operations = []

    # Sort candles chronologically before ingestion.
    ordered_candles = sorted(
        payload.candles,
        key=lambda candle: candle.timestamp,
    )

    for candle in ordered_candles:
        document = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": candle.timestamp,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "tick_volume": candle.tick_volume,
            "spread": candle.spread,
            "real_volume": candle.real_volume,
            "received_at": received_at,
            "source": "mt5",
        }

        operations.append(
            UpdateOne(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": candle.timestamp,
                },
                {
                    "$set": document,
                },
                upsert=True,
            )
        )

    try:
        await collection.bulk_write(
            operations,
            ordered=False,
        )

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market data storage is temporarily unavailable",
        ) from None

    return MarketDataResponse(
        message="Market data received successfully",
        symbol=symbol,
        timeframe=timeframe,
        received=len(operations),
        server_time=received_at,
    )


@router.get(
    "/latest",
    tags=["Market Data"],
)
async def get_latest_market_data(
    symbol: str,
    timeframe: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    current_user: dict = Depends(get_current_user),
):
    symbol = symbol.strip().upper()
    timeframe = timeframe.strip().upper()

    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid market symbol",
        )

    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported timeframe",
        )

    database = get_database()

    try:
        cursor = (
            database.market_candles
            .find(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                },
                {"_id": 0},
            )
            .sort("timestamp", -1)
            .limit(limit)
        )

        candles = await cursor.to_list(length=limit)

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market data is temporarily unavailable",
        ) from None

    # Return candles in chronological order.
    candles.reverse()

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(candles),
        "candles": candles,
    }
