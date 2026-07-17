# Roadmap

## Implemented

- Local daemon with exclusive MIDI ownership.
- Interactive Codex lifecycle state hooks.
- Request-scoped interactive Codex Approve and Reject actions.
- Native-terminal Codex launcher with labels, titles, leases, and immediate cleanup.
- Non-interactive `codex-exec` adapter with targeted Stop.
- Multi-agent registry keyed by backend and session ID.
- Visual Protocol 0.1 with steady, shape-plus-color state glyphs.
- Eight persistent-color session selectors and semantic status LEDs.
- Safe LRU overflow, protected approvals, explicit session cleanup, and TTL.
- Selected-session action routing with state and live-capability checks.
- Privacy-preserving persistent accent preferences.
- Human-readable, live color-legend, and JSON daemon status inspection.
- Declarative, hierarchical JSON device profiles with conformance levels.
- Supported Novation Launchpad Pro Mk1 profile.
- Experimental Novation Launchpad Mini Mk3 profile.
- Guided physical profile testing with sanitized reports.
- On-demand GitHub workflows for tests, documentation, TestPyPI, and PyPI.

## Next

- Recruit Mini Mk3 testers and promote the profile after a complete passing
  physical report.
- Add a supported broader Codex control channel for interactive Stop, Retry,
  and ordinary chat replies.
- Publish signed releases to TestPyPI and PyPI.
- Add more community-authored controller profiles.
- Validate Visual Protocol 0.1 on devices with different layouts and palettes.

## Longer Term

- Additional coding-agent integrations.
- Manufacturer-maintained profiles that extend MIDI hardware beyond music.
- Alternative selector layouts for devices with fewer or more controls.
- Repository activity, workflow phase, and risk displays built on the same
  semantic surface interface.
- A transport abstraction for platforms without Unix-domain socket support.
