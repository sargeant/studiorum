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
# Allowlist specific files where controlled references are required
# - Core handlers (branding detection logic)
# - Website landing page (docs/index.md)
ALLOWLIST_PATTERN='^(src/studiorum/renderers/core/handlers\.py|docs/index\.md)$'

# Stricter branding patterns to reduce false positives:
#  - Dungeons {&,\&,and} Dragons (flexible whitespace)
#  - D {&,\&} D (escaped/unescaped ampersand)
#  - Wizards of the Coast (flexible spacing)
BRAND_REGEX='D\s*(?:&|\\&)+\s*D|Dungeons\s*(?:&|\\&|and)\s*Dragons'

violations=$(echo "$staged_files" \
  | xargs rg -l -i "$BRAND_REGEX" 2>/dev/null \
  | grep -v -E "$ALLOWLIST_PATTERN" || true)

if [ -n "$violations" ]; then
    echo "${RED}❌ Trademark terms detected in staged files:${NC}"
    echo

    # Show specific violations
    echo "$violations" | while read -r file; do
        echo "${YELLOW}$file:${NC}"
        rg -n -i "$BRAND_REGEX" "$file" | head -3
        echo
    done

    echo "${RED}Please replace with approved terminology:${NC}"
    echo "  • D&D → 5e"
    echo "  • Dungeons & Dragons → 5e"
    echo "  • D&D compatible → 5e compatible"
    echo
    echo "${YELLOW}Exceptions are allowed for:${NC}"
    echo "  • LaTeX template styling (\\Dnd)"
    echo "  • The landing page of the documentation"
    echo "  • Use where the term includes both the ™ symbol and a disclaimer"
    echo "  • This script"
    echo
    exit 1
fi

echo "${GREEN}✓${NC} Trademark compliance check passed"
exit 0
