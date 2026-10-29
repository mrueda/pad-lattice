import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {existsSync, mkdirSync, readFileSync, renameSync, writeFileSync} from 'node:fs';

const plugin = 'io.github.mrueda.pad-lattice';
const version = JSON.parse(readFileSync('package.json', 'utf8')).version;
const manifest = JSON.parse(readFileSync(`${plugin}.sdPlugin/manifest.json`, 'utf8'));
if (manifest.Version !== `${version}.0`) throw Error('Plugin and package versions differ');
mkdirSync('dist', {recursive: true});
execFileSync(process.execPath, ['node_modules/@elgato/cli/bin/streamdeck.mjs', 'pack',
  `${plugin}.sdPlugin`, '--output', 'dist', '--force', '--no-update-check'], {stdio: 'inherit'});
const name = `pad-lattice-${version}.streamDeckPlugin`;
renameSync(`dist/${plugin}.streamDeckPlugin`, `dist/${name}`);
const oldChecksum = `dist/${plugin}.streamDeckPlugin.sha256`;
if (existsSync(oldChecksum)) renameSync(oldChecksum, `dist/${name}.sha256`);
const digest = createHash('sha256').update(readFileSync(`dist/${name}`)).digest('hex');
writeFileSync(`dist/${name}.sha256`, `${digest}  ${name}\n`);
console.log(`Created dist/${name}`);
writeFileSync('dist/source.json', JSON.stringify({version, platform: 'stream-deck',
  dirty: Boolean(execFileSync('git', ['status', '--porcelain', '--untracked-files=no'], {encoding: 'utf8'}).trim()),
  sha: execFileSync('git', ['rev-parse', 'HEAD'], {encoding: 'utf8'}).trim()}, null, 2) + '\n');
