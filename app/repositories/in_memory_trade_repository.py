from typing import List

from .trade_repository import TradeRepository
from ..models.trade import TradeEvent


class InMemoryTradeRepository(TradeRepository):
    def __init__(self) -> None:
        self._storage: List[TradeEvent] = []

    def save(self, trade: TradeEvent) -> None:
        self._storage.append(trade)

    def list_all(self) -> List[TradeEvent]:
        return list(self._storage)
