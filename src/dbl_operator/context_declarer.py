from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .domain_types import ContextRef, ContextSpec


@dataclass(frozen=True)
class ContextDeclarer:
    def declare(self, *, refs: Sequence[ContextRef], assembly_rules: Mapping[str, object]) -> ContextSpec:
        return ContextSpec(declared_refs=tuple(refs), assembly_rules=dict(assembly_rules))
