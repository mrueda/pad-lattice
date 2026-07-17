# Codex Integration

Pad-Lattice integrates with Codex CLI through two documented event paths.
Interactive terminals use lifecycle hooks; non-interactive tasks use the
`codex exec --json` event stream. Neither path requires a graphical UI.

## Install the Hooks

Install the user-level hooks once:

```bash
pad-lattice install-codex-hooks
```

The installer merges five handlers into `~/.codex/hooks.json` and preserves
other hooks. It records an absolute Pad-Lattice executable and resolved socket
path. Start a new session, then run `/hooks` to review and explicitly trust the
commands. Reinstalling a changed definition requires another review.

| Codex hook | Pad-Lattice state |
| --- | --- |
| `SessionStart` | `waiting_for_reply` |
| `UserPromptSubmit` | `running` |
| `PermissionRequest` | `waiting_for_approval`; wait for hardware decision |
| `PostToolUse` | `running` |
| `Stop` | `success`, then `waiting_for_reply` |

The hook forwards `session_id` as the stable agent identity. Working directory,
model, and label are display metadata, never identity keys. Simultaneous
sessions occupy separate slots; an update from an unselected session changes
only its status LED.

## Integrated Launcher

Use the Pad-Lattice launcher for labeled terminals and reliable cleanup:

```bash
pad-lattice codex --label implementation
pad-lattice codex --label docs -- resume <SESSION_ID>
```

Everything after `--` is passed to Codex unchanged when an explicit separator
is useful:

```bash
pad-lattice codex --label review -- --ask-for-approval on-request
```

This is a thin process launcher, not a terminal emulator. Codex inherits the
real stdin, stdout, and stderr. The launcher keeps a reconnecting Unix-socket
lease open and sets a terminal title such as `[S2 MAGENTA] docs`. Closing or
terminating the child closes the lease, clears its Scene, and never silently
selects another agent.

`--no-terminal-title` leaves Codex's normal title behavior unchanged. Without
`--label`, the hook uses the Codex working-directory name.

Use the live screen legend when several agents are active:

```bash
pad-lattice status --watch
```

The legend matches Scene number and accent to label, project, state, short
session ID, and lease status.

## Hardware Approval and Rejection

For a Codex permission request:

1. The requesting session changes to the amber approval state.
2. Select its right-side Agent Scene if it is not already selected.
3. Press the lit green Approve or red Reject control.
4. The hook returns a one-request `allow` or `deny` decision directly to Codex.

Each pending request has a unique request ID. One press reaches exactly one
selected request; concurrent requests for the same agent are handled in
arrival order and actions are never broadcast. Approve does not create a
persistent permission rule.

The hook waits 60 seconds. A timeout, unavailable daemon, or disconnected
controller returns control to Codex's normal keyboard approval prompt. Action
controls are completely dark when no live request can consume them.

This path uses Codex's supported `PermissionRequest` hook output. It does not
scrape terminals or inject synthetic keys.

## Direct Codex Fallback

Plain `codex` and `codex resume` sessions still report state and accept
hardware permission decisions after the hooks are trusted. Codex exposes no
terminal-close hook, so direct sessions use the 24-hour unleased-session TTL
or explicit cleanup:

```bash
pad-lattice status
pad-lattice end-session --backend codex --session-id <SESSION_ID>
```

The leased launcher is the recommended multi-agent path because it clears
Scenes immediately and supplies terminal labels.

## Interactive Action Boundary

`PermissionRequest` provides a supported decision point for Approve and
Reject. Interactive Stop, Retry, and ordinary yes/no chat replies are not
permission decisions and remain unavailable. Supporting those actions
requires a broader Codex app-server or equivalent control integration.

Hooks do not expose individual keystrokes, so live `user_typing` state is also
unavailable.

## Non-Interactive Tasks

Use `codex-exec` for a real Codex CLI run with JSON-line events:

```bash
pad-lattice codex-exec "summarize this repository"
```

The adapter maps these events:

| Codex event | Pad-Lattice state |
| --- | --- |
| `thread.started` | `running` |
| `turn.started` | `running` |
| `item.started` | `running` |
| `turn.completed` | `success` |
| `turn.failed` | `error` |
| `error` | `error` |

Each invocation generates a unique agent identity and subscribes only to Stop.
After selecting that task on the controller, the common top-rail Stop control
(`CC 98`) terminates that process without affecting
another concurrent `codex-exec` task.

## Hook Trust and Scope

Codex records trust against the exact hook definition. Reinstalling a changed
definition requires another review. To install project-local hooks instead:

```bash
pad-lattice install-codex-hooks --path .codex/hooks.json
```

Use `--socket PATH` when the daemon runs on a non-default socket. Reinstall the
hooks after changing that path. The launcher also exports its socket path to
the child, allowing one integrated invocation to override the installed
default.

Set a different hardware wait when installing hooks:

```bash
pad-lattice install-codex-hooks --approval-timeout 90
```

The installed Codex handler timeout includes a five-second shutdown margin.

Project hooks run only after Codex trusts both the project configuration layer
and the hook definition.
