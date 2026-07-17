<div align="center">
  <a href="https://github.com/mrueda/pad-lattice">
    <img src="https://raw.githubusercontent.com/mrueda/pad-lattice/main/assets/pad-lattice-logo.svg" width="220" alt="Pad-Lattice logo">
  </a>
  <p><em>Repurpose MIDI controllers as physical interfaces for AI agents</em></p>
</div>

# Pad-Lattice

[![Build](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml)
[![Documentation Status](https://github.com/mrueda/pad-lattice/actions/workflows/documentation.yml/badge.svg)](https://github.com/mrueda/pad-lattice/actions/workflows/documentation.yml)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://github.com/mrueda/pad-lattice/blob/main/pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/mrueda/pad-lattice/blob/main/LICENSE)

**📘 Documentation:** <https://mrueda.github.io/pad-lattice/>

**🚀 Quick Start:** <https://mrueda.github.io/pad-lattice/docs/usage/quickstart>

**🎛️ Device Testing:** <https://mrueda.github.io/pad-lattice/docs/usage/device-testing>

**📦 GitHub Repository:** <https://github.com/mrueda/pad-lattice>

**Pad-Lattice repurposes MIDI grid controllers as physical control surfaces for
AI agents.** A local daemon owns the controller, renders agent state with
steady RGB feedback, and routes physical actions through a small Unix-socket
protocol. No browser or graphical agent UI is required.

It also defines **Visual Protocol 0.1**: a hardware-independent grammar for
agent identity, state, selection, action availability, and overflow. Device
profiles translate that grammar to MIDI without redefining it.

The first integration is **Codex CLI**. Interactive `codex` and `codex resume`
sessions report lifecycle state through hooks, while `codex-exec` supports
non-interactive tasks and a hardware Stop action.

Pad-Lattice is alpha software. State rendering, device profiles, multi-agent
selection, targeted action routing, Codex lifecycle hooks, and the
non-interactive Codex adapter are implemented. Directly applying approval,
reject, and retry actions to an interactive Codex terminal remains planned.

## Hardware

| Device | Profile ID | Status |
| --- | --- | --- |
| Novation Launchpad Pro Mk1 | `novation/launchpad/pro-mk1` | **Supported and physically tested** |
| Novation Launchpad Mini Mk3 | `novation/launchpad/mini-mk3` | **Experimental; testers wanted** |

The generic `midi.palette-grid` driver reads declarative JSON profiles. New
controllers can define port matching, programmer-mode messages, note maps,
static palette colors, Agent Scene controls, actions, and overflow indicators
without changing the agent or visual protocols.

## Installation

Install the current GitHub version in an isolated environment:

```bash
pipx install git+https://github.com/mrueda/pad-lattice.git
```

For development:

```bash
git clone https://github.com/mrueda/pad-lattice.git
cd pad-lattice
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

## Quick Start

Discover hardware and run the supported-device demo:

```bash
pad-lattice devices
pad-lattice demo
```

Start the daemon and install Codex lifecycle hooks:

```bash
pad-lattice daemon --no-greeting
pad-lattice install-codex-hooks
pad-lattice status
```

Start a new Codex session, run `/hooks`, and review and trust the installed
commands. The controller will then follow prompt, running, approval, and
completion states.

The experimental Mini Mk3 profile must be selected explicitly:

```bash
pad-lattice demo --profile novation/launchpad/mini-mk3
```

Run its guided physical verification and create a privacy-preserving report:

```bash
pad-lattice profile test novation/launchpad/mini-mk3 \
  --report mini-mk3-report.json
```

## Surface Cheat Sheet

**Common Launchpad surface:** the eight top controls carry actions and system
state; the eight right-side controls are Agent Scenes. The rightmost square in
each row is that agent's state. The remaining 7x8 matrix is the selected
agent's glyph. This example has agent 1 selected and **waiting for approval**:

| ⬛ | ⬛ | ⬛ | 🟨 | ⬛ | ⬛ | ⬛ | 🟨 S1 | 🩵 A1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ⬛ | ⬛ | ⬛ | 🟨 | ⬛ | ⬛ | ⬛ | 🔵 S2 | 🟪 A2 |
| ⬛ | ⬛ | ⬛ | 🟨 | ⬛ | ⬛ | ⬛ | ⚪ S3 | 🟢 A3 |
| ⬛ | ⬛ | ⬛ | 🟨 | ⬛ | ⬛ | ⬛ | 🟢 S4 | 🟠 A4 |
| ⬛ | ⬛ | ⬛ | 🟨 | ⬛ | ⬛ | ⬛ | 🔴 S5 | 🟣 A5 |
| ⬛ | ⬛ | ⬛ | ⬛ | ⬛ | ⬛ | ⬛ | 🩵 S6 | 🔷 A6 |
| ⬛ | ⬛ | ⬛ | ⬛ | ⬛ | ⬛ | ⬛ | ◻️ S7 | 🩷 A7 |
| ⬛ | ⬛ | ⬛ | 🟨 | ⬛ | ⬛ | ⬛ | 🔵 S8 | 🔵 A8 |

Top controls are common across the Launchpad profiles:

| 🟢 approve | 🔴 reject | ⚫ | ⚫ | 🟨 overflow | ⚫ | 🔵 retry | 🔴 stop |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `CC91` | `CC92` | `CC93` | `CC94` | `CC95` | `CC96` | `CC97` | `CC98` |

| Visual | Meaning |
| --- | --- |
| Blue ellipsis | Running; optional slow motion is off by default |
| White `?` | Waiting for reply |
| Cyan chevron | User typing |
| Restrained amber `!` | Waiting for approval |
| Green happy face | Success |
| Red X | Error |
| Gray hollow square | Cancelled |
| Dim two-pad dash | No session selected |

The selected accent is bright; other occupied Agent Scenes are dim. Hardware
actions are sent only to the selected session and only when both its state and
live adapter permit that action. See the [full visual protocol](https://mrueda.github.io/pad-lattice/docs/usage/visual-language).

The Launchpad-family common surface is **8x8 plus eight top and eight right
controls**. The Pro Mk1 has 16 additional controls on its left and bottom
rails; Protocol 0.1 leaves them reserved so the core interaction remains
portable across Launchpad models.

## Development

```bash
.venv/bin/python -m unittest discover -s tests
python3 -m py_compile src/pad_lattice/*.py src/pad_lattice/devices/*.py tests/*.py
```

Documentation checks:

```bash
cd docs-site
npm install
npm run typecheck
npm run build
```

Release instructions are in [RELEASING.md](RELEASING.md).

## Citation

No formal publication is available yet. For now, cite:

> Pad-Lattice: repurposing MIDI grid controllers as physical control surfaces
> for AI agents. <https://github.com/mrueda/pad-lattice>

## Author

Written by Manuel Rueda.

## Copyright and License

Copyright (C) 2026 Manuel Rueda.

Distributed under the Apache License 2.0. See [LICENSE](LICENSE).
