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
pad-lattice codex --label implementation
pad-lattice codex --label docs -- resume <SESSION_ID>
```

Run `/hooks` in each new Codex session to review and trust the installed
commands. Each hook update carries its Codex session identity. Up to eight
sessions remain visible on the controller, and the right-side Agent Scene
controls select which state is shown in the center. Use a persistent legend in
another terminal when several agents are active:

```bash
pad-lattice status --watch
```

The terminal title and legend use the same Scene number, accent, and label.
The launcher owns no pseudo-terminal; it passes the real terminal directly to
Codex and holds only a daemon lease.

During a permission request, select the matching Agent Scene and press the lit
Approve or Reject control. The hook returns that one decision directly to
Codex. After 60 seconds without hardware input, Codex restores its keyboard
prompt.

## Non-Interactive Codex

Run independent tasks from other terminals:

```bash
pad-lattice codex-exec "summarize this repository"
pad-lattice codex-exec "review the current diff"
```

Each process receives its own ephemeral agent identity and visible slot. Select
the desired task, then press the common top-rail Stop control (`CC 98`) to target only that
process. Stop is bright only while the selected adapter has a live subscriber.

## Session Policy

The surface shows eight sessions:

1. The first session is selected.
2. Later sessions use free slots without stealing selection.
3. The selected session and approval-waiting sessions are protected from slot eviction.
4. A ninth session replaces the least recently active unselected session that
   is not waiting for approval.
5. New activity can bring an overflow session back into a visible slot.
6. A steady amber indicator reports that at least one session is in overflow.
7. Closing a leased launcher removes its session immediately.
8. Any unleased inactive session expires after 24 hours unless
   `--session-ttl 0` disables cleanup.

Slot assignments are ephemeral. Preferred identity accents persist across
daemon restarts in a local store that contains hashed identities, not raw
session IDs.

Inspect or explicitly remove sessions from another terminal:

```bash
pad-lattice status
pad-lattice end-session --backend codex --session-id <SESSION_ID>
```

Plain `codex` remains a hooks-compatible fallback, including hardware
Approve/Reject, but it cannot signal terminal closure. Prefer the leased
launcher for multi-agent operation.

## Custom Socket

The daemon, clients, and installed hooks must use the same path:

```bash
pad-lattice daemon --socket /tmp/pad-lattice.sock --no-greeting
pad-lattice install-codex-hooks --socket /tmp/pad-lattice.sock
pad-lattice codex --socket /tmp/pad-lattice.sock --label docs -- resume <SESSION_ID>
```

The default is `$XDG_RUNTIME_DIR/pad-lattice.sock` when available, otherwise a
per-user socket under `/tmp`. The hook installer resolves and embeds that path;
reinstall and review the hooks after changing it.

## Shutdown

Stop the daemon with `Ctrl-C`. The surface clears its LEDs, sends any profile
shutdown command, and closes both MIDI ports. Both bundled profiles return the
controller to their normal Live mode.
