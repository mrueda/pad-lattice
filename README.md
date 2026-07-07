# Pad-Lattice

## Vision

Pad-Lattice is a proof-of-concept that transforms a Novation Launchpad Pro into a hardware control surface for autonomous coding agents.

The goal is **not** to build another macro keyboard or replace keyboard shortcuts. Instead, it explores a new interaction model where AI agents are supervised through a spatial, visual, always-on interface.

Initially the backend will be **Codex CLI**, but the architecture should remain agent-agnostic so it can later support Claude Code, Aider, Gemini CLI, Goose, or future coding agents.

---

# Environment

- macOS host
- Ubuntu VM in Parallels
- Codex CLI running inside the VM
- Launchpad Pro connected directly to the VM through USB passthrough
- Python implementation
- Libraries:
  - `mido`
  - `python-rtmidi`

---

# Design Philosophy

This is **not** a macro pad.

Buttons that simply emulate keyboard shortcuts provide very little value.

Instead, the Launchpad should become a **live dashboard** for an autonomous coding agent.

The LEDs are the primary feature.

The buttons are secondary.

The project should answer a broader UX question:

> How should humans supervise autonomous coding agents?

---

# MVP

Implement only four agent states:

| State | Color |
|--------|-------|
| Running | Blue |
| Waiting for approval | Yellow |
| Success | Green |
| Error | Red |

Display these using one LED or a small dedicated area.

Implement only four controls:

- Approve
- Reject
- Stop
- Retry

The objective of the MVP is **not** feature completeness.

It is to determine whether a physical status display is genuinely more useful than watching a terminal.

---

# Current Implementation

This repository now contains the first Python MVP skeleton:

- `pad_lattice.events` defines agent-agnostic states and control actions.
- `pad_lattice.launchpad` maps states to Launchpad LEDs and pad presses to actions.
- `pad_lattice.demo_agent` cycles through the four MVP states for hardware testing.
- `pad-lattice` provides a CLI for listing MIDI ports and running the demo loop.

Install locally from the repository root:

```bash
python3 -m pip install -e .
```

List MIDI ports:

```bash
pad-lattice ports
```

Run the hardware demo:

```bash
pad-lattice demo
```

The demo starts by scrolling `HELLO FROM CODEX CLI` across the Launchpad,
then switches to the MVP state and control display. The state area uses shape
and motion, not color alone:

| State | Display |
|--------|---------|
| Running | Steady blue symbol with one slow activity dot |
| Waiting for reply | Steady white question mark |
| Waiting for approval | Steady yellow frame |
| Success | Green checkmark |
| Error | Red X |

Tune the greeting speed if needed:

```bash
pad-lattice demo --greeting-delay 0.12
```

If auto-detection picks the wrong MIDI port, pass explicit names:

```bash
pad-lattice demo --input "Launchpad Pro" --output "Launchpad Pro"
```

Run Codex CLI under Launchpad control:

```bash
pad-lattice codex
```

Pass arguments through to Codex after `--`:

```bash
pad-lattice codex -- resume --last
```

The Codex bridge runs Codex in a terminal PTY, keeps normal keyboard input
working, and maps Launchpad controls to Codex input:

| Control | Default behavior |
|----------|------------------|
| Approve | Send Enter |
| Reject | Send Escape |
| Retry | Send `r` then Enter |
| Stop | Send Ctrl-C to Codex |

The approval keys are configurable because Codex prompt bindings can vary by
version or terminal mode:

```bash
pad-lattice codex --approve-keys "y\n" --reject-keys "n\n" -- resume --last
```

Skip the hardware greeting for everyday Codex use:

```bash
pad-lattice codex --no-greeting -- resume --last
```

The current pad layout assumes Launchpad Pro programmer-style grid notes:

| Control | Pad | Action |
|----------|-----|--------|
| Approve | 11 | approve |
| Reject | 12 | reject |
| Retry | 17 | retry |
| Stop | 18 | stop |

The four center pads `44`, `45`, `54`, and `55` display the current agent state.

---

# Future Ideas

## Repository Map

Represent repository modules spatially.

Example:

```
API
DB
CLI
UI
TESTS
DOCS
CI
SCRIPTS
```

Modules illuminate whenever the agent is working inside them.

---

## Workflow Visualization

Display the current phase of execution.

```
PLAN
 ↓
READ
 ↓
EDIT
 ↓
TEST
 ↓
REVIEW
 ↓
COMMIT
```

Each phase has a unique color or animation.

---

## Progress Visualization

Rather than showing a spinner, animate the Launchpad to indicate progress through a task.

---

## Confidence Visualization

Instead of simply indicating "approval required", estimate the confidence or risk level of the proposed changes.

Example:

- 🟢 Low risk
- 🟡 Medium risk
- 🔴 High risk

This could help users decide when a careful review is necessary.

---

## Repository Activity

Show where activity is occurring.

Examples:

- Files being read
- Files being modified
- Tests currently executing
- Git status
- Build failures

The Launchpad should feel alive while the agent works.

---

# Architecture

```
Agent Backend
      │
      ▼
Agent Events
      │
      ▼
Launchpad Renderer
      │
      ▼
Launchpad LEDs + Controls
```

The renderer should only receive abstract events.

Examples:

- running
- reading_files
- editing_files
- running_tests
- waiting_for_approval
- completed
- failed

It should know nothing about Codex specifically.

---

# Long-Term Vision

Pad-Lattice should evolve into a generic hardware interface for AI coding agents rather than a Codex-specific project.

The Launchpad is simply the first supported device.

Eventually the backend could support:

- Codex CLI
- Claude Code
- Aider
- Gemini CLI
- Goose
- Future autonomous coding agents

---

# Success Criteria

The project succeeds if the Launchpad becomes a genuinely useful supervision interface rather than a novelty.

The key question is:

> Can a spatial, LED-based hardware interface make supervising autonomous coding agents easier than constantly watching terminal output?

If the answer is yes, Pad-Lattice has discovered a new interaction model—not just another macro keyboard.
