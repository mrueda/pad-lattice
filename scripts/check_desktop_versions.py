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
    for filename in ("web-app/package.json", "web-app/src-tauri/tauri.conf.json"):
        found = json.loads((root / filename).read_text())["version"]
        if found != version:
            raise ValueError(f"{filename}: version {found} does not match Python {version}")
    manifest = tomllib.loads((root / "web-app/src-tauri/Cargo.toml").read_text())
    if manifest["package"]["version"] != version:
        raise ValueError("Cargo package version does not match Python")
    return version


if __name__ == "__main__":
    print(check_versions())
