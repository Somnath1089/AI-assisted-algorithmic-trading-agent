from dataclasses import dataclass
from typing import Optional

@dataclass
class PaperTradeRecord:
    symbol: str
    side: str
    expected_entry: float
    expected_stop: float
    expected_target1: float
    actual_entry: Optional[float] = None
    actual_exit: Optional[float] = None
    actual_exit_reason: Optional[str] = None

class PaperTradeTracker:
    def __init__(self):
        self.records: list[PaperTradeRecord] = []

    def record_signal(self, signal) -> PaperTradeRecord:
        record = PaperTradeRecord(
            symbol=signal.symbol,
            side=signal.side,
            expected_entry=signal.entry,
            expected_stop=signal.stop_loss,
            expected_target1=signal.target1,
        )
        self.records.append(record)
        return record

    def record_execution(self, record: PaperTradeRecord, actual_entry: float):
        record.actual_entry = actual_entry

    def record_exit(self, record: PaperTradeRecord, actual_exit: float, reason: str):
        record.actual_exit = actual_exit
        record.actual_exit_reason = reason

    def summary(self) -> dict:
        entry_slippage = [
            r.actual_entry - r.expected_entry
            for r in self.records if r.actual_entry is not None
        ]
        completed = [r for r in self.records if r.actual_exit_reason is not None]
        target_hits = sum(1 for r in completed if r.actual_exit_reason == "TARGET1")
        stop_hits = sum(1 for r in completed if r.actual_exit_reason == "STOP")

        return {
            "total_signals": len(self.records),
            "executed": sum(1 for r in self.records if r.actual_entry is not None),
            "avg_entry_slippage": (sum(entry_slippage) / len(entry_slippage)) if entry_slippage else 0.0,
            "target1_hit_rate": (target_hits / len(completed)) if completed else 0.0,
            "stop_hit_rate": (stop_hits / len(completed)) if completed else 0.0,
        }
