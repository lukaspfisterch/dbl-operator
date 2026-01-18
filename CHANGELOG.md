# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-01-19

### Added
- **Observability Suite**: 5 new commands to analyze system health and behavior.
  - `integrity`: Analyzes turn structure for gaps and invariant violations (e.g., Execution without Decision).
  - `latency`: Calculates P50/P95/P99 latency profiles for Policy and Execution phases.
  - `policy-map`: Visualizes a timeline of effective policy versions.
  - `stats`: Displays decision surface statistics (ALLOW/DENY rates per Intent Type) and top reason codes.
  - `failures`: Taxonomizes system failures (Denials, Execution Errors, Orphans).
- **Hardened Tailing**:
  - `tail` command now backfills the last N events upon connection to provide immediate context (`--backlog`, default: 20).
  - Robust auto-reconnect logic handles network protocol errors gracefully.
- **Client Resilience**: `HttpGatewayClient` now includes `get_status` and robust snapshot retrieval logic.

### Changed
- `tail` command default backlog set to 20 events.
- CLI now uses `httpx` for better async/stream handling (implicitly).

### Fixed
- Fixed an issue where `tail` would not show historical events on startup if the Gateway did not support server-side backlog parameters.
