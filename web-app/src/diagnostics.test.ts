import {describe, expect, it} from 'vitest';
import {diagnosticsReport, recordRequestFailure} from './diagnostics';

describe('diagnostics', () => {
  it('copies only safe status fields, never paths, tokens, names or raw errors', () => {
    recordRequestFailure('/home/private/token-secret');
    const report = diagnosticsReport({version: '0.1.0', midi: 'private device',
      midi_error: '/home/private/project', network_url: 'http://secret-host:8001', settings: {token: 'secret'}},
    {available: true, version: '/home/private/codex', error: 'secret prompt'},
    {devices: [{connected: true, name: 'private phone', id: 'secret'}, {connected: false}]});
    expect(report).not.toMatch(/private|secret|prompt|8001/);
    expect(JSON.parse(report)).toMatchObject({version: '0.1.0', codex: {version: 'unavailable'},
      midi: {connected: false, error: true}, devices: {paired: 2, connected: 1}});
  });
  it('handles unavailable services and limits failure history', () => {
    for (let index = 0; index < 50; index++) recordRequestFailure(index % 2 ? 'status' : 'surface');
    const report = JSON.parse(diagnosticsReport(null, null, null));
    expect(report.devices).toEqual({paired: null, connected: null});
    expect(report.recent_failed_requests).toHaveLength(20);
  });
});
