# DBL Operator

The DBL Operator is a **cockpit-style client** for interacting with a DBL-style Gateway. It is an observer with intervention capability: it prepares intents, declares context, and renders views derived from Gateway events.

All normative logic lives exclusively in the **Gateway**:
- Policy evaluation
- Decision making
- Digest computation
- Boundary enforcement

The operator never makes decisions and never owns authoritative state.

## Design Stance
**Operator = Client, not Governor**

- **Observes** Gateway outputs as the single source of truth.
- **Submits** intents but never computes digests or applies policy logic locally.
- **Respects** boundaries: if the Gateway rejects or denies an intent, the Operator reports it as-is. It does not "help", "retry", or "fix" outcomes.
- **Zero-Internal-State**: Never reaches into Gateway internals.

## What this is
- A minimal set of datatypes for **anchors** (`thread_id`, `turn_id`, `parent_turn_id`), **intents**, and **context declarations**.
- A deterministic intent composer and context declarer.
- A Gateway client interface (HTTP client + Fake client for tests).
- Boring presenters and a thin CLI that render Gateway state exactly as-is.

## What this is not
- No policy logic or boundary enforcement.
- Not an agent or a planner.
- Not a UI product or a state store.

## Installation
Clone the repository and install in editable mode:

```bash
git clone https://github.com/lukaspfisterch/dbl-operator.git
cd dbl-operator
pip install -e .
```

This installs the `dbl-operator` command and ensures imports resolve correctly for tests.

## Environment Variables
If no Gateway URL is provided, the operator falls back to a `FakeGatewayClient` (useful for wiring tests).

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DBL_GATEWAY_BASE_URL` | Base URL of the Gateway | (empty) → Fake client |
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
Submits an intent to the Gateway. A successful call returns `202 Accepted`, meaning the intent was queued for processing.

```bash
dbl-operator send-intent \
  --thread-id t-1 \
  --turn-id turn-1 \
  --intent-type PING \
  --correlation-id my-unique-id
```

### View Thread Timeline
Renders a derived view of all turns observed for a specific thread.

```bash
dbl-operator thread-view --thread-id t-1
```

### View Decision for a Turn
Shows the decision event produced by the Gateway for a specific turn.

```bash
dbl-operator decision-view --thread-id t-1 --turn-id turn-1
```

### Audit Events
Lists all raw Gateway events (INTENT, DECISION, EXECUTION) for a thread.

```bash
dbl-operator audit-view --thread-id t-1
# Or filter by turn
dbl-operator audit-view --thread-id t-1 --turn-id turn-1
```

### Live Event Stream (Tail)
Stream Gateway events in real-time with color-coded output and auto-reconnect.

```bash
# Stream all events (color auto-detected)
dbl-operator tail

# With details for DECISION events
dbl-operator tail --details

# Start from a specific index
dbl-operator tail --since 100

# Filter by event kind
dbl-operator tail --only DECISION
dbl-operator tail --only INTENT,DECISION

# Filter by regex pattern
dbl-operator tail --grep "thread-123"
dbl-operator tail --grep "DENY"

# Force color output
dbl-operator tail --color always
```

**Options:**
- `--since N`: Start from index > N
- `--backlog N`: Number of recent events on connect
- `--color auto|always|never`: Color mode (default: auto, no color when piped)
- `--details`: Show additional details for DECISION events
- `--only KIND[,KIND]`: Filter by event kind (INTENT, DECISION, EXECUTION)
- `--grep PATTERN`: Filter output by regex pattern

**Color coding:**
- **INTENT**: Cyan
- **DECISION (ALLOW)**: Green (bold)
- **DECISION (DENY)**: Red (bold)
- **EXECUTION**: Gray (dim)
- **PROOF**: Magenta

**Production features:**
- Auto-reconnect with exponential backoff on connection loss
- Remembers last seen index for seamless resume
- Immediate output (flush=True)

**Note**: Use Ctrl+C to stop tailing.

## Expected Semantics
- **202 Accepted**: Intent persisted and queued; no decision yet.
- **DENY**: A valid, correct outcome from the Gateway.
- **No EXECUTION after DENY**: Expected behavior.
- **Derived Views**: Views are always derived from events; the operator never invents/infers state.

## Testing
Run tests via `pytest` to verify the components:

```bash
python -m pytest
```

---

## Summary
The DBL Operator is **intentionally boring**. It is deterministic, transparent, and contract-driven. It is incapable of silent policy drift because it doesn't have a policy to drift with. 

**If something looks wrong, the problem is upstream. The operator’s job is to show you exactly that.**