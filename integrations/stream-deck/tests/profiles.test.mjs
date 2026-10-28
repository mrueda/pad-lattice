import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {ZipReader, Uint8ArrayReader, TextWriter} from '@zip.js/zip.js';
import {pageFolder} from '../scripts/profiles.mjs';

test('page directory encoding matches the official exported profile', () => {
  assert.equal(pageFolder('cca21b93-64c5-4578-8a58-a6c35df9a5f2'), 'PIH1N4R4OL2NH2IOKR1LRVD5V8Z');
  assert.equal(pageFolder('58012f2d-6556-4424-a672-51814fcb396c'), 'B00IVBB5AP2299JIA60KWIPPDGZ');
});

test('bundled editable profile has eight distinct sessions and all guarded controls', async () => {
  const dir = 'io.github.mrueda.pad-lattice.sdPlugin';
  const manifest = JSON.parse(readFileSync(`${dir}/manifest.json`, 'utf8'));
  const profile = manifest.Profiles[0];
  assert.equal(profile.DeviceType, 0);
  assert.equal(profile.AutoInstall, true);
  assert.equal(profile.DontAutoSwitchWhenInstalled, true);
  assert.equal(profile.Readonly, false);
  const zip = new ZipReader(new Uint8ArrayReader(readFileSync(`${dir}/${profile.Name}.streamDeckProfile`)));
  try {
    const files = {};
    for (const entry of await zip.getEntries()) files[entry.filename] = JSON.parse(await entry.getData(new TextWriter()));
    const root = Object.keys(files).find(name => name.split('/').length === 2);
    const bundle = files[root];
    assert.equal(bundle.Device.Model, '20GAA9901');
    assert.equal(bundle.Device.UUID, '');
    assert.equal(bundle.Version, '2.0');
    const page = files[`${root.replace('manifest.json', '')}Profiles/${pageFolder(bundle.Pages.Current)}/manifest.json`];
    const actions = page.Controllers[0].Actions;
    assert.equal(page.Controllers[0].Type, 'Keypad');
    assert.equal(Object.keys(actions).length, 11);
    assert.equal(new Set(Object.values(actions).map(a => a.ActionID)).size, 11);
    for (let slot = 0; slot < 8; slot++) {
      const action = actions[`${slot % 5},${Math.floor(slot / 5)}`];
      assert.equal(action.UUID, `${manifest.UUID}.session`);
      assert.deepEqual(action.Settings, {slot});
    }
    for (const [column, mode] of ['approve', 'reject', 'stop'].entries()) {
      assert.equal(actions[`${column},2`].UUID, `${manifest.UUID}.${mode}`);
      assert.deepEqual(actions[`${column},2`].Settings, {});
    }
    for (const action of Object.values(actions)) {
      assert.ok(manifest.Actions.some(a => a.UUID === action.UUID));
      assert.equal(action.States[0].ShowTitle, false);
    }
    assert.doesNotMatch(JSON.stringify(files), /(?:credential|token|pin|http:)/i);
  } finally { await zip.close(); }
});
