# Device Profiles

Device profiles are declarative JSON descriptions of MIDI grid controllers.
They keep hardware-specific behavior out of the daemon and agent integrations.

## Catalog Hierarchy

Profile IDs use three lowercase slugs:

```text
manufacturer/family/model
```

Built-in files follow the same directory hierarchy:

```text
src/pad_lattice/device_profiles/<manufacturer>/<family>/<model>.json
```

Current built-ins:

| Profile ID | Status |
| --- | --- |
| `novation/launchpad/pro-mk1` | Supported, physically tested |
| `novation/launchpad/mini-mk3` | Experimental, tester validation requested |

User profiles are loaded recursively from:

```text
$XDG_CONFIG_HOME/pad-lattice/profiles
~/.config/pad-lattice/profiles
```

Additional roots can be supplied as an OS-separated list in
`PAD_LATTICE_PROFILE_PATH`. Duplicate IDs are rejected so an untracked profile
cannot silently replace a built-in mapping.

## Trust Boundary

Schema version 1 accepts only the built-in `midi.palette-grid` driver. Profiles
contain data, not executable Python. Adding a new trusted driver requires a
normal Pad-Lattice code change and review; arbitrary profile directories cannot
load third-party code.

The generic driver supports:

- one explicit 8x8 note or control-change map;
- static MIDI palette colors;
- startup, clear, and shutdown messages;
- four required semantic actions;
- one to eight selector/status pairs;
- optional 5x7 text scrolling.

All state indicators are steady. Profiles cannot enable MIDI flashing or
pulsing modes.

## Schema

The top-level fields are:

| Field | Purpose |
| --- | --- |
| `schema_version` | Profile contract version; currently `1`. |
| `id` | `manufacturer/family/model` identifier. |
| `name` | Human-readable device name. |
| `manufacturer`, `family`, `model` | Catalog metadata. |
| `status` | `supported` or `experimental`. |
| `driver` | Trusted built-in driver ID. |
| `ports` | Ordered regex patterns for MIDI input and output names. |
| `grid` | Kind, channel, eight explicit rows, and state-row count. |
| `controls` | Four actions plus selector and status addresses. |
| `colors` | Semantic static-palette values. |
| `accents` | Bright/dim identity colors for visible slots. |
| `messages` | Startup, clear, and shutdown MIDI commands. |
| `capabilities` | Optional driver features such as text scrolling. |

An address names its MIDI kind, number, and optional zero-based channel:

```json
{"kind": "note", "number": 11, "channel": 0}
```

SysEx data excludes the framing bytes `F0` and `F7`, matching `mido.Message`:

```json
{
  "kind": "sysex",
  "data": [0, 32, 41, 2, 13, 14, 1]
}
```

The required color tokens are `off`, `white`, `blue`, `yellow`, `green`,
`red`, `dim_blue`, `dim_green`, `dim_red`, and `dim_yellow`.

## Discovery and Selection

Inspect the catalog and attached ports:

```bash
pad-lattice profile list
pad-lattice profile show novation/launchpad/pro-mk1
pad-lattice ports
pad-lattice devices
```

Auto-detection uses ordered port patterns but considers only **supported**
profiles. Multiple matches fail with a diagnostic instead of selecting an
arbitrary port. Experimental hardware must be explicit:

```bash
pad-lattice daemon --profile novation/launchpad/mini-mk3
```

Use a local profile under development without installing it:

```bash
pad-lattice demo --profile-file ./my-controller.json
```

## Authoring Workflow

1. Inspect incoming messages with `pad-lattice monitor-midi`.
2. Start from the closest built-in profile and change only documented device
   mappings.
3. Keep the ID and file hierarchy aligned.
4. Mark unverified hardware as `experimental`.
5. Validate before opening the MIDI ports:

```bash
pad-lattice profile validate ./my-controller.json
```

6. Run the guided physical test and attach its report to a device-validation
   issue.

One complete passing physical report is the minimum evidence for promoting a
built-in profile from experimental to supported. Maintainers may request more
coverage when firmware revisions or platform-specific MIDI names differ.

See [Test a Device](../usage/device-testing.md) for the tester workflow and
privacy guarantees.
