# Quick Start

Install Pad-Lattice locally from the repository root:

```bash
python3 -m pip install -e .
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

Use the raw MIDI monitor when mapping or debugging hardware:

```bash
pad-lattice monitor-midi --seconds 15
```
