# Troubleshooting

Most Pad-Lattice problems fall into one of three areas: MIDI ownership,
Launchpad mode, or socket mismatch.

## No LEDs Change

Check that Pad-Lattice can see the Launchpad:

```bash
pad-lattice ports
```

Then start with the hardware demo:

```bash
pad-lattice demo
```

If the demo does not change the LEDs:

- Confirm the Launchpad Pro Mk1 is attached to the same machine or VM where
  Pad-Lattice is running.
- Confirm USB passthrough is assigned to the VM if you are using virtualization.
- Stop Ableton Live, browser MIDI tools, or any other app that may own the
  Launchpad MIDI ports.
- Pass explicit port names if auto-detection chooses the wrong port:

```bash
pad-lattice demo --input "Launchpad Pro" --output "Launchpad Pro"
```

## Only One Green Button Is Lit

This usually means the Launchpad is not fully under Pad-Lattice control yet, or
the wrong MIDI port is being used.

Try:

```bash
pad-lattice demo --no-greeting
```

If that still does not render the state display, run:

```bash
pad-lattice monitor-midi
```

Press a few pads. If no messages appear, the input port is wrong or another
process owns the device.

## Daemon Starts but Codex Does Not Update LEDs

Use one socket path everywhere:

```bash
export PAD_LATTICE_SOCKET=/tmp/pad-lattice.sock
```

Start the daemon in one terminal:

```bash
pad-lattice daemon --no-greeting --terminal-hold 1.5
```

From another terminal, test the same socket:

```bash
export PAD_LATTICE_SOCKET=/tmp/pad-lattice.sock
pad-lattice send-state running
pad-lattice send-state waiting_for_reply
```

If this works, the daemon is healthy and the problem is in the agent
integration layer.

For interactive Codex, confirm the lifecycle hooks are installed:

```bash
pad-lattice install-codex-hooks
```

Then start a new Codex session and run `/hooks`. The Pad-Lattice commands must
be enabled and trusted before Codex will run them.

## Pad Actions Do Not Reach the Terminal

First verify that the daemon emits actions:

```bash
pad-lattice listen-actions
```

Press the control pads:

| Pad | Expected action |
| --- | --- |
| `11` | `approve` |
| `12` | `reject` |
| `17` | `retry` |
| `18` | `stop` |

If actions appear there, the hardware and daemon are working. The remaining
piece is the agent-side listener or adapter.

## Another Process Owns the MIDI Port

Only one process can own the Launchpad MIDI ports at a time. Stop any existing
demo or daemon process before starting another one:

```bash
ps -ef | grep pad-lattice
```

Then stop the stale process from the terminal where it is running, or kill it
if needed.

## GitHub Pages Does Not Update

The documentation workflow is intentionally on demand. After pushing, open the
repository Actions tab and run:

```text
Documentation
```

That workflow builds `docs-site/`, verifies the search index, uploads the Pages
artifact, and deploys the site to GitHub Pages.
