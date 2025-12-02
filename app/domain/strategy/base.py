from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel

from ...models.market import MarketTick
from ..state import AgentState


class StrategySignal(BaseModel):
    action: str
    reason: Optional[str] = None


class Strategy(ABC):
    @abstractmethod
    def generate_signal(self, state: AgentState, tick: MarketTick) -> StrategySignal:
        ...
