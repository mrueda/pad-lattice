import {build} from 'esbuild';
import {readFileSync, writeFileSync, mkdirSync, copyFileSync} from 'node:fs';
import {Resvg} from '@resvg/resvg-js';
import {Grid2X2} from 'lucide';
import {buildProfiles} from './profiles.mjs';
const images = 'io.github.mrueda.pad-lattice.sdPlugin/images';
const licenses = 'io.github.mrueda.pad-lattice.sdPlugin/licenses';
mkdirSync(images, {recursive: true});
mkdirSync(licenses, {recursive: true});
copyFileSync('../../LICENSE', `${licenses}/Pad-Lattice.txt`);
for (const name of ['@elgato/streamdeck', '@elgato/schemas', '@elgato/utils', 'ws', 'zod', 'lucide']) {
  copyFileSync(`node_modules/${name}/LICENSE`, `${licenses}/${name.replace('@', '').replace('/', '-')}.txt`);
}
const logo = readFileSync('../../assets/pad-lattice-logo.svg', 'utf8');
const grid = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2">${Grid2X2[2].map(([tag, attrs]) => `<${tag} ${Object.entries(attrs).map(([k, v]) => `${k}="${v}"`).join(' ')}/>`).join('')}</svg>`;
for (const [name, svg, size] of [['icon', logo, 72], ['plugin', logo, 256], ['category', grid, 28]]) {
  for (const [suffix, factor] of [['', 1], ['@2x', 2]]) {
    writeFileSync(`${images}/${name}${suffix}.png`, new Resvg(svg, {fitTo: {mode: 'width', value: size * factor}}).render().asPng());
  }
}
await build({
  entryPoints: ['src/plugin.ts'], bundle: true, platform: 'node', target: 'node24',
  format: 'esm', outfile: 'io.github.mrueda.pad-lattice.sdPlugin/bin/plugin.js',
  banner: {js: 'import {createRequire} from "node:module"; const require = createRequire(import.meta.url);'},
});
await buildProfiles('io.github.mrueda.pad-lattice.sdPlugin');
