"""Collect installed dependency notices without fetching license text from the web."""

import argparse
from importlib import metadata
import json
from pathlib import Path
import subprocess
import sys
import sysconfig
import tomllib

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = ("LICENSE", "LICENCE", "COPYING", "NOTICE", "COPYRIGHT")


def notice_files(root):
    return sorted(p for p in root.rglob("*") if p.is_file()
                  and p.name.upper().startswith(PREFIXES)
                  and "node_modules" not in p.relative_to(root).parts)


def python_packages():
    pending = list(tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"])
    seen = set()
    while pending:
        req = Requirement(pending.pop())
        if req.marker and not req.marker.evaluate():
            continue
        dist = metadata.distribution(req.name)
        name = dist.metadata["Name"]
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        pending.extend(dist.requires or [])
        files = [Path(dist.locate_file(p)) for p in dist.files or []
                 if Path(p).name.upper().startswith(PREFIXES)]
        yield name, dist.version, dist.metadata.get("License-Expression") or "See license text", files, "Python"


def collect(offline=False):
    overrides_root = ROOT / "licenses/upstream"
    overrides = json.loads((overrides_root / "sources.json").read_text())
    entries = list(python_packages())
    python_license = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
    if not python_license.is_file():
        raise RuntimeError("Python runtime LICENSE.txt was not found")
    entries.append(("Python", sys.version.split()[0], "PSF-2.0", [python_license], "Runtime"))
    lock = json.loads((ROOT / "web-app/package-lock.json").read_text())
    for path, info in lock["packages"].items():
        if not path or info.get("dev") or info.get("devOptional"):
            continue
        root = ROOT / "web-app" / path
        package = json.loads((root / "package.json").read_text())
        entries.append((package["name"], package["version"], package.get("license", "See license text"),
                        notice_files(root), "JavaScript"))
    host = next(line.split(": ", 1)[1] for line in subprocess.check_output(
        ["rustc", "-vV"], text=True).splitlines() if line.startswith("host: "))
    command = ["cargo", "metadata", "--locked", "--format-version", "1", "--filter-platform", host,
               "--manifest-path", str(ROOT / "web-app/src-tauri/Cargo.toml")]
    if offline:
        command.append("--offline")
    cargo = json.loads(subprocess.check_output(command, text=True))
    for package in cargo["packages"]:
        if not package["source"]:
            continue
        root = Path(package["manifest_path"]).parent
        entries.append((package["name"], package["version"], package["license"] or "See license text",
                        notice_files(root), "Rust"))
    sections = ["PAD-LATTICE THIRD-PARTY NOTICES\n\n"
                "Generated from installed Python and JavaScript dependencies and the resolved\n"
                "Rust dependency graph (including build dependencies) for " + host + ".\n"
                "Platform-provided libraries are not inventoried here. Shared notice texts\n"
                "appear once in the appendix, referenced by number.\n"]
    missing = []
    notices = {}
    for name, version, license_id, files, ecosystem in sorted(entries):
        text = f"\n{'=' * 72}\n{name} {version} ({ecosystem})\nDeclared license: {license_id}\n"
        override = overrides.get(f"{name}@{version}")
        if not files and override:
            files = [overrides_root / override["file"]]
            text += f"License source: {override['source']}\n"
        if not files:
            missing.append(f"{ecosystem}: {name} {version}")
            text += "No standalone license text in installed package; release review required.\n"
        for path in files:
            body = path.read_text(encoding="utf-8", errors="replace").strip()
            number = notices.setdefault(body, len(notices) + 1)
            text += f"{path.name}: notice {number}\n"
        sections.append(text)
    sections.append("\nNOTICE TEXTS\n")
    sections.extend(f"\n{'=' * 72}\nNotice {number}\n\n{body}\n" for body, number in notices.items())
    return "\n".join(sections), missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "web-app/public/third-party-notices.txt")
    args = parser.parse_args()
    text, missing = collect(args.offline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"Wrote {args.output.name}; {len(missing)} packages need license-text review")
    for package in missing:
        print(f"  {package}")
    if missing:
        raise SystemExit("Missing dependency notices: review before building installers")


if __name__ == "__main__":
    main()
