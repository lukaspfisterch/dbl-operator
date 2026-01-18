"""ANSI color utilities for terminal output."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

__all__ = [
    "ColorMode",
    "detect_color_mode",
    "style",
    "strip_ansi",
    "FG_RED",
    "FG_GREEN",
    "FG_YELLOW",
    "FG_BLUE",
    "FG_MAGENTA",
    "FG_CYAN",
    "FG_GRAY",
]

CSI = "\x1b["
ANSI_ESCAPE_RE = None  # Lazy compiled


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    import re
    global ANSI_ESCAPE_RE
    if ANSI_ESCAPE_RE is None:
        ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-9;]*m')
    return ANSI_ESCAPE_RE.sub('', text)

# Foreground colors
FG_RED = 31
FG_GREEN = 32
FG_YELLOW = 33
FG_BLUE = 34
FG_MAGENTA = 35
FG_CYAN = 36
FG_GRAY = 90


@dataclass(frozen=True)
class ColorMode:
    """Color mode configuration."""

    enabled: bool


def detect_color_mode(mode: str) -> ColorMode:
    """
    Detect whether colors should be enabled.

    Args:
        mode: "auto", "always", or "never"

    Returns:
        ColorMode with enabled flag set appropriately.
    """
    m = (mode or "auto").lower().strip()

    if m == "never":
        return ColorMode(enabled=False)
    if m == "always":
        return ColorMode(enabled=True)

    # Auto-detect
    if not sys.stdout.isatty():
        return ColorMode(enabled=False)

    if os.getenv("NO_COLOR"):
        return ColorMode(enabled=False)

    return ColorMode(enabled=True)


def _sgr(*codes: int) -> str:
    """Generate SGR (Select Graphic Rendition) escape sequence."""
    return f"{CSI}{';'.join(str(c) for c in codes)}m"


def style(
    text: str,
    *,
    mode: ColorMode,
    fg: int | None = None,
    bold: bool = False,
    dim: bool = False,
) -> str:
    """
    Apply ANSI styles to text.

    Args:
        text: Text to style
        mode: ColorMode determining if styling is enabled
        fg: Foreground color code (e.g., FG_RED)
        bold: Apply bold styling
        dim: Apply dim styling

    Returns:
        Styled text (or original if colors disabled)
    """
    if not mode.enabled:
        return text

    codes: list[int] = []
    if bold:
        codes.append(1)
    if dim:
        codes.append(2)
    if fg is not None:
        codes.append(fg)

    if not codes:
        return text

    return f"{_sgr(*codes)}{text}{_sgr(0)}"
