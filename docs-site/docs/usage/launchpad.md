# Novation Launchpad

import {LaunchpadDiagram} from '@site/src/components/SurfaceVisuals';

Launchpad profiles use the **8x8 grid**, top action buttons, and right-side
session selectors. Extra controls, where present, remain reserved. Pad-Lattice
uses Programmer mode without modifying the device's firmware.

<LaunchpadDiagram />

## Models

| Model | Status | Profile ID | MIDI interface |
| --- | --- | --- | --- |
| **Launchpad Pro Mk1** | **Supported: physically tested** | `novation/launchpad/pro-mk1` | Standalone Port |
| **Launchpad Mini Mk3** | Experimental: owner testing needed | `novation/launchpad/mini-mk3` | MIDI, not DAW |
| **Launchpad Pro Mk3** | Experimental: owner testing needed | `novation/launchpad/pro-mk3` | MIDI, not DAW or DIN |

## Connect

1. Connect the controller over USB.
2. Open **Settings > MIDI controller** in Pad-Lattice.
3. Select the profile and press **Connect**.

Automatic detection only considers supported profiles; choose either Mk3
profile explicitly. Built-in profiles are included with Pad-Lattice, so no
separate download is needed.

The profiles map session colors, state glyphs, and available actions. They also
describe Demo/Show output, but the Mk3 mappings and visual playback are not
hardware-verified. Do not assume other Launchpad generations share these mappings.

See [How It Works](./control-codex.md) for selecting sessions and acting on
requests, or [Desktop MIDI setup](./desktop.md#connect-a-launchpad) for settings.
For terminal-only operation, use [CLI Setup](./cli.md).

## Help Test a Model

Owners of the experimental models can follow [Device Testing](../technical-details/device-testing.md)
and submit a guided test report. For another model, see
[Request or Contribute a Device](./device-catalog.md#request-or-contribute-a-device).
