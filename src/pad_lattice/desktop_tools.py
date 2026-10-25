"""Executable discovery for the desktop app."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

TESTED_CODEX_VERSION = "0.164.0"


def host_environment() -> dict[str, str]:
    env = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "DYLD_LIBRARY_PATH"):
        env.pop(name, None)
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env.pop("LD_LIBRARY_PATH_ORIG")
    elif getattr(sys, "frozen", False):
        env.pop("LD_LIBRARY_PATH", None)
    paths = env.get("PATH", "").split(os.pathsep)
    paths += [str(Path.home() / ".local/bin"), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    paths += [str(p) for p in sorted((Path.home() / ".nvm/versions/node").glob("*/bin"), reverse=True)]
    env["PATH"] = os.pathsep.join(dict.fromkeys(p for p in paths if p))
    return env


def resolve_codex(configured: str = "") -> str:
    candidate = configured or shutil.which("codex", path=host_environment()["PATH"])
    if not candidate:
        raise ValueError("Codex CLI was not found. Install it, or choose its executable in Settings.")
    path = Path(candidate).expanduser().absolute()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("The selected Codex executable is unavailable.")
    return str(path)


def inspect_codex(configured: str = "") -> dict[str, object]:
    try:
        executable = resolve_codex(configured)
        result = subprocess.run([executable, "--version"], capture_output=True, text=True,
                                timeout=10, env=host_environment(), check=True)
        match = re.search(r"codex-cli (\d+\.\d+\.\d+)(?:\s|$)", result.stdout)
        if match is None:
            raise ValueError("The executable did not report a stable Codex CLI version.")
        version = match.group(1)
        if tuple(map(int, version.split("."))) < (0, 164, 0):
            raise ValueError(f"Desktop integration requires Codex CLI {TESTED_CODEX_VERSION} or newer.")
        return {"available": True, "path": executable, "version": version,
                "tested": version == TESTED_CODEX_VERSION, "tested_version": TESTED_CODEX_VERSION}
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return {"available": False, "error": str(exc), "tested_version": TESTED_CODEX_VERSION}
