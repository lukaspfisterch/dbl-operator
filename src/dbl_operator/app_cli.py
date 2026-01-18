from __future__ import annotations

import argparse
import os
import time

from .ansi_colors import detect_color_mode
from .context_declarer import ContextDeclarer
from .domain_types import Anchors, ContextRef, DomainAction
from .gateway_client import FakeGatewayClient, GatewayClient
from .http_gateway_client import HttpGatewayClient
from .intent_composer import IntentComposer
from .presenters import render_audit_view, render_decision_view, render_thread_view
from .tail_presenter import render_tail_details, render_tail_line


def _build_client() -> GatewayClient:
    base_url = os.getenv("DBL_GATEWAY_BASE_URL", "").strip()
    token = os.getenv("DBL_GATEWAY_TOKEN", "").strip() or None
    raw_timeout = os.getenv("DBL_GATEWAY_TIMEOUT_SECS", "15.0").strip()
    try:
        timeout = float(raw_timeout)
    except ValueError:
        timeout = 15.0

    if not base_url:
        return FakeGatewayClient()

    client = HttpGatewayClient(base_url=base_url, token=token, timeout_secs=timeout)
    # Admission Gate
    try:
        client.check_capabilities()
    except Exception as exc:
        raise RuntimeError(f"Gateway admission failed: {exc}") from exc
    return client


def send_intent(client: GatewayClient, args: argparse.Namespace) -> None:
    composer = IntentComposer()
    anchors = Anchors(thread_id=args.thread_id, turn_id=args.turn_id, parent_turn_id=args.parent_turn_id)
    action = DomainAction(action_type=args.intent_type, payload={})
    
    context = None
    if args.context_ref:
        refs = (ContextRef(ref_type="ref", ref_id=args.context_ref, version=None),)
        context = ContextDeclarer().declare(refs=refs, assembly_rules={})
        
    envelope = composer.compose(anchors=anchors, action=action, context_spec=context)
    
    # Mandatory correlation ID: generate if not provided
    cid = args.correlation_id or f"op-{int(time.time())}"
    
    ack = client.send_intent(envelope, correlation_id=cid)
    print(f"Accepted: correlation_id={ack.correlation_id}")


def thread_view(client: GatewayClient, args: argparse.Namespace) -> None:
    timeline = client.get_timeline(args.thread_id)
    print(render_thread_view(args.thread_id, timeline))


def decision_view(client: GatewayClient, args: argparse.Namespace) -> None:
    view = client.get_decision(args.thread_id, args.turn_id)
    print(render_decision_view(view))


def audit_view(client: GatewayClient, args: argparse.Namespace) -> None:
    events = client.get_audit(args.thread_id, turn_id=args.turn_id)
    print(render_audit_view(events))


def tail_view(client: GatewayClient, args: argparse.Namespace) -> None:
    """Stream events from gateway with color-coded output."""
    mode = detect_color_mode(args.color)
    
    try:
        for event in client.tail(since=args.since, backlog=args.backlog):
            print(render_tail_line(event, mode))
            if args.details:
                for line in render_tail_details(event, mode):
                    print(line)
    except KeyboardInterrupt:
        print("\n[tail interrupted]")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dbl-operator",
        description="Template CLI for a DBL-style Gateway operator. Requires a real GatewayClient to be useful.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    send = sub.add_parser("send-intent")
    send.add_argument("--thread-id", required=True)
    send.add_argument("--turn-id", required=True)
    send.add_argument("--parent-turn-id", default=None)
    send.add_argument("--intent-type", required=True)
    send.add_argument("--context-ref", default=None)
    send.add_argument("--correlation-id", default=None)

    tv = sub.add_parser("thread-view")
    tv.add_argument("--thread-id", required=True)

    dv = sub.add_parser("decision-view")
    dv.add_argument("--thread-id", required=True)
    dv.add_argument("--turn-id", required=True)

    av = sub.add_parser("audit-view")
    av.add_argument("--thread-id", required=True)
    av.add_argument("--turn-id", default=None)

    # NEW: tail subcommand with color support
    tail = sub.add_parser("tail", help="Stream events from gateway (SSE)")
    tail.add_argument("--since", type=int, default=None, help="Start from index > since")
    tail.add_argument("--backlog", type=int, default=None, help="Number of recent events on connect")
    tail.add_argument("--color", choices=["auto", "always", "never"], default="auto", help="Color mode")
    tail.add_argument("--details", action="store_true", help="Show additional details for DECISION events")

    args = parser.parse_args()
    client = _build_client()
    if args.command == "send-intent":
        send_intent(client, args)
    elif args.command == "thread-view":
        thread_view(client, args)
    elif args.command == "decision-view":
        decision_view(client, args)
    elif args.command == "audit-view":
        audit_view(client, args)
    elif args.command == "tail":
        tail_view(client, args)


if __name__ == "__main__":
    main()

