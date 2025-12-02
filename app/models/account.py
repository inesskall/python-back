from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class PositionSide(str, Enum):
    NONE = "NONE"
    LONG = "LONG"


class AccountState(BaseModel):
    balance: float
    equity: float
    position_side: PositionSide
    position_size: float
    avg_entry_price: float
    last_price: Optional[float]
    updated_at: datetime
    realized_pnl: float
    position_open_time: Optional[datetime] = None
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    position_notional: Optional[float] = None

