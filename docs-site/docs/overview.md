# Overview

Pad-Lattice repurposes MIDI grid controllers as physical control surfaces for
AI agents. It separates agent integrations from hardware details so existing
musical controllers can supervise terminal agents without a browser or
graphical agent UI.

:::important Visual protocol

Pad-Lattice defines **Visual Protocol 0.1** as well as a socket protocol. Color,
shape, position, brightness, and motion are semantic fields: together they
communicate agent identity, state, selection, action availability, and
activity. Their meanings must remain deliberate and consistent across devices.

Changing that visual grammar is a protocol-design decision, not a cosmetic
restyling.

:::

## Why MIDI

MIDI hardware already combines tactile input, RGB feedback, low-latency local
communication, and mature operating-system support. Those capabilities are
useful beyond music. Pad-Lattice turns the controller into a local agent
surface while preserving MIDI as the hardware boundary.

The first integration is **Codex CLI**. The first supported controller is the
**Novation Launchpad Pro Mk1**. An experimental profile for the **Launchpad Mini
Mk3** establishes the community testing path for additional devices.

Pad-Lattice is not a token-level sampler. It does not visualize token
probabilities, top-k candidates, or model internals. It focuses on supervision:

- Is the selected agent running or waiting?
- Does any visible session need approval?
- Did the selected task succeed or fail?
- Which agent will receive a physical action?
- Is that action currently accepted by a live integration?

## Current Capabilities

- Steady, shape-plus-color rendering for common agent states.
- A local Unix socket daemon that exclusively owns the MIDI ports.
- A multi-agent registry keyed by backend and session ID.
- Eight visible session selectors with persistent accent colors and state LEDs.
- Safe least-recently-used overflow with a steady warning indicator.
- Process leases, explicit cleanup, a 24-hour unleased-session TTL, and a live legend.
- Request-scoped action subscriptions; actions are never broadcast.
- Declarative JSON device profiles behind a trusted generic MIDI-grid driver.
- Supported Launchpad Pro Mk1 and experimental Launchpad Mini Mk3 profiles.
- Lifecycle hooks for interactive `codex` and `codex resume` sessions.
- Hardware Approve and Reject decisions for Codex permission requests.
- Labeled, native-terminal Codex launching with immediate Scene cleanup.
- A `codex-exec` adapter with a targeted Stop action.
- Guided, privacy-preserving physical profile verification.

## Hardware Boundary

The daemon works with semantic states and actions. A device profile owns:

- MIDI port discovery;
- programmer-mode startup and shutdown;
- 8x8 note or control-change maps and optional outer controls;
- static palette values;
- action controls;
- session selector, status, and overflow locations;
- calibrated palette values and declared protocol conformance levels.

This boundary lets controller manufacturers and community developers add
hardware without coupling it to Codex-specific events.

A profile translates the shared visual protocol to a device. It may use
different MIDI addresses, palette values, or physical controls, but it should
preserve the same semantic distinctions.

## Multi-Agent Boundary

The first observed session is selected. Later sessions occupy free slots
without stealing the center display. Pressing one of the eight right-side
Agent Scene buttons changes the active session, and background updates remain
visible on that session's adjacent status LED. Accent preferences survive
daemon restarts without storing raw session IDs.

When capacity is exceeded, the least recently active unselected session that
is not waiting for approval moves to overflow. Ending the selected session
clears selection instead of silently retargeting physical controls.

Physical actions are emitted only when the selected identity has a connected
subscriber advertising that action. Interactive Codex permission hooks expose
one-shot Approve and Reject; `codex-exec` advertises Stop while its process is
live. Every unavailable action is dark.

The controller's Scene and accent are mirrored in terminal titles and
`pad-lattice status --watch`. A persistent launcher lease removes a session
when its Codex process exits, while direct Codex sessions use TTL or explicit
cleanup.

## Non-Goals

- Direct token decoding control.
- A WebMIDI browser application.
- Open-weights model probability visualization.
- Terminal scraping or synthetic keyboard input.
- Replacing the Codex CLI terminal interface.
