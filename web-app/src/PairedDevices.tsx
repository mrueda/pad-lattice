import {useCallback, useEffect, useState} from 'react';
import {MonitorSmartphone, RefreshCw, Unplug, ShieldOff} from 'lucide-react';
import {desktopRequest} from './desktop';

export interface Device {id: string; name: string; connected: boolean}

export function usePairedDevices() {
  const [devices, setDevices] = useState<Device[] | null>(null);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    const result = await desktopRequest<{devices: Device[]}>('paired_devices');
    setDevices(result.devices);
    setError('');
  }, []);
  useEffect(() => {
    let disposed = false;
    let timer: number;
    const poll = async () => {
      try {
        const result = await desktopRequest<{devices: Device[]}>('paired_devices');
        if (!disposed) {setDevices(result.devices); setError('');}
      } catch (reason) {if (!disposed) setError(String(reason));}
      if (!disposed) timer = window.setTimeout(() => { if (!document.hidden) void poll(); else timer = window.setTimeout(poll, 2000); }, 2000);
    };
    void poll();
    return () => {disposed = true; window.clearTimeout(timer);};
  }, []);
  return {devices, setDevices, error, setError, refresh};
}

export function PairedDevices({state}: {state: ReturnType<typeof usePairedDevices>}) {
  const {devices, setDevices, error, setError, refresh} = state;
  const [busy, setBusy] = useState(false);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const manage = async (device: Device, revoke: boolean) => {
    setBusy(true);
    try {
      const result = await desktopRequest<{devices: Device[]}>(revoke ? 'revoke_device' : 'disconnect_device', {device_id: device.id});
      setDevices(result.devices);
      setConfirmId(null);
      setError('');
    } catch (reason) {setError(String(reason));}
    finally {setBusy(false);}
  };
  return <section className="pairedDevices" aria-label="Paired devices">
    <div className="desktopToolbar"><h3>Paired devices</h3>
      <button className="textButton" aria-label="Refresh paired devices" title="Refresh paired devices" disabled={busy}
        onClick={() => void refresh().catch(reason => setError(String(reason)))}><RefreshCw /></button>
    </div>
    {error ? <p className="desktopError" role="alert">{error}</p> : null}
    {!devices ? <p className="desktopNotice">Checking paired devices...</p>
      : !devices.length ? <p className="desktopNotice">No paired devices</p> : <ul className="pairedDeviceList">
      {devices.map(device => <li key={device.id}>
        <MonitorSmartphone aria-hidden="true" />
        <div className="pairedDeviceIdentity"><strong>{device.name}</strong>
          <small className={device.connected ? 'deviceOnline' : ''}>{device.connected ? 'Connected' : 'Offline'} · {device.id.slice(-6)}</small></div>
        <div className="desktopActions">
          {device.connected ? <button className="textButton" title={`Disconnect ${device.name}`} aria-label={`Disconnect ${device.name}`}
            disabled={busy} onClick={() => void manage(device, false)}><Unplug /></button> : null}
          <button className="textButton danger" title={`Revoke access for ${device.name}`} aria-label={`Revoke access for ${device.name}`}
            disabled={busy} onClick={() => setConfirmId(device.id)}><ShieldOff /></button>
        </div>
        {confirmId === device.id ? <div className="deviceRevokeConfirm" role="group" aria-label={`Confirm revoke ${device.name}`}>
          <span>Revoke access? This device will need to pair again.</span>
          <button className="textButton danger" disabled={busy} onClick={() => void manage(device, true)}>Revoke access</button>
          <button className="textButton" disabled={busy} onClick={() => setConfirmId(null)}>Cancel</button>
        </div> : null}
      </li>)}
    </ul>}
  </section>;
}
