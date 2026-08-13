"""
F&O instruments are fundamentally different from a cash-equity ticker: they
carry a lot size (contracts trade in fixed multiples, not single shares) and
an expiry (the contract stops existing). Both are exchange-set facts that
change periodically via NSE/SEBI circulars - lot sizes in particular are
rebased when index levels move enough to matter. When this was written, a
web search for the current NIFTY lot size returned conflicting figures (65
vs 75) from different sources, and the source sites themselves were
unreachable to verify directly. That is exactly why lot_size is a required
constructor argument here with no default: guessing it would silently
corrupt every position-sizing and margin calculation downstream. Verify the
current lot size against the NSE F&O circular (or your broker's contract
master) before constructing an instrument for real use.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class FnoInstrument:
    symbol: str
    underlying: str
    instrument_type: str  # "FUT" or "OPT"
    lot_size: int
    expiry: date
    strike: Optional[float] = None
    option_type: Optional[str] = None  # "CE" or "PE" - options only

    def __post_init__(self):
        if self.lot_size <= 0:
            raise ValueError(
                f"{self.symbol}: lot_size must be a positive integer verified "
                f"against the current NSE F&O circular - it must never be guessed."
            )
        if self.instrument_type not in ("FUT", "OPT"):
            raise ValueError(f"instrument_type must be 'FUT' or 'OPT', got {self.instrument_type!r}")
        if self.instrument_type == "OPT":
            if self.strike is None or self.strike <= 0:
                raise ValueError(f"{self.symbol}: options require a positive strike")
            if self.option_type not in ("CE", "PE"):
                raise ValueError(f"{self.symbol}: option_type must be 'CE' or 'PE', got {self.option_type!r}")

def days_to_expiry(instrument: FnoInstrument, as_of: date) -> int:
    return (instrument.expiry - as_of).days

def is_expired(instrument: FnoInstrument, as_of: date) -> bool:
    return days_to_expiry(instrument, as_of) < 0

def is_near_expiry(instrument: FnoInstrument, as_of: date, threshold_days: int = 2) -> bool:
    remaining = days_to_expiry(instrument, as_of)
    return 0 <= remaining <= threshold_days

def nifty_futures(lot_size: int, expiry: date) -> FnoInstrument:
    """Build a NIFTY index futures instrument. lot_size and expiry are
    required arguments on purpose - see the module docstring. Do not fill
    in a lot size you haven't verified against a current, authoritative
    source."""
    return FnoInstrument(
        symbol=f"NIFTY-FUT-{expiry.isoformat()}",
        underlying="NIFTY",
        instrument_type="FUT",
        lot_size=lot_size,
        expiry=expiry,
    )
