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

Action message:

```json
{"type":"action","action":"approve"}
```

Subscribe to actions:

```json
{"type":"subscribe_actions"}
```
