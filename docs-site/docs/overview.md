# Overview

**Pad-Lattice shows which Codex CLI session needs you and lets you act on it.**
Use the desktop pad, a phone or tablet, or a physical controller.
**No MIDI hardware is required.**

![A Codex approval request reaches physical and virtual pads; the user's decision returns to the selected agent](/img/human-control-workflow.svg)

Colors identify sessions. Glyphs show whether an agent is working, waiting for
you, asking permission, finished, or reporting an error. Select a session,
read its request in Codex, and use the available Approve, Reject, or Stop control.

:::info One visual language

The symbols mean the same thing on screen and on hardware. A Launchpad draws
the selected session's glyph across its grid. On [Stream Deck](./usage/stream-deck.md),
**one Session key represents one Codex conversation**. Press it to select;
separate action keys control only that selected conversation.

:::

## Get Started

1. [Install Pad-Lattice](./usage/install.md) on the computer running Codex CLI.
2. Open your Codex chats normally on the same computer.
3. Select **Connect** beside each chat in Pad-Lattice.

The desktop app starts its own local service. Your conversations stay in Codex;
you do not need to restart them or install hooks for desktop attachment.

[Quick Start](./usage/quickstart.md) walks through the first connection.
[How It Works](./usage/control-codex.md) explains the symbols and controls.

## Choose a Surface

The [Device Catalog](./usage/device-catalog.md) covers desktop and browser pads,
Novation Launchpads, and the experimental Stream Deck plugin. You can use
several surfaces together; they share the selected session and actions.

[Novation Launchpad](./usage/launchpad.md) uses an RGB grid;
[Elgato Stream Deck](./usage/stream-deck.md) uses LCD keys through an experimental
plugin. The virtual pad provides the same controls without buying hardware.
Desktop includes **Grid, Stream Deck, XL, and Neo** layouts. Switching the
on-screen layout preserves the selected chat; it does not pair a physical device.

## Try It First

The [public playground](pathname:///play/) includes an autoplay Demo, Sandbox, and
audiovisual Show. **It is a simulation**, not a connection to your local agents.
Choose Virtual Pad, Launchpad Pro, or Stream Deck in **Surface** to compare
layouts without restarting Demo, Sandbox, or Show.
Sandbox includes parallel work, requests answered elsewhere, and disconnected
sessions. Each scenario can be restarted; its activity list records what changed.

For terminal-based use, see [CLI Setup](./usage/cli.md). For implementation
details, start with [Architecture](./technical-details/architecture.md).
