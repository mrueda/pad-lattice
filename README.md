<div align="center">
  <a href="https://github.com/mrueda/pad-lattice">
    <img src="https://raw.githubusercontent.com/mrueda/pad-lattice/main/assets/pad-lattice-logo.svg" width="220" alt="Pad-Lattice logo">
  </a>
  <p><em>Repurpose MIDI controllers as physical interfaces for AI agents</em></p>
</div>

# Pad-Lattice

**Pad-Lattice repurposes MIDI grid controllers as physical control surfaces for
AI agents.**

[![Build](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml)
[![Documentation Status](https://github.com/mrueda/pad-lattice/actions/workflows/documentation.yml/badge.svg)](https://github.com/mrueda/pad-lattice/actions/workflows/documentation.yml)
[![Documentation](https://img.shields.io/badge/docs-online-blue)](https://mrueda.github.io/pad-lattice/)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://github.com/mrueda/pad-lattice/blob/main/pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/mrueda/pad-lattice/blob/main/LICENSE)

MIDI controllers already provide durable pads, RGB feedback, low-latency input,
and a mature cross-platform protocol. Pad-Lattice brings that hardware
ecosystem beyond music by turning a grid controller into a physical supervisor
for coding agents. Its daemon owns the hardware, renders agent state on the
LEDs, and exposes a small local protocol for agent integrations.

The first supported device is the **Novation Launchpad Pro Mk1**. The first
agent integration is **Codex CLI**, including direct lifecycle state updates
for normal terminal sessions. Pad-Lattice does not require a browser or
graphical agent UI to be open or focused.

Pad-Lattice is currently **alpha software**. The hardware demo, local daemon,
socket protocol, interactive Codex state hooks, and non-interactive Codex
adapter are functional. Applying Launchpad actions directly to interactive
Codex approval prompts remains on the roadmap.

Pad-Lattice is not a token-probability visualizer, macro keyboard, or browser
WebMIDI app. It is a local agent state and action surface: running, waiting for
reply, waiting for approval, success, error, approve, reject, retry, and stop.

**Documentation:** <a href="https://mrueda.github.io/pad-lattice/" target="_blank">https://mrueda.github.io/pad-lattice/</a>

**Quick Start:** <a href="https://mrueda.github.io/pad-lattice/docs/usage/quickstart" target="_blank">https://mrueda.github.io/pad-lattice/docs/usage/quickstart</a>

**Production Use:** <a href="https://mrueda.github.io/pad-lattice/docs/usage/production" target="_blank">https://mrueda.github.io/pad-lattice/docs/usage/production</a>

**GitHub Repository:** <a href="https://github.com/mrueda/pad-lattice" target="_blank">https://github.com/mrueda/pad-lattice</a>

## Installation

Install the command in an isolated environment with
[pipx](https://pipx.pypa.io/):

```bash
pipx install pad-lattice
```

Alternatively, install it into the active Python environment:

```bash
python3 -m pip install pad-lattice
```

Confirm the installed version:

```bash
pad-lattice --version
```

## Quick Start

List MIDI ports:

```bash
pad-lattice ports
```

Run the hardware demo:

```bash
pad-lattice demo
```

Run the production daemon:

```bash
pad-lattice daemon
```

Install lifecycle hooks for normal `codex` and `codex resume` sessions:

```bash
pad-lattice install-codex-hooks
```

Start a new Codex CLI session, run `/hooks`, and explicitly review and trust
the installed commands. Interactive prompt, running, approval, and completion
states will then update the Launchpad automatically.

Send a state from another process:

```bash
pad-lattice send-state waiting_for_reply
pad-lattice send-state running
pad-lattice send-state waiting_for_approval
```

Run a non-interactive Codex task with Launchpad state updates:

```bash
pad-lattice codex-exec "summarize this repository in one sentence"
```

## Hardware

Currently tested:

- Novation Launchpad Pro Mk1

Planned extension point:

- Additional Launchpad and MIDI grid controllers through device profiles.

The protocol is intentionally device-agnostic so controller manufacturers and
hardware developers can add profiles without coupling their devices to Codex.

Only one process can own the Launchpad MIDI ports at a time. For normal use,
run one long-lived `pad-lattice daemon` and let agent integrations talk to it
through the local socket.

The current surface displays one global state. Hook messages already carry the
Codex session identity, but selecting among simultaneous agents and routing
actions to only the selected session are not implemented yet.

## Development

Install an editable checkout and run the Python test suite:

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests
```

Run bytecode checks:

```bash
python3 -m py_compile src/pad_lattice/*.py tests/*.py
```

Run the docs checks:

```bash
cd docs-site
npm install
npm run typecheck
npm run build
```

The maintainer release process is documented in
[RELEASING.md](https://github.com/mrueda/pad-lattice/blob/main/RELEASING.md).

## Citation

No formal citation is available yet. For now, cite the GitHub repository:

Pad-Lattice: hardware control surface for coding agents.
https://github.com/mrueda/pad-lattice

## Author

Written by Manuel Rueda.

Repository: <https://github.com/mrueda/pad-lattice>

## Copyright and License

Copyright (C) 2026 Manuel Rueda.

This project is distributed under the Apache License 2.0. See the
[LICENSE](https://github.com/mrueda/pad-lattice/blob/main/LICENSE) for details.
