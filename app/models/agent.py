from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .account import AccountState
from .trade import TradeEvent


class AgentConfig(BaseModel):
    initial_balance: float = 10_000.0
    risk_per_trade_pct: float = 1.0
    take_profit_pct: float = 0.7
    stop_loss_pct: float = 0.5
    max_position_pct_of_balance: float = 50.0
    min_time_in_position_seconds: int = 5
    max_time_in_position_seconds: int = 60


class BotDecision(BaseModel):
    trades: List[TradeEvent]
    account: AccountState
    debug: Optional[Dict[str, Any]] = None
