# Overview

Pad-Lattice turns **browsers and MIDI grid controllers into control surfaces
for AI agents**. A desktop browser, phone, tablet, and Launchpad can all render
the same selected agent and issue the same currently available actions.

The surfaces are different; the language and routing policy are shared.

:::important Visual Protocol 1

Color, shape, position, brightness, and motion communicate agent identity,
state, selection, action availability, and capacity. Their meanings remain
consistent across physical and virtual surfaces.

Changing that grammar is a protocol decision, not cosmetic restyling.

:::

## Start Without Hardware

Open the [public virtual pad](pathname:///play/) to experience a simulated multi-agent
approval and retry flow. After the guided story, its sandbox exposes every
state, action, identity accent, and Agent Scene.

The public page is a simulation and never connects to a local agent. To control
real Codex CLI sessions, install Pad-Lattice and run:

```bash
pad-lattice web
```

Use `pad-lattice web --lan` to pair a phone or tablet on the same trusted local
network. See [Virtual Surface](./usage/virtual-surface.md) for the exact trust
boundary and pairing lifecycle.

## Why MIDI Still Matters

MIDI hardware already combines tactile input, RGB feedback, low-latency local
communication, and mature operating-system support. Pad-Lattice repurposes
those strengths beyond music instead of requiring custom AI hardware.

The virtual surface broadens access to anyone with a browser. The physical
surface remains the flagship tactile implementation, and both can run at once:

```bash
pad-lattice daemon --web
```

## What It Supervises

Pad-Lattice does not inspect model internals or decode tokens. It answers
operational questions:

- Which agent is selected?
- Is it running, waiting, successful, failed, or requesting approval?
- Do any background sessions need attention?
- Which actions can a live integration consume now?
- Which exact agent and request will receive a press or tap?

Prompts and terminal output stay in Codex. A browser receives sanitized labels,
semantic states, selection, and action availability only.

## Choose Your Path

| I want to... | Start here |
| --- | --- |
| Experience the idea immediately | [Try the virtual pad](pathname:///play/). |
| Control Codex without MIDI hardware | [Quick Start](./usage/quickstart.md) and [Virtual Surface](./usage/virtual-surface.md). |
| Pair a phone or tablet | [Virtual Surface: LAN pairing](./usage/virtual-surface.md#phone-and-tablet-pairing). |
| Use a Launchpad | [Quick Start](./usage/quickstart.md#physical-launchpad). |
| Run several real Codex sessions | [Production Use](./usage/production.md) and [Codex Integration](./usage/codex-integration.md). |
| Understand the visual grammar | [Visual Language](./usage/visual-language.md). |
| Test another MIDI controller | [Test a Device](./usage/device-testing.md). |
| Contribute code or an integration | [Developer Guide](./technical-details/developer-guide.md). |

:::note Current maturity

Pad-Lattice is alpha software. Real browser control and the Novation Launchpad
Pro Mk1 implement the same protocol. Mini Mk3 and Pro Mk3 MIDI profiles remain
experimental. Interactive Codex currently exposes request-scoped Approve and
Reject rather than arbitrary terminal input.

:::

## Current Capabilities

- Public guided simulation and free protocol sandbox.
- Local browser control of real Codex CLI sessions.
- Ephemeral QR/PIN pairing for phones and tablets on a trusted LAN.
- Simultaneous MIDI and browser surfaces on one deterministic control plane.
- Steady shape-plus-color state glyphs and eight persistent identity accents.
- Multi-agent selection, compact background status, protected approvals, and overflow.
- Request-scoped actions that are capability-gated and never broadcast.
- Interactive Codex lifecycle hooks and Approve/Reject permission decisions.
- Native-terminal labeled launcher with leases and immediate Scene cleanup.
- Non-interactive `codex-exec` adapter with targeted Stop.
- Supported Launchpad Pro Mk1 and community-testable device profiles.
- Optional semantic earcons and an authored audiovisual hardware show.

## System Boundaries

The deterministic control plane owns sessions, selection, action routing, and
expiry. A semantic `SurfaceView` is broadcast to one or more surfaces:

- the browser surface compiles it into versioned web messages;
- a MIDI profile translates it to device addresses and palette values;
- a composite surface keeps both synchronized.

Agent integrations use a local Unix socket and never know which surfaces are
active. Browser clients never connect directly to that socket.

## Non-Goals

- Direct token decoding or probability visualization.
- WebMIDI access from the public page.
- Terminal scraping or synthetic keyboard input.
- Replacing the Codex CLI terminal interface.
- Built-in cloud relay or internet-facing remote control.
