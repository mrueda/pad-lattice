import {mkdir, writeFile} from 'node:fs/promises';
import {ZipWriter, Uint8ArrayWriter, TextReader} from '@zip.js/zip.js';

// Archive structure follows Elgato's exported Lights Out profile. See README.md.
const profileId = '85996A0A-C431-42C9-98E4-554813C20D22';
const pageId = 'fe21f0b9-8737-4d19-a28a-de4a7095eaa3';
const defaultPageId = '68c7aa15-c38b-4c8f-ac47-56786e2eaf69';

export function pageFolder(uuid) {
  const bits = [...Buffer.from(uuid.replaceAll('-', ''), 'hex')]
    .map(byte => byte.toString(2).padStart(8, '0')).join('').padEnd(130, '0');
  // Elgato's alphabet omits U; Z terminates a page identifier.
  return bits.match(/.{5}/g).map(group => '0123456789ABCDEFGHIJKLMNOPQRSTVW'[parseInt(group, 2)]).join('') + 'Z';
}

export async function buildProfiles(pluginDir) {
  const manifest = {Device: {Model: '20GAA9901', UUID: ''}, Name: 'Pad-Lattice - 15 keys',
    Pages: {Current: pageId, Default: defaultPageId, Pages: [pageId]}, Version: '2.0'};
  const actions = {};
  const key = (name, index, settings = {}) => ({
    ActionID: `267c28b5-4c55-4771-aae3-${index.toString(16).padStart(12, '0')}`,
    LinkedTitle: true, Name: name, Settings: settings, State: 0,
    States: [{ShowTitle: false, Title: ''}], UUID: `io.github.mrueda.pad-lattice.${name.toLowerCase()}`,
  });
  for (let slot = 0; slot < 8; slot++) actions[`${slot % 5},${Math.floor(slot / 5)}`] = key('Session', slot, {slot});
  for (const [column, name] of ['Approve', 'Reject', 'Stop'].entries()) actions[`${column},2`] = key(name, 8 + column);
  const page = actions => ({Controllers: [{Actions: actions, Type: 'Keypad'}], Icon: '', Name: ''});
  const files = {
    'manifest.json': manifest,
    [`Profiles/${pageFolder(defaultPageId)}/manifest.json`]: page({}),
    [`Profiles/${pageFolder(pageId)}/manifest.json`]: page(actions),
  };
  const zip = new ZipWriter(new Uint8ArrayWriter(), {level: 0, useWebWorkers: false,
    lastModDate: new Date('2026-01-01T00:00:00Z'), extendedTimestamp: false});
  for (const [path, data] of Object.entries(files)) {
    await zip.add(`${profileId}.sdProfile/${path}`, new TextReader(JSON.stringify(data)));
  }
  await mkdir(`${pluginDir}/profiles`, {recursive: true});
  await writeFile(`${pluginDir}/profiles/pad-lattice-15.streamDeckProfile`, await zip.close());
}
