import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import useBaseUrl from '@docusaurus/useBaseUrl';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <img 
          src={useBaseUrl('/img/kaizen_logo_smaller.png')} 
          alt="Kaizen Agent Logo" 
          className={styles.heroLogo}
          width="120"
          height="120"
        />
        <Heading as="h1" className="hero__title">
          Kaizen Agent
        </Heading>
        <p className="hero__subtitle">
          Test, debug, and improve your AI agents automatically
        </p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/quickstart">
            Get Started - 5min ⏱️
          </Link>
        </div>
      </div>
    </header>
  );
}

function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          <div className="col col--6">
            <div className="text--center padding-horiz--md">
              <img 
                src={useBaseUrl('/img/undraw_docusaurus_react.svg')} 
                alt="AI Testing" 
                className={styles.featureImage}
                width="200"
                height="150"
              />
              <Heading as="h3">🤖 AI-Powered Testing</Heading>
              <p>
                Automatically test your AI agents with realistic scenarios and AI-powered evaluation.
                No test code required - just define your criteria in YAML.
              </p>
            </div>
          </div>
          <div className="col col--6">
            <div className="text--center padding-horiz--md">
              <img 
                src={useBaseUrl('/img/undraw_docusaurus_mountain.svg')} 
                alt="Automatic Fixes" 
                className={styles.featureImage}
                width="200"
                height="150"
              />
              <Heading as="h3">🔧 Automatic Fixes</Heading>
              <p>
                Kaizen analyzes failures and automatically improves your prompts and code.
                Get better results without manual debugging.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function DocumentationLinks() {
  return (
    <section className={styles.docs}>
      <div className="container">
        <div className="text--center margin-bottom--lg">
          <Heading as="h2">Documentation</Heading>
          <p>Everything you need to get started with Kaizen Agent</p>
        </div>
        <div className="row">
          <div className="col col--4">
            <div className="card">
              <div className="card__header">
                <Heading as="h3">🚀 Quick Start</Heading>
              </div>
              <div className="card__body">
                <p>Get up and running with Kaizen Agent in under 5 minutes.</p>
              </div>
              <div className="card__footer">
                <Link className="button button--primary button--block" to="/docs/quickstart">
                  Get Started
                </Link>
              </div>
            </div>
          </div>
          <div className="col col--4">
            <div className="card">
              <div className="card__header">
                <Heading as="h3">📖 Usage Guide</Heading>
              </div>
              <div className="card__body">
                <p>Learn about YAML configuration, CLI commands, and advanced features.</p>
              </div>
              <div className="card__footer">
                <Link className="button button--primary button--block" to="/docs/usage">
                  Learn More
                </Link>
              </div>
            </div>
          </div>
          <div className="col col--4">
            <div className="card">
              <div className="card__header">
                <Heading as="h3">💡 Examples</Heading>
              </div>
              <div className="card__body">
                <p>Explore real-world examples of AI agents and their test configurations.</p>
              </div>
              <div className="card__footer">
                <Link className="button button--primary button--block" to="/docs/examples">
                  View Examples
                </Link>
              </div>
            </div>
          </div>
        </div>
        <div className="row margin-top--lg">
          <div className="col col--4">
            <div className="card">
              <div className="card__header">
                <Heading as="h3">🔗 GitHub Integration</Heading>
              </div>
              <div className="card__body">
                <p>Set up automatic pull requests with fixes and improvements.</p>
              </div>
              <div className="card__footer">
                <Link className="button button--primary button--block" to="/docs/github">
                  Setup Guide
                </Link>
              </div>
            </div>
          </div>
          <div className="col col--4">
            <div className="card">
              <div className="card__header">
                <Heading as="h3">❓ FAQ</Heading>
              </div>
              <div className="card__body">
                <p>Find answers to common questions and troubleshooting tips.</p>
              </div>
              <div className="card__footer">
                <Link className="button button--primary button--block" to="/docs/faq">
                  Read FAQ
                </Link>
              </div>
            </div>
          </div>
          <div className="col col--4">
            <div className="card">
              <div className="card__header">
                <Heading as="h3">🎥 Demo Video</Heading>
              </div>
              <div className="card__body">
                <p>Watch Kaizen Agent in action with a real example.</p>
              </div>
              <div className="card__footer">
                <a className="button button--primary button--block" href="https://www.loom.com/share/d3d8a5c344dc4108906d60e5c209962e" target="_blank" rel="noopener noreferrer">
                  Watch Demo
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ExternalLinks() {
  return (
    <section className={styles.external}>
      <div className="container">
        <div className="text--center margin-bottom--lg">
          <Heading as="h2">Community & Resources</Heading>
        </div>
        <div className="row">
          <div className="col col--4">
            <div className="text--center">
              <a href="https://github.com/Kaizen-agent/kaizen-agent" target="_blank" rel="noopener noreferrer" className={styles.externalLink}>
                <Heading as="h3">📦 GitHub</Heading>
                <p>View source code, report issues, and contribute</p>
              </a>
            </div>
          </div>
          <div className="col col--4">
            <div className="text--center">
              <a href="https://discord.gg/2A5Genuh" target="_blank" rel="noopener noreferrer" className={styles.externalLink}>
                <Heading as="h3">💬 Discord</Heading>
                <p>Join our community for support and discussions</p>
              </a>
            </div>
          </div>
          <div className="col col--4">
            <div className="text--center">
              <a href="https://www.loom.com/share/d3d8a5c344dc4108906d60e5c209962e" target="_blank" rel="noopener noreferrer" className={styles.externalLink}>
                <Heading as="h3">🎬 Demo Video</Heading>
                <p>See Kaizen Agent in action</p>
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function DemoVideo() {
  return (
    <section className={styles.demo}>
      <div className="container">
        <div className="text--center margin-bottom--lg">
          <Heading as="h2">🎬 See Kaizen Agent in Action</Heading>
          <p>Watch how Kaizen Agent automatically tests and improves AI agents</p>
        </div>
        <div className={styles.workflowContainer}>
          <img 
            src="https://raw.githubusercontent.com/Kaizen-agent/kaizen-agent/main/kaizen_agent_workflow.png"
            alt="Kaizen Agent Architecture and Workflow"
            className={styles.workflowImage}
          />
        </div>
        <div className={styles.videoContainer}>
          <iframe
            src="https://www.loom.com/embed/d3d8a5c344dc4108906d60e5c209962e"
            frameBorder="0"
            allowFullScreen
            className={styles.demoVideo}
            title="Kaizen Agent Demo"
          />
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title="Kaizen Agent - AI Debugging Engineer for AI Agents"
      description="Test, debug, and improve your AI agents automatically. Kaizen Agent runs your agents, analyzes failures, and fixes code and prompts using AI.">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
        <DemoVideo />
        <DocumentationLinks />
        <ExternalLinks />
      </main>
    </Layout>
  );
}
