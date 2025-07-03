#!/bin/bash

echo "🚀 Manual GitHub Pages Deployment"

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the kaizen-agent-docs directory"
    exit 1
fi

# Build the documentation
echo "📦 Building documentation..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed! Please fix the errors and try again."
    exit 1
fi

echo "✅ Build successful!"

# Go to parent directory
cd ..

# Create or switch to gh-pages branch
echo "🌿 Setting up gh-pages branch..."
if git ls-remote --heads origin gh-pages | grep -q gh-pages; then
    echo "gh-pages branch exists, switching to it..."
    git checkout gh-pages
    git pull origin gh-pages
else
    echo "Creating new gh-pages branch..."
    git checkout --orphan gh-pages
fi

# Remove all files and copy build files
echo "📁 Copying built files..."
git rm -rf . || true
cp -r kaizen-agent-docs/build/* .

# Commit and push
echo "💾 Committing changes..."
git add .
git commit -m "Deploy docs to GitHub Pages"

echo "🚀 Pushing to GitHub..."
git push origin gh-pages

# Go back to main branch
git checkout main

echo "✅ Manual deployment complete!"
echo "🌐 Your site will be live at: https://kaizen-agent.github.io"
echo "⏳ It may take a few minutes for changes to appear." 