# GitHub Pages Setup

## 🔧 One-time Setup

Before you can deploy, you need to configure GitHub Pages:

### 1. Enable GitHub Pages

1. Go to your repository: https://github.com/Kaizen-agent/kaizen-agent
2. Click **Settings** tab
3. Scroll down to **Pages** section
4. Under **Source**, select **Deploy from a branch**
5. Choose **gh-pages** branch
6. Click **Save**

### 2. That's it!

Now you can deploy anytime with:
```bash
cd kaizen-agent-docs
./simple-deploy.sh
```

## 🎯 How it works:

- The `gh-pages` branch contains only the built documentation
- GitHub automatically serves files from this branch
- Your main code stays in the `main` branch
- No complex workflows needed!

## ✅ You're ready to deploy! 