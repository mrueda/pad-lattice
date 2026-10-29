# How It Works

import {StateLegend} from '@site/src/components/SurfaceVisuals';
import DesktopWalkthrough from '@site/src/components/DesktopWalkthrough';

Pad-Lattice shows what Codex is doing and gives you physical or browser
controls for actions that Codex makes available.

**Connect a chat, recognize its state, select it, then act.** Colors identify
sessions; glyphs show their states. Prompts, ordinary replies, and the actual
permission request stay in Codex, where you review them before deciding.

<DesktopWalkthrough />

Choose a virtual or physical surface in the [Device Catalog](./device-catalog.md).
All connected surfaces share the same selected conversation. On the desktop,
browser, and Launchpad, the main grid shows the selected session and the right
rail selects sessions. On [Stream Deck](./stream-deck.md), **one Session key
represents one Codex conversation**: its name and color identify it, and its
glyph shows its state. Press it to select; separate action keys name their target.

## Connect Your Chats

Open **Pad-Lattice**, find your existing chat under **Codex conversations**,
and select **Connect**. Codex continues in its original terminal.
The [Quick Start](./quickstart.md) covers installation and the first connection.

No hooks are needed for desktop attachment. The independent
[CLI workflow](./cli.md) instead uses `pad-lattice codex` and scoped hook review;
choose that path when you want to run without the desktop app.

## Read the Surface

The glyph on the main grid, or inside a Stream Deck session key, shows its state:

<StateLegend />

Select a right-side Agent Scene or a Stream Deck session key before
acting on that agent. See [Visual Protocol](../technical-details/visual-language.md)
for the complete color and symbol reference.

## Approve or Reject a Request

When Codex requests permission:

1. Find the session with an amber approval status: a right-side Agent Scene on
   a grid surface, or a Stream Deck Session key showing an amber **!**.
2. Select that session. On Stream Deck, its key gains a white border.
3. Read its request in Codex, then press the lit green **Approve** or red
   **Reject** control. Stream Deck action keys also show the selected session's name.
4. Confirm that the amber request clears.

The decision applies only to that selected, current request. It does not create
a permanent permission rule. Review the request in Codex before deciding.
Only available actions light up. Ordinary replies and unsupported requests stay in Codex.

## Resume an Existing Conversation

Resume the conversation in Codex, then select
**Refresh chats > Connect** in Pad-Lattice. The desktop does not start or resume
Codex processes for you.

For the CLI-only setup, use
`pad-lattice codex --label work -- resume <SESSION_ID>` instead.

## Run Several Agents

Open the Codex chats you need and connect each from the desktop list.
Names and working folders come from Codex. Match each chat to its Scene number
and color; new connections use an available slot without renumbering existing ones.

Up to eight session slots are available. Selecting an Agent Scene or a Stream
Deck Session key updates every connected surface. A background agent may change
its status, but it never steals selection.
