import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: 'Kaizen Agent',
  tagline: 'AI Debugging Engineer for AI Agents',
  favicon: 'img/favicon.ico',

  // Future flags, see https://docusaurus.io/docs/api/docusaurus-config#future
  future: {
    v4: true, // Improve compatibility with the upcoming Docusaurus v4
  },

  // Set the production url of your site here
  url: 'https://kaizen-agent.github.io',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/kaizen-agent/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'Kaizen-agent', // Usually your GitHub org/user name.
  projectName: 'kaizen-agent', // Usually your repo name.

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
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
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            'https://github.com/Kaizen-agent/kaizen-agent/tree/main/kaizen-agent-docs/',
        },
        blog: false, // Disable the blog
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    // Replace with your project's social card
    image: 'img/docusaurus-social-card.jpg',
    navbar: {
      title: 'Kaizen Agent',
      logo: {
        alt: 'Kaizen Agent Logo',
        src: 'img/kaizen_logo_smaller.png',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docs',
          position: 'left',
          label: 'Documentation',
        },
        {
          href: 'https://github.com/Kaizen-agent/kaizen-agent',
          label: 'GitHub',
          position: 'right',
        },
        {
          href: 'https://discord.gg/2A5Genuh',
          label: 'Discord',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {
              label: 'Quick Start',
              to: '/docs/quickstart',
            },
            {
              label: 'Usage Guide',
              to: '/docs/usage',
            },
            {
              label: 'Examples',
              to: '/docs/examples',
            },
            {
              label: 'FAQ',
              to: '/docs/faq',
            },
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'Discord',
              href: 'https://discord.gg/2A5Genuh',
            },
            {
              label: 'GitHub',
              href: 'https://github.com/Kaizen-agent/kaizen-agent',
            },
            {
              label: 'Demo Video',
              href: 'https://www.loom.com/share/d3d8a5c344dc4108906d60e5c209962e',
            },
          ],
        },
        {
          title: 'Resources',
          items: [
            {
              label: 'GitHub Integration',
              to: '/docs/github',
            },
            {
              label: 'Issues',
              href: 'https://github.com/Kaizen-agent/kaizen-agent/issues',
            },
            {
              label: 'Discussions',
              href: 'https://github.com/Kaizen-agent/kaizen-agent/discussions',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Kaizen Agent. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
