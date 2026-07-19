# Quick Start

## Try It Now

Open the [virtual pad](pathname:///play/) on any modern desktop, phone, or tablet. The
guided simulation demonstrates three agents, explicit selection, a real-looking
approval gate, retry, and shared success. Its sandbox then exposes the complete
Visual Protocol 1 vocabulary, while Show plays the full audiovisual story.

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

Pad-Lattice prints and opens a tokenized loopback administrator URL. Leave this
process running; it is both the agent daemon and local browser bridge. Treat
that URL as a credential and do not share it.

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

Continue with [Control Codex](./control-codex.md) for resuming conversations,
running several agents, and understanding what each surface state means.

## Phone, Tablet, or Laptop

Expose the virtual surface to the trusted local network:

```bash
pad-lattice web --lan
```

The local admin page shows a one-use QR code and six-digit PIN that expire in
five minutes. Scan the QR or open the printed LAN URL and enter the PIN. The
paired device can reconnect until the daemon stops.

See [Connect a Phone, Tablet, or Laptop](./connect-browsers.md) for one or more
devices, network troubleshooting, and Parallels Desktop. LAN mode is for a
network you trust; never expose it through a router or use it on public Wi-Fi.

## Physical Launchpad

Discover attached hardware and run the supported-device demo:

```bash
pad-lattice ports
pad-lattice devices
pad-lattice demo
```

Demo and Show can also run without MIDI:

```bash
pad-lattice demo --surface web
pad-lattice show --surface web
```

The tokenized local page opens first. Choose **Demo** or **Show** there to
start. Its Sound control is muted by default and belongs only to that browser.
Use `--surface both` to keep a Launchpad and every browser synchronized.

Run normal physical control by itself:

```bash
pad-lattice daemon --no-greeting
```

Mirror the same state and actions in browsers at the same time:

```bash
pad-lattice daemon --web --no-greeting
```

Only the daemon owns MIDI ports. Every surface feeds the same selected-session
action router, so a tap and a physical press have identical semantics.

## Where Next

| I want to... | Continue with... |
| --- | --- |
| Resume or run several Codex sessions | [Control Codex](./control-codex.md) |
| Connect several browser devices | [Connect a Phone, Tablet, or Laptop](./connect-browsers.md) |
| Learn the colors and symbols | [Visual Protocol](../technical-details/visual-language.md) |
| Enable sounds | [Audio Feedback](./audio-feedback.md) |
| Play the audiovisual story | [Visual Show](./visual-show.md) |
| Test experimental hardware | [Device Testing](../technical-details/device-testing.md) |
| Work on Pad-Lattice itself | [Developer Guide](../technical-details/developer-guide.md) |
