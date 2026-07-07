<div align="center">
  <a href="https://github.com/mrueda/pad-lattice">
    <img src="assets/pad-lattice-logo.svg" width="180" alt="Pad-Lattice logo">
  </a>
  <p><em>Launchpad control surface for coding agents</em></p>
</div>

![version](https://img.shields.io/badge/version-0.1.0-28a745)
![python](https://img.shields.io/badge/python-%3E%3D3.10-blue)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

---

# Pad-Lattice

**Pad-Lattice** is a hardware control-surface framework for autonomous coding
agents, initially implemented for the Novation Launchpad Pro Mk1. It provides
visible agent state, dedicated approval controls, and a local socket protocol
that agent integrations can use without owning the MIDI device directly.

Pad-Lattice is not a macro keyboard. The useful part is the always-on LED
surface: a spatial status display for supervising agents while they read,
edit, test, wait for input, or require approval.

The agent protocol is intended to stay device-agnostic. The current tested
device is Launchpad Pro Mk1, but the long-term model is to add other MIDI grid
controllers through device profiles.

# Table of contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI](#cli)
- [Socket Protocol](#socket-protocol)
- [Cheat Sheet](#cheat-sheet)
- [Current Layout](#current-layout)
- [Architecture](#architecture)
- [Hardware and Environment](#hardware-and-environment)
- [Development](#development)
- [Roadmap](#roadmap)
- [Citation](#citation)
- [Author](#author)
- [Copyright and license](#copyright-and-license)

# Installation

Install locally from the repository root:

```bash
python3 -m pip install -e .
```

Pad-Lattice requires Python 3.10 or newer and uses:

- `mido`
- `python-rtmidi`

# Quick Start

List available MIDI ports:

```bash
pad-lattice ports
```

Run the hardware demo:

```bash
pad-lattice demo
```

Run the durable sidecar daemon:

```bash
pad-lattice daemon
```

Send a state to the daemon from another process:

```bash
pad-lattice send-state waiting_for_reply
pad-lattice send-state running
pad-lattice send-state waiting_for_approval
pad-lattice send-state success
pad-lattice send-state error
```

Listen for Launchpad button actions:

```bash
pad-lattice listen-actions
```

Run a real Codex CLI task and mirror Codex JSON events to the Launchpad:

```bash
pad-lattice codex-exec "summarize this repository in one sentence"
```

# CLI

| Command | Purpose |
| --- | --- |
| `pad-lattice ports` | List MIDI input and output ports. |
| `pad-lattice demo` | Run the standalone hardware demo loop. |
| `pad-lattice daemon` | Own the Launchpad and expose the local socket API. |
| `pad-lattice send-state STATE` | Send an agent state to the daemon. |
| `pad-lattice hook-state STATE` | Send a state from a Codex hook; exits successfully if the daemon is offline. |
| `pad-lattice listen-actions` | Print Launchpad actions emitted by the daemon. |
| `pad-lattice codex-exec PROMPT` | Run `codex exec --json` and mirror Codex state to the daemon. |
| `pad-lattice monitor-midi` | Print raw MIDI input messages for pad mapping/debugging. |

The demo starts by scrolling `HELLO FROM CODEX CLI` across the Launchpad, then
switches to the state and control display.

Tune the greeting speed:

```bash
pad-lattice demo --greeting-delay 0.12
```

If auto-detection picks the wrong MIDI port, pass explicit names:

```bash
pad-lattice demo --input "Launchpad Pro" --output "Launchpad Pro"
pad-lattice daemon --input "Launchpad Pro" --output "Launchpad Pro"
```

By default, `success` and `error` are temporary confirmation states. The daemon
shows them for two seconds, then returns to `waiting_for_reply`, which is the
idle state for a completed Codex turn:

```bash
pad-lattice daemon --terminal-hold 1.5
```

# Socket Protocol

The daemon owns the Launchpad MIDI ports and exposes a local Unix socket. Other
processes send newline-delimited JSON messages to that socket.

State message:

```json
{"type":"state","state":"waiting_for_reply"}
```

Action message:

```json
{"type":"action","action":"approve"}
```

Subscribe to action messages:

```json
{"type":"subscribe_actions"}
```

By default, the socket path is selected in this order:

1. `PAD_LATTICE_SOCKET`
2. `$XDG_RUNTIME_DIR/pad-lattice.sock`
3. `/tmp/pad-lattice-$UID.sock`

The first Codex integration is `pad-lattice codex-exec`, which runs
`codex exec --json` and maps Codex JSONL events to Pad-Lattice states. The
protocol remains intentionally agent-agnostic so hooks, remote-control clients,
or other coding agents can use the same daemon.

Interactive Codex CLI sessions can use Codex lifecycle hooks to update the
surface at turn boundaries. Hooks can show "prompt submitted", "running",
"approval requested", and "waiting again"; they do not expose every keystroke
while the user is typing in the terminal.

Example hook configuration:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "pad-lattice hook-state running",
            "timeout": 5
          }
        ]
      }
    ],
    "PermissionRequest": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "pad-lattice hook-state waiting_for_approval",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "pad-lattice hook-state waiting_for_reply",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

# Cheat Sheet

State colors:

| Pad color | Agent state | Meaning |
| --- | --- | --- |
| 🟦 Blue | `running` | Codex is working. |
| ⬜ White `?` | `waiting_for_reply` | Codex is waiting for a user reply. |
| ⬜ White line | `user_typing` | Reserved for integrations that can observe live typing. |
| 🟨 Yellow compact `?` | `waiting_for_approval` | Approval or review is needed. |
| 🟩 Green happy face | `success` | Completed successfully; then returns to waiting. |
| 🟥 Red | `error` | Failed; then returns to waiting. |

Control pads:

| Pad | Color | Action | Use |
| --- | --- | --- | --- |
| `11` | 🟩 Dim green | `approve` | Yes, approve, continue. |
| `12` | 🟥 Dim red | `reject` | No, reject, do not proceed. |
| `17` | 🟦 Dim blue | `retry` | Try again. |
| `18` | 🟥 Red | `stop` | Stop or interrupt. |

Launchpad Pro Mk1 programmer-grid note numbers, shown as the device faces you:

|  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `81` | `82` | `83` | `84` | `85` | `86` | `87` | `88` |
| `71` | `72` | `73` | `74` | `75` | `76` | `77` | `78` |
| `61` | `62` | `63` | `64` | `65` | `66` | `67` | `68` |
| `51` | `52` | `53` | `54` | `55` | `56` | `57` | `58` |
| `41` | `42` | `43` | `44` | `45` | `46` | `47` | `48` |
| `31` | `32` | `33` | `34` | `35` | `36` | `37` | `38` |
| `21` | `22` | `23` | `24` | `25` | `26` | `27` | `28` |
| ✅ `11` | ❌ `12` | `13` | `14` | `15` | `16` | 🔁 `17` | 🛑 `18` |

# Current Layout

The state area uses shape and motion, not color alone:

| State | Display |
| --- | --- |
| Running | Steady blue center block with one slow activity dot. |
| Waiting for reply | Steady white question mark. |
| User typing | Steady white input line. |
| Waiting for approval | Compact yellow approval/question mark. |
| Success | Green happy face, shown briefly. |
| Error | Red X, shown briefly. |

The current control layout assumes Launchpad Pro programmer-style grid notes:

| Control | Pad | Action |
| --- | --- | --- |
| Approve | `11` | `approve` |
| Reject | `12` | `reject` |
| Retry | `17` | `retry` |
| Stop | `18` | `stop` |

The four center pads `44`, `45`, `54`, and `55` display the current agent
state.

# Architecture

Pad-Lattice separates hardware ownership from agent integration:

```text
Agent backend
  -> Pad-Lattice socket protocol
  -> Pad-Lattice daemon
  -> Device profile
  -> Hardware LEDs and controls
```

The renderer receives abstract events and actions. It does not need to know
whether the backend is Codex CLI, Claude Code, Aider, Gemini CLI, Goose, or a
future coding agent.

Likewise, agent integrations should not depend on a specific controller. Device
profiles are the intended extension point for different note maps, color
palettes, setup SysEx messages, and available buttons.

Main modules:

| Module | Purpose |
| --- | --- |
| `pad_lattice.events` | Agent-agnostic states and control actions. |
| `pad_lattice.launchpad` | Launchpad LED rendering and pad press mapping. |
| `pad_lattice.daemon` | Local sidecar daemon and action broadcaster. |
| `pad_lattice.protocol` | JSON-line socket protocol helpers. |
| `pad_lattice.codex_exec` | Codex CLI JSONL adapter. |
| `pad_lattice.demo_agent` | Demo state cycle for hardware testing. |
| `pad_lattice.cli` | Command-line interface. |

# Hardware and Environment

Pad-Lattice currently ships with a tested **Novation Launchpad Pro Mk1**
profile. Other Launchpad models or MIDI grid controllers are intentionally left
as device-profile work, not agent-protocol work.

Likely future device profiles include:

- Novation Launchpad Mini Mk3
- Novation Launchpad X
- Novation Launchpad Pro Mk3
- Other 8x8 RGB MIDI grid controllers

The initial development setup is:

- macOS host
- Ubuntu VM in Parallels
- Novation Launchpad Pro Mk1 connected directly to the VM through USB
  passthrough
- Codex CLI running inside the VM

Only one process can own the Launchpad MIDI ports at a time. Stop any existing
`pad-lattice demo` or `pad-lattice daemon` process before starting another one.

# Development

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

Run bytecode compilation checks:

```bash
python3 -m py_compile src/pad_lattice/*.py tests/*.py
```

# Roadmap

Near-term goals:

- Package live Codex CLI hook setup for interactive sessions, not only `codex exec`.
- Introduce an explicit device-profile API for controller-specific behavior.
- Investigate app-server or terminal integration for true live typing state.
- Map Launchpad actions directly to Codex approvals and interruptions.
- Expand the action model for common approval, rejection, retry, and stop workflows.
- Make the LED states more readable under normal desk lighting.
- Add documentation for Launchpad Pro setup and troubleshooting.

Longer-term ideas:

- Repository activity map.
- Workflow phase visualization.
- Risk or confidence display for approvals.
- Support for additional coding agents.
- Community-contributed profiles for additional MIDI grid controllers.

# Citation

No formal citation is available yet. For now, cite the GitHub repository:

Pad-Lattice: Launchpad control surface for coding agents.
https://github.com/mrueda/pad-lattice

# Author

Written by Manuel Rueda (mrueda). GitHub repository:
[https://github.com/mrueda/pad-lattice](https://github.com/mrueda/pad-lattice).

# Copyright and license

Copyright (C) 2026 Manuel Rueda.

Please see the included [LICENSE](LICENSE) file for distribution and usage
terms.
