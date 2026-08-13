from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    capital: float = float(os.getenv("CAPITAL", "100000"))
    risk_per_trade: float = float(os.getenv("RISK_PER_TRADE", "0.01"))
    max_daily_loss: float = float(os.getenv("MAX_DAILY_LOSS", "0.02"))
    max_trades_per_day: int = int(os.getenv("MAX_TRADES_PER_DAY", "3"))
    max_open_risk: float = float(os.getenv("MAX_OPEN_RISK", "0.02"))
    min_signal_score: int = int(os.getenv("MIN_SIGNAL_SCORE", "75"))
    live_trading: bool = os.getenv("LIVE_TRADING", "false").lower() == "true"
    fo_enabled: bool = os.getenv("FO_ENABLED", "false").lower() == "true"
    enforce_market_hours: bool = os.getenv("ENFORCE_MARKET_HOURS", "true").lower() == "true"
    data_provider: str = os.getenv("DATA_PROVIDER", "yfinance")
    dhan_client_id: str = os.getenv("DHAN_CLIENT_ID", "")
    dhan_access_token: str = os.getenv("DHAN_ACCESS_TOKEN", "")

    # F&O is a leveraged, lot-based instrument class with no safe default
    # lot size or expiry (see fno/instruments.py) - both must be supplied
    # explicitly and verified against the current NSE F&O circular. Left
    # unset (empty string), main.py skips the F&O leg even if FO_ENABLED
    # is true, rather than guess.
    fno_lot_size: str = os.getenv("FNO_LOT_SIZE", "")
    fno_expiry: str = os.getenv("FNO_EXPIRY", "")  # YYYY-MM-DD
    fno_margin_pct: float = float(os.getenv("FNO_MARGIN_PCT", "0.12"))

settings = Settings()
