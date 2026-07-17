# CLI Reference

## `pad-lattice --version`

Print the installed Pad-Lattice version.

```bash
pad-lattice --version
```

## `pad-lattice ports`

List MIDI input and output ports.

```bash
pad-lattice ports
```

## `pad-lattice demo`

Run the standalone hardware demo loop.

```bash
pad-lattice demo --no-greeting
```

Useful options:

```bash
pad-lattice demo --input "Launchpad Pro" --output "Launchpad Pro"
pad-lattice demo --greeting-delay 0.12
```

## `pad-lattice daemon`

Own the Launchpad MIDI ports and expose the local Unix socket API.

```bash
pad-lattice daemon --no-greeting --terminal-hold 1.5
```

## `pad-lattice send-state`

Send an agent state to the daemon.

```bash
pad-lattice send-state running
pad-lattice send-state waiting_for_reply
pad-lattice send-state waiting_for_approval
pad-lattice send-state success
pad-lattice send-state error
```

## `pad-lattice hook-state`

Send a state from a Codex hook. If the daemon is offline, the command exits
successfully so the hook does not block Codex.

```bash
pad-lattice hook-state running
```

## `pad-lattice codex-hook`

Process one Codex lifecycle hook event from standard input and mirror its state
to the daemon. This is the low-level handler referenced by the installed Codex
configuration, not normally a command users run directly.

```bash
pad-lattice codex-hook
```

The command always returns a no-op hook response and does not fail when the
daemon is offline.

## `pad-lattice install-codex-hooks`

Merge Pad-Lattice handlers into the user-level Codex hook configuration:

```bash
pad-lattice install-codex-hooks
```

Install into a project-local file instead:

```bash
pad-lattice install-codex-hooks --path .codex/hooks.json
```

After installation, start a new Codex session and use `/hooks` to review and
trust the commands.

## `pad-lattice listen-actions`

Print Launchpad actions emitted by the daemon.

```bash
pad-lattice listen-actions
```

## `pad-lattice monitor-midi`

Print raw MIDI input messages for pad mapping and debugging.

```bash
pad-lattice monitor-midi --seconds 15
```

## `pad-lattice codex-exec`

Run `codex exec --json` and mirror Codex state to the daemon.

```bash
pad-lattice codex-exec "summarize this repository"
```

During `codex-exec`, pad `18` emits `stop` and terminates the running Codex
process.
