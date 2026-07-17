# Quick Start

## Install

Install the current GitHub version as an isolated command:

```bash
pipx install git+https://github.com/mrueda/pad-lattice.git
```

Confirm the installation:

```bash
pad-lattice --version
```

## Find the Controller

List raw MIDI ports and matched profiles:

```bash
pad-lattice ports
pad-lattice devices
```

Run the hardware demo. Auto-detection considers only supported profiles:

```bash
pad-lattice demo
```

The Launchpad Mini Mk3 profile is experimental and must be selected explicitly:

```bash
pad-lattice demo --profile novation/launchpad/mini-mk3
```

## Start the Daemon

Only the daemon should own the MIDI ports during normal operation:

```bash
pad-lattice daemon --no-greeting
```

Keep it running in a dedicated terminal or user service. Other commands talk
to it through the local Unix socket.

## Connect Codex

Install the interactive lifecycle hooks once:

```bash
pad-lattice install-codex-hooks
```

Start a new `codex` or `codex resume` session and run `/hooks` to review and
trust the Pad-Lattice commands. Prompt, running, approval, and completion
states will then update the selected session automatically.

Run a non-interactive task with a targeted hardware Stop action:

```bash
pad-lattice codex-exec "summarize this repository"
```

## Exercise Multiple Sessions

Manual state messages can use explicit identities:

```bash
pad-lattice send-state running --backend test --session-id agent-a
pad-lattice send-state waiting_for_approval --backend test --session-id agent-b
```

Pads `13` through `16` select visible sessions. Pads `23` through `26` retain
their semantic states. Background updates do not change the selected agent.

Use an action listener to advertise controls for one test identity:

```bash
pad-lattice listen-actions --backend test --session-id agent-a
```

The four action pads become bright only for the selected session with a live
listener:

| Pad | Action |
| --- | --- |
| `11` | `approve` |
| `12` | `reject` |
| `17` | `retry` |
| `18` | `stop` |

Interactive Codex hooks report state but do not yet apply these actions to a
terminal approval prompt. See [Codex Integration](./codex-integration.md).

## Development Checkout

```bash
git clone https://github.com/mrueda/pad-lattice.git
cd pad-lattice
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```
