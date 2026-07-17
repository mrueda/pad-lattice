# Device Profiles

Device profiles are declarative JSON descriptions of MIDI grid controllers.
They keep hardware-specific behavior out of the daemon and agent integrations.

:::caution Preserve the visual protocol

A device profile is a hardware translation of Pad-Lattice's visual protocol.
It may relocate controls or substitute supported palette values, but it must
not redefine identity, state, selection, action availability, or activity.
Profile review therefore includes semantic consistency as well as correct MIDI
messages.

:::

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
- a 7x8 state region within that grid, leaving the rightmost matrix column for
  compact per-agent status;
- four semantic actions;
- one to eight selector/status pairs;
- an optional overflow indicator;
- named selected/unselected accent pairs;
- protocol conformance declarations;
- optional 5x7 text scrolling.

All state indicators are steady. Profiles cannot enable MIDI flashing or
pulsing modes.

## Schema

The top-level fields are:

| Field | Purpose |
| --- | --- |
| `schema_version` | Profile contract version; currently `1`. |
| `visual_protocol` | Visual contract implemented by the profile; currently `0.1`. |
| `id` | `manufacturer/family/model` identifier. |
| `name` | Human-readable device name. |
| `manufacturer`, `family`, `model` | Catalog metadata. |
| `status` | `supported` or `experimental`. |
| `driver` | Trusted built-in driver ID. |
| `ports` | Ordered regex patterns for MIDI input and output names. |
| `grid` | Kind, channel, and eight explicit MIDI-address rows. |
| `surface` | State region, actions, agent selectors/statuses, and indicators. |
| `palette` | Static values for semantic states, actions, activity, and overflow. |
| `accents` | Named selected/unselected identity colors. |
| `conformance` | `core-state`, `multi-agent`, and/or `actions`. |
| `messages` | Startup, clear, and shutdown MIDI commands. |
| `capabilities` | Optional driver features such as text scrolling. |

An address names its MIDI kind, number, and optional zero-based channel:

```json
{"kind": "note", "number": 11, "channel": 0}
```

SysEx data excludes the framing bytes `F0` and `F7`, matching `mido.Message`:

```json
{
  "type": "sysex",
  "data": [0, 32, 41, 2, 13, 14, 1]
}
```

The profile schema and visual protocol are versioned independently. This is
the first public profile schema, so it is `schema_version: 1`; there is no
legacy schema to preserve.

The central surface declaration is explicit:

```json
{
  "surface": {
    "state_region": {"x": 0, "y": 0, "width": 7, "height": 8},
    "actions": {
      "approve": {"kind": "cc", "number": 91},
      "reject": {"kind": "cc", "number": 92},
      "retry": {"kind": "cc", "number": 97},
      "stop": {"kind": "cc", "number": 98}
    },
    "agent_selectors": [
      {"kind": "cc", "number": 89}
    ],
    "agent_statuses": [
      {"kind": "note", "number": 88}
    ],
    "indicators": {
      "overflow": {"kind": "cc", "number": 95}
    }
  }
}
```

All states, including `cancelled`, require both a primary glyph color and a
compact summary color. Every action requires one enabled color; unavailable
actions use the global `off` value. Accent names must be unique, and the
profile must define exactly one accent pair per selector/status slot.

The Launchpad Pro Mk1 profile opens the **Standalone Port**, switches to
Standalone Programmer layout, and restores Live Session mode during clean
shutdown. Both bundled profiles keep actions on the common top rail; the Pro's
extra left and bottom controls remain reserved. Explicit Pro Mk1 port
overrides should therefore also select the Standalone Port.

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
