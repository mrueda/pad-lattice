import {compileVisualFrame, tokenColor} from '../../../web-app/src/surfaceModel';
import type {SessionView} from '../../../web-app/src/types';
import type {ActionName} from './bridge';
import {Check, X, Square} from 'lucide';

export function xml(text: string): string {
  return text.replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;'}[c]!));
}
function short(text: string, length = 14) {
  const points = Array.from(text);
  return xml(points.length > length ? points.slice(0, length - 1).join('') + '…' : text);
}
function image(content: string, border = '#38444e') {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144" viewBox="0 0 144 144"><rect x="3" y="3" width="138" height="138" rx="8" fill="#10151a" stroke="${border}" stroke-width="5"/>${content}</svg>`;
}
function text(label: string, y: number, size = 14, color = '#edf2f5') {
  return `<text x="72" y="${y}" text-anchor="middle" font-family="sans-serif" font-size="${size}" fill="${color}">${short(label)}</text>`;
}
export function sessionImage(session: SessionView | undefined, slot: number, status: string): string {
  if (!session) return image(text(`Session ${slot + 1}`, 65) + text(status === 'Connected' ? 'Empty' : status, 88, 12, '#8e99a2'));
  const frame = compileVisualFrame({selected_state: session.state, sessions: [], frame: 0,
    available_actions: [], overflow_count: 0, activity_motion: false});
  const pixels = frame.state.flatMap((row, y) => row.map((token, x) => token === 'off' ? ''
    : `<rect x="${38 + x * 10}" y="${26 + y * 10}" width="8" height="8" rx="1" fill="${tokenColor(token)}"/>`)).join('');
  const accent = tokenColor(`accent:${session.accent}:selected`);
  return image(`<rect x="14" y="13" width="116" height="6" rx="2" fill="${accent}"/>${pixels}${text(session.label, 125, 13)}`,
    session.selected ? '#ffffff' : '#38444e');
}
export function actionImage(action: ActionName, selected: SessionView | undefined, enabled: boolean): string {
  const color = enabled ? tokenColor(`action:${action}:enabled`) : '#657079';
  const icon = {approve: Check, reject: X, stop: Square}[action];
  const nodes = (icon[2] ?? []).map(([tag, attrs]) => `<${tag} ${Object.entries(attrs).map(([k, v]) => `${k}="${xml(String(v))}"`).join(' ')}/>`).join('');
  return image(`<g transform="translate(36 31) scale(3)" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${nodes}</g>`
    + text(action[0].toUpperCase() + action.slice(1), 113, 16, color) + text(selected?.label ?? 'No session', 132, 11),
    enabled && selected ? tokenColor(`accent:${selected.accent}:selected`) : '#38444e');
}
export function dataImage(svg: string): string {
  return 'data:image/svg+xml;base64,' + Buffer.from(svg).toString('base64');
}
