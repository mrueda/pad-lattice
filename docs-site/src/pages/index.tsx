import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './index.module.css';

const featureLinks = [
  {
    label: 'Setup',
    title: 'Start the daemon',
    text: 'Install Pad-Lattice, detect a device profile, and run the sidecar process that owns the MIDI controller.',
    to: '/docs/usage/quickstart',
  },
  {
    label: 'Operation',
    title: 'Use with Codex',
    text: 'Connect normal Codex CLI sessions directly through local lifecycle hooks, without a graphical agent UI.',
    to: '/docs/usage/codex-integration',
  },
  {
    label: 'Profiles',
    title: 'Test more hardware',
    text: 'Validate an experimental or community device with a guided, privacy-preserving physical report.',
    to: '/docs/usage/device-testing',
  },
  {
    label: 'Protocol',
    title: 'Read the visual protocol',
    text: 'See how eight identity accents, state glyphs, selection, actions, and overflow form one physical language.',
    to: '/docs/usage/visual-language',
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

  return (
    <Layout
      title="Pad-Lattice"
      description="MIDI pad controllers reimagined as tactile interfaces for AI agents">
      <main className={styles.page}>
        <section className={styles.hero}>
          <div className={styles.heroGrid}>
            <div className={styles.copy}>
              <p className={styles.kicker}>Pad-Lattice</p>
              <h1>MIDI pad controllers, reimagined for AI agents.</h1>
              <p className={styles.lede}>
                <strong>A tactile language between people and AI agents.</strong>{' '}
                Pad-Lattice brings input and RGB feedback beyond music, turning
                compatible <strong>Novation Launchpads</strong> into local control
                surfaces that integrate directly with <strong>Codex CLI</strong>.
              </p>
              <div className={styles.actions}>
                <Link className="button button--primary button--lg" to="/docs/overview">
                  Read the docs
                </Link>
                <Link className="button button--secondary button--lg" to="/docs/usage/quickstart">
                  Quick start
                </Link>
                <Link className="button button--secondary button--lg" to="/docs/usage/production">
                  Production use
                </Link>
              </div>
            </div>

            <div className={styles.surfacePanel} aria-label="Pad-Lattice Launchpad state preview">
              <Link className={styles.identity} to="/docs/overview">
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
            </div>
          </div>
        </section>

        <section className={styles.sections}>
          <div className={styles.grid}>
            {featureLinks.map((feature) => (
              <Link className={styles.card} to={feature.to} key={feature.title}>
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
