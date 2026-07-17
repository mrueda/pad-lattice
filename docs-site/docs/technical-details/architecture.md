# Architecture

Pad-Lattice separates agent integration from hardware ownership.

```text
Agent backend
  -> Pad-Lattice socket protocol
  -> Pad-Lattice daemon
  -> Device profile
  -> Hardware LEDs and controls
```

## Components

| Module | Purpose |
| --- | --- |
| `pad_lattice.events` | Agent-agnostic states and control actions. |
| `pad_lattice.protocol` | JSON-line socket protocol helpers. |
| `pad_lattice.daemon` | Local Unix socket daemon and action broadcaster. |
| `pad_lattice.launchpad` | Launchpad Pro Mk1 rendering and input mapping. |
| `pad_lattice.codex_hooks` | Interactive Codex lifecycle hook adapter and installer. |
| `pad_lattice.codex_exec` | Codex CLI JSONL adapter. |
| `pad_lattice.cli` | Command-line interface. |

## Daemon

Only one process should own the MIDI ports. The daemon keeps that ownership and
exposes a local Unix socket so agents and tools can send state updates without
touching MIDI directly.

The daemon also broadcasts Launchpad button presses to action subscribers.

## Protocol

The protocol uses newline-delimited JSON.

State message:

```json
{"type":"state","state":"running"}
```

Integrations can attach agent identity without coupling the core state model to
a particular backend:

```json
{
  "type": "state",
  "state": "running",
  "agent": {
    "backend": "codex",
    "session_id": "019f...",
    "cwd": "/work/project"
  }
}
```

Action message:

```json
{"type":"action","action":"approve"}
```

Subscribe to actions:

```json
{"type":"subscribe_actions"}
```

## Multi-agent routing

The current daemon renders one global state and broadcasts actions to every
subscriber. That is sufficient for one active agent, but it is not a safe
approval model for multiple simultaneous sessions.

The planned control-plane model is:

1. Keep an agent registry keyed by backend and session ID.
2. Assign active agents stable accent colors and selector slots.
3. Use Launchpad pads `13` through `16` to select up to four visible sessions.
4. Render the selected session's semantic state in the center of the grid.
5. Route approve, reject, retry, and stop only to the selected subscriber.

This division is portable: device profiles may expose different selector
controls, while session identity and action routing remain in the daemon.
