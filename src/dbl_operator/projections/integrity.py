from collections import defaultdict
from typing import Any, NamedTuple
from .base import Projection

class TurnState:
    def __init__(self, turn_id: str):
        self.turn_id = turn_id
        self.has_intent = False
        self.has_decision = False
        self.decision_result: str | None = None
        self.has_execution = False
        self.events: list[dict[str, Any]] = []

    def update(self, event: dict[str, Any]):
        kind = str(event.get("kind", "")).upper()
        self.events.append(event)
        
        if kind == "INTENT":
            self.has_intent = True
        elif kind == "DECISION":
            self.has_decision = True
            payload = event.get("payload", {})
            # payload structure varies? Gateway typically decision payload has "decision" or "result"
            # In v0.4.x: payload["decision"] = "ALLOW" / "DENY"
            # Check projection.py: data.get("decision", "DENY")
            self.decision_result = str(payload.get("decision") or payload.get("result") or "UNKNOWN")
        elif kind == "EXECUTION":
            self.has_execution = True

class IntegrityStatus(NamedTuple):
    status: str  # OK, GAP, VIOLATION
    detail: str

class IntegrityProjection(Projection):
    def __init__(self):
        self.turns: dict[str, TurnState] = defaultdict(lambda: TurnState(""))
        # Need to fix lambda to set turn_id correctly? 
        # Easier: explicit creation in feed.
        self.turns = {}

    def feed(self, event: dict[str, Any]) -> None:
        turn_id = str(event.get("turn_id"))
        if not turn_id:
            return # Skip events without turn_id?
        
        if turn_id not in self.turns:
            self.turns[turn_id] = TurnState(turn_id)
        
        self.turns[turn_id].update(event)

    def evaluate(self, state: TurnState) -> IntegrityStatus:
        if not state.has_intent:
            # Orphaned decision/execution?
            if state.has_decision or state.has_execution:
                 return IntegrityStatus("VIOLATION", "Orphaned (No Intent)")
            return IntegrityStatus("GAP", "Empty Turn") # Should not happen

        if not state.has_decision:
            if state.has_execution:
                return IntegrityStatus("VIOLATION", "EXECUTION without DECISION")
            return IntegrityStatus("GAP", "Missing DECISION")

        # Has Intent + Decision
        if state.decision_result == "ALLOW":
            if not state.has_execution:
                return IntegrityStatus("GAP", "ALLOW but no EXECUTION")
            return IntegrityStatus("OK", "Complete (ALLOW->EXEC)")
        
        elif state.decision_result == "DENY":
            if state.has_execution:
                return IntegrityStatus("VIOLATION", "EXECUTION after DENY")
            return IntegrityStatus("OK", "Complete (DENY)")
            
        else:
            return IntegrityStatus("GAP", f"Unknown Decision: {state.decision_result}")

    def render(self) -> str:
        lines = []
        lines.append("Turn Integrity Projection")
        lines.append("=========================")
        lines.append(f"{'TURN ID':<36} | {'STATUS':<10} | {'DETAIL'}")
        lines.append("-" * 80)
        
        counts = defaultdict(int)
        
        # Sort by turn_id usually implies time roughly? Or sort by first event index?
        # We can sort by turns.values() -> min index?
        # For now, simple sort by ID or insert order.
        
        sorted_turns = sorted(self.turns.values(), key=lambda t: t.events[0].get("index") if t.events else 0)

        for turn in sorted_turns:
            res = self.evaluate(turn)
            counts[res.status] += 1
            lines.append(f"{turn.turn_id:<36} | {res.status:<10} | {res.detail}")

        lines.append("-" * 80)
        lines.append("Summary:")
        for k, v in counts.items():
            lines.append(f"  {k}: {v}")
            
        return "\n".join(lines)
