# Technical Guide

Pad-Lattice separates agent semantics, routing policy, visual meaning, and
surface-specific I/O. You do not need every page to make one kind of change.
Choose the path that matches the work in front of you.

## Choose A Path

| Goal | Read in this order |
| --- | --- |
| Understand the complete system | [Architecture](./architecture.md) -> [Multi-Agent Design](./multi-agent-design.md) -> [Visual Protocol](./visual-language.md) |
| Integrate an agent | [Architecture](./architecture.md) -> [Codex Integration](./codex-integration.md) -> [Socket Protocol](../reference/socket-protocol.md) |
| Understand the virtual controller | [Browser Surface](./virtual-surface.md) -> [Security Model](./security-model.md) |
| Add a MIDI controller | [Visual Protocol](./visual-language.md) -> [Device Profiles](./device-profiles.md) -> [Device Testing](./device-testing.md) |
| Change Demo, Show, or audio | [Developer Guide](./developer-guide.md#experience-path) -> [Experience Asset Compiler](./developer-guide.md#experience-asset-compiler) -> [Visual Show](../usage/visual-show.md) |
| Run Pad-Lattice for regular use | [Security Model](./security-model.md) -> [Production Operations](./production.md) |

## How The Section Is Organized

**Core Model** explains the boundaries that must remain stable: one control
plane, explicit agent identity, targeted actions, and a versioned visual
language.

**Integrations & Surfaces** follows information across the system boundary:
Codex lifecycle events enter through a scoped adapter, while authenticated
browsers render and return semantic surface events.

**Hardware** covers the data-driven controller layer. Device profiles map the
common visual contract to MIDI addresses and colors; the testing guide proves
that a profile behaves correctly on real hardware.

**Operations & Development** covers security, long-running deployment, and the
code ownership map. The Developer Guide also documents the **experience asset
compiler**, which turns one authored Show and score into shared physical and
virtual playback assets.

## Architectural Rule Of Thumb

An integration should report **what an agent means**. The control plane should
decide **what is allowed**. The Visual Protocol should decide **what the state
looks like**. A surface should decide only **how to render or receive it on one
device**.

Keeping those decisions separate is what lets the same agent session appear on
a Launchpad, phone, tablet, and laptop without duplicating policy.
