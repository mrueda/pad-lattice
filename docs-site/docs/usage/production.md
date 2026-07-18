# Production Use

Run one long-lived daemon per socket. It owns the deterministic control plane,
agent IPC, and every enabled surface. Agent processes never open MIDI hardware
or connect directly to a browser.

## Choose the Surfaces

Use a browser without MIDI hardware:

```bash
pad-lattice web
```

Use an auto-detected supported MIDI controller:

```bash
pad-lattice daemon --no-greeting
```

Mirror one control plane to MIDI and browsers:

```bash
pad-lattice daemon --web --no-greeting
```

The last command initializes a `CompositeSurface`. Both surfaces render the
same authoritative state and feed semantic actions through the same routing
gates. A tap and a MIDI press are equivalent; actions are still delivered to
only one selected agent request.

Use `--input` and `--output` only when several MIDI ports match. The daemon
fails on ambiguous detection instead of guessing. Experimental profiles must
be selected explicitly:

```bash
pad-lattice daemon \
  --profile novation/launchpad/mini-mk3 \
  --web \
  --no-greeting
```

Substitute `novation/launchpad/pro-mk3` for the experimental Pro Mk3 profile.

## Phone and Tablet Access

Add paired access on a trusted local network:

```bash
pad-lattice web --lan
pad-lattice daemon --web --lan
```

The local page displays a five-minute, one-use QR code and PIN. Remote clients
receive no agent state until paired. Pairing tokens exist only for the current
daemon process and can be revoked from the local browser.

:::warning Trusted network only

LAN mode uses HTTP and WebSocket traffic without transport encryption. Do not
forward its port to the internet or use it on public Wi-Fi. See [Virtual
Surface](./virtual-surface.md) for the complete security boundary.

:::

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
sessions remain visible, and an Agent Scene selects which state occupies the
center. Keep a persistent legend in another terminal for larger setups:

```bash
pad-lattice status --watch
```

The terminal title and legend use the same Scene number, accent, and label.
The launcher owns no pseudo-terminal; it passes the real terminal directly to
Codex and holds only a daemon lease.

During a permission request, select the matching Agent Scene and press or tap
the lit Approve or Reject control. The hook returns that one decision directly
to Codex. After 60 seconds without a surface decision, Codex restores its
keyboard prompt.

## Non-Interactive Codex

Run independent tasks from other terminals:

```bash
pad-lattice codex-exec "summarize this repository"
pad-lattice codex-exec "review the current diff"
```

Each process receives its own ephemeral agent identity and visible slot.
Select the desired task, then use the common Stop control to target only that
process. Stop is bright only while the selected adapter has a live subscriber.

## Optional Audio

Add short state and action earcons without changing agent behavior:

```bash
pad-lattice web --audio-feedback
pad-lattice daemon --web --audio-feedback --no-greeting
```

Routine running and typing remain silent. See [Audio
Feedback](./audio-feedback.md) for the complete vocabulary and local player
requirements.

## Session Policy

The control plane exposes eight visible sessions:

1. The first session is selected.
2. Later sessions use free slots without stealing selection.
3. Selected and approval-waiting sessions are protected from slot eviction.
4. A ninth session replaces the least recently active eligible session.
5. A steady amber indicator reports overflow.
6. Closing a leased launcher removes its session immediately.
7. Any unleased inactive session expires after 24 hours unless
   `--session-ttl 0` disables cleanup.

Slot assignments are ephemeral. Preferred identity accents persist across
daemon restarts in a local store containing hashed identities, not raw session
IDs.

Inspect or explicitly remove sessions from another terminal:

```bash
pad-lattice status
pad-lattice end-session --backend codex --session-id <SESSION_ID>
```

Plain `codex` remains a hooks-compatible fallback, including Approve and
Reject, but it cannot signal terminal closure. Prefer the leased launcher for
multi-agent operation.

## Custom Socket

The daemon, clients, and installed hooks must use the same path:

```bash
pad-lattice web --socket /tmp/pad-lattice.sock
pad-lattice install-codex-hooks --socket /tmp/pad-lattice.sock
pad-lattice codex --socket /tmp/pad-lattice.sock --label docs -- resume <SESSION_ID>
```

The default is `$XDG_RUNTIME_DIR/pad-lattice.sock` when available, otherwise a
per-user socket under `/tmp`. The hook installer resolves and embeds that path;
reinstall and review the hooks after changing it.

## Shutdown

Stop the daemon with `Ctrl-C`. Browser connections close immediately. Physical
surfaces clear their LEDs, send the profile shutdown command, close both MIDI
ports, and return bundled controllers to their normal Live mode.
