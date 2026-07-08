import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './index.module.css';

const featureLinks = [
  {
    label: 'Setup',
    title: 'Start the daemon',
    text: 'Install Pad-Lattice, find MIDI ports, and run the sidecar process that owns the Launchpad.',
    to: '/docs/usage/quickstart',
  },
  {
    label: 'Operation',
    title: 'Use with Codex',
    text: 'Mirror Codex task state to the hardware surface and route Launchpad actions back to listeners.',
    to: '/docs/usage/codex-integration',
  },
  {
    label: 'Hardware',
    title: 'Read the surface',
    text: 'Understand the color and shape language for running, waiting, approval, success, and error.',
    to: '/docs/usage/visual-language',
  },
  {
    label: 'Protocol',
    title: 'Integrate agents',
    text: 'Send JSON-line state messages to the daemon and receive approve, reject, retry, and stop actions.',
    to: '/docs/technical-details/architecture',
  },
];

const activePads = new Set([19, 20, 27, 28, 56, 57, 62, 63]);

export default function Home() {
  const logoUrl = useBaseUrl('/img/pad-lattice-logo.svg');

  return (
    <Layout
      title="Pad-Lattice"
      description="Hardware control surface framework for coding agents">
      <main className={styles.page}>
        <section className={styles.hero}>
          <div className={styles.heroGrid}>
            <div className={styles.copy}>
              <p className={styles.kicker}>Pad-Lattice</p>
              <h1>Physical state and action controls for coding agents.</h1>
              <p className={styles.lede}>
                Turn a <strong>Novation Launchpad Pro Mk1</strong> into a
                local supervisor for <strong>Codex CLI</strong>: steady LED
                state, approval controls, and a small socket protocol for
                agent integrations.
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
              <div className={styles.launchpadGrid} aria-hidden="true">
                {Array.from({length: 64}, (_, index) => (
                  <span
                    className={activePads.has(index) ? styles.activePad : styles.pad}
                    key={index}
                  />
                ))}
              </div>
              <div className={styles.statusRow}>
                <span className={styles.approve}>approve</span>
                <span className={styles.waiting}>waiting</span>
                <span className={styles.stop}>stop</span>
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
