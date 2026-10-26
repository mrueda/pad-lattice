# Pad-Lattice Stream Deck Plugin

**Experimental; not physically tested or published to the Elgato Marketplace.**
The official Elgato SDK plugin presents one session glyph per LCD key, with
separate Approve, Reject, and Stop keys. It does not emulate an 8x8 controller
across the keys or run Demo/Show.

## Build and Install

Use Node.js 24 and Stream Deck 7.1 or newer on macOS or Windows. From this folder:

```sh
npm ci
npm run typecheck
npm run build
npm test
npm run pack
```

Open the generated `.streamDeckPlugin` file on the machine running Elgato's
Stream Deck software. The source build, tests, and packaging can also run on
Linux, but the official Stream Deck host application cannot.

## Pair and Use

1. Run the current Pad-Lattice desktop preview (or `pad-lattice web` from this
   checkout) and connect your Codex CLI sessions. Released 0.1.0 predates this plugin.
2. Choose **Pair device** beside the pad. Note its address and six-digit PIN.
3. In Stream Deck, drag **Pad-Lattice > Session** onto a key. Choose its session
   number, enter the address and PIN, and press **Pair**.
4. Add more Session keys and assign different numbers. Add **Approve**, **Reject**,
   and **Stop** keys. Pairing is shared across the plugin; do not pair every key.
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

`npm run pack` uses Elgato's official validator and packaging CLI. Generated
bundles/installers are ignored by Git. The narrowly scoped Zod override updates
the SDK utility's `zod/v4-mini` implementation to its security-fixed release;
the bundled SDK test covers startup and message handling with that override.

To regenerate the documentation diagram from the actual key renderer:

```sh
node --import tsx scripts/diagram.ts
```

Hardware acceptance: verify pairing, session labels/selection, approval/rejection,
Stop, unavailable actions, disconnect/reconnect, revocation, long labels, and
coexistence with other plugins. Report exact device, OS, and Stream Deck version.
