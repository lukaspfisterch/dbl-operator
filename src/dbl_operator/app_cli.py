from __future__ import annotations

import argparse
import os
import re
import sys
import time

from .ansi_colors import detect_color_mode, strip_ansi
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
    """Stream events from gateway with color-coded output and auto-reconnect."""
    import signal
    import threading
    
    mode = detect_color_mode(args.color)
    
    # One-time warning if colors disabled in auto mode
    if args.color == "auto" and not mode.enabled:
        print("[colors disabled: piped output or NO_COLOR set]", file=sys.stderr, flush=True)
    
    # Compile grep pattern if provided
    grep_pattern = None
    if args.grep:
        try:
            grep_pattern = re.compile(args.grep, re.IGNORECASE)
        except re.error as e:
            print(f"Invalid grep pattern: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Parse --only filter
    only_kinds: set[str] | None = None
    if args.only:
        only_kinds = {k.strip().upper() for k in args.only.split(",")}
    
    # Parse --result filter (for DECISION events)
    result_filter: str | None = None
    if args.result:
        result_filter = args.result.strip().upper()
        if result_filter not in ("ALLOW", "DENY"):
            print(f"Invalid --result value: {args.result}. Must be ALLOW or DENY.", file=sys.stderr)
            sys.exit(1)
    
    # Graceful shutdown flag
    stop_event = threading.Event()
    
    def handle_signal(signum: int, frame: object) -> None:
        stop_event.set()
    
    # Register signal handlers (wrapped for embedded environments)
    try:
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        if hasattr(signal, 'SIGBREAK'):  # Windows-specific
            signal.signal(signal.SIGBREAK, handle_signal)  # type: ignore[attr-defined]
    except (ValueError, OSError):
        # Signal handling not available in this environment
        pass
    
    last_index: int | None = args.since
    reconnect_delay = 1.0
    max_reconnect_delay = 30.0
    event_count = 0
    
    try:
        while not stop_event.is_set():
            try:
                for event in client.tail(since=last_index, backlog=args.backlog):
                    if stop_event.is_set():
                        break
                        
                    # Track last seen index for reconnect
                    event_index = event.get("index")
                    if isinstance(event_index, int):
                        last_index = event_index
                    elif isinstance(event_index, str) and event_index.isdigit():
                        last_index = int(event_index)
                    
                    # Apply --only filter
                    event_kind = str(event.get("kind", "")).upper()
                    if only_kinds and event_kind not in only_kinds:
                        continue
                    
                    # Apply --result filter (only for DECISION events)
                    if result_filter and event_kind == "DECISION":
                        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
                        event_result = str(payload.get("result", payload.get("decision", ""))).upper()
                        if event_result != result_filter:
                            continue
                    
                    # Render line
                    line = render_tail_line(event, mode)
                    
                    # Apply --grep filter (on uncolored text to avoid ANSI interference)
                    if grep_pattern:
                        plain_line = strip_ansi(line) if mode.enabled else line
                        if not grep_pattern.search(plain_line):
                            continue
                    
                    print(line, flush=True)
                    event_count += 1
                    if args.details:
                        for detail_line in render_tail_details(event, mode):
                            print(detail_line, flush=True)
                    
                    # Reset reconnect delay on successful event
                    reconnect_delay = 1.0
                    
            except (ConnectionError, OSError) as e:
                if stop_event.is_set():
                    break
                # Auto-reconnect with exponential backoff
                print(f"\n[connection lost: {e}, reconnecting in {reconnect_delay:.0f}s...]", flush=True)
                # Use wait with timeout so we can check stop_event
                if stop_event.wait(timeout=reconnect_delay):
                    break
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                continue
                
    except KeyboardInterrupt:
        pass
    
    print(f"\n[tail stopped, {event_count} events received]", flush=True)


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

    # tail subcommand with production hardening
    tail = sub.add_parser("tail", help="Stream events from gateway (SSE)")
    tail.add_argument("--since", type=int, default=None, help="Start from index > since")
    tail.add_argument("--backlog", type=int, default=None, help="Number of recent events on connect")
    tail.add_argument("--color", choices=["auto", "always", "never"], default="auto", help="Color mode (default: auto)")
    tail.add_argument("--details", action="store_true", help="Show additional details for DECISION events")
    tail.add_argument("--only", type=str, default=None, help="Filter by event kind (comma-separated: INTENT,DECISION,EXECUTION)")
    tail.add_argument("--result", type=str, default=None, help="Filter DECISION events by result (ALLOW or DENY)")
    tail.add_argument("--grep", type=str, default=None, help="Filter output by regex pattern")

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

