import React from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';

export default function DesktopWalkthrough() {
  return (
    <figure style={{margin: '1.5rem 0'}}>
      <video controls preload="none" playsInline style={{width: '100%', borderRadius: 8}}
        poster={useBaseUrl('/media/desktop-workflow-poster.png')}
        src={useBaseUrl('/media/desktop-workflow.mp4')}
        aria-label="Desktop walkthrough: select a Codex session and approve its request" />
      <figcaption>Illustrated walkthrough with simulated chats. No audio.</figcaption>
    </figure>
  );
}
