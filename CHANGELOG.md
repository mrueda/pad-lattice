# Changelog

All notable changes to Pad-Lattice will be documented in this file. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/), and
versions follow [PEP 440](https://peps.python.org/pep-0440/).

## Unreleased

### Added

- Desktop preview for Linux and macOS with bundled Python, the shared virtual
  pad, live conversation connections, MIDI selection, and phone pairing.
- Manual desktop installer builds and packaged-engine/native-window checks.
- A maximized-pad view with the selected conversation label, visible
  Connect/Disconnect buttons, and interface reload without restarting Codex.
- Discovery and explicit connection to loaded local Codex CLI conversations,
  with names, working folders, status, and automatic refresh. Live attachments
  receive state and route single-request approvals and turn-specific Stop
  without opening a terminal or installing hooks.
- Automatically saved sound, pad-view, Codex executable, and MIDI preferences.

### Changed

- Desktop-first README, landing page, navigation, and onboarding, with separate
  preview installation and independent CLI setup guides.
- Updated the Codex integration for CLI 0.164.0, including interruption and
  session-end hooks, executable discovery, and desktop compatibility checks.
- Moved Demo and Show into an Explore menu, separate from the live pad,
  and added named actions for the selected conversation.

### Fixed

- Refresh drops ended attachment entries instead of preserving disconnected chats.
- Demo and Show cannot replace the live surface while real sessions are
  connected; connecting a session stops playback and restores live controls.
- Native audio playback now uses cached blob URLs for bundled WAV files instead
  of unsupported custom-protocol media URLs; playback errors are displayed.

## 0.1.0 - 2026-07-20

### Added

- Initial physical and virtual control surfaces, including authenticated local
  browsers, trusted-LAN pairing, and synchronized MIDI/browser operation.
- Visual Protocol 1 with steady state glyphs, capability-gated actions,
  identity accents, and Agent Scenes for multiple concurrent sessions.
- Scoped Codex CLI lifecycle integration for state feedback and targeted
  Approve, Reject, Retry, and Stop actions.
- Supported Novation Launchpad Pro Mk1 hardware plus experimental Mini Mk3 and
  Pro Mk3 profiles, backed by extensible declarative device definitions.
- Shared Demo and audiovisual Show experiences, optional audio feedback,
  versioned schemas, deterministic experience assets, and complete
  documentation.
