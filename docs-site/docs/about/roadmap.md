# Roadmap

## Implemented

- Local daemon with exclusive agent IPC and enabled-surface ownership.
- Responsive virtual surface for desktop, phone, and tablet.
- Public, installation-free guided simulation and visual-protocol sandbox.
- Real local browser control for Codex CLI without MIDI hardware.
- Expiring QR/PIN pairing for trusted-LAN browser clients.
- Simultaneous browser and MIDI control through one composite surface.
- Interactive Codex lifecycle state hooks.
- Request-scoped interactive Codex Approve and Reject actions.
- Native-terminal Codex launcher with labels, titles, leases, and immediate cleanup.
- Non-interactive `codex-exec` adapter with targeted Stop.
- Multi-agent registry keyed by backend and session ID.
- Visual Protocol 1 with steady, shape-plus-color state glyphs.
- Eight persistent-color session selectors and semantic status LEDs.
- Safe LRU overflow, protected approvals, explicit session cleanup, and TTL.
- Selected-session action routing with state and live-capability checks.
- Privacy-preserving persistent accent preferences.
- Human-readable, live color-legend, and JSON daemon status inspection.
- Versioned, documented browser protocol with sanitized state exposure.
- Declarative, hierarchical JSON device profiles with conformance levels.
- Supported Novation Launchpad Pro Mk1 profile.
- Experimental Novation Launchpad Mini Mk3 profile.
- Experimental Novation Launchpad Pro Mk3 profile mapped from Novation's
  Programmer's Reference Guide.
- Guided physical profile testing with sanitized reports.
- Read-only `pad-lattice doctor` diagnostics for profiles, MIDI, daemon, and hooks.
- Full-surface **A Spark Becomes a Constellation** audiovisual performance.
- Shared manifest-driven Demo and Show playback on MIDI, browser, or both.
- Deterministic browser audio assets and per-device muted sound controls.
- Live-experience preemption when an agent needs a reply or approval.
- Optional semantic earcons for agent states, actions, and Scene selection.
- On-demand GitHub workflows for tests and documentation, plus annotated-tag
  publication to PyPI.

## Next

- Recruit Mini Mk3 and Pro Mk3 testers and promote each profile after a
  complete passing physical report.
- Add a supported broader Codex control channel for interactive Stop, Retry,
  and ordinary chat replies.
- Publish the first stable annotated-tag release to PyPI.
- Add more community-authored controller profiles.
- Validate Visual Protocol 1 on devices with different layouts and palettes.
- Gather usability evidence from people using only the virtual surface.

## Longer Term

- Additional coding-agent integrations.
- Optional encrypted remote transport for deployments beyond a trusted LAN.
- Manufacturer-maintained profiles that extend MIDI hardware beyond music.
- Alternative selector layouts for devices with fewer or more controls.
- Repository activity, workflow phase, and risk displays built on the same
  semantic surface interface.
- A transport abstraction for platforms without Unix-domain socket support.

## How to Help

- **Use Codex with a Launchpad Pro Mk1** and report reproducible integration
  failures.
- **Try the virtual pad** on desktop and mobile and report accessibility,
  pairing, or layout problems.
- **Run the guided hardware test** for the Launchpad Mini Mk3, Pro Mk3, or
  another MIDI grid and attach its privacy-preserving report.
- **Author a declarative device profile** when the controller fits the trusted
  palette-grid driver.
- **Prototype another agent adapter** against the semantic state and socket
  contracts without adding MIDI logic to the integration.
- **Review Visual Protocol 1** for distinctions that remain clear across
  different RGB palettes and controller layouts.

Start with the [Developer Guide](../technical-details/developer-guide.md) for
code changes or [Device Testing](../technical-details/device-testing.md) for hardware
validation. Open focused reports in the [GitHub issue
tracker](https://github.com/mrueda/pad-lattice/issues).
