#!/bin/bash
# ============================================
# xyvaClaw Release Script
# Usage: bash scripts/release.sh <version>
# Example: bash scripts/release.sh 1.1.0
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

if [ $# -lt 1 ]; then
    echo -e "${RED}Usage: bash scripts/release.sh <version>${NC}"
    echo "  Example: bash scripts/release.sh 1.1.0"
    echo "  Version format: MAJOR.MINOR.PATCH (without 'v' prefix)"
    exit 1
fi

VERSION="$1"
TAG="v${VERSION}"

# Validate version format
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo -e "${RED}Error: Invalid version format '${VERSION}'. Expected: MAJOR.MINOR.PATCH${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# Check we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}Error: Must be on 'main' branch (currently on '${CURRENT_BRANCH}')${NC}"
    exit 1
fi

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${YELLOW}Warning: You have uncommitted changes.${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag already exists
if git tag -l "$TAG" | grep -q "$TAG"; then
    echo -e "${RED}Error: Tag '${TAG}' already exists${NC}"
    exit 1
fi

echo -e "${BOLD}Releasing xyvaClaw ${TAG}${NC}"
echo ""

# Step 1: Update version in setup script
echo -e "${GREEN}[1/5]${NC} Updating version numbers..."
sed -i.bak "s/\"v\":\"[0-9]*\.[0-9]*\.[0-9]*\"/\"v\":\"${VERSION}\"/" "$PROJECT_DIR/xyvaclaw-setup.sh"
rm -f "$PROJECT_DIR/xyvaclaw-setup.sh.bak"
echo "  ✅ xyvaclaw-setup.sh"

# Step 2: Commit
echo -e "${GREEN}[2/5]${NC} Committing..."
git add -A
git commit -m "release: v${VERSION}" || echo "  (nothing to commit)"

# Step 3: Create tag
echo -e "${GREEN}[3/5]${NC} Creating tag ${TAG}..."
git tag -a "$TAG" -m "xyvaClaw ${TAG}"

# Step 4: Push
echo -e "${GREEN}[4/5]${NC} Pushing to origin..."
git push origin main --tags

# Step 5: Create GitHub Release via API (if GITHUB_TOKEN is set)
if [ -n "${GITHUB_TOKEN:-}" ]; then
    echo -e "${GREEN}[5/5]${NC} Creating GitHub Release..."
    RELEASE_BODY="## xyvaClaw ${TAG}\n\n### Installation\n\n\`\`\`bash\ngit clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh\n\`\`\`\n\nOr download ZIP from the assets below.\n\n### What's New\n\n- See commit history for details"

    curl -s -X POST \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/xyva-yuangui/XyvaClaw/releases" \
        -d "{
            \"tag_name\": \"${TAG}\",
            \"target_commitish\": \"main\",
            \"name\": \"xyvaClaw ${TAG}\",
            \"body\": \"${RELEASE_BODY}\",
            \"draft\": false,
            \"prerelease\": false
        }" > /dev/null

    echo "  ✅ GitHub Release created"
else
    echo -e "${YELLOW}[5/5]${NC} Skipped GitHub Release (set GITHUB_TOKEN to enable)"
    echo "  You can create it manually at:"
    echo "  https://github.com/xyva-yuangui/XyvaClaw/releases/new?tag=${TAG}"
fi

echo ""
echo -e "${GREEN}${BOLD}✅ xyvaClaw ${TAG} released successfully!${NC}"
echo ""
echo "  Tag: ${TAG}"
echo "  GitHub: https://github.com/xyva-yuangui/XyvaClaw/releases/tag/${TAG}"
