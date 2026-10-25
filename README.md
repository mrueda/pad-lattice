<div align="center">
  <a href="https://github.com/mrueda/pad-lattice">
    <img src="https://raw.githubusercontent.com/mrueda/pad-lattice/main/assets/pad-lattice-logo.svg" width="220" alt="Pad-Lattice logo">
  </a>
  <p><em>Human-in-the-loop control surfaces for AI agents</em></p>
</div>

# Pad-Lattice

[![Build](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml)
[![Documentation Status](https://github.com/mrueda/pad-lattice/actions/workflows/documentation.yml/badge.svg)](https://github.com/mrueda/pad-lattice/actions/workflows/documentation.yml)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://github.com/mrueda/pad-lattice/blob/main/pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/mrueda/pad-lattice/blob/main/LICENSE)

**🖥️ Desktop app:** <https://mrueda.github.io/pad-lattice/docs/usage/install>

**🎛️ Try the virtual pad:** <https://mrueda.github.io/pad-lattice/play/>

**📘 Documentation:** <https://mrueda.github.io/pad-lattice/>

**🚀 Quick Start:** <https://mrueda.github.io/pad-lattice/docs/usage/quickstart>

**Pad-Lattice is a human-in-the-loop control surface for monitoring and
directing multiple AI agents.** At a glance, it shows which session is working,
waiting for a reply, requesting approval, completed successfully, or failed.
When an action is available, illuminated controls route it only to the selected
agent.

The same tactile visual language runs on physical Novation Launchpad MIDI
controllers, the desktop app, and browser surfaces on phones, tablets, or
computers. **No MIDI controller is required.**

Pad-Lattice grew from [mrueda](https://github.com/mrueda)'s personal need to
interact more directly with Codex CLI. As a musician and member of the duo [The
New Assembly](https://www.thenewassembly.com/), he had used a Launchpad Pro
with Ableton Live and recognized that its mature grid interface could become a
visual surface for agents. Read the [origin
story](https://mrueda.github.io/pad-lattice/docs/about/origin-and-development).

<div align="center">
  <img src="docs-site/static/img/human-control-workflow.svg" width="1200" alt="Codex asks for approval, physical and virtual pads light up, and one human press returns a targeted action">
</div>

The first integration is **Codex CLI**. Connect an open conversation, select
its colored Scene, and use the available controls to approve or reject a
permission request or stop a running turn. Prompts and replies stay in Codex.

## Get Started

**Desktop is recommended for interactive use.** It bundles Python, starts the
local service, and connects to existing Codex CLI chats without restarting
them or installing hooks. Add a Launchpad or pair a phone through Settings.

1. [Install the desktop preview](https://mrueda.github.io/pad-lattice/docs/usage/install) for Linux or macOS.
2. Open Pad-Lattice and select **Connect** beside an open Codex conversation.
3. Select its Scene and respond when an action lights up.

Pad-Lattice is alpha software. Desktop installers are currently available
through successful preview workflow runs, not a published desktop release.
Codex CLI must be installed and authenticated separately on the same computer.

**The Python CLI remains available from PyPI** for terminal workflows,
automation, and headless use. It works independently of the desktop app:
`pipx install pad-lattice`. See [CLI Setup](https://mrueda.github.io/pad-lattice/docs/usage/cli).

**Just exploring?** [Try the public pad](https://mrueda.github.io/pad-lattice/play/)
without installing anything. Its Demo, Sandbox, and Show are simulations;
real control runs through your local Pad-Lattice app or CLI service.

## Supported Hardware

| Device | Profile ID | Status |
| --- | --- | --- |
| Novation Launchpad Pro Mk1 | `novation/launchpad/pro-mk1` | **Supported and physically tested** |
| Novation Launchpad Mini Mk3 | `novation/launchpad/mini-mk3` | **Experimental; testers wanted** |
| Novation Launchpad Pro Mk3 | `novation/launchpad/pro-mk3` | **Experimental; testers wanted** |

Declarative JSON profiles map Visual Protocol 1 to MIDI ports, programmer
mode, note layouts, palettes, actions, selectors, and status indicators. New
controllers do not require changes to Codex integrations.

## Documentation

| Topic | Guide |
| --- | --- |
| Connect your first conversation | [Quick Start](https://mrueda.github.io/pad-lattice/docs/usage/quickstart) |
| Learn the colors, glyphs, actions, and 8x8 layout | [Visual Protocol](https://mrueda.github.io/pad-lattice/docs/technical-details/visual-language) |
| Connect phones, tablets, and laptops | [Browser Setup](https://mrueda.github.io/pad-lattice/docs/usage/connect-browsers) |
| Run the guided Demo or audiovisual Show | [Visual Show](https://mrueda.github.io/pad-lattice/docs/usage/visual-show) |
| Add or test a MIDI controller | [Device Profiles](https://mrueda.github.io/pad-lattice/docs/technical-details/device-profiles) |
| Understand or extend the implementation | [Technical Guide](https://mrueda.github.io/pad-lattice/docs/technical-details/) |
| Review the trust boundary | [Security Model](https://mrueda.github.io/pad-lattice/docs/technical-details/security-model) |

Release history is recorded in [CHANGELOG.md](CHANGELOG.md).

## Development Approach

Pad-Lattice is an independent hobby project developed by
[mrueda](https://github.com/mrueda) in his free time. It is developed through
an architecture-led, human-in-the-loop collaboration with Codex CLI (OpenAI,
GPT-5.6), automated testing, and evaluation on physical and virtual surfaces.
The [origin and development
page](https://mrueda.github.io/pad-lattice/docs/about/origin-and-development)
documents the process.

## Citation

Machine-readable citation metadata is available in [CITATION.cff](CITATION.cff).
No formal publication is available yet. For now, cite:

> Pad-Lattice: A Visual Protocol for AI Agent Control on MIDI and Virtual Pad
> Surfaces.
> <https://github.com/mrueda/pad-lattice>

## Author

Created and maintained by [mrueda](https://github.com/mrueda).

## Copyright and License

Copyright (C) 2026 Manuel Rueda.

Distributed under the Apache License 2.0. See [LICENSE](LICENSE).
