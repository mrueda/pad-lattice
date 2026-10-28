# Desktop Architecture

**Tauri owns the window and bundled Python service.** React displays the pad;
Python connects Codex sessions and routes actions to physical and virtual surfaces.
Desktop, browser, and CLI share the same control plane.

For setup, use [Desktop Pad](../usage/desktop.md). For the overall design, see
the [architecture diagram](./architecture.md).

## Code Map

| Layer | Start here |
| --- | --- |
| Native window and process ownership | `web-app/src-tauri/src/` |
| Conversations and settings UI | `web-app/src/DesktopControls.tsx`, `OpenConversations.tsx` |
| Discovery and live attachment | `codex_discovery.py`, `codex_attachment.py` |
| Python service and startup | `desktop_service.py`, `desktop_entry.py` |
| Shared surface transport | `web-app/src/desktop.ts`, `live.ts` |
| Attention and hardware checks | `web-app/src/AttentionView.tsx`, `HardwareTest.tsx`, `devices/test_run.py` |
| Bundled interpreter and assets | `scripts/build_desktop_engine.py` |

Python modules are under `src/pad_lattice/`. Routing stays in `ControlPlane`,
not in the native window or individual surfaces.

## Process Ownership

Tauri starts one engine and exchanges ID-tagged JSON requests and surface events
over private stdin/stdout. Closing the app stops that engine, **not Codex**.
If another daemon owns the socket, startup fails rather than replacing it.

Discovery runs on a worker so the pad stays responsive. Losing MIDI does not
disconnect browser surfaces or release session leases. The optional LAN listener
can stop without resetting the control plane.

Native settings and attachment commands are **not exposed to paired browsers**.
See [Security Model](./security-model.md) for pairing and access boundaries.

Attention queries also run on the worker. The control plane records when a state
begins using a monotonic clock; duplicate updates and selection do not reset it.
The list carries the daemon revision so a stale row cannot select a reused slot.

The hardware wizard and CLI share a nonblocking `ProfileTestRun`. Desktop owns its
test ports separately from live MIDI, consumes all test input, and cancels on live
sessions, playback, device loss, shutdown, or a 30-second interface timeout.
Reports contain device checks only; a native save dialog controls their destination.

## Conversation Lifetime

1. **Discover:** read summaries of loaded CLI threads from the same user's Codex
   control socket. Never start a server, resume a thread, or send a turn.
2. **Connect:** explicitly join a loaded CLI-owned thread. No model, sandbox,
   or permission overrides are sent.
3. **Observe and act:** translate events into the shared surface protocol.
   Each supported pending request gets a one-shot action subscription.
4. **Disconnect:** release the lease and socket without interrupting Codex.
   Never silently replay actions or reconnect automatically.

**Approve/Reject applies to one supported request; Stop applies to one known
running turn.** Multiple simultaneous approvals, special permissions, identity
checks, prompts, and ordinary replies remain in Codex. Resolved requests and
connection loss clear the controls.

Desktop attachment needs no Pad-Lattice hooks. The independent
[CLI integration](./codex-integration.md) uses scoped hooks instead.

<details>
<summary>Discovery and routing safeguards</summary>

Discovery checks ownership of the WebSocket-over-Unix-socket endpoint under
`$CODEX_HOME` (normally `~/.codex/app-server-control/app-server-control.sock`).
It pages `thread/loaded/list` and reads summaries with `includeTurns: false`,
bounded to 64 threads and six seconds. Only IDs, names, folders, and normalized
states reach the UI. Transcripts and tool output are not retained or forwarded.

Refresh replaces the discovered list; active attachments can supplement it
during discovery failure. Codex may retain threads after their terminal closes.

Connect sends `thread/resume` with only `threadId` and `excludeTurns: true`.
An attachment may fetch one metadata-only turn to identify work already running.
It fails if scoped hooks already own the thread or all eight slots are occupied.

Approve/Reject requires exactly one pending request supporting `accept`/`decline`.
Each subscription has a fresh capability token. Server events are drained before
dispatch; Codex decides whether another client already answered. Stop includes
the current thread and turn IDs.

See the [Codex app-server reference](https://learn.chatgpt.com/docs/app-server).

</details>

## Settings and Devices

Typed preferences are merged and written atomically to `settings.json` in the
platform app-data directory. They contain no credentials, project data, or saved
connections. [Installation](../usage/install.md) lists storage and uninstall steps.

The sound preference covers live cues, Demo, and Show. Reconnecting does not
replay old cues. CLI audio remains independent. Pairing records last only for the
engine's lifetime; disconnect waits for manual reconnect, while revocation
requires pairing again.

<details>
<summary>Audio and pairing implementation</summary>

Live `audio_cue` events carry a cue name and session slot through IPC and browser
WebSockets. Muting stops playback. Desktop uses cached blob URLs because WebKit
cannot play bundled `tauri://` audio URLs directly; they are released when the
player closes. Linux needs GStreamer's good plugins for WAV playback.

Native `paired_devices`, `disconnect_device`, and `revoke_device` commands use
random device IDs. Credentials never appear in the UI. LAN reconfiguration
revokes paired clients and retains the existing host and message checks.
Device `kind` groups browsers and Stream Deck plugins in Settings. Like the
display name, it comes from the client and grants no permissions.

</details>

## Build From Source

<details>
<summary>Build from source</summary>

Install Python 3.12, Node.js 24, Rust 1.90, and the
[Tauri prerequisites](https://v2.tauri.app/start/prerequisites/), then run:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[desktop-build]'
npm --prefix web-app ci
npm --prefix web-app run build
.venv/bin/python scripts/build_desktop_engine.py
npm --prefix web-app run desktop
```

Use `npm --prefix web-app run desktop:build` for installers. Linux ARM64 is
supported; native Windows requires additional backend work.

The engine build collects Python, npm, and resolved Cargo license notices for
offline access in About. Missing texts stop the build. `licenses/upstream/`
provides texts omitted by archives; `sources.json` records provenance.
Use the collector's `--offline` option when Cargo sources are cached.
Platform libraries are outside this inventory.

</details>

<details>
<summary>Tests and acceptance checks</summary>

- `tests/test_desktop.py`: lifecycle, validation, settings, routing, and MIDI failures.
- `tests/test_codex_discovery.py`: read-only discovery, ownership, limits, and failures.
- `tests/test_codex_attachment.py`: a simulated Codex server with the real daemon,
  covering stale approvals, unsupported prompts, turn-specific Stop, and disconnect.

Set `PAD_LATTICE_TEST_ENGINE` to test the bundled engine, including relocation.
Native smoke builds exercise the WebView with isolated sockets and settings.

A live Codex 0.164.0 join/state/detach check succeeded without starting a turn.
Interactive approval, physical hardware, installer publication, and
signing/notarization remain separate release acceptance checks.

</details>

<details>
<summary>Reproduce the documentation walkthrough</summary>

With project dependencies, Playwright Chromium, and FFmpeg installed:

```bash
npm --prefix web-app run build
node scripts/render_desktop_demo.mjs
```

This records the real renderer and Python service with **simulated discovery,
attachment, agent events, and MIDI status**. Approval uses the ordinary socket
protocol. No live Codex session or physical controller receives commands.

The muted MP4 and poster go to `docs-site/static/media/`.
`PLAYWRIGHT_CHROMIUM_PATH` selects an existing browser executable.

</details>
