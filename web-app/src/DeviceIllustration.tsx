import {Check, Square, X} from 'lucide-react';
import {compileVisualFrame, tokenColor} from './surfaceModel';
import type {SurfaceView} from './types';

// Setup illustrations use the same state glyphs and colors as the live surface.
const view: SurfaceView = {
  selected_state: 'waiting_for_approval', frame: 0, available_actions: ['approve', 'reject'],
  overflow_count: 0, activity_motion: false,
  sessions: [
    {slot: 0, label: 'Build', accent: 'cyan', state: 'running', selected: false},
    {slot: 1, label: 'Review', accent: 'magenta', state: 'waiting_for_approval', selected: true},
    {slot: 2, label: 'Tests', accent: 'lime', state: 'success', selected: false},
  ],
};
const frame = compileVisualFrame(view);

function Grid({size = 8}: {size?: number}) {
  return <g>{Array.from({length: 64}, (_, index) => {
    const row = Math.floor(index / 8), column = index % 8;
    return <rect key={index} x={column * (size + 2)} y={row * (size + 2)} width={size} height={size} rx="1.5"
      fill={tokenColor(column === 7 ? frame.statuses[row] : frame.state[row][column])} stroke="#46515a" strokeWidth=".4" />;
  })}</g>;
}

export function DeviceIllustration({kind}: {kind: 'midi' | 'browser' | 'stream_deck'}) {
  return <svg className="deviceIllustration" viewBox="0 0 224 164" role="img"
    aria-label={kind === 'midi' ? 'Launchpad grid controller illustration' : kind === 'stream_deck' ? 'Stream Deck LCD keys illustration' : 'Virtual Pad on a computer and phone illustration'}>
    {kind === 'midi' ? <>
      <rect x="47" y="7" width="137" height="147" rx="8" fill="#293038" stroke="#57626c" />
      <rect x="49" y="9" width="133" height="141" rx="6" fill="#171d22" />
      <g transform="translate(66 40)"><Grid size={10} /></g>
      {Array.from({length: 8}, (_, i) => <g key={i}>
        <circle cx={71 + i * 12} cy="31" r="4" fill={i < 2 ? tokenColor(frame.actions[i ? 'reject' : 'approve']) : '#374049'} />
        <circle cx="166" cy={45 + i * 12} r="4" fill={tokenColor(frame.selectors[i])} stroke={i === 1 ? '#edf2f5' : '#46515a'} />
        <circle cx="57" cy={45 + i * 12} r="3" fill="#303940" />
        <circle cx={71 + i * 12} cy="141" r="3" fill="#303940" />
      </g>)}
      <text x="112" y="20" textAnchor="middle" fill="#aab6c0" fontSize="7">LAUNCHPAD</text>
    </> : kind === 'stream_deck' ? <>
      <path d="M41 137 52 114h119l12 23" fill="#303940" stroke="#57626c" />
      <rect x="24" y="25" width="176" height="111" rx="8" fill="#252c33" stroke="#57626c" />
      <text x="112" y="39" textAnchor="middle" fill="#aab6c0" fontSize="7">STREAM DECK</text>
      {Array.from({length: 15}, (_, i) => {
        const x = 37 + i % 5 * 31, y = 47 + Math.floor(i / 5) * 27;
        const session = view.sessions[i];
        const accent = session ? tokenColor(`accent:${session.accent}:selected`) : '#374049';
        const Icon = i === 10 ? Check : i === 11 ? X : i === 12 ? Square : null;
        const glyph = session ? compileVisualFrame({...view, selected_state: session.state}).state : null;
        return <g key={i}>
          <rect x={x} y={y} width="26" height="23" rx="3" fill="#0c1014" stroke={i === 1 ? '#edf2f5' : '#46515a'} />
          {i < 8 ? <rect x={x + 4} y={y + 3} width="18" height="2" rx="1" fill={accent} /> : null}
          {glyph?.flatMap((row, r) => row.map((token, c) => token === 'off' ? null
            : <rect key={`${r}-${c}`} x={x + 6 + c * 2} y={y + 6 + r * 1.8} width="1.6" height="1.4" fill={tokenColor(token)} />))}
          {Icon ? <Icon x={x + 6} y={y + 5} width="14" height="14" stroke={i === 10 ? '#55c76a' : i === 11 ? '#ef5b64' : '#657079'} /> : null}
        </g>;
      })}
    </> : <>
      <rect x="16" y="26" width="165" height="106" rx="5" fill="#252c33" stroke="#57626c" />
      <rect x="22" y="33" width="153" height="92" rx="2" fill="#0c1014" />
      <g transform="translate(36 39)"><Grid /></g>
      <rect x="128" y="43" width="32" height="3" rx="1" fill={tokenColor('accent:magenta:selected')} />
      <rect x="128" y="53" width="26" height="2" rx="1" fill="#7d8993" />
      <rect x="128" y="67" width="12" height="8" rx="2" fill="#55c76a" />
      <rect x="144" y="67" width="12" height="8" rx="2" fill="#ef5b64" />
      <path d="M16 133H181l11 10H6Z" fill="#303940" stroke="#57626c" />
      <rect x="155" y="67" width="53" height="88" rx="7" fill="#20272e" stroke="#66747f" />
      <rect x="159" y="74" width="45" height="71" rx="2" fill="#0c1014" />
      <g transform="translate(162 89) scale(.48)"><Grid /></g>
      <rect x="174" y="149" width="15" height="2" rx="1" fill="#66747f" />
    </>}
  </svg>;
}
