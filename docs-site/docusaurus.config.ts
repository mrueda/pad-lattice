import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Pad-Lattice',
  tagline: 'Physical and virtual control surfaces for AI agents',
  url: 'https://mrueda.github.io',
  baseUrl: '/pad-lattice/',
  organizationName: 'mrueda',
  projectName: 'pad-lattice',
  onBrokenLinks: 'throw',
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'throw',
    },
  },
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },
  staticDirectories: ['static', '../src/pad_lattice/web_dist'],
  plugins: ['./plugins/publish-schemas'],
  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: 'docs',
        },
        blog: false,
        sitemap: {
          createSitemapItems: async (params) => {
            const items = await params.defaultCreateSitemapItems(params);
            const virtualPadUrl = `${params.siteConfig.url}${params.siteConfig.baseUrl}play/`;
            return items.some((item) => item.url === virtualPadUrl)
              ? items
              : [...items, {url: virtualPadUrl}];
          },
        },
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
    image: 'img/pad-lattice-social.png',
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
          to: '/docs/usage/control-codex',
          label: 'How It Works',
          position: 'left',
        },
        {
          to: '/docs/usage/device-catalog',
          label: 'Device Catalog',
          position: 'left',
        },
        {
          to: '/docs/usage/install',
          label: 'Install',
          position: 'left',
        },
        {
          href: 'pathname:///play/',
          label: 'Try the Pad',
          position: 'left',
          target: '_self',
        },
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          href: 'https://www.youtube.com/playlist?list=PLNX7c9WDBavo',
          label: 'Videos',
          position: 'right',
        },
        {
          href: 'https://github.com/mrueda/pad-lattice',
          label: 'GitHub',
          position: 'right',
        },
        {to: '/docs/help/faq', label: 'Help', position: 'right'},
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'FAQ', to: '/docs/help/faq'},
            {label: 'Install Desktop', to: '/docs/usage/install'},
            {
              label: 'Virtual Pad',
              href: 'pathname:///play/',
            },
            {
              label: 'Overview',
              to: '/docs/overview',
            },
            {
              label: 'Quick Start',
              to: '/docs/usage/quickstart',
            },
            {
              label: 'Device Catalog',
              to: '/docs/usage/device-catalog',
            },
            {
              label: 'How It Works',
              to: '/docs/usage/control-codex',
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
            {label: 'Cite Pad-Lattice', to: '/docs/about/citation'},
            {
              label: 'YouTube walkthroughs',
              href: 'https://www.youtube.com/playlist?list=PLNX7c9WDBavo',
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
