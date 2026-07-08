# Overview

Pad-Lattice is a local hardware control-surface framework for coding agents.
It currently targets the Novation Launchpad Pro Mk1, but the protocol is
intended to stay device-agnostic so other MIDI grid controllers can be added
through device profiles.

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
- `codex-exec` adapter for non-interactive `codex exec --json` runs.
- Raw MIDI monitor for controller mapping and debugging.
- Production instructions for running the daemon outside the Codex session.

## Non-goals

- Direct token decoding control.
- WebMIDI browser application.
- Open-weights model probability visualization.
- Replacing the Codex CLI terminal interface.
