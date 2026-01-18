from __future__ import annotations

import json
import os
from typing import Any, Iterable, Mapping, Optional, Sequence

import httpx

from .domain_types import (
    AuditEventViewModel,
    DecisionViewModel,
    GatewayAck,
    IntentEnvelope,
    TurnSummary,
)
from .gateway_client import GatewayClient


class HttpGatewayClient(GatewayClient):
    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        timeout_secs: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout_secs
        self.headers = {"Content-Type": "application/json"}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def check_capabilities(self) -> None:
        url = f"{self.base_url}/capabilities"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            
            # Admission Gate: verify interface version
            if data.get("interface_version") != 2:
                raise RuntimeError(f"Gateway interface mismatch. Expected 2, got {data.get('interface_version')}")
                
            surfaces_raw = data.get("surfaces")
            if isinstance(surfaces_raw, dict):
                enabled = {str(k) for k, v in surfaces_raw.items() if v}
            elif isinstance(surfaces_raw, list):
                enabled = set(surfaces_raw)
            else:
                enabled = set()

            # Enforce required surfaces defined in the contract
            # Note: 'capabilities' itself is not listed - if we got here, it works
            required = {"snapshot", "ingress_intent", "tail"}
            missing = sorted(required - enabled)
            if missing:
                raise RuntimeError(f"Gateway missing required surfaces: {missing}")

    def send_intent(self, envelope: IntentEnvelope, correlation_id: str) -> GatewayAck:
        url = f"{self.base_url}/ingress/intent"
        # Map IntentEnvelope to Gateway's expected shape (v2)
        payload: dict[str, Any] = {
            "interface_version": 2,
            "correlation_id": correlation_id,
            "payload": {
                "stream_id": "default",
                "lane": "default",
                "actor": "operator",
                "intent_type": envelope.intent_type,
                "thread_id": envelope.anchors.thread_id,
                "turn_id": envelope.anchors.turn_id,
                "parent_turn_id": envelope.anchors.parent_turn_id,
                "payload": envelope.payload,
                "requested_model_id": None,
                "inputs": None,
            },
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            return GatewayAck(correlation_id=data["correlation_id"])

    def get_timeline(self, thread_id: str) -> Sequence[TurnSummary]:
        events = self._fetch_events()
        # Filter by thread_id and group by turn_id
        thread_events = [e for e in events if e.get("thread_id") == thread_id]
        
        turns_map: dict[str, list[dict[str, Any]]] = {}
        for e in thread_events:
            tid = e["turn_id"]
            if tid not in turns_map:
                turns_map[tid] = []
            turns_map[tid].append(e)
            
        summaries = []
        # Sort turns by the index of their first event to preserve order
        sorted_turn_ids = sorted(turns_map.keys(), key=lambda tid: turns_map[tid][0]["index"])
        
        for tid in sorted_turn_ids:
            events_in_turn = turns_map[tid]
            first_event = events_in_turn[0]
            
            # Find digests in any event of the turn (as fallback if turn object is missing)
            ctx_digest = None
            dec_digest = None
            for e in events_in_turn:
                p = e.get("payload", {})
                if not ctx_digest:
                    ctx_digest = p.get("context_digest")
                if not dec_digest:
                    if e.get("kind") == "DECISION":
                        dec_digest = e.get("digest")
            
            summaries.append(TurnSummary(
                turn_id=tid,
                parent_turn_id=first_event.get("parent_turn_id"),
                context_digest=ctx_digest,
                decision_digest=dec_digest,
                execution_status=None
            ))
        return summaries

    def get_decision(self, thread_id: str, turn_id: str) -> DecisionViewModel | None:
        events = self._fetch_events()
        # Find DECISION event for the specific turn
        for e in events:
            if (e.get("thread_id") == thread_id and 
                e.get("turn_id") == turn_id and 
                e.get("kind") == "DECISION"):
                
                p = e.get("payload", {})
                return DecisionViewModel(
                    policy_identity={
                        "id": p.get("policy_id"),
                        "version": p.get("policy_version")
                    },
                    result=p.get("decision", "UNKNOWN"),
                    reasons=p.get("reason_codes", []),
                    context_digest=p.get("context_digest"),
                    decision_digest=e.get("digest")
                )
        return None

    def get_audit(self, thread_id: str, turn_id: str | None = None) -> Sequence[AuditEventViewModel]:
        events = self._fetch_events()
        audit_events = []
        for e in events:
            if e.get("thread_id") != thread_id:
                continue
            if turn_id is not None and e.get("turn_id") != turn_id:
                continue
                
            audit_events.append(AuditEventViewModel(
                event_kind=e.get("kind", "UNKNOWN"),
                # Use the authoritative event digest
                event_digest=e.get("digest"),
                v_digest=None,
                payload=e.get("payload", {})
            ))
        return audit_events

    def tail(
        self,
        since: int | None = None,
        backlog: int | None = None,
    ) -> Iterable[dict]:
        """
        Stream events from /tail endpoint using SSE.

        Args:
            since: Start streaming from index > since
            backlog: Number of recent events to emit on connect

        Yields:
            Event dicts from the SSE stream
        """
        params: dict[str, str] = {}
        if since is not None:
            params["since"] = str(since)
        if backlog is not None:
            params["backlog"] = str(backlog)

        url = f"{self.base_url}/tail"
        headers = dict(self.headers)
        headers["Accept"] = "text/event-stream"

        # Use no timeout for streaming connection
        with httpx.Client(timeout=None, headers=headers) as client:
            with client.stream("GET", url, params=params) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload:
                        continue
                    try:
                        yield json.loads(payload)
                    except json.JSONDecodeError:
                        continue

    def _fetch_events(self, limit: int = 1000) -> list[dict[str, Any]]:
        # Fetching snapshots to derive views, as no direct timeline surface is documented.
        url = f"{self.base_url}/snapshot"
        params = {"limit": limit}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, params=params, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("events", [])

