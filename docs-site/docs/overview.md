# Overview

Pad-Lattice repurposes MIDI grid controllers as physical control surfaces for
AI agents. It currently targets the Novation Launchpad Pro Mk1, but the
protocol is device-agnostic so other controllers can be added through device
profiles.

## Why MIDI

MIDI hardware already combines tactile input, RGB feedback, low-latency local
communication, and broad operating-system support. Those capabilities are
useful well beyond music. Pad-Lattice separates the common agent protocol from
the device profile so existing controller ecosystems can support new agent
workflows without requiring new hardware.

The first direct integration is **Codex CLI**. It works with terminal sessions
through local lifecycle hooks; no browser or graphical agent UI needs to be
open or focused.

The project is not a token-level LLM sampler. It does not visualize token
probabilities, top-k candidates, or model internals. Pad-Lattice focuses on
agent supervision:

- Is the agent running?
- Is it waiting for a reply?
- Does it need approval?
- Did the task succeed or fail?
- Can the user approve, reject, retry, or stop from hardware?

The first tested agent integration is Codex CLI. The first tested hardware
target is Novation Launchpad Pro Mk1.

## Current capabilities

- Launchpad LED rendering for common agent states.
- A local Unix socket daemon that owns the MIDI ports.
- JSON-line protocol for state updates and hardware actions.
- Lifecycle hooks for interactive `codex` and `codex resume` sessions.
- `codex-exec` adapter for non-interactive `codex exec --json` runs.
- Raw MIDI monitor for controller mapping and debugging.
- Production instructions for running the daemon outside the Codex session.

## Non-goals

- Direct token decoding control.
- WebMIDI browser application.
- Open-weights model probability visualization.
- Replacing the Codex CLI terminal interface.

## Multi-agent boundary

One physical surface can display only a limited amount of information at once.
The current daemon displays the most recent global state and does not route
actions to an individual interactive session. Codex hook messages already
include their session identity so this limitation can be removed without
changing the integration contract.

The planned Launchpad layout assigns pads `13` through `16` to four active
sessions. Each session receives a stable accent color; pressing its pad selects
it, while the center shape continues to communicate the selected agent's
state. Approve, reject, retry, and stop will then be routed only to that agent.
