# Control Codex

Pad-Lattice shows what Codex is doing and gives you physical or browser
controls for actions that Codex makes available.

## 1. Start a Control Surface

Choose the setup you want and leave its terminal open:

| I want to use... | Command |
| --- | --- |
| A browser on this computer | `pad-lattice web` |
| A connected Launchpad | `pad-lattice daemon --no-greeting` |
| A Launchpad and browsers together | `pad-lattice daemon --web --no-greeting` |
| A phone, tablet, or another laptop | Follow [Connect a Phone, Tablet, or Laptop](./connect-browsers.md). |

Every enabled surface mirrors the same Agent Scenes and available actions.

## 2. Start Codex Through Pad-Lattice

Open another terminal in your project and run:

```bash
pad-lattice codex --label work
```

Use any short label that helps you recognize the session, such as `docs`,
`tests`, or `review`. The label and its Scene color appear on every surface.

:::important Use the Pad-Lattice launcher

A plain `codex` process does not connect to Pad-Lattice. Start or resume the
conversation through `pad-lattice codex` whenever you want surface control.

:::

## 3. Review Hooks Once

The first Pad-Lattice-launched Codex session asks you to review its hooks. In
Codex, enter:

```text
/hooks
```

Review and trust the Pad-Lattice definitions. They apply only to Codex sessions
started by the Pad-Lattice launcher; ordinary Codex sessions remain unchanged.

## 4. Read the Surface

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
a permanent permission rule. If no surface decision arrives within 60 seconds,
Codex returns to its normal keyboard prompt.

## Resume an Existing Conversation

Use the Codex session ID you normally resume:

```bash
pad-lattice codex --label work -- resume <SESSION_ID>
```

You cannot attach hooks to a Codex process that is already running. Exit that
process and resume it with the command above.

## Run Several Agents

Start each session in its own terminal with a clear label:

```bash
pad-lattice codex --label implementation
pad-lattice codex --label docs -- resume <SESSION_ID>
pad-lattice codex --label review
```

Up to eight sessions remain visible as Agent Scenes. Selecting a Scene on a
Launchpad, phone, or laptop updates every other connected surface. A background
agent may change its status, but it never steals selection.

For a text legend in another terminal, run:

```bash
pad-lattice status --watch
```

## Current Limits

Interactive Codex currently exposes request-scoped **Approve** and **Reject**
to Pad-Lattice. Ordinary chat replies, typing state, interactive Stop, and
Retry remain in the Codex terminal because current hooks do not provide those
control points.

For hook events, timeout behavior, non-interactive `codex-exec`, and routing
details, see [Codex Integration](../technical-details/codex-integration.md).
