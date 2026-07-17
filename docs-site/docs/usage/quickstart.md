# Quick Start

Install Pad-Lattice as an isolated command with
[pipx](https://pipx.pypa.io/):

```bash
pipx install pad-lattice
```

Alternatively, install it into the active Python environment:

```bash
python3 -m pip install pad-lattice
```

Confirm the installation:

```bash
pad-lattice --version
```

List MIDI ports:

```bash
pad-lattice ports
```

Run the hardware demo:

```bash
pad-lattice demo
```

Start the daemon:

```bash
pad-lattice daemon --no-greeting
```

Install interactive Codex lifecycle hooks:

```bash
pad-lattice install-codex-hooks
```

Start a new Codex CLI session and run `/hooks` to review and trust the
Pad-Lattice commands. The Launchpad will then follow prompt, running, approval,
and completion states automatically.

Send a state from another terminal:

```bash
pad-lattice send-state running
pad-lattice send-state success
```

Listen for hardware actions:

```bash
pad-lattice listen-actions
```

Press the mapped control pads:

| Pad | Action |
| --- | --- |
| `11` | `approve` |
| `12` | `reject` |
| `17` | `retry` |
| `18` | `stop` |

Interactive hooks currently display state only. Directly applying these
hardware actions to an interactive Codex session is still planned.

Use the raw MIDI monitor when mapping or debugging hardware:

```bash
pad-lattice monitor-midi --seconds 15
```

## Development version

Install the current GitHub version without cloning the repository:

```bash
pipx install git+https://github.com/mrueda/pad-lattice.git
```

Use `pipx upgrade pad-lattice` after new commits are published.
