# DBL Operator

The DBL Operator is a **cockpit-style client** for interacting with a DBL-style Gateway.

It is an **observer with controlled intervention capability**:
- it prepares and submits intents,
- declares context references,
- and renders views derived strictly from Gateway events.

All **normative logic** lives exclusively in the **Gateway**:
- Policy evaluation
- Decision making
- Digest computation
- Boundary enforcement

The operator never makes decisions and never owns authoritative state.

---

## Design Stance
**Operator = Client, not Governor**

- **Observes** Gateway outputs as the single source of truth.
- **Submits** intents but never computes digests or applies policy logic locally.
- **Respects** boundaries: if the Gateway rejects or denies an intent, the Operator reports it verbatim.
- **Does not compensate**: no retries, no heuristics, no “helpful” fixes.
- **Zero Internal State**: the Operator never reaches into Gateway internals.

If something looks wrong, the Operator does not correct it.  
It exposes it.

---

## What this is
- A minimal set of datatypes for **anchors** (`thread_id`, `turn_id`, `parent_turn_id`).
- A deterministic **intent composer** and **context declarer**.
- A Gateway client interface (HTTP client plus Fake client for tests).
- Boring presenters and a thin CLI that render Gateway state exactly as emitted.

---

## What this is not
- No policy logic.
- No boundary enforcement.
- Not an agent.
- Not a planner.
- Not a UI product.
- Not a state store.

---

## Installation
Clone the repository and install in editable mode:

```bash
git clone https://github.com/lukaspfisterch/dbl-operator.git
cd dbl-operator
pip install -e .
```

This installs the `dbl-operator` command and ensures imports resolve correctly for tests.

## Environment Variables
If no Gateway URL is provided, the operator falls back to a `FakeGatewayClient`.
This is intentional and useful for wiring tests and local development.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DBL_GATEWAY_BASE_URL` | Base URL of the Gateway | empty → Fake client |
| `DBL_GATEWAY_TOKEN` | Bearer token (OIDC/Auth) | none |
| `DBL_GATEWAY_TIMEOUT_SECS` | Request timeout | 15.0 |

**Example (Bash/Zsh):**

```bash
export DBL_GATEWAY_BASE_URL=http://127.0.0.1:8010
```

**Example (PowerShell):**

```powershell
$env:DBL_GATEWAY_BASE_URL = "http://127.0.0.1:8010"
```

## CLI Usage

### Send an Intent
Submits an intent to the Gateway.
A successful call returns `202 Accepted`, meaning the intent was persisted and queued for processing.

```bash
dbl-operator send-intent \
  --thread-id t-1 \
  --turn-id turn-1 \
  --intent-type PING \
  --correlation-id my-unique-id
```

**Note**: Not all intent types necessarily result in a DECISION or EXECUTION.
That behavior is defined entirely by the Gateway and its runners.

### View Thread Timeline
Renders a derived view of all turns observed for a specific thread.

```bash
dbl-operator thread-view --thread-id t-1
```

### View Decision for a Turn
Shows the decision event produced by the Gateway for a specific turn, if available.

```bash
dbl-operator decision-view --thread-id t-1 --turn-id turn-1
```

### Audit Events
Lists all raw Gateway events for a thread.

```bash
dbl-operator audit-view --thread-id t-1
```

Filter by turn:

```bash
dbl-operator audit-view --thread-id t-1 --turn-id turn-1
```

### Live Event Stream (Tail)
Stream Gateway events in real time with color-coded output and automatic reconnect.

```bash
dbl-operator tail
dbl-operator tail --details
dbl-operator tail --since 100
dbl-operator tail --only DECISION
dbl-operator tail --only INTENT,DECISION
dbl-operator tail --grep "thread-123"
dbl-operator tail --only DECISION --result DENY
dbl-operator tail --result ALLOW --details
dbl-operator tail --color always
```

**Options:**
- `--since N`: Start from index greater than N
- `--backlog N`: Request recent events on connect (if supported by the Gateway)
- `--color auto|always|never`: Color mode
- `--details`: Show DECISION metadata
- `--only KIND[,KIND]`: Filter by event kind
- `--result ALLOW|DENY`: Filter DECISION events
- `--grep PATTERN`: Regex filter

**Color coding:**
- **INTENT**: Cyan
- **DECISION (ALLOW)**: Green (bold)
- **DECISION (DENY)**: Red (bold)
- **EXECUTION**: Gray (dim)
- **PROOF**: Magenta

**Production behavior:**
- Automatic reconnect with exponential backoff
- Resume from last seen index
- Immediate output (flush enabled)
- Stop with Ctrl+C.

## Observability & Analysis
The operator provides deterministic projections derived solely from Gateway events.

### Turn Integrity
Verifies protocol completeness per turn.

```bash
dbl-operator integrity
```

### Latency Profiling
Computes P50, P95 and P99 latencies across policy and execution phases.

```bash
dbl-operator latency
```

### Policy Timeline
Displays which policy version was active during which time window.

```bash
dbl-operator policy-map
```

### Decision Statistics
Aggregates ALLOW/DENY outcomes per intent type and reason code.

```bash
dbl-operator stats
```

### Failure Analysis
Classifies observed failures without interpretation or blame.

```bash
dbl-operator failures
```

## Expected Semantics
- **202 Accepted** means persisted and queued, not decided.
- **DENY** is a valid and correct outcome.
- **No EXECUTION after DENY** is expected.
- All views are derived strictly from events.
- The Operator never invents or infers state.

## Testing
Run the test suite:

```bash
python -m pytest
```

## Summary
The DBL Operator is **intentionally boring**.

It is deterministic, transparent and contract-driven.
It cannot drift silently because it does not own policy.

**If something looks wrong, the problem is upstream.
The operator’s job is to show you exactly that.**