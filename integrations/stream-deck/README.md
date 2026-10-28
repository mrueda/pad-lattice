# Pad-Lattice Stream Deck Plugin

**Experimental; not physically tested or published to the Elgato Marketplace.**
**One Session key represents one Codex conversation.** Its name and color strip
identify the session; its glyph shows the state. Press it to select. The white
border marks which session the separate **Approve**, **Reject**, and **Stop**
keys control; those action keys also show its name.

An editable **Pad-Lattice - 15 keys** starter profile places eight sessions
above Approve, Reject, and Stop. It installs separately without switching your
current profile. Other deck sizes need a manual layout. The plugin does not emulate an
8x8 controller across the keys or run Demo/Show.

## Install

Download `pad-lattice-0.2.0.streamDeckPlugin` from the
[release assets](https://github.com/mrueda/pad-lattice/releases), then open it on
the computer running Elgato Stream Deck. No Node.js installation is needed to
use the packaged plugin. Requires Stream Deck 7.1+ and Pad-Lattice 0.2.0+.

## Build from Source

Use Node.js 24 and Stream Deck 7.1 or newer on macOS or Windows. From this folder:

```sh
npm ci
npm run typecheck
npm run build
npm test
npm run pack
```

Open the generated `dist/*.streamDeckPlugin` file on the machine running Elgato's
Stream Deck software. The source build, tests, and packaging can also run on
Linux, but the official Stream Deck host application cannot.

## Pair and Use

1. Run Pad-Lattice Desktop (or `pad-lattice web`) and connect your Codex sessions.
2. Choose **Settings > Devices > Stream Deck > Pair device**. Note its address and PIN.
3. In Elgato's profile menu, choose **Pad-Lattice - 15 keys**. Select any
   Pad-Lattice key, enter the address and PIN, and press **Pair**.
4. For a custom layout, add **Session** keys with different slot numbers and
   **Approve**, **Reject**, and **Stop** keys. Pairing is shared; do not pair every key.
5. Press a session key to select it. A white border identifies the selection.
   Action keys show its label and only become available when the bridge permits it.

Use the actual displayed port, not necessarily 8765. Same-computer pairing uses
`http://127.0.0.1:PORT` without enabling LAN access. For a VM or a different
computer, enable trusted-LAN pairing and use the reachable private IPv4 address;
see the [connection guide](https://mrueda.github.io/pad-lattice/docs/usage/connect-browsers).
The plugin accepts only HTTP localhost/private IPv4 origins, not arbitrary hosts,
administrator URLs, public addresses, or reverse-proxy paths.

After restarting the plugin or Pad-Lattice, create a new PIN and pair again.
**Disconnect** forgets the plugin's in-memory credential. **Revoke paired devices**
in Pad-Lattice invalidates all paired credentials, including this plugin's.
Never enable trace logging while pairing or share logs containing credentials.

## Implementation

- `src/bridge.ts`: authenticated WebSocket connection, bounded messages,
  memory-only reconnect token, heartbeat, backoff, and fail-closed action gating.
- `src/plugin.ts`: official SDK lifecycle, per-key settings, coalesced rendering,
  and property-inspector messages. Only the bridge address persists globally;
  action settings contain only the session slot.
- `src/render.ts`: the **existing web surface glyph compiler and palette** plus
  Lucide action icons. No second alphabet or copied glyph table.
- `ui/settings.*` inside the plugin: local property inspector; no external scripts.
- `tests/`: rendering/transport checks and a bundled-plugin test with simulated
  Elgato and Pad-Lattice WebSocket hosts. These do not prove hardware compatibility.
- `scripts/profiles.mjs`: generates the editable starter profile, with fixed
  identifiers and no connection credentials. Its archive structure follows
  [Elgato's exported Lights Out profiles](https://github.com/elgatosf/streamdeck/tree/b6e9b3923495ef3b729734dbda7b23a88dd5de2d/examples/lights-out/com.elgato.lightsout.sdPlugin)
  and [official profile bundling](https://docs.elgato.com/streamdeck/sdk/guides/profiles/).
  Archive generation uses the CLI's existing zip.js dependency at build time,
  declared explicitly; it is not bundled into the plugin runtime.

Every plugin selection/action carries the control revision shown on the key.
The daemon checks it immediately before routing the queued event. A changed
selection, replaced request, or other control-state change causes rejection and
a fresh frame; the plugin never retries an action automatically. Sessions share
selection with the desktop, browsers, and MIDI surface. A revision is not a
credential; authenticated pairing and the daemon's normal request/capability
checks still apply.

No prompts, terminal output, filesystem access, shell execution, or Codex API
credentials are required. LAN traffic is unencrypted and requires a trusted
network. The plugin does not provide Windows support for the Python engine:
its bridge must run on a platform supported by Pad-Lattice.

`npm run pack` uses Elgato's official validator and packaging CLI, producing the
installer, SHA-256 checksum, and source revision in `dist/`. Both manual build
workflows upload these; desktop builds use the same commit for app and plugin.
Generated bundles/installers are ignored by Git. The narrowly scoped Zod override updates
the SDK utility's `zod/v4-mini` implementation to its security-fixed release;
the bundled SDK test covers startup and message handling with that override.

To regenerate the documentation diagram from the actual key renderer:

```sh
node --import tsx scripts/diagram.ts
```

Hardware acceptance: verify pairing, session labels/selection, approval/rejection,
Stop, unavailable actions, disconnect/reconnect, revocation, long labels, and
coexistence with other plugins. Report exact device, OS, and Stream Deck version.
