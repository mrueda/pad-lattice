import {expect, test} from '@playwright/test';
import {compileVisualFrame, tokenColor} from '../src/surfaceModel';
import {agentStates} from '../src/types';

test('switches layouts without resetting sessions, selection, or action history', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button', {name: 'Sandbox', exact: true}).click();
  await page.getByRole('button', {name: 'View Reviewer', exact: true}).click();
  await page.getByRole('button', {name: 'Approve', exact: true}).click();
  await page.getByLabel('Surface', {exact: true}).selectOption('stream-deck');
  const deck = page.getByLabel('Stream Deck simulation', {exact: true});
  await expect(deck.locator('.deckKey')).toHaveCount(15);
  await expect(deck.getByRole('button', {name: 'Select Reviewer', exact: true})).toHaveAttribute('aria-pressed', 'true');
  await expect(deck.getByRole('button', {name: 'Select Reviewer', exact: true})).toHaveAttribute('title', 'Reviewer: Running');
  await expect(deck.getByRole('button', {name: 'Approve', exact: true})).toBeDisabled();
  await expect(deck.getByRole('button', {name: 'Stop', exact: true})).toBeEnabled();
  await expect(deck.getByRole('button', {name: 'Retry', exact: true})).toHaveCount(0);
  await expect(page.getByLabel('View agent')).toContainText('SELECTED: Reviewer');
  await expect(page.locator('.playgroundHistory summary')).toContainText('Reviewer: approve received; work resumed.');

  await deck.getByRole('button', {name: 'Select Tests', exact: true}).click();
  await expect(deck.locator('.deckActionKey:enabled')).toHaveCount(0);
  await page.getByLabel('Surface', {exact: true}).selectOption('launchpad');
  const launchpad = page.getByLabel('Launchpad Pro Mk1 simulation', {exact: true});
  await expect(launchpad.locator('.matrixPad')).toHaveCount(64);
  await expect(launchpad.locator('.railControl')).toHaveCount(8);
  await expect(launchpad.locator('.sceneControl')).toHaveCount(8);
  await expect(launchpad.locator('.reservedRail > span')).toHaveCount(16);
  await expect(launchpad.getByRole('button', {name: 'Select Tests', exact: true})).toHaveAttribute('aria-pressed', 'true');
  await launchpad.getByRole('button', {name: 'Retry', exact: true}).click();
  await page.getByLabel('Surface', {exact: true}).selectOption('virtual');
  await expect(page.locator('.selectedReadout')).toContainText('Tests');
  await expect(page.getByLabel('Reviewer state')).toHaveValue('running');
  await expect(page.getByLabel('Tests state')).toHaveValue('running');
  await expect(page.getByLabel('Builder state')).toHaveValue('running');
});

test('Stream Deck names the action target and keeps unselected requests separate', async ({page}) => {
  const sockets: string[] = [];
  page.on('websocket', socket => sockets.push(socket.url()));
  await page.goto('/?surface=stream-deck');
  await page.getByRole('button', {name: 'Sandbox', exact: true}).click();
  const deck = page.getByLabel('Stream Deck simulation', {exact: true});
  await expect(deck.getByRole('button', {name: 'Select Reviewer', exact: true})).toHaveAttribute('aria-pressed', 'false');
  await expect(deck.getByRole('button', {name: 'Approve', exact: true})).toContainText('Builder');
  await expect(deck.getByRole('button', {name: 'Approve', exact: true})).toBeDisabled();
  await deck.getByRole('button', {name: 'Select Reviewer', exact: true}).focus();
  await page.keyboard.press('Enter');
  await expect(deck.getByRole('button', {name: 'Select Reviewer', exact: true})).toHaveCSS('border-top-color', 'rgb(255, 255, 255)');
  await expect(deck.getByRole('button', {name: 'Approve', exact: true})).toContainText('Reviewer');
  await deck.getByRole('button', {name: 'Approve', exact: true}).click();
  await expect(page.getByLabel('Reviewer state')).toHaveValue('running');
  await expect(page.getByLabel('Builder state')).toHaveValue('running');
  await expect(page.getByLabel('Tests state')).toHaveValue('error');

  await page.getByLabel('Scenario', {exact: true}).selectOption('resolved');
  await page.getByRole('button', {name: 'Reviewer permission answered in Codex'}).click();
  await expect(deck.getByRole('button', {name: 'Approve', exact: true})).toBeDisabled();
  await page.getByLabel('Scenario', {exact: true}).selectOption('disconnect');
  await page.getByRole('button', {name: 'Reviewer disconnects'}).click();
  await expect(deck.locator('.deckActionKey:enabled')).toHaveCount(0);
  await expect(deck.getByRole('button', {name: 'Approve', exact: true})).toContainText('No session');
  await expect(deck.getByRole('button', {name: 'Empty Session 2', exact: true})).toBeDisabled();
  await page.getByRole('button', {name: 'Builder requests permission'}).click();
  await expect(deck.locator('.deckActionKey:enabled')).toHaveCount(0);
  await deck.getByRole('button', {name: 'Select Builder', exact: true}).click();
  await deck.getByRole('button', {name: 'Reject', exact: true}).click();
  await expect(page.getByLabel('Builder state')).toHaveValue('cancelled');
  expect(sockets.filter(url => !url.includes('token='))).toEqual([]);
});

test('uses the shared visual compiler for all eight Stream Deck session keys', async ({page}) => {
  await page.goto('/?surface=stream-deck');
  await page.getByRole('button', {name: 'Sandbox', exact: true}).click();
  await page.getByLabel('Scenario', {exact: true}).selectOption('vocabulary');
  const deck = page.getByLabel('Stream Deck simulation', {exact: true});
  await expect(deck.locator('.deckSessionKey')).toHaveCount(8);
  for (const [index, state] of [...agentStates, 'waiting_for_reply' as const].entries()) {
    const expected = compileVisualFrame({selected_state: state, sessions: [], frame: 0,
      available_actions: [], overflow_count: 0, activity_motion: false});
    const pixels = expected.state.flatMap((row, y) => row.flatMap((token, x) => token === 'off' ? [] :
      [{x: x * 10 + 1, y: y * 10 + 1, fill: tokenColor(token)}]));
    const actual = await deck.locator('.deckSessionKey').nth(index).locator('.deckGlyph rect').evaluateAll(rects =>
      rects.map(rect => ({x: Number(rect.getAttribute('x')), y: Number(rect.getAttribute('y')), fill: rect.getAttribute('fill')})));
    expect(actual).toEqual(pixels);
  }
  await page.getByLabel('Agent 8 state').selectOption('waiting_for_approval');
  await deck.getByRole('button', {name: 'Select Agent 8', exact: true}).click();
  await expect(deck.getByRole('button', {name: 'Reject', exact: true})).toContainText('Agent 8');
  await deck.getByRole('button', {name: 'Reject', exact: true}).click();
  await expect(page.getByLabel('Agent 8 state')).toHaveValue('cancelled');
});

test('autoplay points at the matching hardware control without restarting on layout changes', async ({page}) => {
  await page.clock.install();
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  await page.goto('/?surface=stream-deck');
  await page.getByLabel('Demo playback').waitFor();
  await expect(page.locator('.deckKey:enabled')).toHaveCount(0);
  await page.clock.runFor(6800);
  await expect(page.locator('.deckSessionKey.guidedControl')).toHaveAttribute('aria-label', 'Select Reviewer');
  await expect(page.locator('.deckSessionKey .demoPointer.pressed')).toBeVisible();
  await page.getByLabel('Surface', {exact: true}).selectOption('launchpad');
  await expect(page.locator('.sceneControl .demoPointer.pressed')).toBeVisible();
  await page.clock.runFor(200);
  await expect(page.getByRole('heading', {name: 'Allow the test command?'})).toBeVisible();
  await page.getByLabel('Surface', {exact: true}).selectOption('stream-deck');
  await page.clock.runFor(6800);
  await expect(page.locator('.deckActionKey.guidedControl')).toHaveAttribute('aria-label', 'Approve');
  await expect(page.locator('.deckActionKey .demoPointer.pressed')).toBeVisible();
  await page.clock.runFor(200);
  await expect(page.getByRole('heading', {name: 'Now Tests needs a decision.'})).toBeVisible();
  await page.clock.runFor(13800);
  await expect(page.locator('.deckActionKey.guidedControl')).toHaveAttribute('aria-label', 'Reject');
  await expect(page.locator('.deckActionKey .demoPointer.pressed')).toBeVisible();
  await page.clock.runFor(7200);
  await expect(page.getByRole('heading', {name: 'Two decisions. The right agents.'})).toBeVisible();
  await expect(page.locator('.deckKey:enabled')).toHaveCount(0);
});

test('Show is confined to grid layouts and leaves reserved Launchpad buttons dark', async ({page}) => {
  await page.goto('/?surface=stream-deck');
  await expect(page.getByRole('button', {name: 'Show', exact: true})).toBeDisabled();
  await page.getByLabel('Surface', {exact: true}).selectOption('launchpad');
  await page.getByRole('button', {name: 'Show', exact: true}).click();
  await expect(page.getByLabel('Surface', {exact: true}).locator('option[value="stream-deck"]')).toBeDisabled();
  await page.getByRole('button', {name: 'Start Show', exact: true}).click();
  await expect(page.locator('.performanceStory')).toBeVisible();
  await expect(page.locator('.launchpadSurface')).toBeVisible();
  const colors = await page.locator('.reservedRail > span').evaluateAll(buttons => buttons.map(button => getComputedStyle(button).backgroundColor));
  expect(colors).toEqual(Array(16).fill('rgb(17, 23, 28)'));
  await expect(page.locator('.railControl:enabled, .sceneControl:enabled')).toHaveCount(0);
  await page.locator('.experiencePanel').getByRole('button', {name: 'Stop', exact: true}).click();
  await page.getByRole('button', {name: 'Sandbox', exact: true}).click();
  await page.getByLabel('Surface', {exact: true}).selectOption('stream-deck');
  await expect(page.getByRole('button', {name: 'Show', exact: true})).toBeDisabled();
});

test('device layouts fit the viewport and retain protocol colors in both themes', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button', {name: 'Sandbox', exact: true}).click();
  await page.getByRole('button', {name: 'View Reviewer', exact: true}).click();
  for (const surface of ['launchpad', 'stream-deck']) {
    await page.getByLabel('Surface', {exact: true}).selectOption(surface);
    const housing = page.locator(surface === 'launchpad' ? '.launchpadSurface' : '.streamDeckSurface');
    if (surface === 'launchpad') {
      // Wait for the selection's color transition before comparing themes.
      await expect(housing.locator('.matrixPad').nth(3)).toHaveCSS('background-color', 'rgb(240, 182, 63)');
    }
    const colors = () => housing.locator('.matrixPad, .deckGlyph rect').evaluateAll(pixels => pixels.map(pixel =>
      pixel.tagName === 'rect' ? pixel.getAttribute('fill') : getComputedStyle(pixel).backgroundColor));
    const before = await colors();
    expect(before.length).toBeGreaterThan(0);
    for (const theme of ['light', 'dark']) {
      await page.getByRole('button', {name: `Switch to ${theme} theme`, exact: true}).click();
      expect(await colors()).toEqual(before);
      const box = await housing.boundingBox();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(page.viewportSize()!.width);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
    }
  }
});

test('unknown preview links fall back to Virtual Pad and live mode ignores device previews', async ({page}) => {
  await page.goto('/?surface=unknown');
  await expect(page.getByLabel('Surface', {exact: true})).toHaveValue('virtual');
  await expect(page.getByLabel('Pad-Lattice virtual control surface', {exact: true})).toBeVisible();
  await page.goto('http://127.0.0.1:4174/?surface=stream-deck#admin=pad-lattice-e2e-admin');
  await expect(page.getByText('Pad connected', {exact: true})).toBeVisible();
  await expect(page.getByLabel('Surface', {exact: true})).toHaveCount(0);
  await expect(page.getByLabel('Stream Deck simulation', {exact: true})).toHaveCount(0);
});
