from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeEvent(BaseModel):
    id: str
    symbol: str
    side: TradeSide
    price: float
    volume: float
    realized_pnl: float
    balance_after: float
    position_size_after: float
    timestamp: datetime
    reason: Optional[str] = None
