# Codex Integration

Pad-Lattice integrates directly with Codex CLI. Interactive terminal sessions
use Codex lifecycle hooks; non-interactive tasks use the Codex JSONL event
stream. Neither path requires a graphical agent UI.

## Interactive Codex

Install Pad-Lattice's user-level lifecycle hooks once:

```bash
pad-lattice install-codex-hooks
```

The command merges five handlers into `~/.codex/hooks.json` and preserves
other hooks already present. Start a new `codex` or `codex resume` session,
then run `/hooks` to review and explicitly trust the installed commands.

Keep the daemon running in another terminal:

```bash
pad-lattice daemon --no-greeting
```

The hook adapter maps stable Codex lifecycle events to Pad-Lattice states:

| Codex hook | Pad-Lattice state |
| --- | --- |
| `SessionStart` | `waiting_for_reply` |
| `UserPromptSubmit` | `running` |
| `PermissionRequest` | `waiting_for_approval` |
| `PostToolUse` | `running` |
| `Stop` | `success`, then `waiting_for_reply` |

The hook is passive. It never approves, denies, rewrites, or stops a Codex
operation. If the daemon is offline, it exits successfully so Codex continues
normally.

Codex includes `session_id`, working directory, and model in each lifecycle
event. Pad-Lattice forwards that metadata in the local state message in
preparation for multi-agent selection and routing. The current daemon still
shows one global state, so simultaneous sessions can overwrite one another on
the display.

Hooks do not expose individual keystrokes, so the surface cannot switch to a
typing state as soon as the first character is entered.

## Non-interactive Codex

Use `codex-exec` for real Codex CLI runs that expose JSON-line events:

```bash
pad-lattice codex-exec "summarize this repository"
```

The adapter runs:

```bash
codex exec --json ...
```

and maps Codex events to Pad-Lattice states:

| Codex event | Pad-Lattice state |
| --- | --- |
| `thread.started` | `running` |
| `turn.started` | `running` |
| `item.started` | `running` |
| `turn.completed` | `success` |
| `turn.failed` | `error` |
| `error` | `error` |

`success` and `error` are transient. The daemon shows them briefly and then
returns to `waiting_for_reply`.

## Hook trust and scope

Codex hooks are enabled by default, but non-managed command hooks do not run
until reviewed and trusted. Codex records trust against the exact hook
definition; reinstalling a changed definition requires another review.

The installer targets the user-level hook file so the integration follows you
across repositories. Use an explicit path for a project-local setup:

```bash
pad-lattice install-codex-hooks --path .codex/hooks.json
```

Project-local hooks run only after Codex trusts both the project configuration
layer and the hook definition.
