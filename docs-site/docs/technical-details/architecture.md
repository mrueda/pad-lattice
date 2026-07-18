# Architecture

Pad-Lattice separates agent integration, session routing, and physical
hardware:

:::tip New to the codebase?

Read the [Developer Guide](./developer-guide.md) first for the runtime model,
end-to-end code paths, failure behavior, and change map.

:::

![Pad-Lattice architecture from agent adapters through the local daemon and visual protocol to a MIDI controller](/img/architecture.svg)

_State and light output flow toward the controller; selection and targeted
actions return to the owning agent integration._

## Design Boundaries

- Agent adapters know agent events and the local socket protocol, but not MIDI.
- `ControlPlane` owns deterministic routing policy. `PadLatticeDaemon` adapts
  sockets, clocks, and MIDI to that policy and is the only normal MIDI owner.
- The visual compiler knows semantic state, identity, and actions, but not MIDI
  addresses or palette numbers.
- Device profiles and trusted drivers know hardware, but not Codex events.

This separation allows another agent backend and another controller to evolve
independently.

## Components

| Module | Purpose |
| --- | --- |
| `pad_lattice.events` | Agent identities, semantic states, and actions. |
| `pad_lattice.protocol` | Versioned JSON-line framing, typed commands, and direct validation. |
| `pad_lattice.client` | Public typed API for third-party agent integrations. |
| `pad_lattice.control_plane` | Deterministic sessions, slots, selection, leases, previews, and action routing. |
| `pad_lattice.daemon_runtime` | Unix socket, selector loop, MIDI polling, and rendering adapter. |
| `pad_lattice.identity_store` | Hashed session-to-accent preferences with bounded LRU persistence. |
| `pad_lattice.visual_protocol` | Hardware-independent state glyphs and semantic light tokens. |
| `pad_lattice.devices.base` | Hardware-independent surface view and input events. |
| `pad_lattice.devices.profiles` | Dependency-free profile parsing and catalog. |
| `pad_lattice.devices.midi_grid` | Trusted static-palette MIDI grid driver. |
| `pad_lattice.devices.factory` | Discovery, explicit selection, and port resolution. |
| `pad_lattice.diagnostics` | Read-only installation and integration checks. |
| `pad_lattice.codex_hooks` | Interactive Codex lifecycle adapter and installer. |
| `pad_lattice.codex_session` | Native-terminal Codex launcher and reconnecting process lease. |
| `pad_lattice.codex_exec` | Non-interactive Codex JSONL adapter and Stop sink. |
| `pad_lattice.cli` | User-facing orchestration and profile tools. |

## Daemon Ownership

Only one process should own a controller's MIDI ports. The daemon keeps that
ownership and exposes a local Unix socket. Agent integrations never need to
know the attached device model or emit MIDI directly.

The control plane converts its selected session into a `SurfaceView`. Drivers
receive semantic state, visible session indicators, and currently available
actions. Drivers return semantic `ActionPressed` or `SessionSelected` events.

The runtime runs one synchronous `selectors` loop. Socket reads, control-plane
transitions, rendering decisions, and MIDI input polling are serialized in
that loop. The policy object receives the current clock value from the runtime,
which makes routing and expiry behavior deterministic in tests.

## Protocol

Wire Protocol 1 messages are newline-delimited JSON over a local Unix stream
socket. There are four client interaction patterns:

| Pattern | Messages | Lifetime |
| --- | --- | --- |
| State reporting | `state`, `session_end` | Usually one short connection. |
| Inspection | `status`, `ping` | Request and response. |
| Action routing | `subscribe_actions` to `action` | Connected while capabilities are live. |
| Process ownership | `session_lease` | Connected for the owning process lifetime. |

See the [Socket Protocol](../reference/socket-protocol.md) for complete message
schemas, replies, connection semantics, routing gates, and errors.

State update:

```json
{
  "protocol": 1,
  "type": "state",
  "state": "running",
  "agent": {
    "backend": "codex",
    "session_id": "019f...",
    "model": "gpt-5"
  }
}
```

Only `backend` and `session_id` form the identity key. Other string fields are
optional metadata. A manual state message without `agent` uses
`local/default`.

Action subscription:

```json
{
  "protocol": 1,
  "type": "subscribe_actions",
  "agent": {
    "backend": "codex",
    "session_id": "019f..."
  },
  "actions": ["approve", "reject"],
  "request_id": "c42a...",
  "one_shot": true
}
```

Targeted action response:

```json
{
  "protocol": 1,
  "type": "action",
  "action": "approve",
  "agent": {
    "backend": "codex",
    "session_id": "019f..."
  },
  "request_id": "c42a..."
}
```

An action is sent only when the subscription identity equals the selected
session, its capability list contains that action, and the current state permits
it. Request-scoped subscriptions are delivered one at a time. With no matching
live subscriber, the action is ignored and rendered dark.

An interactive launcher opens a persistent `session_lease` connection. Hook
state messages bind its random lease ID to the real Codex session identity.
Disconnecting the owning socket removes that session; reconnect messages may
carry the previously bound identity to restore it after a daemon restart.

Explicit session cleanup uses:

```json
{
  "protocol": 1,
  "type": "session_end",
  "agent": {"backend": "codex", "session_id": "019f..."}
}
```

A `{"protocol":1,"type":"status"}` request returns device metadata, selection, every
registered session, visible slots, accent names, labels, lease status, and
overflow count.

## Session Registry

Control-plane records hold identity, current semantic state, metadata, visible
slot, persistent accent, recency, and terminal-state expiry. The first session
is selected; background updates never steal selection. Eight selector slots
are available in the bundled profiles.

Success, error, and cancellation are tracked per session. After
`--terminal-hold`, that session returns to `waiting_for_reply` without changing
another session's state. Live leased sessions do not expire. A 24-hour TTL
retires any inactive unleased session, including a stale selected or approval
session left by a directly launched Codex process.

## Profile Resolution

Supported profiles may be auto-detected by ordered input and output regexes.
Experimental profiles require explicit selection. Ambiguous ports fail with a
diagnostic. User profile IDs cannot override a built-in or another user
profile.

Profiles are data only. Schema version 1 can select the trusted
`midi.palette-grid` driver but cannot import arbitrary Python.

Published JSON Schemas describe the external device-profile and socket
contracts for tooling. Live code uses small typed parsers; general schema
validation is an explicit profile-authoring dry run, not a daemon dependency.

## Platform Scope

The current transport uses Unix-domain sockets, so the supported runtime scope
is Linux and other Unix-like systems with compatible MIDI backends. The
protocol and surface interfaces do not require this transport forever, but a
cross-platform transport is not currently implemented and is independent of
device profile schema 1.
