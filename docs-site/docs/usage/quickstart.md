# Quick Start

## Try It Now

Open the [virtual pad](pathname:///play/) on any modern desktop, phone, or tablet. The
guided simulation demonstrates three agents, explicit selection, a real-looking
approval gate, retry, and shared success. Its sandbox then exposes the complete
Visual Protocol 1 vocabulary.

No account, MIDI hardware, API key, or installation is required. This public
mode is deliberately simulated.

## Install

Install the current GitHub version as an isolated command:

```bash
pipx install git+https://github.com/mrueda/pad-lattice.git
```

Confirm the installation:

```bash
pad-lattice --version
pad-lattice doctor
```

The normal package includes physical MIDI support, the local browser bridge,
and QR pairing.

## Control Real Codex in a Browser

Start the virtual surface:

```bash
pad-lattice web
```

Pad-Lattice prints and opens a loopback URL. Leave this process running; it is
both the agent daemon and local browser bridge.

Launch an integrated session:

```bash
pad-lattice codex --label implementation
```

On the first Pad-Lattice-launched session, run `/hooks` to review and trust the
scoped commands. Prompt, running, approval, and completion states then update
automatically. Ordinary `codex` sessions do not load these hooks or show their
review prompt.

When Codex requests permission, select its Agent Scene and tap the lit Approve
or Reject control. A decision applies only to the selected session and current
request. After 60 seconds without a surface decision, Codex restores its normal
keyboard prompt.

## Phone and Tablet

Expose the virtual surface to the trusted local network:

```bash
pad-lattice web --lan
```

The local admin page shows a one-use QR code and six-digit PIN that expire in
five minutes. Scan the QR or open the printed LAN URL and enter the PIN. The
paired device can reconnect until the daemon stops.

Use `--advertise-host` when automatic address selection chooses the wrong
network interface:

```bash
pad-lattice web --lan --advertise-host 192.168.1.20
```

LAN mode is for a network you trust. Do not port-forward it or use it on public
Wi-Fi. See [Virtual Surface](./virtual-surface.md) for pairing and security.

## Multiple Sessions

Start or resume labeled sessions from other terminals:

```bash
pad-lattice codex --label docs -- resume <SESSION_ID>
pad-lattice codex --label review
pad-lattice status --watch
```

Each session receives a stable accent and one of eight visible Agent Scenes.
Background updates change their compact status pads without stealing selection.
Closing a leased launcher removes its Scene immediately.

## Physical Launchpad

Discover attached hardware and run the supported-device demo:

```bash
pad-lattice ports
pad-lattice devices
pad-lattice demo
```

Run normal physical control by itself:

```bash
pad-lattice daemon --no-greeting
```

Mirror the same state and actions in browsers at the same time:

```bash
pad-lattice daemon --web --no-greeting
pad-lattice daemon --web --lan --audio-feedback
```

Only the daemon owns MIDI ports. Every surface feeds the same selected-session
action router, so a tap and a physical press have identical semantics.

Experimental profiles must be selected explicitly:

```bash
pad-lattice demo --profile novation/launchpad/mini-mk3
pad-lattice demo --profile novation/launchpad/pro-mk3
```

## Audiovisual Hardware Show

Stop the daemon, then run:

```bash
pad-lattice show
pad-lattice show --audio
```

**A Spark Becomes a Constellation** is an authored 43-second performance across
the full physical surface. `--audio` adds its synchronized score.

## Development Checkout

```bash
git clone https://github.com/mrueda/pad-lattice.git
cd pad-lattice
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```
