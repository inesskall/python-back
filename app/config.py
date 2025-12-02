import os
from pydantic import BaseModel


class Settings(BaseModel):
    initial_balance: float = float(os.getenv("AGENT_INITIAL_BALANCE", "10000"))
    risk_per_trade_pct: float = float(os.getenv("AGENT_RISK_PER_TRADE_PCT", "1.0"))
    take_profit_pct: float = float(os.getenv("AGENT_TAKE_PROFIT_PCT", "0.7"))
    stop_loss_pct: float = float(os.getenv("AGENT_STOP_LOSS_PCT", "0.5"))
    max_position_pct_of_balance: float = float(
        os.getenv("AGENT_MAX_POSITION_PCT_OF_BALANCE", "50.0")
    )
    min_time_in_position_seconds: int = int(
        os.getenv("AGENT_MIN_TIME_IN_POSITION_SECONDS", "5")
    )
    max_time_in_position_seconds: int = int(
        os.getenv("AGENT_MAX_TIME_IN_POSITION_SECONDS", "60")
    )


def get_settings() -> Settings:
    return Settings()
