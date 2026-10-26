"""Check desktop metadata against the canonical Python version."""

import ast
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def check_versions(root: Path = ROOT) -> str:
    tree = ast.parse((root / "src/pad_lattice/__init__.py").read_text())
    version = next(ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                   and target.id == "__version__" for target in node.targets))
    packages = ("web-app", "docs-site", "integrations/stream-deck")
    for filename in (*[f"{package}/package.json" for package in packages], "web-app/src-tauri/tauri.conf.json"):
        found = json.loads((root / filename).read_text())["version"]
        if found != version:
            raise ValueError(f"{filename}: version {found} does not match Python {version}")
    for package in packages:
        filename = f"{package}/package-lock.json"
        lock = json.loads((root / filename).read_text())
        if lock["version"] != version or lock["packages"][""]["version"] != version:
            raise ValueError(f"{filename}: root version does not match Python {version}")
    manifest = tomllib.loads((root / "web-app/src-tauri/Cargo.toml").read_text())
    if manifest["package"]["version"] != version:
        raise ValueError("Cargo package version does not match Python")
    lock = tomllib.loads((root / "web-app/src-tauri/Cargo.lock").read_text())
    package = next(item for item in lock["package"] if item["name"] == "pad-lattice-desktop")
    if package["version"] != version:
        raise ValueError("Cargo lockfile version does not match Python")
    plugin = json.loads((root / "integrations/stream-deck/io.github.mrueda.pad-lattice.sdPlugin/manifest.json").read_text())
    if plugin["Version"] != f"{version}.0":
        raise ValueError("Stream Deck manifest version does not match Python")
    citation = (root / "CITATION.cff").read_text().splitlines()
    if f"version: {version}" not in citation:
        raise ValueError("Citation version does not match Python")
    return version


if __name__ == "__main__":
    print(check_versions())
