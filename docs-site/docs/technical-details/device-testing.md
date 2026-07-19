# Device Testing

Community hardware testing is the practical path to supporting more MIDI
controllers. The guided command verifies both LED output and pad input, then
writes a small JSON report suitable for a GitHub issue.

## What the Report Contains

The report includes only:

- Pad-Lattice and profile versions;
- profile ID and status;
- MIDI input and output port names;
- operating system, kernel release, and Python version;
- yes/no visual checks;
- action and selector input results.

It does **not** contain prompts, Codex session IDs, working directories,
filesystem paths, model output, or free-form terminal content. Read the JSON
before attaching it, as you should with any diagnostic artifact.

## Launchpad Mk3 Profiles

The bundled Mini Mk3 and Pro Mk3 profiles are experimental. Connect the device
directly over USB, stop software that may own its MIDI ports, and inspect
detection:

```bash
pad-lattice ports
pad-lattice devices
pad-lattice profile show novation/launchpad/mini-mk3
pad-lattice profile show novation/launchpad/pro-mk3
```

Run the test:

```bash
pad-lattice profile test novation/launchpad/mini-mk3 \
  --report mini-mk3-report.json
```

The test enters Programmer mode, asks you to confirm the idle mark, seven
steady state glyphs, and overflow warning, then requests each action and all
eight agent selectors in turn. It clears the surface and returns the device to
Live mode on exit, including most failure paths.

The Pro Mk3 mapping follows Novation's official [Programmer's Reference
Guide](https://downloads.novationmusic.com/novation/launchpad-mk3/launchpad-pro-mk3-0).
It selects the device's MIDI interface, not its DAW or DIN interface. Run the
same test with `novation/launchpad/pro-mk3` and a `pro-mk3-report.json` output
to validate the mapping on real hardware.

Use explicit ports if several names match:

```bash
pad-lattice profile test novation/launchpad/mini-mk3 \
  --input "LPMiniMK3 MIDI" \
  --output "LPMiniMK3 MIDI" \
  --report mini-mk3-report.json
```

## Test a Local Profile

Validate and exercise an uninstalled JSON file:

```bash
pad-lattice profile validate ./my-controller.json
pad-lattice profile test \
  --profile-file ./my-controller.json \
  --report my-controller-report.json
```

## Submit Results

Open the repository's **Device profile validation** issue form. Attach the JSON
report and state the exact controller model and firmware version. A screenshot
or video is welcome but not required.

A complete passing physical report makes an experimental built-in profile
eligible for supported status. A failed report is equally useful: include what
you observed and retain the generated report so note, mode, or port matching
can be corrected without guessing.

## Safety

- Disconnect photosensitive lighting or other MIDI-controlled equipment from
  the selected output port.
- Confirm the exact input and output when several devices are attached.
- Stop the daemon or demo before running the test; only one process can own a
  MIDI port.
- Press `Ctrl-C` to abort. The command still attempts profile shutdown and port
  closure before returning control to the terminal.
