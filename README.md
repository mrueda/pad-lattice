<div align="center">
  <a href="https://github.com/mrueda/pad-lattice">
    <img src="https://raw.githubusercontent.com/mrueda/pad-lattice/main/assets/pad-lattice-logo.svg" width="220" alt="Pad-Lattice logo">
  </a>
  <p><em>Human-in-the-loop control surfaces for AI agents</em></p>
</div>

# Pad-Lattice

[![Build](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml)
[![Desktop installers](https://github.com/mrueda/pad-lattice/actions/workflows/build-desktop.yml/badge.svg?branch=main)](https://github.com/mrueda/pad-lattice/actions/workflows/build-desktop.yml)
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

**Desktop is recommended for interactive use.** Follow the
[installation guide](https://mrueda.github.io/pad-lattice/docs/usage/install)
and [Quick Start](https://mrueda.github.io/pad-lattice/docs/usage/quickstart).
Python is bundled; Codex CLI must be installed and authenticated separately.

The independent [Python CLI](https://mrueda.github.io/pad-lattice/docs/usage/cli)
is available from PyPI for terminal workflows and automation:
`pipx install pad-lattice`.

Pad-Lattice is alpha software; desktop builds are currently previews.
The public virtual pad is a simulation, not a connection to your agents.

The **Novation Launchpad Pro Mk1** is physically tested. Mini Mk3 and Pro Mk3
support is experimental. See [device profiles](https://mrueda.github.io/pad-lattice/docs/technical-details/device-profiles).

## About

Created and maintained by [mrueda](https://github.com/mrueda) as an independent
free-time project, developed iteratively with Codex CLI.
See [origin and development](https://mrueda.github.io/pad-lattice/docs/about/origin-and-development)
for the background and development process.

[Changelog](CHANGELOG.md) · [Citation](CITATION.cff) · [Technical guide](https://mrueda.github.io/pad-lattice/docs/technical-details/)

## License

Copyright (C) 2026 Manuel Rueda.
Distributed under the [Apache License 2.0](LICENSE).
