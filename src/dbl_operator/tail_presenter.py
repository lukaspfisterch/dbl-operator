"""Color-coded output renderer for tail command."""
from __future__ import annotations

from typing import Any

from .ansi_colors import (
    ColorMode,
    FG_CYAN,
    FG_GRAY,
    FG_GREEN,
    FG_MAGENTA,
    FG_RED,
    FG_YELLOW,
    style,
)

__all__ = ["render_tail_line", "render_tail_details"]


def _event_color(event: dict[str, Any]) -> tuple[int | None, bool, bool]:
    """
    Determine color, bold, and dim settings for an event.

    Returns:
        Tuple of (fg_color, is_bold, is_dim)
    """
    kind = str(event.get("kind", "")).upper()

    if kind == "DECISION":
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        result = str(payload.get("result", payload.get("decision", ""))).upper()
        if result == "DENY":
            return (FG_RED, True, False)
        if result == "ALLOW":
            return (FG_GREEN, True, False)
        return (FG_YELLOW, True, False)

    if kind == "INTENT":
        return (FG_CYAN, True, False)

    if kind == "EXECUTION":
        return (FG_GRAY, False, True)

    if kind == "PROOF":
        return (FG_MAGENTA, False, False)

    return (None, False, False)


def render_tail_line(event: dict[str, Any], mode: ColorMode) -> str:
    """
    Render a single event line for tail output.

    Args:
        event: Event dict from SSE stream
        mode: Color mode configuration

    Returns:
        Formatted string for terminal output
    """
    fg, bold, dim = _event_color(event)

    idx = event.get("index", "?")
    thread_id = event.get("thread_id", "")[:12]
    turn_id = event.get("turn_id", "")[:12]
    corr = event.get("correlation_id", "")[:16]
    kind = event.get("kind", "")

    # For DECISION events, include ALLOW/DENY in the kind field
    if kind == "DECISION":
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        result = str(payload.get("result", payload.get("decision", ""))).upper()
        if result in ("ALLOW", "DENY"):
            kind = f"DECISION/{result}"

    base = f"{idx:>6}  {kind:<15}  t={thread_id}  turn={turn_id}  c={corr}"
    return style(base, mode=mode, fg=fg, bold=bold, dim=dim)


def _short_digest(digest: str | None, length: int = 16) -> str:
    """Shorten a digest, stripping 'sha256:' prefix."""
    if not digest:
        return ""
    # Remove common prefixes
    for prefix in ("sha256:", "sha512:", "blake2b:"):
        if digest.startswith(prefix):
            digest = digest[len(prefix):]
            break
    return digest[:length]


def render_tail_details(event: dict[str, Any], mode: ColorMode) -> list[str]:
    """
    Render additional detail lines for DECISION events.

    Args:
        event: Event dict from SSE stream
        mode: Color mode configuration

    Returns:
        List of additional lines to print (may be empty)
    """
    kind = str(event.get("kind", "")).upper()
    if kind != "DECISION":
        return []

    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    reasons = payload.get("reasons") or payload.get("reason_codes") or []
    boundary = payload.get("boundary") if isinstance(payload.get("boundary"), dict) else {}

    out: list[str] = []

    if reasons:
        reason_str = ", ".join(str(r) for r in reasons) if isinstance(reasons, list) else str(reasons)
        out.append("       " + style(f"reasons: {reason_str}", mode=mode, fg=FG_GRAY, dim=True))

    config_digest = boundary.get("context_config_digest")
    if config_digest:
        short = _short_digest(config_digest, 16)
        out.append("       " + style(f"config: {short}...", mode=mode, fg=FG_GRAY, dim=True))

    context_digest = payload.get("context_digest")
    if context_digest:
        short = _short_digest(context_digest, 16)
        out.append("       " + style(f"context: {short}...", mode=mode, fg=FG_GRAY, dim=True))

    return out
