# Browser Surface

The virtual surface implements the same **8x8 matrix, top action rail, status
column, and eight Agent Scenes** as the common Launchpad layout. It is not a
separate agent UI and does not imitate a terminal.

## Public and Live Modes

| Mode | Where it runs | Agent connection |
| --- | --- | --- |
| Public surface | [GitHub Pages](pathname:///play/) | Deterministic Demo, sandbox, and Show only. |
| Local live | `pad-lattice web` | Real Codex sessions on the same computer. |
| Paired LAN | `pad-lattice web --lan` | Real Codex sessions from a phone or tablet on the same trusted network. |
| Mirrored | `pad-lattice daemon --web` | Browser clients and a MIDI controller share one control plane. |

The exact same compiled application serves public and local modes. A local
configuration endpoint selects live transport; the public build cannot discover
or control a daemon.

The public surface presents three modes with distinct roles: **Demo** is the
35-second autoplay walkthrough, **Sandbox** offers repeatable scenarios and editable states, and **Show** is
authored audiovisual playback. In live mode, **Start Demo** and **Start Show**
are administrator commands, matching the `pad-lattice demo` and
`pad-lattice show` CLI experiences.

The public Demo demonstrates session selection, approval, and rejection with a
visible pointer. Pause or replay it, then choose **Try it yourself** to enter
Sandbox. Playback pauses outside its tab and when the browser page is hidden.
It follows the shared Demo graph; only this public presentation advances
automatically. CLI and live demos remain interactive. No real agent actions
are sent. Light/dark appearance is saved in this browser; sound is opt-in.

### Device Layouts

The public **Surface** selector offers Virtual Pad, Launchpad Pro Mk1, and a
15-key, XL, and Neo Stream Deck examples. Switching keeps the same sessions, selection,
scenario history, Demo playback position, and Show playback. The Demo pointer follows the
matching control in each layout. Links can select a view with
`?surface=launchpad` or `?surface=stream-deck`.

`VirtualSurface.tsx` renders both grid layouts; `StreamDeckSurface.tsx` puts one
session glyph in each LCD key. Both use `surfaceModel.ts`, the visual compiler
and palette also used by the real Stream Deck plugin. In Show, the brightest
grid color in each region maps to one key. This is a reduced visual
interpretation, not a 1:1 rendering. Desktop also offers Retry in its virtual
Stream Deck layouts; on Neo it appears outside the eight-key illustration.
Neither feature changes the physical plugin.

These are interactive illustrations, not MIDI/USB emulators or hardware tests.
The desktop selector changes only its local layout; paired browsers, MIDI
controllers, and the physical plugin remain connected. The actual plugin's
key positions are user-configurable.

### Playground Scenarios

Sandbox starts with Builder running, Reviewer waiting for approval, and Tests
in an error state. Other scenarios cover a request answered in Codex, a selected
session disconnecting, and the vocabulary across eight sessions. Background
events advance only when requested; restarting restores the same initial state.
Approve and Retry resume simulated work rather than declaring it successful.

`web-app/src/playground.ts` contains the fixtures and a pure reducer. Inputs
carry the displayed revision, so stale presses cannot act on a changed target.
Tests cover repeated actions, selection, disconnects, reset, and deterministic
replay. The renderer uses the normal visual compiler, but **the scenario engine
is a teaching model, not the Python control plane or a hardware emulator**.
It opens no agent or device connections. Real integrations expose only actions
their backend supports; simulated Retry does not imply Codex supports it.

## Local Live Control

```bash
pad-lattice web
```

The bridge binds to `127.0.0.1:8765`, prints and opens a tokenized local
administrator URL, and starts the normal Unix-socket agent daemon. Use
`--port 0` for an automatically selected port or `--no-open` on a headless
host. The administrator token is random for each daemon and remains in the URL
fragment, so it is not sent with the initial HTTP request.

A loopback browser becomes a local administrator only after presenting that
token. It can see sanitized session labels and semantic state, select Agent
Scenes, and invoke lit actions. The local administrator can generate pairing
credentials for local clients, including the Stream Deck plugin, without enabling
LAN access. With `--lan` enabled, those credentials also work for trusted-network
clients. Paired clients remain non-administrators, even on loopback. Revocation
disconnects all paired clients.
Do not share the tokenized local URL.

The administrator is also the only browser allowed to start or stop Demo and
Show. Paired clients receive the same lifecycle and frames, and may answer the
guided Demo's Scene and action prompts, but cannot replace live state with an
experience themselves.

## Phone and Tablet Pairing

```bash
pad-lattice web --lan
```

`--lan` binds only to the selected private IPv4 interface and adds these
protections:

1. Remote browsers receive no agent state until authenticated.
2. A one-use QR secret or six-digit PIN expires after five minutes.
3. Successful pairing creates a random reconnect token stored only for the
   current daemon process.

The browser stores its reconnect token locally, but a restarted daemon does
not recognize it. Pair again after every daemon restart. A loopback
administrator can create a replacement code or revoke every remote token.
Desktop can also disconnect or revoke individual paired devices. The
`device_disconnected` message stops automatic reconnect without removing the
credential; a `forbidden` error clears it and returns the browser to PIN entry.

For ordinary setup, multiple browsers, and NATed VM instructions, follow
[Connect a Phone, Tablet, or Laptop](../usage/connect-browsers.md). This page focuses on the
surface lifecycle and technical boundary.

## Security Boundary

:::warning Trusted local network only

LAN mode uses local HTTP and WebSocket traffic. Pairing prevents an
unauthenticated browser from controlling agents, but it does not encrypt a
hostile network. A host-to-VM forward may be used inside the trusted LAN, but
never expose the port to the internet, configure router port forwarding, or
use LAN mode on public Wi-Fi.

Use loopback mode when the network is not trusted. A separately managed VPN or
TLS reverse proxy is advanced deployment territory and is not configured by
Pad-Lattice.

:::

The bridge additionally requires same-origin WebSocket requests, validates the
Host header, disables CORS, limits message size, rate-limits PIN failures, and
serves a restrictive Content Security Policy. Authenticated command rates,
browser connection counts, and the daemon-facing event queue are also bounded.
QR secrets remain in the URL fragment and are not sent in the initial HTTP
request.

A paired browser is an authorized control surface, not a read-only viewer. It
can invoke any action currently exposed for the selected agent, including a
request-scoped Approve decision. See the [Security
Model](./security-model.md) for the full trust boundary.

## Data Exposed to Browsers

The browser receives:

- sanitized session label;
- slot and identity accent;
- semantic state and selected state;
- available actions and overflow count;
- compiled Visual Protocol light tokens.
- current Demo/Show lifecycle and, during Show, exact 8x8 plus rail RGB frames;
- semantic browser-audio cue names and the packaged Show soundtrack path.

It does **not** receive prompts, responses, terminal output, full working
directories, raw Codex event payloads, or session metadata. A browser action
still passes the control plane's selection, state, capability, request, and
debounce gates.

## Use Alongside MIDI

```bash
pad-lattice daemon --web
pad-lattice daemon --web --lan
```

The daemon wraps the MIDI and browser implementations in a `CompositeSurface`.
Every authoritative `SurfaceView` is rendered to both. Input events are merged
before routing, but no action is broadcast to agents: one valid press or tap
still reaches one selected subscriber.

`pad-lattice status --json` reports every active surface in its `surfaces`
array and reports `demo`, `show`, or `null` in `experience`.

## Experience Playback

The public and live applications consume the same Version 1 Demo and
performance manifests as the Python runtime. Demo transitions are semantic
`select_session` and `action` events. Show frames use exact RGB values and an
absolute timeline, so a delayed browser skips stale cues instead of extending
the performance.

Each browser has an independent Sound toggle that is muted by default. Demo
uses packaged earcon WAV files; Show uses one generated soundtrack and seeks
when transport drift becomes visible. Host audio remains a separate CLI
choice. Browser autoplay rules therefore never block LEDs or controls.

Inside a live daemon, operational state has priority. If any agent enters
`waiting_for_reply` or `waiting_for_approval`, the daemon stops the active
experience, broadcasts the reason, and immediately renders the real
`SurfaceView` on every surface.

## Current Action Coverage

The virtual surface cannot provide a capability that the connected agent does
not advertise:

| Integration | Available live actions |
| --- | --- |
| Interactive Codex permission hook | Approve and Reject |
| `codex-exec` | Stop |
| Manual action listener | Approve, Reject, Retry, or Stop according to state |

Interactive Stop, Retry, and ordinary chat replies remain outside the current
Codex permission-hook boundary. Their controls stay dark.
