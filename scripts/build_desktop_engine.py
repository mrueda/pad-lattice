"""Bundle Python, MIDI libraries, and the shared web/experience assets."""

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts/collect_desktop_notices.py")], check=True)
    shutil.copy2(ROOT / "web-app/public/third-party-notices.txt",
                 ROOT / "src/pad_lattice/web_dist/play/third-party-notices.txt")
    work = ROOT / "build/desktop-engine"
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--name", "pad-lattice-engine", "--noupx", "--distpath", str(work / "dist"),
        "--workpath", str(work / "work"), "--specpath", str(work),
        "--paths", str(ROOT / "src"), "--collect-all", "pad_lattice",
        "--collect-all", "mido", "--collect-all", "rtmidi", "--collect-all", "websockets",
        "--collect-all", "segno", "--copy-metadata", "pad-lattice",
        str(ROOT / "scripts/desktop_engine_entry.py"),
    ], check=True)
    built = work / "dist/pad-lattice-engine"
    subprocess.run([str(built / "pad-lattice-engine"), "--version"], check=True, cwd="/tmp")
    target = ROOT / "web-app/src-tauri/engine"
    if target.is_symlink():
        raise ValueError("Refusing to replace a symlinked engine directory")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(built, target, symlinks=True)


if __name__ == "__main__":
    main()
