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
pad-lattice demo --audio
```

`--audio` speaks **HELLO FROM CODEX CLI** while it scrolls, then plays the
daemon's default semantic earcons in context: question, approval request,
approve or reject, and success. `--no-greeting` suppresses both the spoken and
visual greeting. The controller still carries MIDI control data only; sound
comes from the computer.

`--greeting-delay` controls the LED scroll and proportionally resynchronizes
the spoken word entrances.

Common device-selection options:

```bash
pad-lattice demo --profile novation/launchpad/pro-mk1
pad-lattice demo --profile-file ./controller.json
pad-lattice demo --input "MIDI input" --output "MIDI output"
```

`--profile` and `--profile-file` are mutually exclusive. Without either,
auto-detection considers only supported profiles.

## `pad-lattice show`

Play the authored full-surface performance without starting the daemon:

```bash
pad-lattice show
pad-lattice show --audio
pad-lattice show --tempo 0.8
pad-lattice show --profile novation/launchpad/pro-mk3
```

The default script is approximately 43 seconds. `--tempo` is a positive speed
multiplier, so values below `1` slow the story down. `--audio` synthesizes and
plays the synchronized piano-and-strings score through the computer.
Device-selection options match `demo`. Stop the daemon first because the show
owns the MIDI ports directly.

## `pad-lattice web`

Start the real local daemon with a virtual surface and no MIDI device:

```bash
pad-lattice web
pad-lattice web --port 0
pad-lattice web --no-open
```

The default listener is `127.0.0.1:8765`. Loopback clients are local
administrators and may inspect sanitized session labels, select Agent Scenes,
invoke available actions, and manage remote pairing. `--port 0` asks the
operating system for a free port.

Allow explicitly paired browsers on a trusted local network:

```bash
pad-lattice web --lan
pad-lattice web --lan --advertise-host 192.168.1.20 --port 8765
```

The command prints a one-use QR link and six-digit PIN valid for five minutes.
`--advertise-host` changes the address encoded in pairing links and requires
`--lan`. LAN mode is unencrypted and must not be exposed to the internet.

The command also accepts `--socket`, `--terminal-hold`, `--session-ttl`,
`--activity-motion`, `--audio-feedback`, and `--identity-store`.

## `pad-lattice daemon`

Own the MIDI ports and expose the local Unix socket:

```bash
pad-lattice daemon --no-greeting --terminal-hold 1.5
```

The daemon accepts the same `--profile`, `--profile-file`, `--input`, and
`--output` options as the demo. `--socket` overrides the local socket path.

Mirror the physical surface in browsers:

```bash
pad-lattice daemon --web
pad-lattice daemon --web --lan
```

`--web` adds the same virtual surface served by `pad-lattice web`. It accepts
`--port`, `--no-open`, and, with LAN mode, `--advertise-host`. `--lan` requires
`--web`. MIDI and browser input share one selected-session action router.

Additional lifecycle options:

| Option | Meaning |
| --- | --- |
| `--session-ttl SECONDS` | Retire inactive unleased sessions after this interval; default 86400, `0` disables. |
| `--activity-motion` | Opt in to the slow running-state activity marker. |
| `--audio-feedback` | Speak the visual startup greeting and play short semantic earcons for important states, actions, and Scene selection. |
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
It also lists every active surface and its profile or transport details.
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
resolved daemon socket path. Installed definitions call the lightweight
`pad-lattice-hook` executable, which silently no-ops when the daemon socket is
absent.

`codex-hook` remains available as a low-level diagnostic handler and is not
normally invoked directly:

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
