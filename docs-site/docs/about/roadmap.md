# Roadmap

## Implemented

- Local daemon with exclusive MIDI ownership.
- Interactive Codex lifecycle state hooks.
- Non-interactive `codex-exec` adapter with targeted Stop.
- Multi-agent registry keyed by backend and session ID.
- Four steady-color session selectors and semantic status LEDs.
- Selected-session action routing with live capability checks.
- Declarative, hierarchical JSON device profiles.
- Supported Novation Launchpad Pro Mk1 profile.
- Experimental Novation Launchpad Mini Mk3 profile.
- Guided physical profile testing with sanitized reports.
- On-demand GitHub workflows for tests, documentation, TestPyPI, and PyPI.

## Next

- Recruit Mini Mk3 testers and promote the profile after a complete passing
  physical report.
- Package a supported interactive Codex action bridge when a durable API is
  available.
- Add request correlation and keyboard fallback for physical approvals.
- Add daemon session inspection for operational debugging.
- Publish signed releases to TestPyPI and PyPI.
- Add more community-authored controller profiles.

## Longer Term

- Additional coding-agent integrations.
- Manufacturer-maintained profiles that extend MIDI hardware beyond music.
- Alternative selector layouts for devices with fewer or more controls.
- Repository activity, workflow phase, and risk displays built on the same
  semantic surface interface.
- A transport abstraction for platforms without Unix-domain socket support.
