from collections import defaultdict
from typing import Any, NamedTuple
from datetime import datetime
from .base import Projection

def parse_ts(ts_str: str) -> float:
    # Example: 2023-10-27T10:00:00.123456+00:00
    if not ts_str:
        return 0.0
    try:
        # Python 3.11 supports ISO format directly
        dt = datetime.fromisoformat(ts_str)
        return dt.timestamp()
    except ValueError:
        return 0.0

class TurnTimes(NamedTuple):
    turn_id: str
    intent_ts: float
    decision_ts: float
    execution_ts: float

class LatencyProjection(Projection):
    def __init__(self):
        self.turns: dict[str, dict[str, float]] = defaultdict(dict)

    def feed(self, event: dict[str, Any]) -> None:
        turn_id = str(event.get("turn_id"))
        kind = str(event.get("kind", "")).upper()
        ts = parse_ts(str(event.get("timestamp", "")))
        
        if not turn_id: 
            return
            
        if kind == "INTENT":
            self.turns[turn_id]["intent"] = ts
        elif kind == "DECISION":
            self.turns[turn_id]["decision"] = ts
        elif kind == "EXECUTION":
            self.turns[turn_id]["execution"] = ts

    def render(self) -> str:
        # Collect measurements
        policy_latency = []
        exec_latency = []
        total_latency = []
        
        slowest_turns = []

        for tid, times in self.turns.items():
            t_int = times.get("intent")
            t_dec = times.get("decision")
            t_exe = times.get("execution")
            
            p_lat = None
            e_lat = None
            tot_lat = None

            if t_int and t_dec:
                p_lat = (t_dec - t_int) * 1000.0 # ms
                policy_latency.append(p_lat)
            
            if t_dec and t_exe:
                e_lat = (t_exe - t_dec) * 1000.0 # ms
                exec_latency.append(e_lat)
                
            if t_int and t_exe:
                tot_lat = (t_exe - t_int) * 1000.0 # ms
                total_latency.append(tot_lat)
                
            if tot_lat:
                slowest_turns.append((tot_lat, tid, p_lat or 0, e_lat or 0))

        # Sort measurements
        policy_latency.sort()
        exec_latency.sort()
        total_latency.sort()
        slowest_turns.sort(key=lambda x: x[0], reverse=True) # Slowest first

        def get_p(data, p):
            if not data: return 0.0
            idx = int(len(data) * p)
            return data[min(idx, len(data)-1)]

        lines = []
        lines.append("Latency Profile (ms)")
        lines.append("====================")
        
        header = f"{'Metric':<20} | {'P50':>8} | {'P95':>8} | {'P99':>8} | {'Count':>6}"
        lines.append(header)
        lines.append("-" * len(header))
        
        def row(name, data):
            p50 = get_p(data, 0.50)
            p95 = get_p(data, 0.95)
            p99 = get_p(data, 0.99)
            count = len(data)
            return f"{name:<20} | {p50:8.1f} | {p95:8.1f} | {p99:8.1f} | {count:6d}"

        lines.append(row("Intent -> Decision", policy_latency))
        lines.append(row("Decision -> Exec", exec_latency))
        lines.append(row("Total (E2E)", total_latency))
        
        lines.append("")
        lines.append("Slowest 5 Turns")
        lines.append("---------------")
        lines.append(f"{'Turn ID':<36} | {'Total':>8} | {'Policy':>8} | {'Exec':>8}")
        for t, tid, p, e in slowest_turns[:5]:
            lines.append(f"{tid:<36} | {t:8.1f} | {p:8.1f} | {e:8.1f}")

        return "\n".join(lines)
