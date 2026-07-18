# Changelog

All notable changes to Pad-Lattice will be documented in this file. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/), and
versions follow [PEP 440](https://peps.python.org/pep-0440/).

## Unreleased

### Fixed

- Codex lifecycle hooks now use a lightweight, silent no-daemon runner instead
  of loading the full CLI after every event.

## 0.1.0a1 - 2026-07-18

### Added

- Physical control through the supported Novation Launchpad Pro Mk1, with
  experimental Launchpad Mini Mk3 and Launchpad Pro Mk3 profiles.
- Visual Protocol 1, with steady state glyphs, action controls, identity
  colors, and Agent Scenes for up to eight concurrent sessions.
- Native Codex CLI lifecycle hooks and launcher for state feedback, Approve,
  and Reject, with targeted Stop through `codex-exec`.
- A public browser demonstration and real local browser control, including
  trusted-LAN phone pairing and synchronized MIDI/browser operation.
- Declarative device profiles, versioned protocol schemas, and interactive
  hardware-conformance tooling for extending controller support.
- Optional semantic audio feedback and the authored audiovisual show *A Spark
  Becomes a Constellation*.
- Docusaurus documentation covering setup, operation, visual language,
  architecture, multi-agent behavior, device extension, and security.
