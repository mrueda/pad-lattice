import {useState} from 'react';
import {ExternalLink} from 'lucide-react';
import {isDesktop, openProjectLink} from './desktop';

export function PageFrame({
  children,
  modeLabel,
  connected,
  connectionLabel,
  padOnly = false,
  headerActions,
}: {
  children: React.ReactNode;
  modeLabel: string;
  connected: boolean;
  connectionLabel?: string;
  padOnly?: boolean;
  headerActions?: React.ReactNode;
}) {
  const [linkError, setLinkError] = useState('');
  const openLink = (event: React.MouseEvent, destination: 'docs' | 'github') => {
    if (!isDesktop()) return;
    event.preventDefault();
    setLinkError('');
    void openProjectLink(destination).catch((error: unknown) => setLinkError(String(error)));
  };
  return (
    <main className={`appPage${isDesktop() ? ' desktopApp' : ''}${padOnly ? ' padOnly' : ''}`}>
      <header className="appHeader">
        <a className="brand" href={isDesktop() ? 'https://mrueda.github.io/pad-lattice/' : '../'} target={isDesktop() ? '_blank' : '_top'} onClick={(event) => openLink(event, 'docs')}>
          <img src="./pad-lattice-logo.svg" alt="" />
          <span><strong>Pad-Lattice</strong><small>{isDesktop() ? 'Desktop' : 'Virtual Surface'}</small></span>
        </a>
        <div className="headerStatus">
          {headerActions}
          {connectionLabel ? <span className={`connectionBadge${connected ? ' connected' : ''}`} role="status">
            <span className={connected ? 'connectionDot connected' : 'connectionDot'} aria-hidden="true" />
            {connectionLabel}
          </span> : <span className={connected ? 'connectionDot connected' : 'connectionDot'} aria-hidden="true" />}
          <span>{modeLabel}</span>
        </div>
      </header>
      {children}
      {linkError ? <p className="desktopError" role="alert">{linkError}</p> : null}
      <footer className="appFooter">
        <span>A tactile visual language between people and AI agents.</span>
        <a href="https://github.com/mrueda/pad-lattice" target="_blank" rel="noreferrer" onClick={(event) => openLink(event, 'github')}>
          GitHub <ExternalLink aria-hidden="true" />
        </a>
      </footer>
    </main>
  );
}

export function Loading() {
  return (
    <main className="loadingPage">
      <img src="./pad-lattice-logo.svg" alt="Pad-Lattice" />
      <span>Opening surface…</span>
    </main>
  );
}

export function LoadFailure({message}: {message: string}) {
  return (
    <main className="loadingPage">
      <img src="./pad-lattice-logo.svg" alt="Pad-Lattice" />
      <span>{message}</span>
    </main>
  );
}
