import re
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


Timeframe = Literal["M5", "M15", "M30", "H1", "H4", "D1"]


class Candle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: int = Field(gt=0)
    open: float = Field(gt=0, allow_inf_nan=False)
    high: float = Field(gt=0, allow_inf_nan=False)
    low: float = Field(gt=0, allow_inf_nan=False)
    close: float = Field(gt=0, allow_inf_nan=False)

    tick_volume: int = Field(default=0, ge=0)
    spread: int = Field(default=0, ge=0)
    real_volume: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_ohlc(self):
        if self.high < max(self.open, self.close, self.low):
            raise ValueError(
                "Candle high cannot be below open, close, or low"
            )

        if self.low > min(self.open, self.close, self.high):
            raise ValueError(
                "Candle low cannot be above open, close, or high"
            )

        return self


class MarketDataBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Annotated[str, Field(min_length=3, max_length=30)]
    timeframe: Timeframe
    candles: list[Candle] = Field(min_length=1, max_length=500)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        value = value.strip().upper()

        if not re.fullmatch(r"[A-Z0-9._-]{3,30}", value):
            raise ValueError("Invalid broker symbol")

        return value

    @model_validator(mode="after")
    def validate_candle_order(self):
        timestamps = [c.timestamp for c in self.candles]

        if len(timestamps) != len(set(timestamps)):
            raise ValueError(
                "Duplicate candle timestamps in the same batch"
            )

        if timestamps != sorted(timestamps):
            raise ValueError(
                "Candles must be submitted in ascending timestamp order"
            )

        return self


class MarketDataResponse(BaseModel):
    message: str
    symbol: str
    timeframe: str
    received: int
    server_time: datetime