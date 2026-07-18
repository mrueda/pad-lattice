"""Lightweight Codex hook entry point."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO


SocketChecker = Callable[[str], bool]


def daemon_socket_available(socket_path: str) -> bool:
    """Return whether the configured daemon socket currently exists."""

    try:
        return Path(socket_path).is_socket()
    except OSError:
        return False


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    socket_checker: SocketChecker = daemon_socket_available,
) -> int:
    """Run one hook, or drain it as a no-op when no daemon is listening."""

    parser = argparse.ArgumentParser(
        prog="pad-lattice-hook",
        description="Forward one Codex lifecycle event to a running Pad-Lattice daemon.",
    )
    parser.add_argument("--socket", required=True, help="daemon Unix socket path")
    parser.add_argument(
        "--approval-timeout",
        type=float,
        default=60.0,
        help="seconds to wait for a surface approval decision",
    )
    args = parser.parse_args(argv)
    if args.approval_timeout <= 0:
        parser.error("--approval-timeout must be positive")

    input_stream = sys.stdin if stdin is None else stdin
    output_stream = sys.stdout if stdout is None else stdout
    socket_path = os.environ.get("PAD_LATTICE_SOCKET", args.socket)

    if not socket_checker(socket_path):
        # Consume Codex's payload so the parent can finish writing without a
        # broken pipe, but avoid loading the full CLI or parsing tool output.
        input_stream.read()
        return 0

    from pad_lattice.codex_hooks import run_codex_hook

    return run_codex_hook(
        socket_path,
        input_stream,
        output_stream,
        approval_timeout=args.approval_timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
