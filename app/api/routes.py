from typing import List

from fastapi import APIRouter

from ..models.agent import BotDecision
from ..models.account import AccountState
from ..models.market import MarketTick
from ..models.trade import TradeEvent
from ..services import agent_service

router = APIRouter()


@router.post("/on-tick", response_model=BotDecision)
def on_tick(tick: MarketTick) -> BotDecision:
    return agent_service.process_tick(tick)


@router.get("/state", response_model=AccountState)
def get_state() -> AccountState:
    return agent_service.get_state()


@router.get("/trades", response_model=List[TradeEvent])
def get_trades() -> List[TradeEvent]:
    return agent_service.get_trades()


@router.post("/reset", response_model=AccountState)
def reset_agent() -> AccountState:
    return agent_service.reset()
