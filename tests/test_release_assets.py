import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    'collect_release_assets', Path(__file__).parents[1] / 'scripts/collect_release_assets.py'
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReleaseAssetsTest(unittest.TestCase):
    def populate(self, root):
        for name in ('linux-x64.AppImage', 'linux-arm64.AppImage',
                     'macos-x64.dmg', 'macos-arm64.dmg', 'plugin.streamDeckPlugin'):
            directory = root / name.split('.')[0]
            directory.mkdir(parents=True)
            (directory / name).write_bytes(name.encode())
            (directory / (name + '.sha256')).write_text('internal checksum')
        (root / 'source.json').write_text('{}')

    def test_collect_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'input', Path(tmp) / 'output'
            self.populate(source)
            module.collect(source, target)
            self.assertEqual(len(list(target.iterdir())), 6)
            lines = (target / 'SHA256SUMS').read_text().splitlines()
            self.assertEqual(len(lines), 5)
            for line in lines:
                checksum, name = line.split('  ', 1)
                self.assertEqual(checksum, hashlib.sha256((target / name).read_bytes()).hexdigest())
            self.assertEqual(lines, sorted(lines, key=lambda line: line.split('  ', 1)[1]))

    def test_missing_installer(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                module.collect(Path(tmp), Path(tmp) / 'output')

    def test_duplicate_installer(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'input'
            self.populate(source)
            (source / 'duplicate').mkdir()
            (source / 'duplicate/linux-x64.AppImage').write_bytes(b'duplicate')
            with self.assertRaises(ValueError):
                module.collect(source, Path(tmp) / 'output')

    def test_output_must_be_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'input', Path(tmp) / 'output'
            self.populate(source)
            target.mkdir()
            (target / 'stale.sha256').touch()
            with self.assertRaises(ValueError):
                module.collect(source, target)
