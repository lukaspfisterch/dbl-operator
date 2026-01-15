from __future__ import annotations

from dbl_operator.context_declarer import ContextDeclarer
from dbl_operator.domain_types import Anchors, ContextRef, ContextSpec, DomainAction
from dbl_operator.intent_composer import IntentComposer


def test_context_spec_deterministic() -> None:
    refs = (ContextRef(ref_type="doc", ref_id="a", version="1"),)
    rules = {"mode": "all"}
    spec_a = ContextDeclarer().declare(refs=refs, assembly_rules=rules)
    spec_b = ContextDeclarer().declare(refs=refs, assembly_rules=rules)
    assert spec_a == spec_b
    assert isinstance(spec_a, ContextSpec)


def test_intent_envelope_pure_and_stable() -> None:
    anchors = Anchors(thread_id="t", turn_id="1", parent_turn_id=None)
    action = DomainAction(action_type="demo.action", payload={"value": 1})
    spec = ContextDeclarer().declare(refs=(), assembly_rules={"mode": "none"})
    envelope = IntentComposer().compose(anchors=anchors, action=action, context_spec=spec)
    assert envelope.anchors == anchors
    assert envelope.intent_type == "demo.action"
    assert envelope.payload["value"] == 1
    assert envelope.context_spec == spec


def test_anchors_preserved() -> None:
    anchors = Anchors(thread_id="thread-123", turn_id="turn-1", parent_turn_id="parent-0")
    action = DomainAction(action_type="demo.action", payload={})
    envelope = IntentComposer().compose(anchors=anchors, action=action, context_spec=None)
    assert envelope.anchors.thread_id == "thread-123"
    assert envelope.anchors.turn_id == "turn-1"
    assert envelope.anchors.parent_turn_id == "parent-0"
