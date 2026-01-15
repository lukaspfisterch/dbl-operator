from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class Anchors:
    thread_id: str
    turn_id: str
    parent_turn_id: str | None


@dataclass(frozen=True)
class DomainAction:
    action_type: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class ContextRef:
    ref_type: str
    ref_id: str
    version: str | None


@dataclass(frozen=True)
class ContextSpec:
    declared_refs: Sequence[ContextRef]
    assembly_rules: Mapping[str, Any]


@dataclass(frozen=True)
class IntentEnvelope:
    anchors: Anchors
    intent_type: str
    payload: Mapping[str, Any]
    context_spec: ContextSpec | None


@dataclass(frozen=True)
class GatewayAck:
    correlation_id: str


@dataclass(frozen=True)
class TurnSummary:
    turn_id: str
    parent_turn_id: str | None
    context_digest: str | None
    decision_digest: str | None
    execution_status: str | None


@dataclass(frozen=True)
class DecisionViewModel:
    policy_identity: Mapping[str, Any]
    result: str
    reasons: Sequence[str]
    context_digest: str | None
    decision_digest: str | None


@dataclass(frozen=True)
class AuditEventViewModel:
    event_kind: str
    event_digest: str | None
    v_digest: str | None
    payload: Mapping[str, Any]
