# Overview

**Pad-Lattice is a human-in-the-loop control surface for monitoring and
directing multiple AI agents.** At a glance, it shows which session is working,
waiting for a reply, requesting approval, completed successfully, or failed.
When an action is available, illuminated controls route it only to the selected
agent.

The same tactile visual language runs on physical Novation Launchpad MIDI
controllers, the desktop app, and browser surfaces on phones, tablets, or
computers. **No MIDI controller is required.**

![A Codex approval request lighting physical and virtual Pad-Lattice surfaces before one human decision returns to the selected agent](/img/human-control-workflow.svg)

[Open the human workflow illustration at full size](/img/human-control-workflow.svg).

:::important Visual Protocol 1

Color, shape, position, brightness, and motion communicate agent identity,
state, selection, action availability, and capacity. Their meanings remain
consistent across physical and virtual surfaces.

Changing that grammar is a protocol decision, not cosmetic restyling.

:::

## Start with Desktop

**The desktop app is recommended for interactive use.** It bundles Python and
starts the local Pad-Lattice service. Open your Codex CLI chats as usual, then
select **Connect** beside each conversation in Pad-Lattice. No restart or hook
installation is needed for this connection.

[Install the desktop preview](./usage/install.md), then follow
[Quick Start](./usage/quickstart.md). Preview builds target Linux and macOS;
Codex CLI must be installed and authenticated separately on the same computer.

The on-screen pad works by itself. Add a Launchpad through **Settings > MIDI
controller**, or [pair a phone or tablet](./usage/connect-browsers.md).
Every connected surface shows the same selection and available actions.

Prefer terminals or a headless setup? The [Python CLI](./usage/cli.md)
works independently and uses the same control engine.

## Explore Before Installing

Open the [public virtual pad](pathname:///play/) for the guided Demo, free
Sandbox, or audiovisual Show. This page is a simulation, not a connection to
your local agents. The desktop app also offers **Explore > Demo** and
**Explore > Show** when no real conversations are connected.

## Why MIDI Still Matters

MIDI controllers already combine tactile input, RGB feedback, and low-latency
local communication. Pad-Lattice repurposes those strengths beyond music.
The desktop and browser pads make the same visual language available without
buying hardware; a Launchpad adds physical buttons and LEDs.

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
| Connect open Codex chats | [Quick Start](./usage/quickstart.md). |
| Pair phones, tablets, or laptops | [Connect a Phone, Tablet, or Laptop](./usage/connect-browsers.md). |
| Use a Launchpad | [Desktop MIDI setup](./usage/desktop.md#connect-a-launchpad). |
| Run several real Codex sessions | [Control Codex](./usage/control-codex.md#run-several-agents) and [Multi-Agent Design](./technical-details/multi-agent-design.md). |
| Understand the visual grammar | [Visual Protocol](./technical-details/visual-language.md). |
| Test another MIDI controller | [Device Testing](./technical-details/device-testing.md). |
| Contribute code or an integration | [Developer Guide](./technical-details/developer-guide.md). |

:::note Current maturity

Pad-Lattice is alpha software. Real browser control and the Novation Launchpad
Pro Mk1 implement the same protocol. Mini Mk3 and Pro Mk3 MIDI profiles remain
experimental. Desktop connections expose request-scoped Approve/Reject and turn-specific
Stop, not arbitrary terminal input.

:::

## Current Capabilities

- Public guided simulation and free protocol sandbox.
- Shared Demo and audiovisual Show on MIDI, browser, or both surfaces.
- Desktop discovery and connection to existing Codex CLI chats.
- Local and paired browser control of real sessions.
- Ephemeral QR/PIN pairing for phones and tablets on a trusted LAN.
- Simultaneous MIDI and browser surfaces on one deterministic control plane.
- Steady shape-plus-color state glyphs and eight persistent identity accents.
- Multi-agent selection, compact background status, protected approvals, and overflow.
- Request-scoped actions that are capability-gated and never broadcast.
- Interactive Codex lifecycle hooks and Approve/Reject permission decisions.
- Independent Python CLI with scoped hooks and leased session cleanup.
- Non-interactive `codex-exec` adapter with targeted Stop.
- Supported Launchpad Pro Mk1 and community-testable device profiles.
- Optional host earcons, per-browser sound, and an authored audiovisual Show.

## System Boundaries

![A physical Launchpad and virtual browser surfaces controlling several Codex CLI Agent Scenes through one Pad-Lattice daemon](/img/control-surfaces-overview.svg)

[Open the control-surface diagram at full size](/img/control-surfaces-overview.svg).

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
