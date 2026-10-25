# Control Codex

Pad-Lattice shows what Codex is doing and gives you physical or browser
controls for actions that Codex makes available.

## Connect Your Chats

Open **Pad-Lattice**, find your existing chat under **Open Codex conversations**,
and select **Connect**. Codex continues in its original terminal.
The [Quick Start](./quickstart.md) covers installation and the first connection.

No hooks are needed for desktop attachment. The independent
[CLI workflow](./cli.md) instead uses `pad-lattice codex` and scoped hook review;
choose that path when you want to run without the desktop app.

## Read the Surface

The selected Agent Scene fills the center of the pad. Its shape and color tell
you the current state:

| You see | Codex is... |
| --- | --- |
| White question mark | waiting for your reply |
| Blue dots | working |
| Amber exclamation mark | asking for permission |
| Green happy face | finished successfully |
| Red X | reporting an error |

The right-side Agent Scenes identify active sessions. Select a Scene before
acting on that agent. See [Visual Protocol](../technical-details/visual-language.md)
for the complete color and symbol reference.

## Approve or Reject a Request

When Codex requests permission:

1. Find the Agent Scene with the amber status.
2. Select that Scene if another agent is selected.
3. Tap or press the lit green **Approve** or red **Reject** control.
4. Confirm that the amber request clears.

The decision applies only to that selected, current request. It does not create
a permanent permission rule. Review the request in Codex before deciding.
A control goes dark when the request is resolved or no supported decision is
available. The CLI hook path has a separate 60-second surface-decision timeout.

## Resume an Existing Conversation

Resume the conversation in Codex as you normally would, then select
**Refresh chats > Connect** in Pad-Lattice. The desktop does not start or resume
Codex processes for you.

For the CLI-only setup, use
`pad-lattice codex --label work -- resume <SESSION_ID>` instead.

## Run Several Agents

Open the Codex chats you need and connect each from the desktop list.
Names and working folders come from Codex. Match each chat to its Scene number
and color; new connections use an available slot without renumbering existing ones.

Up to eight sessions remain visible as Agent Scenes. Selecting a Scene on a
Launchpad, phone, or laptop updates every other connected surface. A background
agent may change its status, but it never steals selection.

## Current Limits

| Action | Desktop connection | CLI hooks |
| --- | --- | --- |
| Approve / Reject | One supported pending command or file-change request | Current permission request |
| Stop | Known running turn | Not exposed by permission hooks |
| Retry, typing, ordinary replies | Stay in Codex | Stay in Codex |

When several approval requests are pending in the same desktop-connected chat,
use Codex to resolve them: the pad will not guess which request you mean.
Special permission changes and identity verification also remain in Codex.

See [Desktop Architecture](../technical-details/desktop.md) for live attachment
and [Codex Integration](../technical-details/codex-integration.md) for CLI hooks
and non-interactive tasks.
