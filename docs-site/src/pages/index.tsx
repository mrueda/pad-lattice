import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './index.module.css';

const featureLinks = [
  {
    label: 'Recommended',
    title: 'Start with Desktop',
    text: 'Connect open Codex CLI chats in one app. Python is bundled; no MIDI controller is required. Preview builds for Linux and macOS.',
    to: '/docs/usage/install',
  },
  {
    label: 'No hardware needed',
    title: 'Try the virtual pad',
    text: 'Explore a guided multi-agent story and the complete visual vocabulary directly in your browser.',
    to: 'pathname:///play/',
  },
  {
    label: 'Everyday setup',
    title: 'Connect your screens',
    text: 'Pair phones, tablets, and laptops, including a clear setup for Parallels Desktop.',
    to: '/docs/usage/connect-browsers',
  },
  {
    label: 'Protocol',
    title: 'Read the visual protocol',
    text: 'See how identity accents, state glyphs, selection, actions, and overflow form one shared visual language.',
    to: '/docs/technical-details/visual-language',
  },
];

const approvalGlyph = new Set([3, 11, 19, 27, 35, 59]);
const statusPads: Record<number, string> = {
  7: 'statusApproval',
  15: 'statusRunning',
  23: 'statusReply',
  31: 'statusSuccess',
};
const topControls = [
  'actionApprove',
  'actionReject',
  'railOff',
  'railOff',
  'railOff',
  'railOff',
  'railOff',
  'railOff',
];
const sceneControls = [
  'sceneCyan',
  'sceneMagenta',
  'sceneLime',
  'sceneOrange',
  'railOff',
  'railOff',
  'railOff',
  'railOff',
];

export default function Home() {
  const logoUrl = useBaseUrl('/img/pad-lattice-logo.svg');
  const workflowUrl = useBaseUrl('/img/human-control-workflow.svg');
  const workflowMobileUrl = useBaseUrl('/img/human-control-workflow-mobile.svg');

  return (
    <Layout
      title="Human control surfaces for AI agents"
      description="Connect open Codex CLI conversations with the Pad-Lattice desktop app. Use the virtual pad, a Launchpad, or paired phones and tablets.">
      <main className={styles.page}>
        <section className={styles.hero}>
          <div className={styles.heroGrid}>
            <div className={styles.copy}>
              <p className={styles.kicker}>Pad-Lattice</p>
              <h1>Monitor and direct AI agents from a physical or virtual pad.</h1>
              <p className={styles.lede}>
                <strong>A tactile visual language between people and AI agents.</strong>{' '}
                See which session is working, waiting, requesting approval, or
                finished. Connect your open <strong>Codex CLI</strong> chats in the{' '}
                <strong>desktop app</strong>, then act from its pad, a{' '}
                <strong>Novation Launchpad</strong>, or a paired phone or tablet.
                No MIDI controller is required.
              </p>
              <div className={styles.actions}>
                <Link className="button button--primary button--lg" to="/docs/usage/install">
                  Get Desktop Preview
                </Link>
                <Link className="button button--secondary button--lg" to="pathname:///play/" target="_self">
                  Try the simulation
                </Link>
              </div>
            </div>

            <div className={styles.surfacePanel} aria-label="Pad-Lattice virtual surface preview">
              <Link className={styles.identity} to="pathname:///play/" target="_self">
                <img className={styles.logo} src={logoUrl} alt="Pad-Lattice logo" />
                <span>Pad-Lattice</span>
              </Link>
              <div className={styles.surfaceTopology} aria-hidden="true">
                <div className={styles.topRail}>
                  {topControls.map((control, index) => (
                    <span className={`${styles.railPad} ${styles[control]}`} key={index} />
                  ))}
                </div>
                <div className={styles.controllerBody}>
                  <div className={styles.launchpadGrid}>
                    {Array.from({length: 64}, (_, index) => {
                      const semanticClass = approvalGlyph.has(index)
                        ? styles.glyphApproval
                        : statusPads[index]
                          ? styles[statusPads[index]]
                          : '';
                      return (
                        <span className={`${styles.pad} ${semanticClass}`} key={index} />
                      );
                    })}
                  </div>
                  <div className={styles.sceneRail}>
                    {sceneControls.map((control, index) => (
                      <span className={`${styles.scenePad} ${styles[control]}`} key={index} />
                    ))}
                  </div>
                </div>
              </div>
              <div className={styles.protocolReadout}>
                <span><i className={styles.cyanDot} />Scene 1</span>
                <span><i className={styles.amberDot} />approval requested</span>
                <span><i className={styles.greenDot} />approve</span>
                <span><i className={styles.redDot} />reject</span>
              </div>
              <Link className={styles.openSurface} to="pathname:///play/" target="_self">
                Open interactive surface
              </Link>
            </div>
          </div>
        </section>

        <section className={styles.workflow} aria-label="A real Pad-Lattice workflow">
          <div className={styles.workflowInner}>
            <picture>
              <source media="(max-width: 640px)" srcSet={workflowMobileUrl} />
              <img
                className={styles.workflowImage}
                src={workflowUrl}
                alt="Codex asks for approval, physical and virtual pads light up, and one human press returns a targeted action"
              />
            </picture>
          </div>
        </section>

        <section className={styles.sections}>
          <div className={styles.grid}>
            {featureLinks.map((feature) => (
              <Link
                className={styles.card}
                to={feature.to}
                target={feature.to.startsWith('pathname:') ? '_self' : undefined}
                key={feature.title}>
                <span>{feature.label}</span>
                <h2>{feature.title}</h2>
                <p>{feature.text}</p>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </Layout>
  );
}
