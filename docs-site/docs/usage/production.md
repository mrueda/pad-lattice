# Production Use

Run one long-lived daemon to own the controller's MIDI ports. Agent processes
use the local socket and never open the hardware themselves.

## Start the Daemon

For a supported, auto-detected device:

```bash
pad-lattice daemon --no-greeting --terminal-hold 1.5
```

Select an experimental profile explicitly:

```bash
pad-lattice daemon \
  --profile novation/launchpad/mini-mk3 \
  --no-greeting
```

Use `--input` and `--output` only when several ports match. The daemon fails on
ambiguous detection instead of guessing.

## Interactive Codex

Install lifecycle hooks once:

```bash
pad-lattice install-codex-hooks
```

Start one or more terminal sessions:

```bash
codex
codex resume <SESSION_ID>
```

Run `/hooks` in each new Codex session to review and trust the installed
commands. Each hook update carries its Codex session identity. Up to four
sessions remain visible on the controller, and pads `13` through `16` select
which state is shown in the center.

The lifecycle hook is a passive state source. It does not advertise action
capabilities, so action pads remain dim for interactive Codex sessions until a
native action bridge is implemented.

## Non-Interactive Codex

Run independent tasks from other terminals:

```bash
pad-lattice codex-exec "summarize this repository"
pad-lattice codex-exec "review the current diff"
```

Each process receives its own ephemeral agent identity and visible slot. Select
the desired task, then press pad `18` to send Stop only to that process. Stop is
bright only while the selected adapter has a live subscriber.

## Slot Policy

The surface shows four sessions:

1. The first session is selected.
2. Later sessions use free slots without stealing selection.
3. The selected session and approval-waiting sessions are pinned.
4. A fifth session replaces the least recently active unselected session that
   is not waiting for approval.
5. New activity can bring an overflow session back into a visible slot.

Slot assignments are ephemeral and reset with the daemon.

## Custom Socket

The daemon and all clients must use the same path:

```bash
export PAD_LATTICE_SOCKET=/tmp/pad-lattice.sock
```

The default is `$XDG_RUNTIME_DIR/pad-lattice.sock` when available, otherwise a
per-user socket under `/tmp`.

## Shutdown

Stop the daemon with `Ctrl-C`. The surface clears its LEDs, sends any profile
shutdown command, and closes both MIDI ports. The Mini Mk3 profile explicitly
returns the controller to Live mode.
