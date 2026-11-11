# Ableton Push 3

Use Push 3 **connected to a computer over USB**, in User Mode. The same
glyphs and session colors used on Launchpad fit its 8x8 grid.

:::warning Experimental
Planned for **0.2.1**; not included in the published 0.2.0 installers.
This profile has automated tests but has not been tested on a physical Push 3.
Standalone operation, Push 1/2, the display, encoders, and touch strip are not supported.
:::

[Try the Push layout](pathname:///play/?surface=push): Demo, Sandbox, and Show
run entirely in your browser, without hardware.

![Push 3 mapping: actions below the display, glyph grid, status column and right-side session selectors](/img/push-layout.svg)

## Connect

1. Connect Push 3 over USB in **Control Mode**.
2. Press its **User** button. Set pad expression to Mono or Poly Aftertouch,
   rather than MPE, so notes use a single MIDI channel.
3. Close Ableton Live and other software using the User ports for the first test.
4. In **Settings > Devices > MIDI controllers**, choose **Ableton Push 3**
   (profile `ableton/push/3`) and connect.

The profile matches **Push 3 User** input and output ports, never Live or
External ports. If your OS names them differently, select the User ports
explicitly. Experimental profiles are not automatically selected.

Pad-Lattice does not switch modes, change firmware, rewrite palettes, or take
over the display. Disconnect before returning to Live; press User to leave
User Mode.

## Buttons

- **Eight buttons directly below the display:** approve, reject, two reserved,
  overflow indicator, reserved, retry, stop. Only available actions light up.
- **Right-side Scene buttons:** select sessions 1 through 8, top to bottom.
- **Rightmost grid column:** each session's status. The other seven columns
  show the selected session's state glyph.
- **Other controls:** reserved, including the buttons above the display.
  The User button remains available to exit User Mode.

Demo uses this same mapping. Show uses all 64 pads and the two mapped rails;
its colors fall back to Push's palette rather than sending arbitrary RGB.
The browser illustration uses the shared protocol colors, not a calibrated
preview of hardware LEDs.

## Help Test

Follow [Device Testing](../technical-details/device-testing.md) and report
your firmware, OS, MIDI port names, grid orientation, action buttons, and
LED colors. Do not test approval controls on a sensitive live session first.

The profile uses the shared [MIDI grid driver](../technical-details/device-profiles.md).
Addresses are channel 1 (zero-based 0): grid notes 36-99, action rail CC20-27,
and Scene buttons CC36-43. Startup/shutdown send no mode-changing SysEx.

Sources: [Ableton User Mode manual](https://www.ableton.com/en/push/manual/#user-mode),
[community hardware-tested button map](https://github.com/federico-pepe/ableton-push-hack/blob/main/docs/push3-button-map.md),
and [hardware palette research](https://github.com/federico-pepe/ableton-push-hack/blob/main/docs/push3-led-colors.md).
These inform an experimental implementation, not an Ableton certification.
