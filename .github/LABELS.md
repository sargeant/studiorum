# GitHub Labels Configuration

This document lists all the labels that need to be configured in the GitHub repository to support the issue workflow defined in `plans/ISSUES.md`.

## Type Labels (What kind of work)

| Label | Color | Description |
|-------|-------|-------------|
| `bug` | #d73a49 | Something isn't working correctly |
| `feature` | #a2eeef | New functionality or capability |
| `enhancement` | #84b6eb | Improvement to existing functionality |
| `documentation` | #0075ca | Changes to docs, README, or comments |
| `testing` | #7057ff | Adding or improving tests |
| `refactoring` | #fbca04 | Code cleanup without functional changes |
| `infrastructure` | #5319e7 | Build, deploy, or development environment changes |
| `security` | #b60205 | Security-related improvements or fixes |

## Priority Labels (How urgent)

| Label | Color | Description |
|-------|-------|-------------|
| `P0-critical` | #b60205 | Blocking issue, must be fixed immediately |
| `P1-high` | #d93f0b | Important, should be addressed soon |
| `P2-medium` | #fbca04 | Normal priority, planned work |
| `P3-low` | #0e8a16 | Nice to have, low priority |

## Component Labels (What part of the codebase)

| Label | Color | Description |
|-------|-------|-------------|
| `component/core` | #1d76db | Core logic and models |
| `component/cli` | #1d76db | Command line interface |
| `component/renderers` | #1d76db | LaTeX/PDF rendering system |
| `component/loaders` | #1d76db | Data loading and parsing |
| `component/indexer` | #1d76db | Content indexing and tagging |
| `component/sources` | #1d76db | Data source management |
| `component/config` | #1d76db | Configuration system |
| `component/tests` | #1d76db | Test infrastructure |

## Size Labels (Effort estimation)

| Label | Color | Description |
|-------|-------|-------------|
| `size/XS` | #c2e0c6 | < 1 hour (small bug fix, typo) |
| `size/S` | #7fe883 | 1-4 hours (simple feature, straightforward fix) |
| `size/M` | #fbca04 | 4-8 hours (moderate feature, complex bug) |
| `size/L` | #ff9500 | 1-2 days (large feature, major refactor) |
| `size/XL` | #d73a49 | 2+ days (epic, architectural change) |

## Status Labels (Current state)

| Label | Color | Description |
|-------|-------|-------------|
| `status/ready` | #0e8a16 | Requirements clear, ready to start |
| `status/in-progress` | #fbca04 | Actively being worked on |
| `status/blocked` | #d73a49 | Cannot proceed due to external dependency |
| `status/review` | #ff9500 | Awaiting code review or feedback |
| `status/needs-info` | #d876e3 | Requires more information before proceeding |
| `status/ai-proposed` | #8a2be2 | AI-generated issue awaiting human review and approval |

## Special Labels

| Label | Color | Description |
|-------|-------|-------------|
| `breaking-change` | #b60205 | Will break existing APIs or behavior |
| `good-first-issue` | #7057ff | Suitable for new contributors |
| `help-wanted` | #008672 | Looking for community assistance |
| `dependencies` | #0366d6 | Related to dependency management |
| `performance` | #ff6347 | Performance optimization or concern |

## GitHub CLI Commands to Create Labels

Run these commands to create all the labels in your repository:

```bash
# Type Labels
gh label create "bug" --color "d73a49" --description "Something isn't working correctly"
gh label create "feature" --color "a2eeef" --description "New functionality or capability"
gh label create "enhancement" --color "84b6eb" --description "Improvement to existing functionality"
gh label create "documentation" --color "0075ca" --description "Changes to docs, README, or comments"
gh label create "testing" --color "7057ff" --description "Adding or improving tests"
gh label create "refactoring" --color "fbca04" --description "Code cleanup without functional changes"
gh label create "infrastructure" --color "5319e7" --description "Build, deploy, or development environment changes"
gh label create "security" --color "b60205" --description "Security-related improvements or fixes"

# Priority Labels
gh label create "P0-critical" --color "b60205" --description "Blocking issue, must be fixed immediately"
gh label create "P1-high" --color "d93f0b" --description "Important, should be addressed soon"
gh label create "P2-medium" --color "fbca04" --description "Normal priority, planned work"
gh label create "P3-low" --color "0e8a16" --description "Nice to have, low priority"

# Component Labels
gh label create "component/core" --color "1d76db" --description "Core logic and models"
gh label create "component/cli" --color "1d76db" --description "Command line interface"
gh label create "component/renderers" --color "1d76db" --description "LaTeX/PDF rendering system"
gh label create "component/loaders" --color "1d76db" --description "Data loading and parsing"
gh label create "component/indexer" --color "1d76db" --description "Content indexing and tagging"
gh label create "component/sources" --color "1d76db" --description "Data source management"
gh label create "component/config" --color "1d76db" --description "Configuration system"
gh label create "component/tests" --color "1d76db" --description "Test infrastructure"

# Size Labels
gh label create "size/XS" --color "c2e0c6" --description "< 1 hour (small bug fix, typo)"
gh label create "size/S" --color "7fe883" --description "1-4 hours (simple feature, straightforward fix)"
gh label create "size/M" --color "fbca04" --description "4-8 hours (moderate feature, complex bug)"
gh label create "size/L" --color "ff9500" --description "1-2 days (large feature, major refactor)"
gh label create "size/XL" --color "d73a49" --description "2+ days (epic, architectural change)"

# Status Labels
gh label create "status/ready" --color "0e8a16" --description "Requirements clear, ready to start"
gh label create "status/in-progress" --color "fbca04" --description "Actively being worked on"
gh label create "status/blocked" --color "d73a49" --description "Cannot proceed due to external dependency"
gh label create "status/review" --color "ff9500" --description "Awaiting code review or feedback"
gh label create "status/needs-info" --color "d876e3" --description "Requires more information before proceeding"
gh label create "status/ai-proposed" --color "8a2be2" --description "AI-generated issue awaiting human review and approval"

# Special Labels
gh label create "breaking-change" --color "b60205" --description "Will break existing APIs or behavior"
gh label create "good-first-issue" --color "7057ff" --description "Suitable for new contributors"
gh label create "help-wanted" --color "008672" --description "Looking for community assistance"
gh label create "dependencies" --color "0366d6" --description "Related to dependency management"
gh label create "performance" --color "ff6347" --description "Performance optimization or concern"
```

## Notes

- These labels follow GitHub's standard color conventions where possible
- Component labels use a consistent blue color (#1d76db) for visual grouping
- Priority labels use a red-to-green gradient (critical=red, low=green)
- Size labels use a green-to-red gradient (XS=light green, XL=red)
- The `status/ai-proposed` label is specifically for AI-generated issues that need human review
- All templates automatically apply appropriate default labels via YAML frontmatter