# Simple Deployment Guide

Deploy your documentation to GitHub Pages with just one command!

## 🚀 Quick Deploy

```bash
cd kaizen-agent-docs
./simple-deploy.sh
```

That's it! Your site will be live at: **https://kaizen-agent.github.io**

## 📝 What the command does:

1. **Builds** your documentation (converts markdown to HTML)
2. **Deploys** it to GitHub Pages
3. **Shows** you the URL when done

## 🔧 Manual Steps (if you prefer):

```bash
# 1. Build the docs
npm run build

# 2. Deploy to GitHub Pages
npm run deploy:gh-pages
```

## 🧪 Test Locally First:

```bash
# Start local server
npm start

# Visit http://localhost:3000
```

## ⚠️ Prerequisites:

- Make sure you have write access to the repository
- You may need to enter your GitHub credentials when deploying
- If using password auth, use a Personal Access Token instead of your password

## 🎯 That's it!

No complex GitHub Actions, no configuration files, just one simple command to deploy your docs! 