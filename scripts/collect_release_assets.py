"""Collect final installers and verify a single release checksum manifest."""

import argparse
import hashlib
from pathlib import Path
import shutil


def digest(path):
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def collect(source, target):
    installers = sorted(
        (path for path in source.rglob('*')
         if path.is_file() and path.suffix in ('.dmg', '.AppImage', '.streamDeckPlugin')),
        key=lambda path: path.name,
    )
    if len(installers) != 5 or len({p.name for p in installers}) != 5:
        raise ValueError('Expected five uniquely named installers')
    if sorted(p.suffix for p in installers) != sorted(
        ['.dmg', '.dmg', '.AppImage', '.AppImage', '.streamDeckPlugin']
    ):
        raise ValueError('Expected two DMGs, two AppImages, and one Stream Deck plugin')
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError('Release output directory must be empty')
    entries = []
    for path in installers:
        if any(character in path.name for character in '\r\n\\'):
            raise ValueError('Unsafe installer filename')
        checksum = digest(path)
        destination = target / path.name
        shutil.copy2(path, destination)
        if digest(destination) != checksum:
            raise ValueError(f'Copied installer checksum mismatch: {path.name}')
        entries.append(f'{checksum}  {path.name}\n')
    manifest = target / 'SHA256SUMS'
    manifest.write_text(''.join(entries), encoding='ascii')
    for line in manifest.read_text(encoding='ascii').splitlines():
        expected, name = line.split('  ', 1)
        if digest(target / name) != expected:
            raise ValueError(f'Manifest verification failed: {name}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    collect(args.source, args.target)
