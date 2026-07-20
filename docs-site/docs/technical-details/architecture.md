# Architecture

Pad-Lattice separates **agent integration**, **deterministic policy**, and
**surface translation**. A browser and a MIDI controller are peers at the
surface boundary; neither owns agent state or decides where an action goes.

:::tip New to the codebase?

Read the [Developer Guide](./developer-guide.md) next for end-to-end code paths,
failure behavior, and the change map.

:::

![Pad-Lattice architecture from local agent adapters through one control plane to synchronized browser and MIDI surfaces](/img/architecture.svg)

_State flows from agent adapters to every enabled surface. Scene selections
and actions return through one capability-gated router._

## Design Boundaries

- Agent adapters know agent events and Wire Protocol 1, but not browser layout,
  LED colors, or MIDI addresses.
- `ControlPlane` is the sole authority for sessions, selection, leases,
  overflow, action capability gates, and action targets.
- `PadLatticeDaemon` adapts sockets, clocks, rendering, and surface input to
  that policy.
- `SurfaceView` is the stable semantic boundary between policy and rendering.
- Visual Protocol 1 turns semantic state into glyphs and light tokens without
  knowing whether the output is CSS or MIDI.
- The browser adapter authenticates clients and exposes only sanitized surface
  state. It does not expose Wire Protocol 1.
- Device profiles and trusted drivers translate semantics into hardware I/O;
  they know nothing about Codex events.

These boundaries let a new agent backend, browser client, or physical device
evolve independently.

## Components

| Module | Purpose |
| --- | --- |
| `pad_lattice.events` | Agent identities, semantic states, and actions. |
| `pad_lattice.protocol` | Typed Wire Protocol 1 commands over bounded JSON lines. |
| `pad_lattice.client` | Public Python API for agent integrations. |
| `pad_lattice.control_plane` | Deterministic sessions, slots, selection, leases, previews, and action routing. |
| `pad_lattice.daemon_runtime` | Unix socket selector loop, surface polling, and rendering adapter. |
| `pad_lattice.devices.base` | `SurfaceView`, semantic input events, and the `ControlSurface` contract. |
| `pad_lattice.devices.composite` | Compatible multi-surface fan-out and event merge. |
| `pad_lattice.visual_protocol` | Device-independent glyphs and semantic light tokens. |
| `pad_lattice.web_protocol` | Narrow, versioned browser command and rendering contract. |
| `pad_lattice.web_surface` | Static app server, WebSocket authentication, pairing, and browser event queue. |
| `pad_lattice.experience_manifest` | Dependency-free Version 1 Demo and performance manifest loader. |
| `pad_lattice.experience_runtime` | Nonblocking Demo graph and absolute-time Show playback shared by standalone commands and daemon. |
| `pad_lattice.experience_compiler` | Authoring-time compiler for the performance manifest and browser WAV assets. |
| `pad_lattice.devices.profiles` | Dependency-free device-profile parsing and catalog. |
| `pad_lattice.devices.midi_grid` | Trusted palette-grid driver with optional show-only RGB SysEx. |
| `pad_lattice.identity_store` | Bounded LRU of hashed identity-to-accent preferences. |
| `pad_lattice.audio` | Optional semantic earcons, WAV synthesis, and system-player output. |
| `pad_lattice.codex_hooks` | Interactive Codex lifecycle adapter and scoped-hook configuration. |
| `pad_lattice.codex_session` | Native-terminal Codex launcher and reconnecting lease. |
| `pad_lattice.codex_exec` | Non-interactive Codex JSONL adapter and Stop sink. |

## One Control Plane, Many Surfaces

`ControlPlane.surface_view()` produces one immutable semantic snapshot. A
single surface renders it directly. `CompositeSurface` sends the same snapshot
to each compatible child and merges their `ActionPressed` and
`SessionSelected` events.

Compatibility is explicit: children must have equal selector capacity, accent
order, and Visual Protocol version. Initialization rolls back already-opened
children if a later child fails, and shutdown closes children in reverse order.

Both browser taps and MIDI presses therefore enter the same control-plane
method. They do not choose a socket client themselves. Selection, current
state, live capability, request ordering, and debounce checks still determine
whether one subscriber receives an action.

## Execution Model

The daemon uses one synchronous `selectors` loop for authoritative state. On
each iteration it expires sessions, renders dirty state, handles Unix-socket
clients, and polls surface event queues. The control plane receives an explicit
clock value, keeping policy deterministic in tests.

The browser HTTP/WebSocket server runs in an adapter thread because client
connections wait independently. It compiles no policy. Browser commands become
semantic events in a thread-safe queue, which the daemon consumes on its next
poll. Rendering travels in the opposite direction as a compiled, sanitized
surface message.

MIDI polling remains in the daemon loop. Optional audio starts nonblocking
system-player processes and cannot change routing decisions.

## Shared Demo and Show Pipeline

Python remains the expressive authoring source for the visual story and score,
but neither runtime executes that authoring code independently. The asset
compiler produces a compact Version 1 performance manifest, exact RGB frames,
one synchronized browser soundtrack, and the browser earcon bank. This
deterministic build boundary is the **experience asset compiler**. The guided
Demo is a Version 1 stage graph of semantic views and transitions. The browser
build copies both manifests and audio into the packaged application.

At runtime, Python loads the packaged artifact through small structural
parsers; TypeScript consumes the same JSON. `ExperienceController` advances
Demo transitions from `SessionSelected` and `ActionPressed` events, and chooses
Show cues from absolute monotonic time. A delayed iteration skips stale Show
cues instead of accumulating timing drift.

Standalone `demo` and `show` commands use that controller directly. The live
daemon embeds the same controller in its normal selector loop, so sockets and
surface input remain responsive. Any real agent in `waiting_for_reply` or
`waiting_for_approval` preempts playback and forces an authoritative semantic
render. Only a loopback administrator may send browser start/stop commands;
paired clients may answer Demo inputs and receive Show frames.

See [Experience Asset Compiler](./developer-guide.md#experience-asset-compiler)
for the complete authoring, compilation, validation, and playback path.

## Protocols and Schemas

Pad-Lattice has versioned contracts with different audiences:

| Contract | Audience | Carries |
| --- | --- | --- |
| Wire Protocol 1 | Trusted local agent integrations | State, identity, leases, inspection, subscriptions, targeted actions. |
| Web Surface Protocol 1 | Authenticated browser clients | Compiled visual frames, sanitized labels, Scene selection, actions, pairing administration. |
| Visual Protocol 1 | Any conforming surface | Glyph shapes, semantic colors, identity accents, actions, and overflow. |
| Demo Manifest 1 | Python and browser experience runtimes | Prompt stages, semantic views, and allowed transitions. |
| Performance Manifest 1 | Python and browser experience runtimes | Exact full-surface frames, absolute cue durations, palette, and audio metadata. |

Device Profile Schema 1 translates the visual contract to trusted MIDI-driver
data. Packaged JSON Schemas document the two transports, device profiles, and
both experience manifests for editors, CI, and conformance tooling. Runtime
code uses small typed parsers instead of general schema validation in live
paths.

See [Socket Protocol](../reference/socket-protocol.md), [Browser
Surface](./virtual-surface.md), [Visual
Protocol](./visual-language.md), and [Device
Profiles](./device-profiles.md).

## Browser Security Boundary

Loopback browser clients must present the daemon's random administrator token.
LAN clients receive no state before presenting a valid one-use pairing secret,
PIN, or in-memory session token, and the LAN listener binds only to the selected
private interface. The server also checks Host and same-origin WebSocket
headers, disables CORS, caps frames, bounds clients and pending events,
rate-limits failed PINs and authenticated commands, and serves a restrictive
Content Security Policy.

Only labels, states, slots, accents, available actions, overflow, compiled
light tokens, and explicit Demo/Show lifecycle data reach the browser. Show
adds exact full-surface RGB frames; Demo adds its built-in prompt text. Real
agent prompts, responses, terminal output, full working directories, raw Codex
events, and arbitrary Wire Protocol commands do not.

Pairing authenticates control but does not encrypt LAN traffic. The supported
network scope is a trusted local network, never an internet-facing port.
See the [Security Model](./security-model.md) for the complete threat model.

## Platform Scope

Agent integrations currently use Unix-domain sockets, so real Codex control is
supported on Linux and compatible Unix-like systems. The public browser demo
runs anywhere with a modern browser because it is a deterministic simulation.
The virtual live surface broadens the client device to desktop, phone, and
tablet, but it does not move the agent daemon away from the local Unix host.
