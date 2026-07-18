# CLI Reference

## General

```bash
pad-lattice --version
pad-lattice --help
```

## `pad-lattice doctor`

Inspect the installation without claiming a MIDI port or changing controller
state:

```bash
pad-lattice doctor
pad-lattice doctor --json
```

The report covers the Python runtime, profile catalog, MIDI discovery, profile
matches, daemon reachability and socket permissions, and installed Codex hook
events. Warnings such as a stopped daemon are informational; malformed setup
data returns a nonzero exit status.

## Hardware Discovery

List raw MIDI ports:

```bash
pad-lattice ports
```

Show profile matches for attached hardware, including experimental matches:

```bash
pad-lattice devices
```

## `pad-lattice demo`

Run the standalone hardware demo:

```bash
pad-lattice demo --no-greeting
```

Common device-selection options:

```bash
pad-lattice demo --profile novation/launchpad/pro-mk1
pad-lattice demo --profile-file ./controller.json
pad-lattice demo --input "MIDI input" --output "MIDI output"
```

`--profile` and `--profile-file` are mutually exclusive. Without either,
auto-detection considers only supported profiles.

## `pad-lattice daemon`

Own the MIDI ports and expose the local Unix socket:

```bash
pad-lattice daemon --no-greeting --terminal-hold 1.5
```

The daemon accepts the same `--profile`, `--profile-file`, `--input`, and
`--output` options as the demo. `--socket` overrides the local socket path.

Additional lifecycle options:

| Option | Meaning |
| --- | --- |
| `--session-ttl SECONDS` | Retire inactive unleased sessions after this interval; default 86400, `0` disables. |
| `--activity-motion` | Opt in to the slow running-state activity marker. |
| `--identity-store PATH` | Override the persistent accent-preference file. |

## `pad-lattice status`

Inspect the daemon, selected identity, slots, accents, states, and overflow:

```bash
pad-lattice status
pad-lattice status --json
pad-lattice status --watch
pad-lattice status --watch --interval 1
```

The live legend shows actual accent swatches, Scene, state, label, project,
short session ID, and whether cleanup is controlled by a live lease or TTL.
`NO_COLOR` disables ANSI swatches.

Cycle every state glyph quickly on the selected Scene, then restore its real
state:

```bash
pad-lattice symbols
pad-lattice symbols --hold 1
```

## State Commands

Send a state to the default `local/default` identity:

```bash
pad-lattice send-state running
pad-lattice send-state waiting_for_reply
pad-lattice send-state user_typing
pad-lattice send-state waiting_for_approval
pad-lattice send-state success
pad-lattice send-state error
pad-lattice send-state cancelled
```

Target an explicit identity:

```bash
pad-lattice send-state running \
  --backend test \
  --session-id agent-a
```

`hook-state` sends the same update but treats an unavailable daemon as a
successful no-op, which is useful in external hook scripts:

```bash
pad-lattice hook-state running
```

Remove an identity explicitly:

```bash
pad-lattice end-session --backend test --session-id agent-a
```

If that identity was selected, the surface becomes unselected instead of
automatically targeting another session.

## Codex Commands

Launch interactive Codex with inherited terminal I/O, an optional label,
terminal-title identity, and automatic session cleanup:

```bash
pad-lattice codex --label implementation
pad-lattice codex --label docs -- resume <SESSION_ID>
pad-lattice codex --label review -- --ask-for-approval on-request
```

Useful options are `--socket`, `--codex`, `--label`, and
`--no-terminal-title`. Arguments after `--` are passed to Codex unchanged.
Without a label, the Codex working-directory name is used.

Install lifecycle handlers:

```bash
pad-lattice install-codex-hooks
pad-lattice install-codex-hooks --path .codex/hooks.json
pad-lattice install-codex-hooks --socket /tmp/pad-lattice.sock
pad-lattice install-codex-hooks --approval-timeout 90
```

After installation, start a new Codex session and use `/hooks` to review and
trust the commands. The installer embeds an absolute executable path and the
resolved daemon socket path.

`codex-hook` is the low-level stdin handler referenced by the installed
configuration and is not normally invoked directly:

```bash
pad-lattice codex-hook \
  --socket /tmp/pad-lattice.sock \
  --approval-timeout 60
```

The `PermissionRequest` handler waits for one selected, request-scoped Approve
or Reject action. On timeout or daemon failure it returns no decision, allowing
Codex to show its normal keyboard prompt.

Run a non-interactive Codex task with state and Stop integration:

```bash
pad-lattice codex-exec "summarize this repository"
```

Each invocation receives a unique session identity. The Stop control (`CC 98`
on the common top rail) stops only the selected live
`codex-exec` process.

## Action Listener

Advertise all four actions for an identity and print targeted action messages:

```bash
pad-lattice listen-actions \
  --backend test \
  --session-id agent-a
```

An action pad lights only while this listener is connected, its identity is
selected, and the selected state permits that action. `--once` exits after the
first routed action.

## MIDI Monitor

Print raw input messages for mapping and debugging:

```bash
pad-lattice monitor-midi --seconds 15
pad-lattice monitor-midi --input "MIDI input" --seconds 15
```

With more than one input port, `--input` is required.

## Profile Catalog

List installed profiles:

```bash
pad-lattice profile list
```

Show discovery and capability metadata:

```bash
pad-lattice profile show novation/launchpad/pro-mk1
```

Validate a JSON file without opening MIDI ports:

```bash
pad-lattice profile validate ./controller.json
```

The normal command runs Pad-Lattice's dependency-free parser and semantic
checks. Profile authors can also run the published JSON Schema as an optional,
side-effect-free format check:

```bash
pipx inject pad-lattice 'jsonschema>=4.23,<5'
pad-lattice profile validate ./controller.json --validate-schema
```

For a virtual-environment installation, install `pad-lattice[schema]` instead.
The flag only reads and validates the file; it does not open MIDI ports, start
the daemon, or modify controller state.

Run guided physical verification for an installed profile:

```bash
pad-lattice profile test novation/launchpad/mini-mk3 \
  --report mini-mk3-report.json
```

Test an uninstalled file:

```bash
pad-lattice profile test \
  --profile-file ./controller.json \
  --report controller-report.json
```

Useful test options are `--input`, `--output`, `--event-timeout`, and
`--settle-delay`. The report is sanitized for submission to the public device
validation issue form.
