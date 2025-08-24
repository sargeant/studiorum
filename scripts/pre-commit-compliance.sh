#!/bin/sh
#
# Pre-commit hook to prevent trademark terms in committed files
# Place this in .git/hooks/pre-commit and make executable
#

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check for D&D trademark terms in files being committed
echo "Checking for trademark compliance..."

# Only check files that are staged for commit
staged_files=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|md|yml|yaml|toml)$')

if [ -z "$staged_files" ]; then
    echo "${GREEN}✓${NC} No relevant files to check"
    exit 0
fi

# Check for trademark violations
violations=$(echo "$staged_files" | xargs rg -l -i "d&d|dungeons.*dragons|wizards.*coast" 2>/dev/null || true)

if [ -n "$violations" ]; then
    echo "${RED}❌ Trademark terms detected in staged files:${NC}"
    echo

    # Show specific violations
    echo "$violations" | while read -r file; do
        echo "${YELLOW}$file:${NC}"
        rg -n -i "d&d|dungeons.*dragons|wizards.*coast" "$file" | head -3
        echo
    done

    echo "${RED}Please replace with approved terminology:${NC}"
    echo "  • D&D → 5e"
    echo "  • Dungeons & Dragons → 5e"
    echo "  • D&D compatible → 5e compatible"
    echo
    echo "${YELLOW}Exceptions are allowed for:${NC}"
    echo "  • LaTeX template styling (\\Dnd)"
    echo "  • CSS aesthetic references"
    echo
    exit 1
fi

echo "${GREEN}✓${NC} Trademark compliance check passed"
exit 0
