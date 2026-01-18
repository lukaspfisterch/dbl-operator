from collections import defaultdict, Counter
from typing import Any
from .base import Projection

class DecisionStatsProjection(Projection):
    def __init__(self):
        # (policy_id, intent_type) -> Counter(result)
        self.matrix: dict[tuple[str, str], Counter] = defaultdict(Counter)
        # reason_code -> count
        self.reasons: Counter = Counter()

    def feed(self, event: dict[str, Any]) -> None:
        kind = str(event.get("kind", "")).upper()
        if kind != "DECISION":
            return
            
        payload = event.get("payload", {})
        pid = str(payload.get("policy_id", "unknown"))
        intent_type = str(event.get("intent_type", "unknown"))
        
        # Result normalization
        res = str(payload.get("decision") or payload.get("result") or "UNKNOWN").upper()
        
        # Reason extraction
        codes = payload.get("reason_codes", [])
        if not codes:
            code = payload.get("reason_code")
            if code:
                codes = [code]
        
        if not codes and res == "ALLOW":
            codes = ["allow_all"] # or implied?
        
        self.matrix[(pid, intent_type)][res] += 1
        for c in codes:
            self.reasons[str(c)] += 1

    def render(self) -> str:
        lines = []
        lines.append("Decision Surface Statistics")
        lines.append("===========================")
        
        # Matrix
        lines.append("")
        lines.append("Decision Matrix (Policy x Intent)")
        lines.append(f"{'Policy':<20} | {'Intent Type':<20} | {'ALLOW':>6} | {'DENY':>6} | {'Rate %':>6}")
        lines.append("-" * 80)
        
        for (pid, itype), counts in sorted(self.matrix.items()):
            allow = counts["ALLOW"]
            deny = counts["DENY"]
            total = allow + deny
            rate = (allow / total * 100.0) if total > 0 else 0.0
            
            lines.append(f"{pid:<20} | {itype:<20} | {allow:6d} | {deny:6d} | {rate:6.1f}")
            
        # Top Reasons
        lines.append("")
        lines.append("Top Reason Codes")
        lines.append("----------------")
        for code, count in self.reasons.most_common(10):
            lines.append(f"{code:<30}: {count}")

        return "\n".join(lines)
