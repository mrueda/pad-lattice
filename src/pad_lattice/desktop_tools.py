"""Executable discovery and native-terminal launching for the desktop app."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

from pad_lattice.codex_session import normalize_session_label

TESTED_CODEX_VERSION = "0.164.0"
TERMINALS = {"gnome-terminal": ["--"], "konsole": ["-e"], "xfce4-terminal": ["-x"], "xterm": ["-e"]}


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
        features = subprocess.run([executable, "features", "list"], capture_output=True,
                                  text=True, timeout=10, env=host_environment(), check=True)
        if not re.search(r"^hooks\s+(?:stable|experimental|under development)\s+(?:true|false)\s*$", features.stdout, re.M):
            raise ValueError("This Codex CLI does not expose lifecycle hooks.")
        if tuple(map(int, version.split("."))) < (0, 164, 0):
            raise ValueError(f"Desktop integration requires Codex CLI {TESTED_CODEX_VERSION} or newer.")
        return {"available": True, "path": executable, "version": version,
                "tested": version == TESTED_CODEX_VERSION, "tested_version": TESTED_CODEX_VERSION}
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return {"available": False, "error": str(exc), "tested_version": TESTED_CODEX_VERSION}


def terminal_choices() -> list[str]:
    if sys.platform == "darwin":
        return ["Terminal.app"]
    return [name for name in TERMINALS if shutil.which(name, path=host_environment()["PATH"])]


def engine_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "pad_lattice.desktop_entry"]


def launch_session(params: dict[str, object], socket_path: str, directory: Path) -> dict[str, object]:
    cwd = Path(str(params.get("cwd", ""))).expanduser().resolve(strict=True)
    if not cwd.is_dir():
        raise ValueError("Choose a project folder.")
    label = normalize_session_label(str(params.get("label", "")))
    inspection = inspect_codex(str(params.get("codex", "")))
    if not inspection["available"]:
        raise ValueError(str(inspection["error"]))
    resume = str(params.get("resume", "")).strip()
    if resume and not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", resume):
        raise ValueError("Enter a session ID to resume.")
    choices = terminal_choices()
    terminal = str(params.get("terminal", "")) or (choices[0] if choices else "")
    if terminal not in choices:
        raise ValueError("No supported terminal found. Install or select a terminal in Settings.")
    command = engine_command() + ["session", "--socket", socket_path, "--cwd", str(cwd),
                                  "--label", label or cwd.name, "--codex", str(inspection["path"])]
    if resume:
        command += ["--resume", resume]
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, filename = tempfile.mkstemp(prefix="launch-", suffix=".command", dir=directory)
    script = Path(filename)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write("#!/bin/sh\n" + "rm -f -- " + shlex.quote(str(script)) + "\n")
            output.write("exec " + shlex.join(command) + "\n")
        script.chmod(0o700)
        env = host_environment()
        if sys.platform == "darwin":
            # Pass the command as an argument, never interpolate it into AppleScript.
            subprocess.run(["/usr/bin/osascript", "-e", "on run argv\n tell application \"Terminal\"\n activate\n do script (item 1 of argv)\n end tell\nend run", shlex.join([str(script)])],
                           check=True, timeout=10, env=env, capture_output=True)
        else:
            subprocess.Popen([terminal, *TERMINALS[terminal], str(script)], env=env,
                             start_new_session=True, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except BaseException:
        script.unlink(missing_ok=True)
        raise
    return {"launched": True, "label": label, "codex_version": inspection["version"]}
