from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .domain_types import (
    AuditEventViewModel,
    DecisionViewModel,
    GatewayAck,
    IntentEnvelope,
    TurnSummary,
)


class GatewayClient(Protocol):
    def check_capabilities(self) -> None: ...

    def send_intent(self, envelope: IntentEnvelope, correlation_id: str) -> GatewayAck: ...

    def get_timeline(self, thread_id: str) -> Sequence[TurnSummary]: ...

    def get_decision(self, thread_id: str, turn_id: str) -> DecisionViewModel | None: ...

    def get_audit(self, thread_id: str, turn_id: str | None = None) -> Sequence[AuditEventViewModel]: ...


@dataclass
class FakeGatewayClient:
    def check_capabilities(self) -> None:
        pass

    def send_intent(self, envelope: IntentEnvelope, correlation_id: str) -> GatewayAck:
        return GatewayAck(correlation_id=correlation_id)

    def get_timeline(self, thread_id: str) -> Sequence[TurnSummary]:
        return ()

    def get_decision(self, thread_id: str, turn_id: str) -> DecisionViewModel | None:
        return None

    def get_audit(self, thread_id: str, turn_id: str | None = None) -> Sequence[AuditEventViewModel]:
        return ()
