import {useEffect, useState} from 'react';
import {Wifi, WifiOff, ShieldCheck, ShieldOff, Check, Copy, RefreshCw, QrCode} from 'lucide-react';
import type {PairingMessage} from './types';

export function ConnectionSummary({state, error}: {state: string; error: string | null}) {
  const online = state === 'connected';
  return (
    <section className={`connectionSummary ${online ? 'online' : ''}`} aria-live="polite">
      {online ? <Wifi aria-hidden="true" /> : <WifiOff aria-hidden="true" />}
      <span>
        <strong>{online ? 'Pad connected' : state.replace('_', ' ')}</strong>
        <small>{error ?? (online ? 'State and actions are synchronized.' : 'Waiting for the local bridge.')}</small>
      </span>
    </section>
  );
}

export function PairingPanel({
  pairing,
  onCreate,
  onRevoke,
  kind = 'browser',
}: {
  pairing: PairingMessage | null;
  onCreate: () => void;
  onRevoke: () => void;
  kind?: 'browser' | 'stream_deck';
}) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const streamDeck = kind === 'stream_deck';
  const origin = pairing ? new URL(pairing.pairing_url).origin : '';
  useEffect(() => {setCopied(false); setCopyError(false);}, [origin]);
  async function copyAddress() {
    try {await navigator.clipboard.writeText(origin); setCopied(true); setCopyError(false);}
    catch {setCopyError(true);}
  }
  const pairingHost = pairing ? new URL(pairing.pairing_url).hostname : '';
  const localOnly = pairingHost === 'localhost' || pairingHost.startsWith('127.') || pairingHost === '[::1]';
  return (
    <section className="pairingPanel">
      <div className="sectionTitle"><span>PAIR A SURFACE</span><ShieldCheck aria-hidden="true" /></div>
      {pairing ? (
        <div className={`pairingContent${localOnly || streamDeck ? ' localPairing' : ''}`}>
          {!localOnly && !streamDeck ? <img src={pairing.qr_data_uri} alt="Scan to pair automatically without entering a PIN" /> : null}
          <div>
            {streamDeck ? <>
              <label className="pairingAddress">Pad-Lattice address
                <div><input readOnly aria-label="Pad-Lattice address" value={origin} onFocus={e => e.target.select()} />
                  <button className="textButton" aria-label={copied ? 'Address copied' : 'Copy address'} title={copied ? 'Address copied' : 'Copy address'} onClick={() => void copyAddress()}>
                    {copied ? <Check /> : <Copy />}</button></div>
              </label>
              {copyError ? <small role="status">Clipboard unavailable. Select and copy the address above.</small> : null}
            </> : null}
            {!localOnly && !streamDeck ? <><h3>Scan to pair</h3><small className="pairingScanNote">No PIN needed</small></> : null}
            <span>{streamDeck ? 'ONE-USE PIN' : localOnly ? 'LOCAL PAIRING PIN' : 'OR PAIR MANUALLY'}</span>
            {!localOnly && !streamDeck ? <small>{origin}</small> : null}
            <strong>{pairing.pin}</strong>
            {!localOnly && !streamDeck ? <small>Manual pairing PIN</small> : null}
            <small>One use · expires in five minutes</small>
            {localOnly && !streamDeck ? <small>{origin}</small> : null}
            {localOnly ? <small>{streamDeck ? 'Same computer only. No network setup needed.' : 'This computer only. Phone pairing is off.'}</small> : null}
            {streamDeck ? <small>Elgato software: select a Pad-Lattice key, enter address and PIN, then Pair. All keys share the connection.</small> : null}
          </div>
        </div>
      ) : (
        <p>Pair Stream Deck on this computer, or enable network pairing in Settings for another device.</p>
      )}
      <div className="paneActions">
        <button className="textButton" onClick={onCreate}>
          {pairing ? <RefreshCw aria-hidden="true" /> : <QrCode aria-hidden="true" />} {pairing ? 'New code' : 'Pair device'}
        </button>
        <button className="textButton danger" onClick={onRevoke}>
          <ShieldOff aria-hidden="true" /> Revoke paired devices
        </button>
      </div>
    </section>
  );
}
