# Operator-Gateway Contract (v1)

This document serves as the **Single Source of Truth (SSoT)** for the interaction between the Operator and the `deterministic-ai-gateway`.
Contract doc v1 covers Gateway interface v2.

## 1. Interface & Capabilities

- **Interface Version**: **2** (Must be included in all `IntentEnvelope` requests).
- **Capabilities Surface**:
  - `ingress_intent`: **Supported** (POST `/ingress/intent`)
  - `snapshot`: **Supported** (GET `/snapshot`)
  - `tail`: **Supported** (GET `/tail`)
  - `capabilities`: **Supported** (GET `/capabilities`)
  - `events`: **Not Supported**

## 2. Request/Response Shapes (Normative)

### 2.1 Send Intent
- **Endpoint**: `POST /ingress/intent`
- **Correlation ID**: Mandatory, non-empty string. Must be provided by the caller or CLI.
- **Request Shape** (`IntentEnvelope`):
```json
{
  "interface_version": 2,
  "correlation_id": "string",
  "payload": {
    "stream_id": "string",
    "lane": "string",
    "actor": "string",
    "intent_type": "string",
    "thread_id": "string",
    "turn_id": "string",
    "parent_turn_id": "string | null",
    "payload": "object",
    "requested_model_id": "string | null",
    "inputs": "object | null"
  }
}
```

### 2.2 Snapshot / Fetch Events
- **Snapshot Endpoint**: `GET /snapshot?limit={limit}&offset={offset}&stream_id={stream_id}&lane={lane}`
- **Event Shape** (`EventRecord`):
```json
{
  "index": "number",
  "kind": "INTENT | DECISION | EXECUTION",
  "thread_id": "string",
  "turn_id": "string",
  "parent_turn_id": "string | null",
  "lane": "string",
  "actor": "string",
  "intent_type": "string",
  "stream_id": "string",
  "correlation_id": "string",
  "payload": "object",
  "digest": "string",
  "canon_len": "number",
  "is_authoritative": "boolean"
}
```

## 3. Deterministic Digest Rules

- **Observer Perspective**: The operator does not compute digests. It treats `digest` as the authoritative identifier provided by the gateway.
- **Mappings**:
  - `DECISION` event `digest` -> mapped to `decision_digest` in ViewModels.
  - `EXECUTION` event `payload.trace_digest` -> can be found in payload, but Audit uses the top-level `digest`.
  - No fallbacks or synthesized digests.

## 4. Error Shapes

- **Standard Error**:
```json
{
  "ok": false,
  "reason_code": "string",
  "detail": "string"
}
```

## 5. Mapping to Operator View Models

**Note**: Thread/Turn Views werden momentan aus Snapshot/Tail abgeleitet, weil keine Thread Timeline Surface vorhanden ist.

- **TurnSummary**: Aggregated from `EventRecord`s sharing the same `turn_id`.
- **DecisionViewModel**: Derived from the `DECISION` event.
- **AuditEventViewModel**: Derived from any `EventRecord`. `event_digest` uses the gateway's `digest` field for the specific event.

## 6. Auth Requirements
- **OIDC Mode**: Uses `Authorization: Bearer <token>`.
- **Dev Mode**: Gateway may accept `x-dev-actor`, `x-dev-roles` headers (Optional).
