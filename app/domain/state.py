from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from ..models.account import PositionSide
from ..models.trade import TradeEvent


@dataclass
class AgentState:
    balance: float
    position_side: PositionSide = PositionSide.NONE
    position_size: float = 0.0
    avg_entry_price: float = 0.0
    last_price: Optional[float] = None
    position_open_time: Optional[datetime] = None
    last_tick_at: Optional[datetime] = None
    trade_history: List[TradeEvent] = field(default_factory=list)
    total_realized_pnl: float = 0.0

    def equity(self) -> float:
        if (
            self.position_side == PositionSide.NONE
            or self.last_price is None
            or self.position_size == 0.0
        ):
            return self.balance

        unrealized = (self.last_price - self.avg_entry_price) * self.position_size
        return self.balance + self.position_size * self.last_price
