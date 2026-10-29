import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {ZipReader, Uint8ArrayReader, TextWriter} from '@zip.js/zip.js';
import {pageFolder} from '../scripts/profiles.mjs';

test('page directory encoding matches the official exported profile', () => {
  assert.equal(pageFolder('cca21b93-64c5-4578-8a58-a6c35df9a5f2'), 'PIH1N4R4OL2NH2IOKR1LRVD5V8Z');
  assert.equal(pageFolder('58012f2d-6556-4424-a672-51814fcb396c'), 'B00IVBB5AP2299JIA60KWIPPDGZ');
});

test('bundled profiles match each device layout and contain guarded controls on every page', async () => {
  const dir = 'io.github.mrueda.pad-lattice.sdPlugin';
  const manifest = JSON.parse(readFileSync(`${dir}/manifest.json`, 'utf8'));
  const layouts = JSON.parse(readFileSync('layouts.json', 'utf8'));
  const types = {standard: 0, xl: 2, neo: 9};
  const models = {standard: '20GAA9901', xl: '20GAT9901', neo: '20GBJ9901'};
  const names = {standard: 'profiles/pad-lattice-15', xl: 'profiles/pad-lattice-xl', neo: 'profiles/pad-lattice-neo'};
  assert.equal(manifest.Profiles.length, 3);
  for (const [kind, layout] of Object.entries(layouts)) {
  const profile = manifest.Profiles.find(p => p.Name === names[kind]);
  assert.equal(profile.DeviceType, types[kind]);
  assert.equal(profile.AutoInstall, true);
  assert.equal(profile.DontAutoSwitchWhenInstalled, true);
  assert.equal(profile.Readonly, false);
  const zip = new ZipReader(new Uint8ArrayReader(readFileSync(`${dir}/${profile.Name}.streamDeckProfile`)));
  try {
    const files = {};
    for (const entry of await zip.getEntries()) files[entry.filename] = JSON.parse(await entry.getData(new TextWriter()));
    const root = Object.keys(files).find(name => name.split('/').length === 2);
    const bundle = files[root];
    assert.equal(bundle.Device.Model, models[kind]);
    assert.equal(bundle.Device.UUID, '');
    assert.equal(bundle.Version, '2.0');
    assert.equal(bundle.Pages.Pages.length, layout.pages.length);
    assert.equal(bundle.Pages.Current, bundle.Pages.Pages[0]);
    const covered = new Set();
    for (const [index, expected] of layout.pages.entries()) {
    const page = files[`${root.replace('manifest.json', '')}Profiles/${pageFolder(bundle.Pages.Pages[index])}/manifest.json`];
    const actions = page.Controllers[0].Actions;
    assert.equal(page.Controllers[0].Type, 'Keypad');
    assert.equal(new Set(Object.values(actions).map(a => a.ActionID)).size, Object.keys(actions).length);
    for (const [position, value] of expected.entries()) {
      const action = actions[`${position % layout.columns},${Math.floor(position / layout.columns)}`];
      if (value === null || value === 'retry') {assert.equal(action, undefined); continue;}
      assert.ok(action);
      assert.equal(action.UUID, `${manifest.UUID}.${typeof value === 'number' ? 'session' : value}`);
      assert.deepEqual(action.Settings, typeof value === 'number' ? {slot: value} : {});
      if (typeof value === 'number') covered.add(value);
    }
    for (const action of Object.values(actions)) {
      assert.ok(manifest.Actions.some(a => a.UUID === action.UUID));
      assert.equal(action.States[0].ShowTitle, false);
    }
    for (const mode of ['approve', 'reject', 'stop']) assert.ok(Object.values(actions).some(a => a.UUID === `${manifest.UUID}.${mode}`));
    }
    assert.deepEqual([...covered].sort(), [0, 1, 2, 3, 4, 5, 6, 7]);
    assert.doesNotMatch(JSON.stringify(files), /(?:credential|token|pin|http:)/i);
  } finally { await zip.close(); }
  }
});
