from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .domain_types import Anchors, ContextSpec, DomainAction, IntentEnvelope


@dataclass(frozen=True)
class IntentComposer:
    def compose(
        self,
        *,
        anchors: Anchors,
        action: DomainAction,
        context_spec: ContextSpec | None = None,
    ) -> IntentEnvelope:
        return IntentEnvelope(
            anchors=anchors,
            intent_type=action.action_type,
            payload=dict(action.payload),
            context_spec=context_spec,
        )
