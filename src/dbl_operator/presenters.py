from __future__ import annotations

from typing import Iterable

from .domain_types import AuditEventViewModel, DecisionViewModel, TurnSummary


def render_thread_view(thread_id: str, turns: Iterable[TurnSummary]) -> str:
    lines = [f"Thread: {thread_id}"]
    for turn in turns:
        lines.append(
            f"- turn_id={turn.turn_id} parent={turn.parent_turn_id} "
            f"context_digest={turn.context_digest} decision_digest={turn.decision_digest} "
            f"execution_status={turn.execution_status}"
        )
    return "\n".join(lines)


def render_decision_view(view: DecisionViewModel | None) -> str:
    if view is None:
        return "No decision available"
    return "\n".join(
        [
            f"Policy: {view.policy_identity}",
            f"Result: {view.result}",
            f"Reasons: {list(view.reasons)}",
            f"Context digest: {view.context_digest}",
            f"Decision digest: {view.decision_digest}",
        ]
    )


def render_audit_view(events: Iterable[AuditEventViewModel]) -> str:
    lines = []
    for event in events:
        lines.append(
            f"{event.event_kind} digest={event.event_digest} v_digest={event.v_digest} payload={event.payload}"
        )
    return "\n".join(lines)
