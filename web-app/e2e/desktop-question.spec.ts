import {test, expect} from '@playwright/test';
import {desktopBridge, emitSurface} from './desktopTestHarness';
import {compileVisualFrame} from '../src/surfaceModel';
import type {SurfaceView} from '../src/types';

test('numbered choices answer only the selected live request', async ({page}) => {
  let view: SurfaceView = {selected_state: 'waiting_for_reply', frame: 0, control_revision: 4,
    sessions: [{slot: 0, state: 'waiting_for_reply', selected: true, accent: 'cyan', label: 'Builder'},
      {slot: 1, state: 'running', selected: false, accent: 'lime', label: 'Reviewer'}],
    available_actions: ['stop'], overflow_count: 0, activity_motion: false};
  const questionItems = [{id: 'tests', header: 'Tests', question: 'Which tests?', options: [
    {label: 'Focused', description: 'Run focused tests'}, {label: 'All', description: 'Run all tests'}]}];
  let pending: {token: string; questions: typeof questionItems} | null = {token: 'request-token', questions: questionItems};
  const sent: Record<string, unknown>[] = [];
  const surface = () => ({protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)});
  await desktopBridge(page, async (method, params) => {
    if (method === 'settings') return {};
    if (method === 'status') return {version: '0.2.0', settings: {}, inputs: [], outputs: [], profiles: [], midi: null, lan_host: '127.0.0.1'};
    if (method === 'inspect_codex') return {available: true, version: '0.165.0', tested_version: '0.165.0'};
    if (method === 'list_conversations') return {available: true, conversations: []};
    if (method === 'paired_devices') return {devices: []};
    if (method === 'attention') return {revision: view.control_revision, sessions: [], overflow_count: 0};
    if (method === 'snapshot') return {messages: [{protocol: 1, type: 'authenticated', admin: true, lan_enabled: false}, surface()]};
    if (method === 'question_status') return {slot: 0, revision: 4, question: pending};
    if (method === 'answer_question') {
      sent.push(params);
      await new Promise(resolve => setTimeout(resolve, 200));
      pending = null;
      return {};
    }
    if (method === 'surface' && params.type === 'select_session') {
      view = {...view, control_revision: 5, selected_state: 'running', sessions: view.sessions.map(s => ({...s, selected: s.slot === 1}))};
      await emitSurface(page, surface()); return {};
    }
    if (method === 'surface') return {};
    throw Error(`Unexpected request: ${method}`);
  });
  await page.goto('/');
  const question = page.getByRole('region', {name: 'Codex question'});
  await expect(question).toContainText('Which tests?');
  await page.getByRole('button', {name: 'Maximize pad'}).click();
  await expect(question).toBeVisible();
  const pad = page.getByLabel('Pad-Lattice virtual control surface');
  const questionBox = await question.boundingBox(), padBox = await pad.boundingBox();
  if (page.viewportSize()!.width > 759) expect(questionBox!.x + questionBox!.width).toBeLessThanOrEqual(padBox!.x);
  await page.screenshot({path: test.info().outputPath('question-maximized.png'), fullPage: true});
  await page.getByRole('button', {name: 'Restore workspace'}).click();
  await expect(question.getByRole('button', {name: 'Send answer'})).toHaveCount(0);
  await page.evaluate(() => {const input = document.createElement('input'); input.id = 'typing-test'; document.body.append(input); input.focus();});
  await page.keyboard.press('1');
  expect(sent).toHaveLength(0);
  await page.evaluate(() => document.getElementById('typing-test')?.remove());
  await page.keyboard.down('2');
  await page.keyboard.down('2');
  await page.keyboard.up('2');
  await expect.poll(() => sent).toEqual([{slot: 0, revision: 4, token: 'request-token', answers: {tests: 1}}]);
  await expect(question).toHaveCount(0);
  pending = {token: 'click-token', questions: questionItems};
  await expect(question).toBeVisible();
  await question.getByRole('button', {name: /Focused/}).evaluate(button => {
    (button as HTMLButtonElement).click();
    (button as HTMLButtonElement).click();
  });
  await expect.poll(() => sent).toHaveLength(2);
  expect(sent[1]).toEqual({slot: 0, revision: 4, token: 'click-token', answers: {tests: 0}});
  await expect(question).toHaveCount(0);
  pending = {token: 'multi-token', questions: [...questionItems, {id: 'format', header: 'Format', question: 'Which format?',
    options: [{label: 'Text', description: 'Plain text'}]}]};
  await expect(question).toBeVisible();
  await question.getByRole('button', {name: /Focused/}).click();
  await question.getByRole('button', {name: /Text/}).click();
  expect(sent).toHaveLength(2);
  await question.getByRole('button', {name: 'Send answer'}).click();
  await expect.poll(() => sent).toHaveLength(3);
  expect(sent[2]).toEqual({slot: 0, revision: 4, token: 'multi-token', answers: {tests: 0, format: 0}});
  await expect(question).toHaveCount(0);
  pending = {token: 'stale-token', questions: questionItems};
  await expect(question).toBeVisible();
  await page.getByLabel('Pad-Lattice virtual control surface').getByRole('button', {name: 'Select Reviewer'}).click();
  await expect(question).toHaveCount(0);
  await page.keyboard.press('1');
  expect(sent).toHaveLength(3);
});
