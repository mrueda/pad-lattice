import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    {
      type: 'doc',
      id: 'overview',
      label: 'Overview',
    },
    {
      type: 'doc',
      id: 'usage/control-codex',
      label: 'How It Works',
    },
    {
      type: 'category',
      label: 'Get Started',
      items: [
        {type: 'doc', id: 'usage/install', label: 'Install'},
        {
          type: 'doc',
          id: 'usage/quickstart',
          label: 'Quick Start',
        },
        {type: 'doc', id: 'usage/audio-feedback', label: 'Audio Feedback'},
      ],
    },
    {
      type: 'category',
      label: 'Device Catalog',
      link: {type: 'doc', id: 'usage/device-catalog'},
      items: [
        {
          type: 'category',
          label: 'Virtual Surfaces',
          items: [
            {type: 'doc', id: 'usage/desktop', label: 'Desktop Pad'},
            {type: 'doc', id: 'usage/connect-browsers', label: 'Phones, Tablets & Browsers'},
            {type: 'link', label: 'Public Playground', href: 'pathname:///play/'},
          ],
        },
        {
          type: 'category',
          label: 'Physical Controllers',
          items: [
            {type: 'doc', id: 'usage/launchpad', label: 'Novation Launchpad'},
            {type: 'doc', id: 'usage/stream-deck', label: 'Elgato Stream Deck'},
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Creative Uses',
      items: [
        {
          type: 'doc',
          id: 'usage/visual-show',
          label: 'Visual Show',
        },
      ],
    },
    {
      type: 'category',
      label: 'Technical Details',
      link: {
        type: 'doc',
        id: 'technical-details/index',
      },
      items: [
        {
          type: 'category',
          label: 'Core Model',
          collapsed: false,
          items: [
            {
              type: 'doc',
              id: 'technical-details/architecture',
              label: 'Architecture',
            },
            {
              type: 'doc',
              id: 'technical-details/multi-agent-design',
              label: 'Multi-Agent Design',
            },
            {
              type: 'doc',
              id: 'technical-details/visual-language',
              label: 'Visual Protocol',
            },
            {type: 'doc', id: 'reference/socket-protocol', label: 'Socket Protocol'},
          ],
        },
        {
          type: 'category',
          label: 'Integrations & Surfaces',
          items: [
            {type: 'doc', id: 'technical-details/desktop', label: 'Desktop App'},
            {
              type: 'doc',
              id: 'technical-details/codex-integration',
              label: 'Codex Integration',
            },
            {
              type: 'doc',
              id: 'technical-details/virtual-surface',
              label: 'Browser Surface',
            },
          ],
        },
        {
          type: 'category',
          label: 'Hardware',
          items: [
            {
              type: 'doc',
              id: 'technical-details/device-profiles',
              label: 'Device Profiles',
            },
            {
              type: 'doc',
              id: 'technical-details/device-testing',
              label: 'Device Testing',
            },
          ],
        },
        {
          type: 'category',
          label: 'Operations & Development',
          items: [
            {type: 'doc', id: 'usage/cli', label: 'CLI Setup'},
            {type: 'doc', id: 'reference/cli', label: 'CLI Reference'},
            {
              type: 'doc',
              id: 'technical-details/security-model',
              label: 'Security Model',
            },
            {
              type: 'doc',
              id: 'technical-details/production',
              label: 'Production Operations',
            },
            {
              type: 'doc',
              id: 'technical-details/developer-guide',
              label: 'Developer Guide',
            },
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Help',
      link: {type: 'doc', id: 'help/faq'},
      items: [
        {type: 'doc', id: 'help/faq', label: 'FAQ'},
        {type: 'doc', id: 'usage/troubleshooting', label: 'Troubleshooting'},
        {
          type: 'doc',
          id: 'about/origin-and-development',
          label: 'Origin & Development',
        },
        {
          type: 'doc',
          id: 'about/roadmap',
          label: 'Roadmap',
        },
        {
          type: 'doc',
          id: 'about/license',
          label: 'License',
        },
      ],
    },
  ],
};

export default sidebars;
