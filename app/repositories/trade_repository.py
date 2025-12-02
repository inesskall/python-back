from abc import ABC, abstractmethod
from typing import List

from ..models.trade import TradeEvent


class TradeRepository(ABC):
    @abstractmethod
    def save(self, trade: TradeEvent) -> None:
        ...

    @abstractmethod
    def list_all(self) -> List[TradeEvent]:
        ...
