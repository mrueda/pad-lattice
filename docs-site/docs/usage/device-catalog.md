# Device Catalog

**No controller is required.** The desktop pad and paired phone, tablet, or
laptop browser can control the same Codex CLI sessions. Hardware is optional.

Choose a device below to see its status and setup path. **Supported** means
physically tested; **experimental** means an implementation exists but still
needs an owner's hardware test. These are Pad-Lattice integration statuses,
not manufacturer certifications.

## Novation Launchpad

All three profiles use the 8x8 grid, top action buttons, and right-side session
selectors. Their extra controls, where present, remain reserved. Each uses
Programmer mode without modifying the device's firmware.

| Model | Status | Profile ID | MIDI interface |
| --- | --- | --- | --- |
| **Launchpad Pro Mk1** | **Supported: physically tested** | `novation/launchpad/pro-mk1` | Standalone Port |
| **Launchpad Mini Mk3** | Experimental: owner testing needed | `novation/launchpad/mini-mk3` | MIDI, not DAW |
| **Launchpad Pro Mk3** | Experimental: owner testing needed | `novation/launchpad/pro-mk3` | MIDI, not DAW or DIN |

**Setup:** connect over USB, then open **Settings > MIDI controller** in
Pad-Lattice. Select the profile and press **Connect**. Automatic detection
only considers supported profiles; choose either Mk3 profile explicitly.

The profiles map session colors, state glyphs, and available actions. They also
describe Demo/Show output, but the Mk3 mappings and visual playback are not
hardware-verified. Do not assume other Launchpad generations share these mappings.

[Desktop MIDI setup](./desktop.md#connect-a-launchpad) ·
[CLI setup](./cli.md) ·
[Help test a controller](../technical-details/device-testing.md)

## Elgato Stream Deck

| Integration | Status | Installation | Host software |
| --- | --- | --- | --- |
| **LCD session and action keys** | Experimental: simulated-host tests, no physical validation | Separate plugin built from source | Elgato Stream Deck 7.1+, macOS or Windows |

**One key shows one session's full glyph**, its color, and a short label.
Other keys provide Approve, Reject, and Stop. You choose where these keys go
and can keep other plugins beside them.

The first integration targets **LCD keypad actions**, not dials, touch strips,
pedals, or a controller-wide Demo/Show. No individual Stream Deck model is yet
certified as tested. The Pad-Lattice bridge must run on a supported Linux or
macOS computer; the plugin can pair locally or over a trusted LAN.

[Stream Deck setup and layout](./stream-deck.md)

## Add a MIDI Profile

Built-in Launchpad profiles are included with Pad-Lattice; there is nothing to
download separately. For a new device, obtain a profile from a trusted author
and validate it using the [CLI](./cli.md):

```bash
pad-lattice profile validate ./controller.json
```

This checks the file without opening MIDI ports. It does **not** prove the
mapping is correct for your hardware. A profile may send MIDI and SysEx commands.

To install it, place the JSON file under
`~/.config/pad-lattice/profiles/` (or `$XDG_CONFIG_HOME/pad-lattice/profiles/`
when configured), then restart Pad-Lattice. Its unique profile ID will appear
in the MIDI profile list. Existing IDs cannot be silently overridden.

For a one-off trial without installing the file:

```bash
pad-lattice demo --profile-file ./controller.json
```

Disconnect any running MIDI surface first so two processes do not compete for
the controller. See [Device Profiles](../technical-details/device-profiles.md)
for authoring and [Device Testing](../technical-details/device-testing.md) for
the guided verification procedure.

## Request or Contribute a Device

Open a [device request](https://github.com/mrueda/pad-lattice/issues/new?template=device-request.yml)
with the exact model, available controls/displays, programming documentation,
OS, and whether you own it and can test. Existing profile authors can submit
a pull request with the profile and a guided test report.

**MIDI profiles are data; plugins are executable software.** Importing a JSON
profile cannot add a new USB protocol or install a Stream Deck plugin. A device
outside the existing MIDI driver needs a reviewed adapter and separate setup
instructions. Contributions must preserve the existing meanings of colors,
glyphs, selection, and enabled actions.
