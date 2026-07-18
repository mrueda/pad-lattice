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
          id: 'usage/production',
          label: 'Production Use',
        },
        {
          type: 'doc',
          id: 'usage/codex-integration',
          label: 'Codex Integration',
        },
        {
          type: 'doc',
          id: 'usage/visual-language',
          label: 'Visual Language',
        },
        {
          type: 'doc',
          id: 'usage/device-testing',
          label: 'Test a Device',
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
      label: 'Technical Details',
      items: [
        {
          type: 'doc',
          id: 'technical-details/developer-guide',
          label: 'Developer Guide',
        },
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
          id: 'technical-details/device-profiles',
          label: 'Device Profiles',
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
