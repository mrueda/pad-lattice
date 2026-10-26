# Elgato Stream Deck

import {StreamDeckDiagram} from '@site/src/components/SurfaceVisuals';

:::caution Experimental preview

The Elgato Stream Deck plugin is available as a **source build**, not a Marketplace
download. Automated tests cover the integration, but physical hardware testing
is still needed. Use the current Pad-Lattice checkout, not the older PyPI release.

:::

**One key represents one Codex session.** Its color identifies the session and
its glyph shows the current state. Press the key to select it; a white border
marks the selection. Separate **Approve**, **Reject**, and **Stop** keys act on
that session and show its name.

<StreamDeckDiagram />

This is the same visual vocabulary as the Launchpad, placed inside LCD keys
rather than spread across the controller. You choose the layout and can keep
your other Stream Deck actions. Up to eight session slots are available.

## Connect

1. Install the plugin using its [build instructions](https://github.com/mrueda/pad-lattice/tree/main/integrations/stream-deck).
2. Open Pad-Lattice and connect your Codex conversations.
3. Open **Settings > Phones & tablets > Pair device** for an address and one-use PIN.
4. Add a **Session** key in Elgato's Stream Deck software. Enter that address and
   PIN in its settings, then press **Pair**. Choose the session number for the key.
5. Add other session keys and the action keys. **Pair once for the whole plugin.**

The official Stream Deck application runs on macOS or Windows. The Pad-Lattice
bridge still runs on a supported Linux or macOS computer. On the same computer,
use the displayed localhost address; no network sharing is needed. If the bridge
is in a VM or on another computer, follow [Connect Screens](./connect-browsers.md)
and use its reachable private IPv4 address.

## What to Expect

- **Dim action:** unavailable for the selected session. It does nothing.
- **Selection changed before a press arrived:** the action is rejected. Check
  the updated selection and press again; approvals are never retried automatically.
- **Connection lost:** keys lose their live state and controls are disabled.
- **Plugin or Pad-Lattice restarted:** generate a new PIN and pair again.
- **Revoke access:** removes the selected device in Desktop's paired-device list.
- **Revoke paired devices:** removes all paired devices from the pairing window.

Read the actual request in Codex before approving. The keys do not display
prompts or replace the conversation. Demo, Show, dials, and touch strips are
outside this first integration.

A compact alphabet for smaller LED grids remains a future design exploration;
Stream Deck uses the existing full-resolution glyphs.
