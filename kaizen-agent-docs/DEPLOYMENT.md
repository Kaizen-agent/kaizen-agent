# Deploying to GitHub Pages

This guide will help you deploy your Kaizen Agent documentation site to GitHub Pages.

## Prerequisites

1. Your repository is hosted on GitHub
2. You have admin access to the repository
3. GitHub Pages is enabled for your repository

## Setup Steps

### 1. Enable GitHub Pages

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Pages**
3. Under **Source**, select **GitHub Actions**
4. This will allow the workflow to deploy your site

### 2. Configure Repository Settings

Make sure your repository has the following settings:

- **Repository name**: `kaizen-agent` (should match the `projectName` in `docusaurus.config.ts`)
- **Organization**: `Kaizen-agent` (should match the `organizationName` in `docusaurus.config.ts`)

### 3. Push Your Changes

The GitHub Actions workflow will automatically trigger when you push changes to the `main` branch that affect files in the `kaizen-agent-docs/` directory:

```bash
git add .
git commit -m "Update documentation"
git push origin main
```

### 4. Monitor Deployment

1. Go to your repository on GitHub
2. Click on the **Actions** tab
3. You should see a "Deploy to GitHub Pages" workflow running
4. Wait for it to complete (usually takes 2-3 minutes)

### 5. Access Your Site

Once deployment is complete, your site will be available at:
**https://kaizen-agent.github.io**

## Manual Deployment

If you need to trigger a deployment manually:

1. Go to your repository on GitHub
2. Click on the **Actions** tab
3. Select the "Deploy to GitHub Pages" workflow
4. Click **Run workflow** → **Run workflow**

## Troubleshooting

### Common Issues

1. **Build fails**: Check the Actions logs for specific error messages
2. **Site not updating**: Clear your browser cache or wait a few minutes
3. **404 errors**: Make sure your `baseUrl` in `docusaurus.config.ts` is set to `/`

### Check Configuration

Verify these settings in `docusaurus.config.ts`:

```typescript
url: 'https://kaizen-agent.github.io',
baseUrl: '/',
organizationName: 'Kaizen-agent',
projectName: 'kaizen-agent',
```

## Local Development

To test your site locally before deploying:

```bash
cd kaizen-agent-docs
npm install
npm start
```

Visit `http://localhost:3000` to see your site.

## Build for Production

To build your site locally:

```bash
cd kaizen-agent-docs
npm run build
```

The built files will be in the `build/` directory. 