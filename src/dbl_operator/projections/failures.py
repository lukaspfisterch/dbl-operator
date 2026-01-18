from collections import defaultdict, Counter
from typing import Any
from .base import Projection

class FailureTaxonomyProjection(Projection):
    def __init__(self):
        self.categories: Counter = Counter()
        self.turns: dict[str, dict] = defaultdict(dict)

    def feed(self, event: dict[str, Any]) -> None:
        turn_id = str(event.get("turn_id"))
        kind = str(event.get("kind", "")).upper()
        payload = event.get("payload", {})
        
        if not turn_id: 
            return
            
        if turn_id not in self.turns:
            self.turns[turn_id] = {"state": "OPEN"}

        if kind == "DECISION":
            res = str(payload.get("decision") or payload.get("result") or "").upper()
            if res == "DENY":
                self.categories["policy_deny"] += 1
                self.turns[turn_id]["state"] = "DENIED"
                # Store reason?
                reason = str(payload.get("reason_code") or (payload.get("reason_codes", [""])[0]))
                self.categories[f"deny_reason:{reason}"] += 1

        elif kind == "EXECUTION":
            self.turns[turn_id]["state"] = "EXECUTED"
            # Check for execution error
            err = payload.get("error")
            if err:
                self.categories["execution_error"] += 1
                code = err.get("code") if isinstance(err, dict) else str(err)
                self.categories[f"exec_error:{code}"] += 1
                self.turns[turn_id]["state"] = "FAILED"

    def render(self) -> str:
        # Check for orphans (turns that are OPEN but stream ended)
        for t in self.turns.values():
            if t["state"] == "OPEN":
                self.categories["orphaned_turn"] += 1

        total_failures = (
            self.categories["policy_deny"] + 
            self.categories["execution_error"] + 
            self.categories["orphaned_turn"]
        )
        
        lines = []
        lines.append("Failure Shape Taxonomy")
        lines.append("======================")
        lines.append(f"Total Observed Failures: {total_failures}")
        lines.append("")
        
        def print_cat(name, key):
            count = self.categories[key]
            pct = (count / total_failures * 100) if total_failures > 0 else 0
            lines.append(f"{name:<20}: {count:>5} ({pct:5.1f}%)")

        print_cat("Policy Denials", "policy_deny")
        print_cat("Execution Errors", "execution_error")
        print_cat("Orphaned Turns", "orphaned_turn")
        
        lines.append("")
        lines.append("Detailed Breakdown")
        lines.append("------------------")
        
        # Sort keys
        sorted_keys = sorted([k for k in self.categories.keys() if ":" in k])
        for k in sorted_keys:
            lines.append(f"{k:<30}: {self.categories[k]}")

        return "\n".join(lines)
