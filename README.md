# Pad-Lattice

**Pad-Lattice: a hardware control surface for coding agents, using a Novation
Launchpad as a local state display and action pad.**

[![Build](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/mrueda/pad-lattice/actions/workflows/build-and-test.yml)
[![Documentation Status](https://github.com/mrueda/pad-lattice/actions/workflows/documentation.yml/badge.svg)](https://github.com/mrueda/pad-lattice/actions/workflows/documentation.yml)
[![Documentation](https://img.shields.io/badge/docs-Docusaurus-blue)](https://mrueda.github.io/pad-lattice/)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Pad-Lattice turns a MIDI grid controller into a physical supervisor for coding
agents. The daemon owns the hardware, renders agent state on the LEDs, and
exposes a small local socket protocol that agent integrations can use to send
state updates and receive hardware actions.

The first supported target is the **Novation Launchpad Pro Mk1**. The first
agent integration is **Codex CLI**, with `codex exec --json` support available
through the `pad-lattice codex-exec` adapter.

Pad-Lattice is not a token-probability visualizer, macro keyboard, or browser
WebMIDI app. It is a local agent state and action surface: running, waiting for
reply, waiting for approval, success, error, approve, reject, retry, and stop.

**Documentation:** <a href="https://mrueda.github.io/pad-lattice/" target="_blank">https://mrueda.github.io/pad-lattice/</a>

## Documentation

The documentation site lives in [`docs-site/`](docs-site/) and uses Docusaurus.

- Documentation site: <https://mrueda.github.io/pad-lattice/>
- Quick start: <https://mrueda.github.io/pad-lattice/docs/usage/quickstart>
- Production use: <https://mrueda.github.io/pad-lattice/docs/usage/production>
- CLI reference: <https://mrueda.github.io/pad-lattice/docs/reference/cli>

Build the documentation locally:

```bash
cd docs-site
npm install
npm run build
```

## Quick Start

Install locally from the repository root:

```bash
python3 -m pip install -e .
```

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

Only one process can own the Launchpad MIDI ports at a time. For normal use,
run one long-lived `pad-lattice daemon` and let agent integrations talk to it
through the local socket.

## Development

Run the Python test suite:

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
npm run typecheck
npm run build
```

## Citation

No formal citation is available yet. For now, cite the GitHub repository:

Pad-Lattice: hardware control surface for coding agents.
https://github.com/mrueda/pad-lattice

## Author

Written by Manuel Rueda.

Repository: <https://github.com/mrueda/pad-lattice>

## Copyright and License

Copyright (C) 2026 Manuel Rueda.

This project is distributed under the Apache License 2.0. See [LICENSE](LICENSE)
for details.
