"""Packaged entry point for the desktop service."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    from pad_lattice import __version__
    parser = argparse.ArgumentParser(prog="pad-lattice-engine")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="mode", required=True)
    service = sub.add_parser("service")
    service.add_argument("--settings-dir", required=True)
    service.add_argument("--socket")
    args = parser.parse_args(argv)
    from pad_lattice.desktop_service import run
    return run(args.settings_dir, args.socket)


if __name__ == "__main__":
    raise SystemExit(main())
