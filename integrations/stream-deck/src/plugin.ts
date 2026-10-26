import streamDeck, {action, SingletonAction, type DidReceiveSettingsEvent,
  type KeyDownEvent, type WillAppearEvent, type WillDisappearEvent} from '@elgato/streamdeck';
import {Bridge, type ActionName} from './bridge';
import {actionImage, dataImage, sessionImage} from './render';

type Settings = {slot?: number};
type Key = KeyDownEvent<Settings>['action'];
type Entry = {key: Key; slot: number; revision: number | null; image: string};
const actions: PadAction[] = [];
let address = 'http://127.0.0.1:8765';
const bridge = new Bridge(() => {
  for (const handler of actions) handler.refresh();
  void streamDeck.ui.sendToPropertyInspector({status: bridge.status, address}).catch(() => {});
});

class PadAction extends SingletonAction<Settings> {
  private entries = new Map<string, Entry>();
  private drawing = false;
  private dirty = false;
  constructor(private mode: 'session' | ActionName) { super(); actions.push(this); }

  override onWillAppear(ev: WillAppearEvent<Settings>) {
    if (!ev.action.isKey()) return;
    this.entries.set(ev.action.id, {key: ev.action, slot: this.slot(ev.payload.settings), revision: null, image: ''});
    this.refresh();
  }
  override onWillDisappear(ev: WillDisappearEvent<Settings>) { this.entries.delete(ev.action.id); }
  override onDidReceiveSettings(ev: DidReceiveSettingsEvent<Settings>) {
    const entry = this.entries.get(ev.action.id);
    if (entry) { entry.slot = this.slot(ev.payload.settings); entry.revision = null; this.refresh(); }
  }
  override async onKeyDown(ev: KeyDownEvent<Settings>) {
    const entry = this.entries.get(ev.action.id);
    const sent = entry?.revision != null && (this.mode === 'session'
      ? bridge.select(entry.slot, entry.revision) : bridge.act(this.mode, entry.revision));
    if (!sent) await ev.action.showAlert();
  }
  private slot(settings: Settings): number {
    const slot = settings.slot ?? 0;
    return Number.isInteger(slot) && slot >= 0 && slot < 8 ? slot : -1;
  }
  refresh() {
    this.dirty = true;
    if (!this.drawing) void this.draw();
  }
  private async draw() {
    this.drawing = true;
    try {
      while (this.dirty) {
        this.dirty = false;
        const view = bridge.view;
        const selected = view?.sessions.find(s => s.selected);
        for (const entry of this.entries.values()) {
          const svg = this.mode === 'session'
            ? sessionImage(view?.sessions.find(s => s.slot === entry.slot), entry.slot, bridge.status)
            : actionImage(this.mode, selected, !!view?.available_actions.includes(this.mode));
          entry.revision = null;
          try {
            if (entry.image !== svg) { await entry.key.setImage(dataImage(svg)); entry.image = svg; }
            entry.revision = view?.control_revision ?? null;
          } catch { entry.image = ''; }
        }
      }
    } finally { this.drawing = false; }
  }
}

@action({UUID: 'io.github.mrueda.pad-lattice.session'})
class Session extends PadAction { constructor() { super('session'); } }
@action({UUID: 'io.github.mrueda.pad-lattice.approve'})
class Approve extends PadAction { constructor() { super('approve'); } }
@action({UUID: 'io.github.mrueda.pad-lattice.reject'})
class Reject extends PadAction { constructor() { super('reject'); } }
@action({UUID: 'io.github.mrueda.pad-lattice.stop'})
class Stop extends PadAction { constructor() { super('stop'); } }

for (const handler of [new Session(), new Approve(), new Reject(), new Stop()]) streamDeck.actions.registerAction(handler);
streamDeck.ui.onSendToPlugin(async ev => {
  const message = ev.payload;
  if (!message || typeof message !== 'object' || Array.isArray(message)) return;
  try {
    if (message.type === 'pair' && typeof message.address === 'string' && typeof message.pin === 'string') {
      bridge.pair(message.address, message.pin);
      address = message.address;
      // Only the address persists. PINs and reconnect tokens never enter profiles or settings.
      await streamDeck.settings.setGlobalSettings({address});
    } else if (message.type === 'disconnect') bridge.disconnect();
    await streamDeck.ui.sendToPropertyInspector({status: bridge.status, address});
  } catch {
    await streamDeck.ui.sendToPropertyInspector({status: 'Check the address and six-digit PIN.', address});
  }
});

await streamDeck.connect();
const settings = await streamDeck.settings.getGlobalSettings<{address?: string}>();
if (typeof settings.address === 'string') address = settings.address;
