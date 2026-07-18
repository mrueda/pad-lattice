# Socket Protocol

Pad-Lattice clients communicate with the daemon through **Wire Protocol 1**:
newline-delimited JSON over a local Unix stream socket. It carries agent state,
session lifecycle, status, leases, capabilities, and targeted actions.

This contract is separate from [Visual Protocol 1](../usage/visual-language.md),
[device profile schema 1](../technical-details/device-profiles.md), and the
browser-facing Web Surface Protocol. The wire protocol moves agent semantics;
it does not describe LEDs, browser pixels, or MIDI addresses.

:::tip Prefer the Python client

Python integrations should use `PadLatticeClient`. It supplies protocol
versions, framing, typed identities, states, actions, and bounded reads. Use raw
JSON only when integrating another language or transport adapter.

:::

## Python Client

```python
from pad_lattice import AgentIdentity, AgentState, PadLatticeClient

agent = AgentIdentity("my-agent", "session-42")
client = PadLatticeClient()
client.report_state(
    AgentState.RUNNING,
    agent=agent,
    metadata={"label": "indexer"},
)
```

Subscribe to actions with a context manager so disconnecting removes the
advertised capabilities:

```python
from pad_lattice import ControlAction

with client.subscribe_actions(
    agent,
    (ControlAction.STOP,),
    request_id="task-7",
    one_shot=True,
) as subscription:
    event = subscription.receive()
```

The public client also provides `status()`, `ping()`, and `end_session()`.

## Transport

The default socket path is resolved in this order:

1. `PAD_LATTICE_SOCKET`
2. `$XDG_RUNTIME_DIR/pad-lattice.sock`
3. `/tmp/pad-lattice-<uid>.sock`

The daemon creates the socket with mode `0600`. It is a local control channel,
not a network service. Do not proxy it or share it with untrusted processes.

Every frame is one UTF-8 JSON object followed by `\n`, with a maximum encoded
size of 64 KiB. Every command and response includes the integer wire version:

```json
{"protocol":1,"type":"ping"}
```

A missing or unsupported version receives an `unsupported_protocol` error.

## Domain Values

An agent is identified only by the pair `(backend, session_id)`:

```json
{"backend":"codex","session_id":"019f28ff-..."}
```

Additional non-empty string fields on an agent in a state message are display
metadata, not identity.

| States | Actions |
| --- | --- |
| `running` | `stop` |
| `waiting_for_reply` | None |
| `user_typing` | None |
| `waiting_for_approval` | `approve`, `reject` |
| `success` | None |
| `error` | `retry` |
| `cancelled` | `retry` |

An action is available only when the state allows it **and** a connected client
advertises that capability for the selected agent.

## Message Summary

| Client message | Response | Connection lifetime |
| --- | --- | --- |
| `state` | Optional `state_ack` | Usually short |
| `session_end` | None | Short |
| `status` | `status` | Short |
| `ping` | `pong` | Short |
| `subscribe_actions` | Zero or more `action` events | Long-lived |
| `session_lease` | `session_lease_ack`, then optional binding updates | Process lifetime |
| `preview` | `preview_ack` | Temporary diagnostic connection |
| `preview_end` | `preview_end_ack` | Same preview connection |

## State and Lifecycle

Send a state update:

```json
{
  "protocol": 1,
  "type": "state",
  "state": "running",
  "agent": {
    "backend": "codex",
    "session_id": "019f28ff-...",
    "label": "implementation"
  },
  "lease_id": "09f3...",
  "reply": true
}
```

`agent` defaults to `local/default` for manual clients. `lease_id` binds the
state to a launcher lease. With `reply: true`, the daemon returns a `state_ack`
containing the identity, state, zero-based slot, one-based Scene, accent,
selection, lease status, and label. A slot and Scene are `null` in overflow.

Remove a manually managed session explicitly:

```json
{
  "protocol": 1,
  "type": "session_end",
  "agent": {"backend":"codex","session_id":"019f28ff-..."}
}
```

Ending the selected session clears selection. The daemon never silently
retargets another agent.

## Targeted Actions

Keep this connection open while a client can consume the advertised actions:

```json
{
  "protocol": 1,
  "type": "subscribe_actions",
  "agent": {"backend":"codex","session_id":"019f28ff-..."},
  "actions": ["approve", "reject"],
  "request_id": "c42a...",
  "one_shot": true
}
```

There is no subscription acknowledgement. Disconnecting immediately removes
its capabilities and darkens controls that no other subscriber can consume.

A matching press produces one event:

```json
{
  "protocol": 1,
  "type": "action",
  "action": "approve",
  "agent": {"backend":"codex","session_id":"019f28ff-..."},
  "request_id": "c42a..."
}
```

Delivery requires all four gates:

1. The target identity is selected.
2. Its current state permits the action.
3. A live subscriber advertises the action for that exact identity.
4. The press is outside that identity/action debounce window.

Request-scoped subscribers take priority over unscoped listeners. Within each
class, the oldest match receives the press. Actions are never broadcast, and a
one-shot subscription is disabled before its first delivery.

## Session Leases

A launcher can make socket lifetime represent process ownership:

```json
{
  "protocol": 1,
  "type": "session_lease",
  "lease_id": "09f3...",
  "metadata": {"label":"implementation","cwd":"/work/pad-lattice"}
}
```

The daemon acknowledges the lease. A later state message carrying the same
`lease_id` binds it to the real agent identity and produces a
`session_lease_bound` update. Reconnecting launchers may include that known
`agent` in the lease command.

Closing the active lease connection removes its session when no other live
lease owns that identity. Replacing a connection with the same lease ID
transfers ownership safely.

## Inspection and Previews

`{"protocol":1,"type":"status"}` returns selection, sessions, visible slots,
accents, leases, overflow, TTL, preview status, optional-audio status, and a
`surfaces` array. Each surface entry identifies its kind (`web` or `midi`),
profile, Visual Protocol version, and sanitized input/output description.
`{"protocol":1,"type":"ping"}` returns
`{"protocol":1,"type":"pong"}`.

`preview` and `preview_end` are bounded diagnostic messages used by
`pad-lattice symbols`. A preview has an owner connection, unique ID, semantic
state, and TTL of at most 30 seconds. It never mutates authoritative session
state, and disconnect or timeout restores the real view.

## Errors and Schema

Rejected input receives a machine-readable error:

```json
{
  "protocol": 1,
  "type": "error",
  "code": "unknown_message_type",
  "error": "unknown message type: example"
}
```

The authoritative runtime implementation is the typed builders and parsers in
[`protocol.py`](https://github.com/mrueda/pad-lattice/blob/main/src/pad_lattice/protocol.py).
The packaged [Protocol 1 JSON
Schema](https://github.com/mrueda/pad-lattice/blob/main/src/pad_lattice/schemas/socket-protocol-v1.json)
supports external clients, editors, and conformance tools. The daemon performs
small direct checks on live messages; it does not run JSON Schema validation in
the real-time path.

## Browser Protocol Boundary

The browser does not connect to Wire Protocol 1 and cannot send arbitrary agent
state. `web_surface.py` exposes a narrower Web Surface Protocol over a
same-origin WebSocket. Authenticated clients receive compiled visual frames and
sanitized labels; they may request only Scene selection, currently available
actions, and local-admin pairing operations.

That protocol has its own packaged [Web Surface Protocol 1 JSON
Schema](https://github.com/mrueda/pad-lattice/blob/main/src/pad_lattice/schemas/web-surface-protocol-v1.json).
Its runtime uses the same small typed-parser approach and message-size bounds as
the local protocol. The two protocols share semantic domain values but are not
interchangeable.

Wire Protocol 1, Visual Protocol 1, and Device Profile Schema 1 evolve
independently. A future incompatible socket format must use a new integer
`protocol` value rather than silently changing Protocol 1.
