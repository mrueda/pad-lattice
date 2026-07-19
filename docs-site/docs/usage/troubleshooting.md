# Troubleshooting

Most problems are a socket mismatch, occupied browser port, expired pairing
code, profile selection, or MIDI ownership.

Start with one read-only report:

```bash
pad-lattice doctor
```

It checks discovery, profile matching, daemon reachability, socket permissions,
and stale global Codex hooks without opening the controller or changing LEDs.
Use `pad-lattice doctor --json` when attaching diagnostics to an issue; the
report omits session identities and agent metadata.
It also abbreviates home and runtime-directory paths.

## The Virtual Surface Does Not Open

Start it explicitly and use the URL printed in the terminal:

```bash
pad-lattice web
```

Automatic browser launch is a convenience, not a runtime requirement. On a
headless host or when the desktop opener fails, run `pad-lattice web --no-open`
and open the printed tokenized loopback administrator URL yourself. Do not
share that URL.

If port 8765 is occupied, let the operating system choose a free one:

```bash
pad-lattice web --port 0
```

Only one Pad-Lattice daemon may own a given Unix socket. Stop the existing
daemon or select another path with `--socket`.

## A Phone or Tablet Cannot Pair

Confirm that the daemon was started with `--lan` and that both devices are on
the same trusted network:

```bash
pad-lattice web --lan
```

If the printed address belongs to a VPN, container, or unreachable interface,
select the interface explicitly:

```bash
pad-lattice web --lan --bind-host 192.168.1.20
```

Shared-network VMs are normally hidden from other LAN devices. Follow the
[Parallels Desktop instructions](./connect-browsers.md#running-inside-parallels-desktop)
to forward one private host port without exposing the whole VM.

Also check the host firewall. Pairing QR links and PINs are one-use and expire
after five minutes; create another from the local admin page when needed.
Pairing tokens are deliberately forgotten when the daemon restarts, so a
previously paired browser must pair again.

Do not forward the port through a router or expose it beyond the trusted local
network. LAN mode is unencrypted.

## No Device Is Detected

Inspect raw ports, profile matches, and installed profiles:

```bash
pad-lattice ports
pad-lattice devices
pad-lattice profile list
```

Auto-detection uses supported profiles only. Select experimental hardware such
as the Mini Mk3 or Pro Mk3 explicitly:

```bash
pad-lattice demo --profile novation/launchpad/mini-mk3
```

If multiple ports match, pass exact names:

```bash
pad-lattice demo \
  --profile novation/launchpad/pro-mk1 \
  --input "Launchpad Pro Standalone Port" \
  --output "Launchpad Pro Standalone Port"
```

## No LEDs Change

Start with the demo:

```bash
pad-lattice demo --no-greeting
```

Check that the controller is attached to the same host or VM, USB passthrough
is active, and Ableton Live or another MIDI application does not own the port.

Monitor raw input:

```bash
pad-lattice monitor-midi --seconds 15
```

If pad messages appear but LEDs remain unchanged, verify the output port and
programmer-mode messages in the selected profile.

## Controller Does Not Return to Normal Mode

Stop Pad-Lattice with `Ctrl-C` so profile shutdown runs. All bundled profiles
restore their normal Live mode on close. If a process was terminated without
cleanup, power-cycle the controller or select Live mode from the hardware.

## Another Process Owns MIDI

Only one demo, daemon, test, DAW, or MIDI tool can own a port at a time:

```bash
ps -ef | grep pad-lattice
```

Stop the existing process before starting another.

## Daemon Works but Codex Does Not Update

Use one socket path everywhere:

```bash
export PAD_LATTICE_SOCKET=/tmp/pad-lattice.sock
pad-lattice daemon --no-greeting
```

From another terminal:

```bash
export PAD_LATTICE_SOCKET=/tmp/pad-lattice.sock
pad-lattice send-state running
```

If this renders, start Codex through the launcher with the same socket and run
`/hooks` to verify that every Pad-Lattice command is trusted:

```bash
pad-lattice codex --socket /tmp/pad-lattice.sock --label test
```

The scoped commands contain the resolved socket path. Changing it may require
trusting the new definition.

## Pad-Lattice Hooks Appear in Plain Codex

Current versions inject hooks only through `pad-lattice codex`. If a plain
`codex` session still shows Pad-Lattice hooks, remove entries installed by an
early alpha build:

```bash
pad-lattice uninstall-codex-hooks
```

Restart the plain Codex session after cleanup. Unrelated hook handlers are
preserved.

## A Background Session Replaced the Center

Background state updates should change only their status indicator. Use the
eight right-side Agent Scene selectors to confirm the selected session. If behavior differs,
verify that every integration sends a stable `backend` and `session_id`;
messages without identity all share `local/default`.

Inspect the daemon's exact target and slot assignments:

```bash
pad-lattice status --watch
```

## Amber Overflow Light Stays On

`CC 95` is a steady amber warning when more sessions are registered than the
surface can show. Use `pad-lattice status` to inspect overflow entries, then
end sessions that are no longer active:

```bash
pad-lattice end-session --backend codex --session-id SESSION_ID
```

Closing a `pad-lattice codex` launcher removes its leased Scene immediately.
Plain `codex` sessions do not register with Pad-Lattice.

## Approve or Reject Does Nothing

An action control is completely dark when no live request can consume it. A
lit Approve or Reject control means an interactive Codex `PermissionRequest`
hook is waiting for that exact session.

Confirm all of the following:

- the requesting agent's right-side Scene is selected;
- the session was started with `pad-lattice codex`;
- `/hooks` shows the current Pad-Lattice `PermissionRequest` handler as trusted;
- the daemon and launcher use the same socket;
- the 60-second surface-decision window has not elapsed.

Restart through the launcher and review a changed definition again:

```bash
pad-lattice codex --label task -- resume <SESSION_ID>
```

If the surface window expires, Codex presents its normal keyboard approval
prompt. Approve applies only to the current permission request.

Test routing with an explicit identity:

```bash
pad-lattice listen-actions --backend test --session-id agent-a
```

Select that session's Scene, then press or tap an action. The listener should receive a
JSON message containing the same identity. Actions are intentionally ignored
instead of broadcast when no matching subscriber exists.

For `codex-exec`, only Stop is available. Interactive Stop, Retry, and ordinary
chat replies are not provided by Codex permission hooks.

## A Closed Codex Session Remains Colored

Use the leased launcher for immediate process-lifecycle cleanup:

```bash
pad-lattice codex --label task -- resume <SESSION_ID>
```

Sessions created by an older integration may be removed manually or retired by
the unleased-session TTL:

```bash
pad-lattice status
pad-lattice end-session --backend codex --session-id <SESSION_ID>
```

## Validate a Profile

Run Pad-Lattice's built-in parser and semantic checks without opening MIDI:

```bash
pad-lattice profile validate ./controller.json
```

Profile authors can additionally check the published JSON Schema after
installing the optional `schema` extra:

```bash
pad-lattice profile validate ./controller.json --validate-schema
```

This remains a dry run. Physical mapping is verified separately:

For physical mapping problems, create a guided report:

```bash
pad-lattice profile test \
  --profile-file ./controller.json \
  --report controller-report.json
```

## GitHub Pages Does Not Update

The documentation workflow runs on demand. In the repository Actions tab,
select **Documentation** and choose **Run workflow**. It builds the site,
checks the search index, and deploys the Pages artifact.
