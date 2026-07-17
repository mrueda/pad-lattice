# Troubleshooting

Most problems are profile selection, MIDI ownership, controller mode, or a
socket mismatch.

## No Device Is Detected

Inspect raw ports, profile matches, and installed profiles:

```bash
pad-lattice ports
pad-lattice devices
pad-lattice profile list
```

Auto-detection uses supported profiles only. Select experimental hardware such
as the Mini Mk3 explicitly:

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

Stop Pad-Lattice with `Ctrl-C` so profile shutdown runs. Both bundled profiles
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

If this renders, reinstall the hooks, start a new Codex session, and run
`/hooks` to verify that every Pad-Lattice command is trusted:

```bash
pad-lattice install-codex-hooks --socket /tmp/pad-lattice.sock
```

The installed commands contain the resolved socket path. Changing the daemon
socket therefore requires reinstalling and trusting the updated hooks.

## A Background Session Replaced the Center

Background state updates should change only their status LED. Press the eight
right-side Agent Scene selectors to confirm the selected session. If behavior differs,
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
Inactive sessions started with plain `codex` are retired by the daemon TTL or
can be ended explicitly.

## Approve or Reject Does Nothing

An action control is completely dark when no live request can consume it. A
lit Approve or Reject control means an interactive Codex `PermissionRequest`
hook is waiting for that exact session.

Confirm all of the following:

- the requesting agent's right-side Scene is selected;
- `/hooks` shows the current Pad-Lattice `PermissionRequest` handler as trusted;
- the daemon and installed hooks use the same socket;
- the 60-second hardware window has not elapsed.

Reinstall changed hooks and review them again:

```bash
pad-lattice install-codex-hooks
```

If the hardware window expires, Codex presents its normal keyboard approval
prompt. Approve applies only to the current permission request.

Test generic routing with an explicit identity:

Test routing with an explicit identity:

```bash
pad-lattice listen-actions --backend test --session-id agent-a
```

Select that session's Scene, then press an action. The listener should receive a
JSON message containing the same identity. Actions are intentionally ignored
instead of broadcast when no matching subscriber exists.

For `codex-exec`, only Stop is available. Interactive Stop, Retry, and ordinary
chat replies are not provided by Codex permission hooks.

## A Closed Codex Session Remains Colored

Use the leased launcher for immediate process-lifecycle cleanup:

```bash
pad-lattice codex --label task -- resume <SESSION_ID>
```

Plain Codex exposes no terminal-close hook. Remove a direct session manually
or let the unleased-session TTL retire it:

```bash
pad-lattice status
pad-lattice end-session --backend codex --session-id <SESSION_ID>
```

## Validate a Profile

Run schema validation without opening MIDI:

```bash
pad-lattice profile validate ./controller.json
```

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
