# Roadmap

Near-term goals:

- Add a daemon-side agent registry keyed by backend and session ID.
- Assign stable session accent colors and use pads `13` through `16` as active
  agent selectors.
- Route hardware actions only to the selected agent session.
- Introduce an explicit device-profile API for controller-specific behavior.
- Investigate app-server or terminal integration for true live typing state.
- Map deliberate Launchpad gestures to Codex approvals and interruptions.
- Expand the action model for common approval, rejection, retry, and stop workflows.

Longer-term ideas:

- Repository activity map.
- Workflow phase visualization.
- Risk or confidence display for approvals.
- Support for additional coding agents.
- Community-contributed profiles for additional MIDI grid controllers.
- Manufacturer-supported profiles that extend MIDI hardware beyond music.
