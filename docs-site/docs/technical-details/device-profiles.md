# Device Profiles

Pad-Lattice currently ships with Launchpad Pro Mk1 behavior in code. The
long-term goal is an explicit device-profile API so other controllers can be
added without changing the agent protocol.

Device profiles should own controller-specific details:

- MIDI input and output port matching.
- Startup or programmer-mode SysEx messages.
- Grid note mapping.
- Color palette values.
- Control pad locations.
- Optional side or top button mappings.

Likely future targets include:

- Novation Launchpad Mini Mk3.
- Novation Launchpad X.
- Novation Launchpad Pro Mk3.
- Other 8x8 RGB MIDI grid controllers.

The important boundary is that agent integrations should emit abstract states
and actions. They should not need to know which hardware controller is attached.
