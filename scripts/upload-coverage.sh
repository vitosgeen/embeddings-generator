#!/bin/bash
# Coverage upload script with better error handling

set -e

echo "🔍 Checking for coverage files..."
if [ ! -f "coverage.xml" ]; then
    echo "❌ coverage.xml not found"
    exit 1
fi

echo "📊 Found coverage.xml, file size: $(du -h coverage.xml | cut -f1)"

if [ -n "$CODECOV_TOKEN" ]; then
    echo "🔑 Codecov token found, uploading with authentication..."
    curl -Os https://uploader.codecov.io/latest/linux/codecov
    chmod +x codecov
    ./codecov -f coverage.xml -t "$CODECOV_TOKEN"
else
    echo "⚠️  No Codecov token found, attempting upload without authentication..."
    echo "📝 Note: This may fail due to rate limiting on public repositories"
    
    # Try the action-based upload
    if command -v codecov &> /dev/null; then
        codecov -f coverage.xml || {
            echo "❌ Codecov upload failed (likely rate limited)"
            echo "💡 To fix this, add CODECOV_TOKEN to your GitHub repository secrets"
            echo "   Visit: https://app.codecov.io/gh/$(echo $GITHUB_REPOSITORY)"
            exit 0  # Don't fail the build
        }
    else
        echo "❌ Codecov CLI not found"
        exit 1
    fi
fi

echo "✅ Coverage upload completed successfully"