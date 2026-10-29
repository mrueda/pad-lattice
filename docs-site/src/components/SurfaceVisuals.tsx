import React from 'react';
import {compileVisualFrame, tokenColor} from '../../../web-app/src/surfaceModel';
import type {AgentState, ControlAction, SessionView, SurfaceView} from '../../../web-app/src/types';
import styles from './SurfaceVisuals.module.css';
import deckLayouts from '../../../integrations/stream-deck/layouts.json';

const examples: {state: AgentState; name: string; meaning: string}[] = [
  {state: 'idle', name: 'Ready', meaning: 'Idle. No reply or approval is requested.'},
  {state: 'running', name: 'Working', meaning: 'The agent is running.'},
  {state: 'waiting_for_reply', name: 'Your reply', meaning: 'Codex has asked a question.'},
  {state: 'waiting_for_approval', name: 'Permission needed', meaning: 'Read the request, then approve or reject.'},
  {state: 'success', name: 'Success', meaning: 'The task finished successfully.'},
  {state: 'error', name: 'Error', meaning: 'Check Codex for the details.'},
  {state: 'user_typing', name: 'Typing', meaning: 'Input is in progress, when reported by the integration.'},
  {state: 'cancelled', name: 'Cancelled', meaning: 'The task was stopped.'},
];
const sessions: SessionView[] = [
  {slot: 0, state: 'running', selected: false, accent: 'cyan', label: 'Implement'},
  {slot: 1, state: 'waiting_for_approval', selected: true, accent: 'magenta', label: 'Review'},
  {slot: 2, state: 'success', selected: false, accent: 'lime', label: 'Tests'},
];
function view(state: AgentState): SurfaceView {
  return {selected_state: state, frame: 0, sessions, available_actions: ['approve', 'reject'], overflow_count: 0, activity_motion: false};
}
function Pixels({state, x = 0, y = 0, step = 10}: {state: AgentState; x?: number; y?: number; step?: number}) {
  return <g>{compileVisualFrame(view(state)).state.flatMap((row, r) => row.map((token, c) =>
    <rect key={`${r}-${c}`} x={x + c * step} y={y + r * step} width={step - 2} height={step - 2} rx={1} fill={tokenColor(token)} />))}</g>;
}
export function StateLegend({all = false}: {all?: boolean}) {
  return <div className={styles.legend}>{(all ? examples : examples.slice(0, 6)).map(e =>
    <div className={styles.state} key={e.state}>
      <svg viewBox="0 0 86 96" width="86" height="96" role="img" aria-label={e.name}>
        <rect width="86" height="96" rx="6" fill="#10151a" /><Pixels state={e.state} x={9} y={9} />
      </svg>
      <div><strong>{e.name}</strong><p>{e.meaning}</p></div>
    </div>)}</div>;
}

export function LaunchpadDiagram() {
  const frame = compileVisualFrame(view('waiting_for_approval'));
  const top: (ControlAction | null)[] = ['approve', 'reject', null, null, null, null, 'retry', 'stop'];
  return <figure className={styles.figure}>
    <svg viewBox="0 0 520 550" role="img" aria-label="Launchpad Pro Mk1 shape and controls: 64 square pads, eight round controls on each side, USB connection above. Review is selected; Approve and Reject are lit.">
      <path d="M260 0 V32" stroke="#67747f" strokeWidth="10" />
      <rect x="245" y="20" width="30" height="22" rx="3" fill="#424d58" />
      <rect x="24" y="38" width="472" height="496" rx="18" fill="#05080b" />
      <rect x="24" y="28" width="472" height="496" rx="18" fill="#242c33" stroke="#49545e" strokeWidth="2" />
      <text x="48" y="58" fill="#d6dde2" fontFamily="sans-serif" fontSize="15">novation</text>
      <text x="472" y="58" textAnchor="end" fill="#d6dde2" fontFamily="sans-serif" fontSize="15">Launchpad Pro</text>
      {top.map((action, i) => <g key={i}>
        <circle cx={98 + i * 42} cy="90" r="12" fill={action ? tokenColor(frame.actions[action]) : '#13191e'} stroke="#56616a" />
        <text x={98 + i * 42} y="95" textAnchor="middle" fill={i < 2 ? '#10151a' : '#8b969f'} fontSize="15">{['\u2713', '\u00d7', '', '', '\u2026', '', '\u21bb', '\u25a0'][i]}</text>
      </g>)}
      {Array.from({length: 8}, (_, r) => <g key={r}>
        <circle cx="56" cy={134 + r * 42} r="12" fill="#13191e" stroke="#56616a" />
        <circle cx={98 + r * 42} cy="472" r="12" fill="#13191e" stroke="#56616a" />
        {Array.from({length: 8}, (_, c) => <rect key={c} x={80 + c * 42} y={116 + r * 42} width="36" height="36" rx="4"
          fill={tokenColor(c === 7 ? frame.statuses[r] : frame.state[r][c])} stroke="#4b555e" strokeWidth="1" />)}
        <circle cx="448" cy={134 + r * 42} r="13" fill={tokenColor(frame.selectors[r])} stroke={r === 1 ? '#ffffff' : '#56616a'} strokeWidth={r === 1 ? 3 : 1} />
        <text x="448" y={139 + r * 42} textAnchor="middle" fontSize="13" fill="#ffffff">{r + 1}</text>
      </g>)}
      <text x="260" y="509" textAnchor="middle" fontFamily="sans-serif" fontSize="13" fill="#aab5bd">Pad-Lattice mapping · Review selected</text>
    </svg>
    <figcaption>Illustrated Pro Mk1, not a hardware photograph. The left and bottom buttons are reserved.</figcaption>
    <dl className={styles.key}>
      <div><dt>Top buttons</dt><dd>Approve and Reject are lit. Other actions light only when available.</dd></div>
      <div><dt>Right buttons</dt><dd>Select a session. Here, button 2 selects Review.</dd></div>
      <div><dt>Main grid</dt><dd>The amber exclamation means Review needs permission.</dd></div>
      <div><dt>Last grid column</dt><dd>One status light per session, separate from its identity color.</dd></div>
    </dl>
  </figure>;
}

export function StreamDeckDiagram() {
  return <figure className={styles.figure}>
    <svg viewBox="0 0 700 510" role="img" aria-label="Illustrated Stream Deck MK.2. Top keys each represent one Codex session: Implement, Review, and Tests. Press a session key to select it; Review has the white selection border and amber approval glyph. Bottom action keys target only Review. Approve and Reject are enabled; Stop is disabled. Key positions are configurable.">
      <path d="M350 0 V40" stroke="#67747f" strokeWidth="10" />
      <path d="M238 420 L214 488 Q350 510 486 488 L462 420" fill="#252d34" stroke="#49545e" strokeWidth="3" />
      <rect x="44" y="40" width="612" height="414" rx="26" fill="#080b0e" />
      <rect x="44" y="26" width="612" height="414" rx="26" fill="#272e35" stroke="#505b65" strokeWidth="3" />
      <text x="350" y="60" textAnchor="middle" fontFamily="sans-serif" fontSize="20" fill="#d6dde2">STREAM DECK</text>
      {Array.from({length: 15}, (_, i) => {
        const session = i < 8 ? sessions[i] : undefined;
        const action = i >= 10 && i <= 12 ? ['Approve', 'Reject', 'Stop'][i - 10] : null;
        const active = i === 10 || i === 11;
        const color = i === 10 ? '#55c76a' : i === 11 ? '#ef5b64' : '#657079';
        return <g key={i} transform={`translate(${64 + i % 5 * 116} ${78 + Math.floor(i / 5) * 116})`}>
          <rect width="104" height="104" rx="10" fill="#080b0e" stroke={session?.selected ? '#ffffff' : active ? '#c83ec9' : '#4b555e'} strokeWidth={session?.selected || active ? 3 : 2} />
          {session ? <>
            <rect x="9" y="8" width="86" height="4" rx="2" fill={tokenColor(`accent:${session.accent}:selected`)} />
            <Pixels state={session.state} x={25} y={19} step={8} />
            <text x="52" y="96" textAnchor="middle" fill="#edf2f5" fontSize="11">{session.label}</text>
          </> : action ? <>
            <text x="52" y="57" textAnchor="middle" fill={color} fontSize="42">{['\u2713', '\u00d7', '\u25a0'][i - 10]}</text>
            <text x="52" y="79" textAnchor="middle" fill={color} fontSize="14">{action}</text>
            <text x="52" y="96" textAnchor="middle" fill="#d6dde2" fontSize="11">Review</text>
          </> : <text x="52" y="59" textAnchor="middle" fill="#657079" fontSize="12">{i < 8 ? `Session ${i + 1}` : 'Other apps'}</text>}
        </g>;
      })}
    </svg>
    <figcaption><strong>Top keys select sessions. Bottom keys act on the selected session.</strong><br />MK.2-style example, not physically tested. You choose the key positions.</figcaption>
    <dl className={styles.key}>
      <div><dt>One session per key</dt><dd>Implement, Review, and Tests are three separate Codex conversations. Press one to select it.</dd></div>
      <div><dt>Identity and state</dt><dd>Magenta identifies Review. Its amber exclamation means approval is needed, even before you select it.</dd></div>
      <div><dt>White border: selected</dt><dd>Review is selected here. Another session asking for approval does not change that selection.</dd></div>
      <div><dt>Action keys name their target</dt><dd>Approve and Reject apply only to Review. Stop is dim and unavailable; unused keys can host other plugins.</dd></div>
    </dl>
  </figure>;
}

export function StreamDeckModelDiagram({model}: {model: 'xl' | 'neo'}) {
  const layout = deckLayouts[model];
  const examples: SessionView[] = Array.from({length: 8}, (_, slot) => ({slot,
    state: slot === 1 ? 'waiting_for_approval' : 'running', selected: slot === 1,
    accent: (['cyan', 'magenta', 'lime', 'orange', 'violet', 'teal', 'rose', 'sky'] as const)[slot],
    label: slot === 1 ? 'Review' : `Agent ${slot + 1}`}));
  return <div>{layout.pages.map((page, pageIndex) => <figure className={styles.figure} key={pageIndex}>
    <svg viewBox={`0 0 ${layout.columns * 76 + 28} ${layout.rows * 76 + 46}`} role="img"
      aria-label={`${layout.label}, page ${pageIndex + 1}: session keys and actions for Review`}>
      <rect width="100%" height="100%" rx="8" fill="#20282f" />
      <text x="14" y="22" fill="#edf2f5" fontSize="14">{layout.label}{layout.pages.length > 1 ? ` - page ${pageIndex + 1}` : ''}</text>
      {page.map((value, index) => {
        const session = typeof value === 'number' ? examples[value] : undefined;
        const action = typeof value === 'string' && value !== 'retry' ? value : null;
        const color = action === 'approve' ? '#55c76a' : action === 'reject' ? '#ef5b64' : '#657079';
        return <g key={index} transform={`translate(${14 + index % layout.columns * 76} ${32 + Math.floor(index / layout.columns) * 76})`}>
          <rect width="68" height="68" rx="5" fill="#10151a" stroke={session?.selected ? '#ffffff' : action && action !== 'stop' ? '#c83ec9' : '#4b555e'} strokeWidth={session?.selected ? 2 : 1} />
          {session ? <><rect x="6" y="5" width="56" height="3" rx="1" fill={tokenColor(`accent:${session.accent}:selected`)} />
            <Pixels state={session.state} x={18} y={10} step={4.5} />
            <text x="34" y="62" textAnchor="middle" fill="#edf2f5" fontSize="9">{session.label}</text></>
            : action ? <><text x="34" y="39" textAnchor="middle" fill={color} fontSize="25">{action === 'approve' ? '\u2713' : action === 'reject' ? '\u00d7' : '\u25a0'}</text>
              <text x="34" y="53" textAnchor="middle" fill={color} fontSize="9">{action[0].toUpperCase() + action.slice(1)}</text>
              <text x="34" y="63" textAnchor="middle" fill="#d6dde2" fontSize="8">Review</text></> : null}
        </g>;
      })}
    </svg>
    <figcaption>{layout.label}{layout.pages.length > 1 ? `, page ${pageIndex + 1} of ${layout.pages.length}` : ''}. Editable starter profile; not physically tested.</figcaption>
  </figure>)}</div>;
}
