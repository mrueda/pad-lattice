import {useEffect, useRef, type ReactNode} from 'react';
import {X} from 'lucide-react';

export function PairingDialog({open, onClose, children, title = 'Pair a device'}: {open: boolean; onClose: () => void; children: ReactNode; title?: string}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (open) dialog.current?.showModal();
    else dialog.current?.close();
  }, [open]);
  return <dialog className="pairingDialog" ref={dialog} aria-labelledby="pairing-dialog-title" onCancel={onClose}
    onClick={event => {if (event.target === dialog.current) onClose();}}>
    <div className="pairingDialogBody">
      <div className="desktopToolbar"><h2 id="pairing-dialog-title">{title}</h2>
        <button className="textButton" onClick={onClose} aria-label="Close pairing code" title="Close pairing code"><X /></button></div>
      {children}
    </div>
  </dialog>;
}
