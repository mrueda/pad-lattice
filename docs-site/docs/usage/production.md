# Production Use

Run the daemon in one terminal and Codex in another. Use an explicit socket path
in both terminals so every process connects to the same daemon.

Terminal 1:

```bash
cd /media/mrueda/2TBS/music/pad-lattice
export PAD_LATTICE_SOCKET=/tmp/pad-lattice.sock
.venv/bin/pad-lattice daemon --no-greeting --terminal-hold 1.5
```

Terminal 2:

```bash
cd /media/mrueda/2TBS/music/pad-lattice
export PAD_LATTICE_SOCKET=/tmp/pad-lattice.sock
codex resume 019f28ff-78ad-7c52-b7e4-1d2f4544cda5
```

Test state updates without opening the MIDI device from the Codex terminal:

```bash
.venv/bin/pad-lattice send-state running
.venv/bin/pad-lattice send-state success
```

Listen for pad actions:

```bash
.venv/bin/pad-lattice listen-actions
```

## Stop behavior

During `pad-lattice codex-exec`, pad `18` sends `stop` and terminates the
running Codex process.

For normal interactive `codex` / `codex resume` sessions, Pad-Lattice can emit
the stop action, but interrupting the Codex TUI itself requires a listener or a
future app-server integration.
