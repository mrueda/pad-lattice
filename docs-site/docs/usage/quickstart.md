# Quick Start

## Install

Install the current GitHub version as an isolated command:

```bash
pipx install git+https://github.com/mrueda/pad-lattice.git
```

Confirm the installation:

```bash
pad-lattice --version
pad-lattice doctor
```

`doctor` inspects profiles, MIDI ports, the daemon socket, and installed Codex
hooks without opening the controller or changing LEDs.

## Find the Controller

List raw MIDI ports and matched profiles:

```bash
pad-lattice ports
pad-lattice devices
```

Run the hardware demo. Auto-detection considers only supported profiles:

```bash
pad-lattice demo
pad-lattice demo --audio
```

`demo --audio` speaks the scrolling startup greeting, then pairs the guided
questions and pad choices with the default semantic sounds used by the daemon.

Play the standalone visual performance:

```bash
pad-lattice show
pad-lattice show --audio
```

**A Spark Becomes a Constellation** is an authored story across the complete
8x8 matrix and common top/right rails. It lasts about 43 seconds at the default
tempo. `--audio` adds its synchronized piano-and-strings score. The daemon must
be stopped because both `demo` and `show` open the MIDI ports directly.

The Launchpad Mini Mk3 and Pro Mk3 profiles are experimental and must be
selected explicitly:

```bash
pad-lattice demo --profile novation/launchpad/mini-mk3
pad-lattice demo --profile novation/launchpad/pro-mk3
pad-lattice show --profile novation/launchpad/mini-mk3
```

## Start the Daemon

Only the daemon should own the MIDI ports during normal operation:

```bash
pad-lattice daemon --no-greeting
```

Keep it running in a dedicated terminal or user service. Other commands talk
to it through the local Unix socket.

Enable optional state and action earcons when desired:

```bash
pad-lattice daemon --audio-feedback
```

This speaks **HELLO FROM CODEX CLI** while the controller scrolls the same
text. Add `--no-greeting` when neither form of greeting is wanted.

Inspect the live device and session registry from any terminal:

```bash
pad-lattice status
pad-lattice status --watch
```

## Connect Codex

Install the interactive lifecycle hooks once:

```bash
pad-lattice install-codex-hooks
```

Launch an integrated session:

```bash
pad-lattice codex --label pad-lattice
```

Run `/hooks` once to review and trust the Pad-Lattice commands. Prompt,
running, approval, and completion states now update automatically. The
terminal title shows the assigned Scene and accent, for example
`[S1 CYAN] pad-lattice`.

When Codex requests permission, select its right-side Agent Scene and press
the green Approve or red Reject control. A hardware decision applies only to
that request. If no pad is pressed within 60 seconds, Codex displays its normal
keyboard approval prompt.

Start or resume another labeled session from another terminal:

```bash
pad-lattice codex --label docs -- resume <SESSION_ID>
```

Closing a session launched this way releases its daemon lease and removes its
Scene immediately. Plain `codex` remains compatible with the hooks, but it
cannot provide an immediate terminal-close signal.

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

The eight right-side round buttons select visible Agent Scenes. The rightmost
grid column retains their compact semantic states. Background updates do not
change the selected agent.

Use an action listener to advertise controls for one test identity:

```bash
pad-lattice listen-actions --backend test --session-id agent-a
```

Action pads light only when the selected session has a live listener
**and** its state permits the action:

| Common top control | Action |
| --- | --- |
| `CC 91` | `approve` |
| `CC 92` | `reject` |
| `CC 97` | `retry` |
| `CC 98` | `stop` |

For example, set `agent-a` to `waiting_for_approval` to enable Approve and
Reject, or to `running` to enable Stop.

Remove a finished manual session explicitly:

```bash
pad-lattice end-session --backend test --session-id agent-a
```

Interactive Codex uses Approve and Reject directly. Interactive Stop, Retry,
and ordinary chat replies require a broader Codex control channel and remain
unavailable. See [Codex Integration](./codex-integration.md).

## Development Checkout

```bash
git clone https://github.com/mrueda/pad-lattice.git
cd pad-lattice
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```
