import {useEffect, useRef, useState} from 'react';
import {ChevronDown, Play, Sparkles} from 'lucide-react';

export function ExploreMenu({disabled, onStart, active}: {disabled: boolean; onStart: (kind: 'demo' | 'show') => void; active?: 'demo' | 'show' | null}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (disabled) setOpen(false); }, [disabled]);
  useEffect(() => {
    if (!open) return;
    root.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener('pointerdown', outside);
    return () => document.removeEventListener('pointerdown', outside);
  }, [open]);
  return <div className="exploreMenu" ref={root} onKeyDown={event => {
    if (event.key === 'Escape') { setOpen(false); trigger.current?.focus(); }
    if (event.key === 'Tab') setOpen(false);
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    if (!open) { if (!disabled) setOpen(true); return; }
    const items = Array.from(root.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? []);
    const index = items.indexOf(document.activeElement as HTMLButtonElement);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1
      : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
    items[next]?.focus();
  }}>
    <button className="textButton" ref={trigger} aria-label="Demo & Show" aria-haspopup="menu" aria-expanded={open}
      disabled={disabled} title={disabled ? 'Disconnect conversations before starting Demo or Show' : 'Demo & Show'}
      onClick={() => setOpen(!open)}>{active === 'show' ? <Sparkles aria-hidden="true" /> : <Play aria-hidden="true" />}
      {active === 'demo' ? 'Demo' : active === 'show' ? 'Show' : 'Demo & Show'} <ChevronDown aria-hidden="true" /></button>
    {open ? <div className="exploreChoices" role="menu" aria-label="Demo & Show">
      {(['demo', 'show'] as const).map(kind => <button key={kind} role="menuitem" onClick={() => {
        setOpen(false); trigger.current?.focus(); onStart(kind);
      }}>{kind === 'demo' ? <Play aria-hidden="true" /> : <Sparkles aria-hidden="true" />}{kind === 'demo' ? 'Demo' : 'Show'}</button>)}
    </div> : null}
  </div>;
}
