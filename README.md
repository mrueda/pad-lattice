<div align="center">
  <a href="https://github.com/mrueda/pad-lattice">
    <img src="https://raw.githubusercontent.com/mrueda/pad-lattice/main/assets/pad-lattice-logo.svg" width="220" alt="Pad-Lattice logo">
  </a>
  <p><em>Physical and virtual control surfaces for AI agents</em></p>
</div>

# Pad-Lattice

[![Build](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml)
[![Documentation Status](https://github.com/mrueda/pad-lattice/actions/workflows/documentation.yml/badge.svg)](https://github.com/mrueda/pad-lattice/actions/workflows/documentation.yml)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://github.com/mrueda/pad-lattice/blob/main/pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/mrueda/pad-lattice/blob/main/LICENSE)

**🎛️ Try the virtual pad:** <https://mrueda.github.io/pad-lattice/play/>

**📘 Documentation:** <https://mrueda.github.io/pad-lattice/>

**🚀 Quick Start:** <https://mrueda.github.io/pad-lattice/docs/usage/quickstart>

**🎛️ Device Testing:** <https://mrueda.github.io/pad-lattice/docs/technical-details/device-testing>

**🔒 Security Model:** <https://mrueda.github.io/pad-lattice/docs/technical-details/security-model>

**📦 GitHub Repository:** <https://github.com/mrueda/pad-lattice>

**Pad-Lattice turns browsers and MIDI grid controllers into control surfaces
for AI agents.** One local daemon maintains multi-agent state, renders steady
visual feedback, and routes explicit actions to the selected agent. The same
surface works on a Launchpad, desktop browser, phone, or tablet.

The shared language is **Visual Protocol 1**: identity accents, state glyphs,
selection, capability-gated actions, and overflow. Physical MIDI profiles and
the virtual surface implement that protocol without redefining it.

The first real integration is **Codex CLI**. Lifecycle hooks report state and
can return request-scoped Approve or Reject decisions. `codex-exec` adds a
targeted Stop action. Prompts and terminal output remain in Codex; Pad-Lattice
exposes only labels, semantic state, and actions.

Pad-Lattice is alpha software.

## Choose a Surface

| Surface | Command | Result |
| --- | --- | --- |
| Public browser | [Open `/play/`](https://mrueda.github.io/pad-lattice/play/) | Guided Demo, protocol sandbox, and audiovisual Show; no installation. |
| Local browser | `pad-lattice web` | Real Codex control on the same computer. |
| Phone or tablet | `pad-lattice web --lan` | Real Codex control after one-time pairing on a trusted local network. |
| Launchpad | `pad-lattice daemon` | Physical MIDI input and RGB state feedback. |
| Launchpad plus browsers | `pad-lattice daemon --web` | Synchronized physical and virtual surfaces on one control plane. |

The public demo is intentionally simulated. Real control always requires the
local Pad-Lattice process and Codex hooks.

## Installation

Install the current GitHub version in an isolated environment:

```bash
pipx install git+https://github.com/mrueda/pad-lattice.git
```

The normal installation includes MIDI, browser transport, and QR pairing.

## Quick Start

Start a virtual surface without MIDI hardware:

```bash
pad-lattice web
```

The command opens a per-daemon tokenized local administrator URL. Treat that
URL as a credential and do not share it.

Launch an integrated Codex session:

```bash
pad-lattice codex --label implementation
```

The launcher injects Pad-Lattice lifecycle hooks only into its child Codex
process. On first use, review those commands with `/hooks`. Ordinary `codex`
sessions do not load Pad-Lattice hooks or show their review prompt.

When Codex requests permission, select its Agent Scene and press the lit
Approve or Reject control in the browser. The decision is routed only to that
session and request.

Allow a phone or tablet on the same trusted network:

```bash
pad-lattice web --lan
```

The local admin page displays a five-minute, one-use QR code and PIN. Paired
devices can reconnect until the daemon stops. LAN traffic is not intended for
public Wi-Fi or port forwarding.

For a physical controller:

```bash
pad-lattice devices
pad-lattice demo
pad-lattice daemon --web --audio-feedback
```

`--web` is optional. When present, the Launchpad and every paired browser show
the same selected session and can issue the same currently available actions.

Resume or add labeled sessions from other terminals:

```bash
pad-lattice codex --label docs -- resume <SESSION_ID>
pad-lattice status --watch
```

See the [Quick Start](https://mrueda.github.io/pad-lattice/docs/usage/quickstart)
and [Browser Surface](https://mrueda.github.io/pad-lattice/docs/technical-details/virtual-surface)
guides for complete setup and security details.

## Supported Hardware

| Device | Profile ID | Status |
| --- | --- | --- |
| Novation Launchpad Pro Mk1 | `novation/launchpad/pro-mk1` | **Supported and physically tested** |
| Novation Launchpad Mini Mk3 | `novation/launchpad/mini-mk3` | **Experimental; testers wanted** |
| Novation Launchpad Pro Mk3 | `novation/launchpad/pro-mk3` | **Experimental; testers wanted** |

Declarative JSON profiles map Visual Protocol 1 to MIDI ports, programmer
mode, note layouts, palettes, actions, selectors, and status indicators. New
controllers do not require changes to Codex integrations.

## Visual Cheat Sheet

The reference surface is **8x8 plus eight top actions and eight right Agent
Scenes**. The rightmost matrix column summarizes all visible agents; the other
7x8 pads render the selected agent.

| Visual | Meaning |
| --- | --- |
| Blue ellipsis | Running |
| White `?` | Waiting for reply |
| Cyan chevron | User typing |
| Amber `!` | Waiting for approval |
| Green happy face | Success |
| Red X | Error |
| Gray hollow square | Cancelled |
| Dim three-pad dash | No session selected |

| Top control | Color when available | Action |
| --- | --- | --- |
| 1 | Green | Approve |
| 2 | Red | Reject |
| 5 | Amber | Session overflow indicator |
| 7 | Blue | Retry |
| 8 | Red | Stop |

Actions remain completely dark unless the selected agent has a live subscriber
and its state permits that action. Shapes and colors are steady; rapid flashing
and pulsing are not part of the protocol. See the [full visual
language](https://mrueda.github.io/pad-lattice/docs/technical-details/visual-language).

## Demo and Show

```bash
pad-lattice demo --audio
pad-lattice show --audio
pad-lattice demo --surface web
pad-lattice show --surface both
```

The shared guided Demo exercises three agents, Scene selection, approval,
rejection recovery, and retry. **A Spark Becomes a Constellation** is a
43-second audiovisual performance across the full 8x8 matrix and outer rails.
Use `--surface midi`, `web`, or `both`; MIDI remains the default.

For `web` or `both`, the tokenized local administrator page starts and stops
playback. Paired browsers can answer Demo prompts and watch Show, but cannot
start either experience. Browser sound is per-device and muted by default;
`--audio` independently enables computer audio. In a live daemon, any real
agent waiting for a reply or approval interrupts playback and restores its
authoritative state.

## Development

```bash
git clone https://github.com/mrueda/pad-lattice.git
cd pad-lattice
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests

cd web-app
npm install
npm test
npm run build

cd ../docs-site
npm install
npm run typecheck
npm run build
```

Release history is in [CHANGELOG.md](CHANGELOG.md). Release instructions are
in [RELEASING.md](RELEASING.md).

## Citation

No formal publication is available yet. For now, cite:

> Pad-Lattice: A Visual Protocol for AI Agent Control on MIDI and Virtual Pad
> Surfaces.
> <https://github.com/mrueda/pad-lattice>

## Author

Written by Manuel Rueda.

## Copyright and License

Copyright (C) 2026 Manuel Rueda.

Distributed under the Apache License 2.0. See [LICENSE](LICENSE).
