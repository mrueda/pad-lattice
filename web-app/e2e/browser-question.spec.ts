import {expect, test} from '@playwright/test';
import {compileVisualFrame} from '../src/surfaceModel';
import type {SurfaceView} from '../src/types';

test('paired browser receives and answers only its selected question', async ({page}) => {
  let pending = true;
  const answers: Record<string, unknown>[] = [];
  const view: SurfaceView = {control_revision: 12, selected_state: 'waiting_for_reply', frame: 0,
    sessions: [{slot: 0, label: 'Builder', accent: 'cyan', state: 'waiting_for_reply', selected: true}],
    available_actions: ['stop'], activity_motion: false, overflow_count: 0};
  await page.route('**/config.json', route => route.fulfill({json: {mode: 'live', protocol: 1}}));
  await page.routeWebSocket('**/ws', socket => {
    socket.onMessage(data => {
      const message = JSON.parse(String(data));
      if (message.type === 'authenticate') {
        socket.send(JSON.stringify({protocol: 1, type: 'authenticated', admin: false, session_token: 'test', lan_enabled: true}));
        socket.send(JSON.stringify({protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)}));
      } else if (message.type === 'question_request') {
        let result: unknown = {};
        if (message.operation === 'status') result = {slot: 0, revision: 12, question: pending ? {
          token: 'a'.repeat(32), questions: [{id: 'tests', header: 'Tests', question: 'Which tests?', options: [
            {label: 'Focused', description: 'Only affected tests'}, {label: 'All', description: 'Full suite'}]}]} : null};
        else {answers.push(message); pending = false;}
        socket.send(JSON.stringify({protocol: 1, type: 'question_response', request_id: message.request_id, result}));
      }
    });
  });
  await page.goto('/');
  const question = page.getByRole('region', {name: 'Codex question'});
  await expect(question).toContainText('Which tests?');
  await expect(question).toContainText('Builder · Scene 1');
  const questionBox = await question.boundingBox();
  const padBox = await page.getByLabel('Pad-Lattice virtual control surface').boundingBox();
  expect(questionBox!.y + questionBox!.height).toBeLessThanOrEqual(padBox!.y);
  await page.screenshot({path: test.info().outputPath('browser-question.png'), fullPage: true});
  await question.getByRole('button', {name: /Focused/}).click();
  await expect.poll(() => answers).toHaveLength(1);
  expect(answers[0]).toMatchObject({operation: 'answer', slot: 0, revision: 12,
    token: 'a'.repeat(32), answers: {tests: 0}});
  await expect(question).toHaveCount(0);
});

test('disconnect during an answer does not retry it', async ({page}) => {
  const answers: Record<string, unknown>[] = [];
  const view: SurfaceView = {control_revision: 12, selected_state: 'waiting_for_reply', frame: 0,
    sessions: [{slot: 0, label: 'Builder', accent: 'cyan', state: 'waiting_for_reply', selected: true}],
    available_actions: ['stop'], activity_motion: false, overflow_count: 0};
  await page.route('**/config.json', route => route.fulfill({json: {mode: 'live', protocol: 1}}));
  await page.routeWebSocket('**/ws', socket => {
    socket.onMessage(data => {
      const message = JSON.parse(String(data));
      if (message.type === 'authenticate') {
        socket.send(JSON.stringify({protocol: 1, type: 'authenticated', admin: false, session_token: 'test', lan_enabled: true}));
        socket.send(JSON.stringify({protocol: 1, type: 'surface', visual_protocol: 1, view, visual_frame: compileVisualFrame(view)}));
      } else if (message.type === 'question_request' && message.operation === 'status') {
        socket.send(JSON.stringify({protocol: 1, type: 'question_response', request_id: message.request_id,
          result: {slot: 0, revision: 12, question: {token: 'a'.repeat(32), questions: [{id: 'tests', header: 'Tests',
            question: 'Which tests?', options: [{label: 'Focused', description: 'Only affected tests'}]}]}}}));
      } else if (message.type === 'question_request' && message.operation === 'answer') {
        answers.push(message);
        socket.close();
      }
    });
  });
  await page.goto('/');
  const question = page.getByRole('region', {name: 'Codex question'});
  await question.getByRole('button', {name: /Focused/}).click();
  await expect(page.getByRole('button', {name: 'Reconnect', exact: true})).toBeVisible();
  await page.waitForTimeout(900);
  expect(answers).toHaveLength(1);
});
