# Codex Integration

Pad-Lattice integrates with Codex CLI through two documented event paths.
Interactive terminals use lifecycle hooks; non-interactive tasks use the
`codex exec --json` event stream. Neither path requires a graphical UI.

## Interactive Sessions

Install the user-level hooks once:

```bash
pad-lattice install-codex-hooks
```

The installer merges five handlers into `~/.codex/hooks.json` and preserves
other hooks. Start a new `codex` or `codex resume` session, then run `/hooks` to
review and explicitly trust the commands.

| Codex hook | Pad-Lattice state |
| --- | --- |
| `SessionStart` | `waiting_for_reply` |
| `UserPromptSubmit` | `running` |
| `PermissionRequest` | `waiting_for_approval` |
| `PostToolUse` | `running` |
| `Stop` | `success`, then `waiting_for_reply` |

The hook forwards `session_id` as the stable agent identity. Working directory
and model are optional display metadata, never identity keys. Simultaneous
sessions occupy separate slots; an update from an unselected session changes
only its status LED.

Codex does not currently expose a `SessionEnd` lifecycle hook. Finished
interactive identities remain registered until the background-session TTL
expires or they are removed explicitly:

```bash
pad-lattice status
pad-lattice end-session --backend codex --session-id <SESSION_ID>
```

The hook is deliberately passive. It never approves, denies, rewrites, or
stops an operation. If the daemon is unavailable, it exits successfully so
Codex continues normally. Hooks also do not expose individual keystrokes, so
live `user_typing` state is unavailable on this path.

## Interactive Action Limitation

Lifecycle hooks are reliable state inputs, but they do not provide a general
external-interrupt channel. Pad-Lattice therefore does not scrape terminals,
inject synthetic keys, or launch Codex inside a second pseudo-terminal.

An interactive session currently has no live action subscriber, so approve,
reject, retry, and stop remain dim. Future work requires a supported Codex
action bridge with request correlation and a keyboard fallback.

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

Project hooks run only after Codex trusts both the project configuration layer
and the hook definition.
