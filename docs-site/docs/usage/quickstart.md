# Quick Start

import {StateLegend} from '@site/src/components/SurfaceVisuals';

**The desktop app is the recommended way to use Pad-Lattice interactively.**
It connects to your open Codex CLI conversations and gives them a shared
visual control surface. No MIDI controller is required.

## 1. Install Desktop

Follow [Install](./install.md) to get the app for Linux or macOS.
Python and the Pad-Lattice engine are bundled; Codex CLI must already be
installed and authenticated on the same computer.

## 2. Connect a Conversation

1. Open Codex CLI normally, or resume a saved chat, on the same computer.
2. Open **Pad-Lattice**. Its local service starts automatically.
3. Find the chat under **Codex conversations** and select **Connect**.
4. Note its **Scene number and color**. Use the same process for other open chats.

You do not need to restart Codex, launch another terminal from Pad-Lattice, or
install hooks for this connection. Names and working folders come from Codex.
Use **Refresh chats** if a newly opened conversation is missing.
If a closed chat remains listed, disconnect it or use its trash icon to remove
it from Pad-Lattice. This does not delete Codex history.

## 3. Use the Pad

<StateLegend />

Choose **Grid**, **Stream Deck**, **XL**, or **Neo** above the pad. These are
on-screen layouts; no physical controller is required.
In Grid, the right-side numbered buttons select conversations. The large symbol shows
the selected conversation's state. When Codex asks for permission:

1. Read the request in the Codex terminal.
2. Select that chat's Scene on the pad.
3. Press the lit green **Approve** or red **Reject** control.

The decision applies only to the selected request. **Stop** is available for a
known running turn. Ordinary prompts and replies stay in Codex.

Use **Maximize pad** to give the pad the window. The selected chat's name stays
below it; press Escape or **Restore workspace** to return.
See [Control Codex](./control-codex.md) for the symbols and action limits.

## 4. Add a Controller or Another Screen

See the [Device Catalog](./device-catalog.md) for supported and experimental hardware.

- **Launchpad:** connect it over USB, then use **Settings > Devices > MIDI controllers > Connect**.
- **Elgato Stream Deck, XL, or Neo:** install the experimental plugin and pair
  once through **Settings > Devices > Stream Deck**. Follow [Stream Deck setup](./stream-deck.md#connect).
- **Phone or tablet:** use **Settings > Devices > Browsers** to enable network access on
  your trusted private network. Follow [Connect Screens](./connect-browsers.md).

Every connected surface shares the same selected conversation and actions.
The desktop app manages the service; do not start a second daemon alongside it.

## Try It Without Codex

Disconnect real conversations, then choose **Demo & Show > Demo** for guided
interaction or **Demo & Show > Show** for the audiovisual story. Both work without
MIDI hardware. **Sound** is optional; **Back to live pad** ends the simulation.

For a no-installation preview, [try the public pad](pathname:///play/).
It is a simulation and cannot control your agents.

## Prefer the Terminal?

The [CLI Setup](./cli.md) remains available from PyPI for terminal-based and
headless use. It does not require the desktop app.

Continue with [Desktop App](./desktop.md) for preferences and connection
management, or [Troubleshooting](./troubleshooting.md) if something is missing.
