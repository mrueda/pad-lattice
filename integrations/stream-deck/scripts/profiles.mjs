import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {ZipWriter, Uint8ArrayWriter, TextReader} from '@zip.js/zip.js';

// Archive structure follows Elgato's exported Lights Out profile. See README.md.
const profiles = {
  standard: {name: 'pad-lattice-15', title: 'Pad-Lattice - 15 keys', model: '20GAA9901',
    profile: '85996A0A-C431-42C9-98E4-554813C20D22', fallback: '68c7aa15-c38b-4c8f-ac47-56786e2eaf69',
    pages: ['fe21f0b9-8737-4d19-a28a-de4a7095eaa3']},
  xl: {name: 'pad-lattice-xl', title: 'Pad-Lattice - Stream Deck XL', model: '20GAT9901',
    profile: '9e206947-1d81-42c4-b619-ef6a1c52ca4b', fallback: '37acc394-5962-4a56-968c-f39458fb3b22',
    pages: ['950e76a5-f582-41d4-8844-afb16450e44a']},
  neo: {name: 'pad-lattice-neo', title: 'Pad-Lattice - Stream Deck Neo', model: '20GBJ9901',
    profile: 'c422a57e-7ff1-4d86-a9f1-a59d3d91c329', fallback: '3da8de15-fac0-426b-8ae8-038f73a84046',
    pages: ['eab846a8-fc33-44c2-bb91-436069caabda', 'aacaa927-563b-4510-b879-754442f1d175']},
};

export function pageFolder(uuid) {
  const bits = [...Buffer.from(uuid.replaceAll('-', ''), 'hex')]
    .map(byte => byte.toString(2).padStart(8, '0')).join('').padEnd(130, '0');
  // Elgato's alphabet omits U; Z terminates a page identifier.
  return bits.match(/.{5}/g).map(group => '0123456789ABCDEFGHIJKLMNOPQRSTVW'[parseInt(group, 2)]).join('') + 'Z';
}

function actionId(page, index) {
  const hex = createHash('sha256').update(`${page}:${index}`).digest('hex').slice(0, 32);
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-a${hex.slice(17, 20)}-${hex.slice(20)}`;
}

export async function buildProfiles(pluginDir) {
  const layouts = JSON.parse(await readFile(new URL('../layouts.json', import.meta.url), 'utf8'));
  await mkdir(`${pluginDir}/profiles`, {recursive: true});
  for (const [model, config] of Object.entries(profiles)) {
    const layout = layouts[model];
    if (layout.pages.length !== config.pages.length || layout.pages.some(page => page.length !== layout.columns * layout.rows)) {
      throw Error(`Invalid ${model} layout`);
    }
    const manifest = {Device: {Model: config.model, UUID: ''}, Name: config.title,
      Pages: {Current: config.pages[0], Default: config.fallback, Pages: config.pages}, Version: '2.0'};
    const page = actions => ({Controllers: [{Actions: actions, Type: 'Keypad'}], Icon: '', Name: ''});
    const files = {'manifest.json': manifest, [`Profiles/${pageFolder(config.fallback)}/manifest.json`]: page({})};
    for (const [pageIndex, slots] of layout.pages.entries()) {
      const items = {};
      for (const [index, value] of slots.entries()) {
        if (value === null || value === 'retry') continue;
        const name = typeof value === 'number' ? 'Session' : value[0].toUpperCase() + value.slice(1);
        items[`${index % layout.columns},${Math.floor(index / layout.columns)}`] = {
          ActionID: actionId(config.pages[pageIndex], index), LinkedTitle: true, Name: name,
          Settings: typeof value === 'number' ? {slot: value} : {}, State: 0,
          States: [{ShowTitle: false, Title: ''}], UUID: `io.github.mrueda.pad-lattice.${name.toLowerCase()}`,
        };
      }
      files[`Profiles/${pageFolder(config.pages[pageIndex])}/manifest.json`] = page(items);
    }
    const zip = new ZipWriter(new Uint8ArrayWriter(), {level: 0, useWebWorkers: false,
      lastModDate: new Date('2026-01-01T00:00:00Z'), extendedTimestamp: false});
    for (const [path, data] of Object.entries(files)) {
      await zip.add(`${config.profile}.sdProfile/${path}`, new TextReader(JSON.stringify(data)));
    }
    await writeFile(`${pluginDir}/profiles/${config.name}.streamDeckProfile`, await zip.close());
  }
}
