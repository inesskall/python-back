from datetime import datetime, timedelta

from .base import Strategy, StrategySignal
from ...models.market import MarketTick
from ..state import AgentState


class RuleBasedLongStrategy(Strategy):
    def generate_signal(self, state: AgentState, tick: MarketTick) -> StrategySignal:
        if state.position_side.name == "NONE":
            return self._signal_open_long(state, tick)
        else:
            return self._signal_close_long(state, tick)

    def _signal_open_long(self, state: AgentState, tick: MarketTick) -> StrategySignal:
        if state.last_price is None:
            return StrategySignal(action="HOLD", reason="NO_REFERENCE_PRICE")

        if tick.close > state.last_price * 1.003:
            return StrategySignal(action="HOLD", reason="PRICE_SPIKE_UP")

        if tick.volume < 1:
            return StrategySignal(action="HOLD", reason="LOW_VOLUME")

        return StrategySignal(action="OPEN_LONG", reason="ENTRY_CONDITIONS_MET")

    def _signal_close_long(self, state: AgentState, tick: MarketTick) -> StrategySignal:
        if state.position_open_time is not None:
            delta = datetime.utcnow() - state.position_open_time
            if delta < timedelta(seconds=1):
                return StrategySignal(action="HOLD", reason="TOO_EARLY_TO_CLOSE")

        return StrategySignal(action="HOLD", reason="NO_CLOSE_CONDITION")
