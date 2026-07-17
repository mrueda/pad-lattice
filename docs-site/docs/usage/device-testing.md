# Test a Device

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

## Launchpad Mini Mk3

The bundled Mini Mk3 profile is experimental. Connect the device directly over
USB, stop software that may own its MIDI ports, and inspect detection:

```bash
pad-lattice ports
pad-lattice devices
pad-lattice profile show novation/launchpad/mini-mk3
```

Run the test:

```bash
pad-lattice profile test novation/launchpad/mini-mk3 \
  --report mini-mk3-report.json
```

The test enters Programmer mode, asks you to confirm six steady state visuals,
and requests each action and agent selector in turn. It clears the surface and
returns the Mini Mk3 to Live mode on exit, including most failure paths.

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
