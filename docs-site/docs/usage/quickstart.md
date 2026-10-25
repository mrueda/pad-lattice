# Quick Start

**The desktop app is the recommended way to use Pad-Lattice interactively.**
It connects to your open Codex CLI conversations and gives them a shared
visual control surface. No MIDI controller is required.

## 1. Install Desktop

Follow [Install](./install.md) to get the preview build for Linux or macOS.
Python and the Pad-Lattice engine are bundled; Codex CLI must already be
installed and authenticated on the same computer.

Desktop is currently a preview, separate from the published PyPI CLI.

## 2. Connect a Conversation

1. Open Codex CLI in your project as you normally do.
2. Open **Pad-Lattice**. Its local service starts automatically.
3. Find the chat under **Open Codex conversations** and select **Connect**.
4. Note its **Scene number and color**. Use the same process for other open chats.

You do not need to restart Codex, launch another terminal from Pad-Lattice, or
install hooks for this connection. Names and working folders come from Codex.
Use **Refresh chats** if a newly opened conversation is missing.

## 3. Use the Pad

The right-side numbered buttons select conversations. The large symbol shows
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

- **Launchpad:** connect it over USB, then use **Settings > MIDI controller > Connect**.
- **Phone or tablet:** use **Settings > Phone and tablet** to enable pairing on
  your trusted private network. Follow [Connect Screens](./connect-browsers.md).

Every connected surface shares the same selected conversation and actions.
The desktop app manages the service; do not start a second daemon alongside it.

## Try It Without Codex

Disconnect real conversations, then choose **Explore > Demo** for guided
interaction or **Explore > Show** for the audiovisual story. Both work without
MIDI hardware. **Sound** is optional; **Back to live pad** ends the simulation.

For a no-installation preview, [try the public pad](pathname:///play/).
It is a simulation and cannot control your agents.

## Prefer the Terminal?

The [CLI Setup](./cli.md) remains available from PyPI for terminal-based and
headless use. It does not require the desktop app.

Continue with [Desktop App](./desktop.md) for preferences and connection
management, or [Troubleshooting](./troubleshooting.md) if something is missing.
