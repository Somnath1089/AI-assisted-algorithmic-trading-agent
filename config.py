from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    capital: float = float(os.getenv("CAPITAL", "100000"))
    risk_per_trade: float = float(os.getenv("RISK_PER_TRADE", "0.01"))
    max_daily_loss: float = float(os.getenv("MAX_DAILY_LOSS", "0.02"))
    max_trades_per_day: int = int(os.getenv("MAX_TRADES_PER_DAY", "3"))
    min_signal_score: int = int(os.getenv("MIN_SIGNAL_SCORE", "75"))
    live_trading: bool = os.getenv("LIVE_TRADING", "false").lower() == "true"

settings = Settings()
