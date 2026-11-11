import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {surfaceSocket} from './desktop';

const {invoke, listen} = vi.hoisted(() => ({invoke: vi.fn(), listen: vi.fn()}));
vi.mock('@tauri-apps/api/event', () => ({listen}));
vi.mock('./diagnostics', () => ({recordRequestFailure: vi.fn()}));

function deferred() {
  let resolve!: (value?: unknown) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise((yes, no) => {resolve = yes; reject = no;});
  return {promise, resolve, reject};
}

async function open() {
  await import('@tauri-apps/api/core');
  const socket = surfaceSocket('unused');
  await vi.waitFor(() => expect(socket.readyState).toBe(1));
  return socket;
}

describe('native surface transport', () => {
  beforeEach(() => {
    vi.stubGlobal('window', {__TAURI_INTERNALS__: {invoke}});
    invoke.mockReset().mockResolvedValue({});
    listen.mockReset().mockResolvedValue(() => {});
  });
  afterEach(() => vi.unstubAllGlobals());

  it('waits for stop to finish before starting the next experience', async () => {
    const stop = deferred();
    invoke.mockImplementation((_command, {params}) =>
      params.type === 'stop_experience' ? stop.promise : Promise.resolve({}));
    const socket = await open();
    socket.send(JSON.stringify({type: 'stop_experience'}));
    socket.send(JSON.stringify({type: 'start_experience', kind: 'show'}));
    await vi.waitFor(() => expect(invoke).toHaveBeenCalled());
    expect(invoke).toHaveBeenCalledTimes(1);
    stop.resolve();
    await vi.waitFor(() => expect(invoke).toHaveBeenCalledTimes(2));
    expect(invoke.mock.calls.map(call => call[1].params.type)).toEqual(['stop_experience', 'start_experience']);
    socket.close();
  });

  it('continues after a failed command and reports the error', async () => {
    invoke.mockRejectedValueOnce(new Error('Stop failed'));
    const socket = await open();
    const messages: string[] = [];
    socket.onmessage = event => messages.push(event.data);
    socket.send(JSON.stringify({type: 'stop_experience'}));
    socket.send(JSON.stringify({type: 'start_experience', kind: 'show'}));
    await vi.waitFor(() => expect(invoke).toHaveBeenCalledTimes(2));
    expect(JSON.parse(messages[0]).code).toBe('desktop_error');
    socket.close();
  });

  it('discards queued commands when closed', async () => {
    const stop = deferred();
    invoke.mockReturnValue(stop.promise);
    const socket = await open();
    socket.send(JSON.stringify({type: 'stop_experience'}));
    socket.send(JSON.stringify({type: 'start_experience', kind: 'show'}));
    await vi.waitFor(() => expect(invoke).toHaveBeenCalled());
    socket.close();
    stop.resolve();
    await new Promise(resolve => setTimeout(resolve, 20));
    expect(invoke).toHaveBeenCalledTimes(1);
  });

  it('discards queued commands when authentication fails', async () => {
    invoke.mockRejectedValueOnce(new Error('Service unavailable'));
    const socket = await open();
    const closed = vi.fn();
    socket.onclose = closed;
    socket.send(JSON.stringify({type: 'authenticate'}));
    socket.send(JSON.stringify({type: 'start_experience', kind: 'show'}));
    await vi.waitFor(() => expect(closed).toHaveBeenCalledOnce());
    expect(invoke).toHaveBeenCalledTimes(1);
    expect(socket.readyState).toBe(3);
  });
});
