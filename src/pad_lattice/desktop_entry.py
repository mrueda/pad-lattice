"""Packaged entry point shared by the desktop service and terminal helpers."""

from __future__ import annotations

import argparse
import os
import shlex
import sys


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "codex-hook":
        from pad_lattice.codex_hook_entry import main as hook
        return hook(arguments[1:])
    from pad_lattice import __version__
    parser = argparse.ArgumentParser(prog="pad-lattice-engine")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="mode", required=True)
    service = sub.add_parser("service")
    service.add_argument("--settings-dir", required=True)
    service.add_argument("--socket")
    session = sub.add_parser("session")
    session.add_argument("--socket", required=True)
    session.add_argument("--cwd", required=True)
    session.add_argument("--label", required=True)
    session.add_argument("--codex", required=True)
    session.add_argument("--resume")
    args = parser.parse_args(arguments)
    if args.mode == "service":
        from pad_lattice.desktop_service import run
        return run(args.settings_dir, args.socket)
    from pad_lattice.codex_session import run_codex_session
    from pad_lattice.desktop_tools import engine_command, host_environment
    os.chdir(args.cwd)
    environment = host_environment()
    os.environ.clear()
    os.environ.update(environment)
    hook = shlex.join(engine_command() + ["codex-hook", "--socket", args.socket])
    return run_codex_session(["resume", args.resume] if args.resume else [], args.socket,
                             label=args.label, codex_binary=args.codex, hook_command=hook)


if __name__ == "__main__":
    raise SystemExit(main())
