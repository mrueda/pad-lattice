import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Pad-Lattice Docs',
  tagline: 'MIDI pad controllers, reimagined for AI agents',
  url: 'https://mrueda.github.io',
  baseUrl: '/pad-lattice/',
  organizationName: 'mrueda',
  projectName: 'pad-lattice',
  onBrokenLinks: 'warn',
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },
  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: 'docs',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],
  themes: [
    [
      '@easyops-cn/docusaurus-search-local',
      {
        hashed: true,
        language: ['en'],
        indexDocs: true,
        indexBlog: false,
        docsRouteBasePath: '/docs',
      },
    ],
  ],
  themeConfig: {
    image: 'img/pad-lattice-social.svg',
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Pad-Lattice',
      logo: {
        alt: 'Pad-Lattice logo',
        src: 'img/pad-lattice-logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/docs/usage/quickstart',
          label: 'Quick Start',
          position: 'left',
        },
        {
          to: '/docs/usage/production',
          label: 'Production Use',
          position: 'left',
        },
        {
          to: '/docs/usage/device-testing',
          label: 'Test a Device',
          position: 'left',
        },
        {
          href: 'https://github.com/mrueda/pad-lattice',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {
              label: 'Overview',
              to: '/docs/overview',
            },
            {
              label: 'Quick Start',
              to: '/docs/usage/quickstart',
            },
            {
              label: 'Production Use',
              to: '/docs/usage/production',
            },
            {
              label: 'Test a Device',
              to: '/docs/usage/device-testing',
            },
            {
              label: 'Troubleshooting',
              to: '/docs/usage/troubleshooting',
            },
            {
              label: 'CLI Reference',
              to: '/docs/reference/cli',
            },
          ],
        },
        {
          title: 'Project',
          items: [
            {
              label: 'Repository',
              href: 'https://github.com/mrueda/pad-lattice',
            },
            {
              label: 'License',
              href: 'https://github.com/mrueda/pad-lattice/blob/main/LICENSE',
            },
          ],
        },
      ],
      copyright: 'Copyright (C) 2026 Manuel Rueda.',
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
