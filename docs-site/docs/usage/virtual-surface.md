# Virtual Surface

The virtual surface implements the same **8x8 matrix, top action rail, status
column, and eight Agent Scenes** as the common Launchpad layout. It is not a
separate agent UI and does not imitate a terminal.

## Public and Live Modes

| Mode | Where it runs | Agent connection |
| --- | --- | --- |
| Public demo | [GitHub Pages](pathname:///play/) | Deterministic simulation only. |
| Local live | `pad-lattice web` | Real Codex sessions on the same computer. |
| Paired LAN | `pad-lattice web --lan` | Real Codex sessions from a phone or tablet on the same trusted network. |
| Mirrored | `pad-lattice daemon --web` | Browser clients and a MIDI controller share one control plane. |

The exact same compiled application serves public and local modes. A local
configuration endpoint selects live transport; the public build cannot discover
or control a daemon.

## Local Live Control

```bash
pad-lattice web
```

The bridge binds to `127.0.0.1:8765`, opens the browser, and starts the normal
Unix-socket agent daemon. Use `--port 0` for an automatically selected port or
`--no-open` on a headless host.

Loopback browsers are local administrators. They can see sanitized session
labels and semantic state, select Agent Scenes, and invoke lit actions. When
`--lan` is enabled, the local administrator can also generate pairing
credentials and revoke remote clients.

## Phone and Tablet Pairing

```bash
pad-lattice web --lan
```

`--lan` adds three explicit protections:

1. Remote browsers receive no agent state until authenticated.
2. A one-use QR secret or six-digit PIN expires after five minutes.
3. Successful pairing creates a random reconnect token stored only for the
   current daemon process.

The browser stores its reconnect token locally, but a restarted daemon does
not recognize it. Pair again after every daemon restart. A loopback
administrator can create a replacement code or revoke every remote token.

If the printed address is wrong because the host has VPN, container, or several
network interfaces, select the reachable address explicitly:

```bash
pad-lattice web --lan --advertise-host 192.168.1.20 --port 8765
```

## Security Boundary

:::warning Trusted local network only

LAN mode uses local HTTP and WebSocket traffic. Pairing prevents an
unauthenticated browser from controlling agents, but it does not encrypt a
hostile network. Never expose the port to the internet, configure router port
forwarding, or use LAN mode on public Wi-Fi.

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

## Data Exposed to Browsers

The browser receives:

- sanitized session label;
- slot and identity accent;
- semantic state and selected state;
- available actions and overflow count;
- compiled Visual Protocol light tokens.

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
array.

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
