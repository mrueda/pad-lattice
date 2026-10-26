const operations = new Set(['status', 'inspect_codex', 'paired_devices', 'list_conversations',
  'attach_conversation', 'detach_conversation', 'connect_midi', 'disconnect_midi', 'settings',
  'lan', 'surface', 'snapshot', 'disconnect_device', 'revoke_device']);
const failures: Array<{time: string; operation: string}> = [];

export function recordRequestFailure(method: string) {
  const operation = operations.has(method) ? method : 'request';
  const last = failures.at(-1);
  if (last?.operation === operation && Date.now() - Date.parse(last.time) < 10000) return;
  failures.push({time: new Date().toISOString(), operation});
  if (failures.length > 20) failures.shift();
}

const version = (value: unknown) => typeof value === 'string' && /^\d+\.\d+\.\d+[a-zA-Z0-9.+-]*$/.test(value)
  ? value : 'unavailable';
const object = (value: unknown): Record<string, unknown> => value && typeof value === 'object'
  ? value as Record<string, unknown> : {};

export function diagnosticsReport(statusValue: unknown, codexValue: unknown, devicesValue: unknown) {
  const status = object(statusValue), codex = object(codexValue), devices = object(devicesValue);
  const list = Array.isArray(devices.devices) ? devices.devices : null;
  return JSON.stringify({
    app: 'Pad-Lattice', version: version(status.version),
    codex: {available: codex.available === true, version: version(codex.version)},
    midi: {connected: Boolean(status.midi) && !status.midi_error, error: Boolean(status.midi_error)},
    network_enabled: Boolean(status.network_url),
    devices: {paired: list?.length ?? null, connected: list?.filter(device => object(device).connected === true).length ?? null},
    recent_failed_requests: failures.map(failure => ({...failure})),
  }, null, 2);
}
