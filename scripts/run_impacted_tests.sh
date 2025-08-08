#!/bin/bash
# Run tests impacted by current git changes
# This script analyzes changes since the main branch and runs only the affected tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the base branch (default to main)
BASE_BRANCH="${1:-main}"

echo -e "${BLUE}=== Test Impact Analysis ===${NC}"
echo "Analyzing changes since: $BASE_BRANCH"

# Get list of changed files
CHANGED_FILES=$(git diff --name-only "$BASE_BRANCH"...HEAD 2>/dev/null || git diff --name-only HEAD)

if [ -z "$CHANGED_FILES" ]; then
    echo -e "${YELLOW}No changes detected${NC}"
    exit 0
fi

echo -e "\n${BLUE}Changed files:${NC}"
echo "$CHANGED_FILES" | sed 's/^/  - /'

# Run the impact analyzer
echo -e "\n${BLUE}Analyzing test impact...${NC}"
python scripts/test_impact_analyzer.py $CHANGED_FILES

# Read the generated report
if [ -f .test-impact.json ]; then
    TOTAL_TESTS=$(python -c "import json; print(json.load(open('.test-impact.json'))['total_impacted_tests'])")

    if [ "$TOTAL_TESTS" -eq 0 ]; then
        echo -e "\n${GREEN}No tests need to be run for these changes${NC}"
        exit 0
    fi

    echo -e "\n${BLUE}Running $TOTAL_TESTS impacted tests...${NC}"

    # Extract test paths from the JSON report
    TEST_PATHS=$(python -c "import json; tests = json.load(open('.test-impact.json'))['tests_to_run']; print(' '.join(tests))")

    # Run the tests with appropriate options
    if [ "$TOTAL_TESTS" -lt 10 ]; then
        # For small test sets, show verbose output
        echo -e "${YELLOW}Running tests with verbose output...${NC}"
        uv run pytest $TEST_PATHS -v
    elif [ "$TOTAL_TESTS" -lt 50 ]; then
        # For medium test sets, use normal verbosity
        echo -e "${YELLOW}Running tests...${NC}"
        uv run pytest $TEST_PATHS
    else
        # For large test sets, use parallel execution
        echo -e "${YELLOW}Running tests in parallel...${NC}"
        uv run pytest $TEST_PATHS -n auto --dist=worksteal
    fi

    RESULT=$?

    if [ $RESULT -eq 0 ]; then
        echo -e "\n${GREEN}✓ All impacted tests passed!${NC}"
    else
        echo -e "\n${RED}✗ Some tests failed${NC}"
        exit $RESULT
    fi
else
    echo -e "${RED}Failed to generate impact analysis${NC}"
    exit 1
fi
