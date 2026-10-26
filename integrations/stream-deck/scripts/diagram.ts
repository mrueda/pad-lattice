import {writeFileSync} from 'node:fs';
import {sessionImage, actionImage} from '../src/render';
import type {SessionView} from '../../../web-app/src/types';

const sessions: SessionView[] = [
  {slot: 0, state: 'running', selected: false, accent: 'cyan', label: 'Implement'},
  {slot: 1, state: 'waiting_for_approval', selected: true, accent: 'magenta', label: 'Review'},
  {slot: 2, state: 'success', selected: false, accent: 'lime', label: 'Tests'},
];
const images = [...sessions.map(s => sessionImage(s, s.slot, 'Connected')),
  ...(['approve', 'reject', 'stop'] as const).map(a => actionImage(a, sessions[1], a !== 'stop'))];
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="520" height="394" viewBox="0 0 520 394" role="img" aria-labelledby="title desc">
<title id="title">Pad-Lattice Stream Deck example</title><desc id="desc">Three session keys show blue working dots, an amber approval exclamation, and a green success smile. Review is selected with a white border. Approve and Reject are enabled for Review; Stop is disabled.</desc>
<rect width="520" height="394" rx="8" fill="#20282f"/>
<text x="260" y="28" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#edf2f5">Same glyphs. One session per key.</text>
${images.map((s, i) => s.replace('<svg ', `<svg x="${28 + i % 3 * 160}" y="${46 + Math.floor(i / 3) * 160}" `)).join('\n')}
<text x="260" y="382" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#b5c1c9">Example layout, not a hardware photograph</text></svg>\n`;
writeFileSync('../../docs-site/static/img/stream-deck-layout.svg', svg);
