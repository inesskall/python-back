from datetime import datetime, timedelta
import uuid
from typing import Dict, List
import logging

from ..config import get_settings
from ..domain.state import AgentState
from ..domain.strategy.rule_based import RuleBasedLongStrategy
from ..domain.strategy.base import Strategy
from ..models.account import AccountState, PositionSide
from ..models.agent import AgentConfig, BotDecision
from ..models.market import MarketTick
from ..models.trade import TradeEvent, TradeSide
from ..repositories.trade_repository import TradeRepository
from ..repositories.in_memory_trade_repository import InMemoryTradeRepository

logger = logging.getLogger(__name__)
class AgentService:
    def __init__(
        self,
        config: AgentConfig,
        strategy: Strategy,
        trade_repository: TradeRepository,
    ) -> None:
        self._config = config
        self._state = AgentState(balance=config.initial_balance)
        self._strategy = strategy
        self._trade_repo = trade_repository

    def process_tick(self, tick: MarketTick) -> BotDecision:
        logger.info(
            "TICK_IN: symbol=%s ts=%s o=%.2f h=%.2f l=%.2f c=%.2f v=%.4f | "
            "STATE_BEFORE: balance=%.2f equity=%.2f side=%s size=%.4f avg_entry=%.4f last_price=%s",
            tick.symbol,
            tick.timestamp,
            tick.open,
            tick.high,
            tick.low,
            tick.close,
            tick.volume,
            self._state.balance,
            self._state.equity(),
            self._state.position_side.name,
            self._state.position_size,
            self._state.avg_entry_price,
            self._state.last_price,
        )

        self._state.last_tick_at = datetime.utcnow()
        self._state.last_price = tick.close

        signal = self._strategy.generate_signal(self._state, tick)

        trades: List[TradeEvent] = []
        debug_info: Dict[str, object] = {
            "strategy_action": signal.action,
            "strategy_reason": signal.reason,
        }

        if self._state.position_side == PositionSide.NONE:
            if signal.action == "OPEN_LONG":
                trade = self._open_long_position(tick, signal.reason or "")
                if trade is not None:
                    trades.append(trade)
                    debug_info["entered_long"] = True
        else:
            close_reason = self._check_close_conditions(tick)
            if close_reason is not None:
                trade = self._close_long_position(tick, close_reason)
                if trade is not None:
                    trades.append(trade)
                    debug_info["close_reason"] = close_reason

        account = self._build_account_state()
        debug_info["equity"] = account.equity

        logger.info(
            "TICK_OUT: symbol=%s c=%.2f | "
            "ACCOUNT: balance=%.2f equity=%.2f side=%s size=%.4f avg_entry=%.4f last_price=%s | "
            "STRATEGY: action=%s reason=%s trades=%d",
            tick.symbol,
            tick.close,
            account.balance,
            account.equity,
            account.position_side.name,
            account.position_size,
            account.avg_entry_price,
            account.last_price,
            signal.action,
            signal.reason,
            len(trades),
        )
        logger.info(
            "ROI_CHECK: python_initial_balance=%s current_equity=%.2f diff=%.2f pct=%.2f",
            self._config.initial_balance,
            account.equity,
            account.equity - self._config.initial_balance,
            ((account.equity - self._config.initial_balance) / self._config.initial_balance * 100.0)
            if self._config.initial_balance > 0
            else 0.0,
        )

        return BotDecision(trades=trades, account=account, debug=debug_info)

    def _open_long_position(self, tick: MarketTick, reason: str) -> TradeEvent | None:
        if self._state.position_side != PositionSide.NONE:
            logger.warning("OPEN_LONG_SKIP: already in position side=%s", self._state.position_side)
            return None

        volume = self._calculate_volume(tick.close)
        if volume <= 0:
            logger.info("OPEN_LONG_ABORT: volume<=0 at price=%.2f", tick.close)
            return None

        notional = volume * tick.close
        if self._state.balance < notional:
            logger.info(
                "OPEN_LONG_ABORT: insufficient balance balance=%.2f notional=%.2f",
                self._state.balance,
                notional,
            )
            return None

        logger.info(
            "OPEN_LONG: symbol=%s price=%.2f volume=%.4f notional=%.2f balance_before=%.2f reason=%s",
            tick.symbol,
            tick.close,
            volume,
            notional,
            self._state.balance,
            reason,
        )

        self._state.balance -= notional
        self._state.position_side = PositionSide.LONG
        self._state.position_size = volume
        self._state.avg_entry_price = tick.close
        self._state.position_open_time = datetime.utcnow()

        trade = TradeEvent(
            id=str(uuid.uuid4()),
            symbol=tick.symbol,
            side=TradeSide.BUY,
            price=tick.close,
            volume=volume,
            realized_pnl=0.0,
            balance_after=self._state.balance,
            position_size_after=self._state.position_size,
            timestamp=datetime.utcnow(),
            reason=reason,
        )
        self._state.trade_history.append(trade)
        self._trade_repo.save(trade)

        logger.info(
            "OPEN_LONG_DONE: balance_after=%.2f position_size=%.4f avg_entry=%.4f",
            self._state.balance,
            self._state.position_size,
            self._state.avg_entry_price,
        )

        return trade

    def _check_close_conditions(self, tick: MarketTick) -> str | None:
        if self._state.position_side != PositionSide.LONG or self._state.position_size <= 0:
            return None

        if self._state.position_open_time is not None:
            now = datetime.utcnow()
            elapsed = now - self._state.position_open_time
            min_delta = timedelta(seconds=self._config.min_time_in_position_seconds)
            if elapsed < min_delta:
                return None
            max_delta = timedelta(seconds=self._config.max_time_in_position_seconds)
            if elapsed >= max_delta:
                return "TIME_EXIT"

        tp_level = self._state.avg_entry_price * (1 + self._config.take_profit_pct / 100.0)
        sl_level = self._state.avg_entry_price * (1 - self._config.stop_loss_pct / 100.0)

        if tick.close >= tp_level:
            return "TAKE_PROFIT"
        if tick.close <= sl_level:
            return "STOP_LOSS"

        return None

    def _close_long_position(self, tick: MarketTick, reason: str) -> TradeEvent | None:
        if self._state.position_side != PositionSide.LONG or self._state.position_size <= 0:
            logger.warning("CLOSE_LONG_SKIP: no long position side=%s size=%.4f",
                           self._state.position_side, self._state.position_size)
            return None

        volume = self._state.position_size
        notional = volume * tick.close
        pnl = (tick.close - self._state.avg_entry_price) * volume

        logger.info(
            "CLOSE_LONG: symbol=%s price=%.2f volume=%.4f notional=%.2f pnl=%.2f reason=%s "
            "balance_before=%.2f",
            tick.symbol,
            tick.close,
            volume,
            notional,
            pnl,
            reason,
            self._state.balance,
        )

        self._state.balance += notional
        self._state.position_side = PositionSide.NONE
        self._state.position_size = 0.0
        self._state.avg_entry_price = 0.0
        self._state.position_open_time = None
        self._state.total_realized_pnl += pnl

        trade = TradeEvent(
            id=str(uuid.uuid4()),
            symbol=tick.symbol,
            side=TradeSide.SELL,
            price=tick.close,
            volume=volume,
            realized_pnl=pnl,
            balance_after=self._state.balance,
            position_size_after=self._state.position_size,
            timestamp=datetime.utcnow(),
            reason=reason,
        )
        self._state.trade_history.append(trade)
        self._trade_repo.save(trade)

        logger.info(
            "CLOSE_LONG_DONE: balance_after=%.2f realized_pnl=%.2f",
            self._state.balance,
            pnl,
        )

        return trade

    def _calculate_volume(self, price: float) -> float:
        if price <= 0:
            return 0.0

        max_risk_amount = self._state.balance * (self._config.risk_per_trade_pct / 100.0)
        stop_loss_distance = price * (self._config.stop_loss_pct / 100.0)
        if stop_loss_distance <= 0:
            return 0.0

        volume_by_risk = max_risk_amount / stop_loss_distance

        max_position_notional = self._state.balance * (self._config.max_position_pct_of_balance / 100.0)
        volume_by_balance = max_position_notional / price

        volume = min(volume_by_risk, volume_by_balance)
        return round(volume, 4)

    def _build_account_state(self) -> AccountState:
        tp_price = None
        sl_price = None
        notional = None

        if self._state.position_side == PositionSide.LONG and self._state.position_size > 0:
            notional = self._state.position_size * self._state.avg_entry_price
            if self._config.take_profit_pct > 0:
                tp_price = self._state.avg_entry_price * (1 + self._config.take_profit_pct / 100.0)
            if self._config.stop_loss_pct > 0:
                sl_price = self._state.avg_entry_price * (1 - self._config.stop_loss_pct / 100.0)

        return AccountState(
            balance=self._state.balance,
            equity=self._state.equity(),
            position_side=self._state.position_side,
            position_size=self._state.position_size,
            avg_entry_price=self._state.avg_entry_price,
            last_price=self._state.last_price,
            updated_at=datetime.utcnow(),
            realized_pnl=self._state.total_realized_pnl,
            position_open_time=self._state.position_open_time,
            take_profit_price=tp_price,
            stop_loss_price=sl_price,
            position_notional=notional,
        )

    def get_state(self) -> AccountState:
        return self._build_account_state()

    def get_trades(self) -> List[TradeEvent]:
        return self._trade_repo.list_all()

    def reset(self) -> AccountState:
        self._state = AgentState(balance=self._config.initial_balance)
        return self._build_account_state()


def create_agent_service() -> AgentService:
    settings = get_settings()
    config = AgentConfig(
        initial_balance=settings.initial_balance,
        risk_per_trade_pct=settings.risk_per_trade_pct,
        take_profit_pct=settings.take_profit_pct,
        stop_loss_pct=settings.stop_loss_pct,
        max_position_pct_of_balance=settings.max_position_pct_of_balance,
        min_time_in_position_seconds=settings.min_time_in_position_seconds,
        max_time_in_position_seconds=settings.max_time_in_position_seconds,
    )
    logger.info(
        "AGENT_CONFIG: initial_balance=%s risk_per_trade_pct=%s "
        "take_profit_pct=%s stop_loss_pct=%s max_pos_pct=%s "
        "min_time=%s max_time=%s",
        config.initial_balance,
        config.risk_per_trade_pct,
        config.take_profit_pct,
        config.stop_loss_pct,
        config.max_position_pct_of_balance,
        config.min_time_in_position_seconds,
        config.max_time_in_position_seconds,
    )
    strategy = RuleBasedLongStrategy()
    trade_repo = InMemoryTradeRepository()
    return AgentService(config=config, strategy=strategy, trade_repository=trade_repo)

