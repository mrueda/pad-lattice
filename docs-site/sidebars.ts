import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    {
      type: 'doc',
      id: 'overview',
      label: 'Overview',
    },
    {
      type: 'category',
      label: 'Use',
      items: [
        {
          type: 'doc',
          id: 'usage/quickstart',
          label: 'Quick Start',
        },
        {
          type: 'doc',
          id: 'usage/connect-browsers',
          label: 'Phones, Tablets & Laptops',
        },
        {
          type: 'doc',
          id: 'usage/control-codex',
          label: 'Control Codex',
        },
        {
          type: 'doc',
          id: 'usage/troubleshooting',
          label: 'Troubleshooting',
        },
      ],
    },
    {
      type: 'category',
      label: 'Explore',
      items: [
        {
          type: 'doc',
          id: 'usage/audio-feedback',
          label: 'Audio Feedback',
        },
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
          ],
        },
        {
          type: 'category',
          label: 'Integrations & Surfaces',
          items: [
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
      label: 'Reference',
      items: [
        {
          type: 'doc',
          id: 'reference/socket-protocol',
          label: 'Socket Protocol',
        },
        {
          type: 'doc',
          id: 'reference/cli',
          label: 'CLI',
        },
      ],
    },
    {
      type: 'category',
      label: 'About',
      items: [
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
