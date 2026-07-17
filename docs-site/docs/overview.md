# Overview

Pad-Lattice repurposes MIDI grid controllers as physical control surfaces for
AI agents. It separates agent integrations from hardware details so existing
musical controllers can supervise terminal agents without a browser or
graphical agent UI.

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
- Four visible session selectors with distinct accent colors and state LEDs.
- Agent-scoped action subscriptions; actions are never broadcast.
- Declarative JSON device profiles behind a trusted generic MIDI-grid driver.
- Supported Launchpad Pro Mk1 and experimental Launchpad Mini Mk3 profiles.
- Lifecycle hooks for interactive `codex` and `codex resume` sessions.
- A `codex-exec` adapter with a targeted Stop action.
- Guided, privacy-preserving physical profile verification.

## Hardware Boundary

The daemon works with semantic states and actions. A device profile owns:

- MIDI port discovery;
- programmer-mode startup and shutdown;
- 8x8 note or control-change maps;
- static palette values;
- action controls;
- session selector and status locations.

This boundary lets controller manufacturers and community developers add
hardware without coupling it to Codex-specific events.

## Multi-Agent Boundary

The first observed session is selected. Later sessions occupy free slots
without stealing the center display. Pressing a selector changes the active
session, and background updates remain visible on that session's status LED.

Physical actions are emitted only when the selected identity has a connected
subscriber advertising that action. Interactive Codex lifecycle hooks are
currently state-only, so their action pads remain dim. The `codex-exec` adapter
advertises Stop while its process is live.

## Non-Goals

- Direct token decoding control.
- A WebMIDI browser application.
- Open-weights model probability visualization.
- Terminal scraping or synthetic keyboard input.
- Replacing the Codex CLI terminal interface.
