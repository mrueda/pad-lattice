# Changelog

All notable changes to Pad-Lattice will be documented in this file. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/), and
versions follow [PEP 440](https://peps.python.org/pep-0440/).

## Unreleased

### Added

- The guided multi-agent Demo and **A Spark Becomes a Constellation** Show now
  run on MIDI, browser, or synchronized `both` surfaces from one shared
  experience definition.
- Public and live browser surfaces now include the full-surface Show and
  optional per-device audio, muted by default.
- Version 1 Demo and performance manifest schemas, a deterministic asset
  compiler, and packaged browser WAV assets now keep Python and TypeScript
  playback aligned without runtime schema validation.

### Changed

- Live Demo and Show playback is nonblocking and immediately yields to a real
  agent waiting for a reply or approval.
- Only the token-authenticated local browser administrator may start or stop
  live experiences; paired browsers may still interact with Demo prompts.

### Security

- Local browser administration now requires a random per-daemon token carried
  in the URL fragment.
- LAN mode now adds a listener only on the selected private IPv4 interface,
  while retaining the separate loopback administrator listener. The bind and
  browser-facing hosts may differ for an explicit host-to-VM port forward.
- Linux daemon connections now verify the Unix-socket peer UID in addition to
  mode `0600`; the security model and private reporting policy are documented.

### Fixed

- Codex lifecycle hooks are now scoped to sessions launched with
  `pad-lattice codex`, so ordinary Codex sessions no longer run Pad-Lattice
  hooks or display their review prompt.

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
