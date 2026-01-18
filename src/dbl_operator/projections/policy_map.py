from collections import defaultdict
from typing import Any, NamedTuple
from datetime import datetime
from .base import Projection

class PolicySpan(NamedTuple):
    policy_id: str
    version: str
    start_ts: str
    end_ts: str
    turn_count: int
    start_index: int
    end_index: int

class PolicyMapProjection(Projection):
    def __init__(self):
        self.spans: list[dict] = []
        self.current_span: dict | None = None
        self.last_ts = ""

    def feed(self, event: dict[str, Any]) -> None:
        kind = str(event.get("kind", "")).upper()
        if kind != "DECISION":
            return
            
        payload = event.get("payload", {})
        pid = str(payload.get("policy_id", "unknown"))
        pver = str(payload.get("policy_version", "unknown"))
        idx = int(event.get("index", 0))
        ts = str(event.get("timestamp", ""))
        self.last_ts = ts
        
        # New span if policy changes or no current span
        if not self.current_span or \
           self.current_span["policy_id"] != pid or \
           self.current_span["version"] != pver:
            
            if self.current_span:
                self.spans.append(self.current_span)
            
            self.current_span = {
                "policy_id": pid,
                "version": pver,
                "start_ts": ts,
                "end_ts": ts,
                "start_index": idx,
                "end_index": idx,
                "turn_count": 0
            }
            
        # Update current
        if self.current_span:
            self.current_span["end_ts"] = ts
            self.current_span["end_index"] = idx
            self.current_span["turn_count"] += 1

    def render(self) -> str:
        # Finalize last span
        if self.current_span:
            self.spans.append(self.current_span)
            self.current_span = None

        lines = []
        lines.append("Policy Footprint Timeline")
        lines.append("=========================")
        
        header = f"{'Start Time':<24} | {'Policy ID':<20} | {'Ver':<8} | {'Turns':>6} | {'Idx Range'}"
        lines.append(header)
        lines.append("-" * len(header))
        
        for span in self.spans:
            # Format TS? Keep raw ISO for precision or truncate
            start = span["start_ts"][:19] # YYYY-MM-DDTHH:MM:SS
            # end = span["end_ts"][:19]
            idx_range = f"{span['start_index']} - {span['end_index']}"
            
            lines.append(f"{start:<24} | {span['policy_id']:<20} | {span['version']:<8} | {span['turn_count']:6d} | {idx_range}")

        return "\n".join(lines)
