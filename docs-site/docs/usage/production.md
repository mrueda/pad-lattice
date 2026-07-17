# Production Use

Run one long-lived daemon to own the Launchpad MIDI ports. Other processes use
the local Pad-Lattice socket and never open the MIDI device themselves.

## Non-interactive Codex

Terminal 1:

```bash
pad-lattice daemon --no-greeting --terminal-hold 1.5
```

Terminal 2:

```bash
pad-lattice codex-exec "summarize this repository"
```

The adapter maps `codex exec --json` events to Launchpad states. During the
run, pad `18` sends `stop` and terminates the Codex process.

## Interactive Codex

Install the lifecycle hooks once:

```bash
pad-lattice install-codex-hooks
```

Start a new `codex` or `codex resume` session beside the daemon:

```bash
codex
codex resume <SESSION_ID>
```

Run `/hooks` in Codex to review and trust the Pad-Lattice commands. Prompt,
running, approval, and completion states then update automatically.

Test state rendering manually without opening the MIDI device from the Codex
terminal:

```bash
pad-lattice send-state running
pad-lattice send-state waiting_for_approval
pad-lattice send-state success
```

Listen for pad actions:

```bash
pad-lattice listen-actions
```

The daemon emits `approve`, `reject`, `retry`, and `stop`, but the passive
lifecycle hook does not yet apply those actions to an interactive session.

## Multiple Codex sessions

Hook updates carry their Codex session ID, but the current daemon still renders
one global state. If several sessions run simultaneously, the most recent event
wins and the display can switch between them. Hardware actions are not yet
routed to a selected session.

Until the planned session selector is implemented, use one hooked interactive
session when the Launchpad state must be authoritative.

## Custom socket path

The default socket is selected automatically. To override it, set the same path
for the daemon and every client:

```bash
export PAD_LATTICE_SOCKET=/tmp/pad-lattice.sock
```
