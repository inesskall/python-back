from datetime import datetime
from pydantic import BaseModel


class MarketTick(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
