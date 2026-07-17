# Architecture

Pad-Lattice separates agent integration, session routing, and physical
hardware:

```text
Agent backend
  -> JSON-line Unix socket protocol
  -> multi-agent daemon
  -> semantic ControlSurface interface
  -> Visual Protocol 0.1 frame compiler
  -> trusted driver + declarative device profile
  -> MIDI controller
```

## Components

| Module | Purpose |
| --- | --- |
| `pad_lattice.events` | Agent identities, semantic states, and actions. |
| `pad_lattice.protocol` | JSON-line message encoding and validation. |
| `pad_lattice.daemon` | MIDI ownership, session registry, selection, and targeted routing. |
| `pad_lattice.identity_store` | Hashed session-to-accent preferences with bounded LRU persistence. |
| `pad_lattice.visual_protocol` | Hardware-independent state glyphs and semantic light tokens. |
| `pad_lattice.devices.base` | Hardware-independent surface view and input events. |
| `pad_lattice.devices.profiles` | JSON schema validation and profile catalog. |
| `pad_lattice.devices.midi_grid` | Trusted static-palette MIDI grid driver. |
| `pad_lattice.devices.factory` | Discovery, explicit selection, and port resolution. |
| `pad_lattice.codex_hooks` | Interactive Codex lifecycle adapter and installer. |
| `pad_lattice.codex_exec` | Non-interactive Codex JSONL adapter and Stop sink. |
| `pad_lattice.cli` | User-facing orchestration and profile tools. |

## Daemon Ownership

Only one process should own a controller's MIDI ports. The daemon keeps that
ownership and exposes a local Unix socket. Agent integrations never need to
know the attached device model or emit MIDI directly.

The daemon converts its selected session into a `SurfaceView`. Drivers receive
semantic state, visible session indicators, and currently available actions.
Drivers return semantic `ActionPressed` or `SessionSelected` events.

## Protocol

Messages are newline-delimited JSON.

State update:

```json
{
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
  "type": "subscribe_actions",
  "agent": {
    "backend": "codex-exec",
    "session_id": "6f3a..."
  },
  "actions": ["stop"]
}
```

Targeted action response:

```json
{
  "type": "action",
  "action": "stop",
  "agent": {
    "backend": "codex-exec",
    "session_id": "6f3a..."
  }
}
```

An action is sent only when the subscription identity equals the selected
session, its capability list contains that action, and the current state permits
it. With no matching live subscriber, the action is ignored and rendered dim.

Explicit session cleanup uses:

```json
{
  "type": "session_end",
  "agent": {"backend": "codex", "session_id": "019f..."}
}
```

A `{"type":"status"}` request returns device metadata, selection, every
registered session, visible slots, accent names, and overflow count.

## Session Registry

Registry records hold identity, current semantic state, metadata, visible
slot, persistent accent, recency, and terminal-state expiry. The first session
is selected; background updates never steal selection. Eight selector slots
are available in the bundled profiles.

Success, error, and cancellation are tracked per session. After
`--terminal-hold`, that session returns to `waiting_for_reply` without changing
another session's state. A 24-hour TTL retires quiet unselected sessions but
never approval-waiting sessions.

## Profile Resolution

Supported profiles may be auto-detected by ordered input and output regexes.
Experimental profiles require explicit selection. Ambiguous ports fail with a
diagnostic. User profile IDs cannot override a built-in or another user
profile.

Profiles are data only. Schema version 1 can select the trusted
`midi.palette-grid` driver but cannot import arbitrary Python.

## Platform Scope

The current transport uses Unix-domain sockets, so the supported runtime scope
is Linux and other Unix-like systems with compatible MIDI backends. The
protocol and surface interfaces do not require this transport forever, but a
cross-platform replacement is not part of schema version 1.
