# GitHub Issues Workflow Guide

This document defines our workflow for using GitHub issues to drive development tasks, including metadata standards, templates, and processes for both human contributors and AI assistants.

## Overview

GitHub issues serve as our primary task management system, providing:
- Clear task definition and scope
- Progress tracking and history
- Automatic linking between code changes and requirements
- Collaborative discussion and decision-making
- Integration with GitHub's project management features

## Issue Metadata System

### Labels

#### **Type Labels** (What kind of work)
- `bug` - Something isn't working correctly
- `feature` - New functionality or capability
- `enhancement` - Improvement to existing functionality
- `documentation` - Changes to docs, README, or comments
- `testing` - Adding or improving tests
- `refactoring` - Code cleanup without functional changes
- `infrastructure` - Build, deploy, or development environment changes
- `security` - Security-related improvements or fixes

#### **Priority Labels** (How urgent)
- `P0-critical` - Blocking issue, must be fixed immediately
- `P1-high` - Important, should be addressed soon
- `P2-medium` - Normal priority, planned work
- `P3-low` - Nice to have, low priority

#### **Component Labels** (What part of the codebase)
- `component/core` - Core logic and models
- `component/cli` - Command line interface
- `component/renderers` - LaTeX/PDF rendering system
- `component/loaders` - Data loading and parsing
- `component/indexer` - Content indexing and tagging
- `component/sources` - Data source management
- `component/config` - Configuration system
- `component/tests` - Test infrastructure

#### **Size Labels** (Effort estimation)
- `size/XS` - < 1 hour (small bug fix, typo)
- `size/S` - 1-4 hours (simple feature, straightforward fix)
- `size/M` - 4-8 hours (moderate feature, complex bug)
- `size/L` - 1-2 days (large feature, major refactor)
- `size/XL` - 2+ days (epic, architectural change)

#### **Status Labels** (Current state)
- `status/ready` - Requirements clear, ready to start
- `status/in-progress` - Actively being worked on
- `status/blocked` - Cannot proceed due to external dependency
- `status/review` - Awaiting code review or feedback
- `status/needs-info` - Requires more information before proceeding

#### **Special Labels**
- `breaking-change` - Will break existing APIs or behavior
- `good-first-issue` - Suitable for new contributors
- `help-wanted` - Looking for community assistance
- `dependencies` - Related to dependency management
- `performance` - Performance optimization or concern

### Milestones

Use milestones to group related issues into releases or major features:
- `v2.1.0` - Next minor release
- `v3.0.0` - Major version with breaking changes
- `Epic: New Renderer System` - Large feature spanning multiple issues

### Projects

Use GitHub Projects for organizing work:
- **Active Sprint** - Current work in progress
- **Backlog** - Prioritized future work
- **Long-term** - Ideas and future considerations

## Issue Templates

### Bug Report Template
```markdown
## Bug Description
Brief description of the issue.

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen.

## Actual Behavior
What actually happens.

## Environment
- OS: [e.g., macOS 14.0]
- Python version: [e.g., 3.11]
- Project version: [e.g., 2.0.0]

## Additional Context
Any other relevant information.

## Acceptance Criteria
- [ ] Bug is fixed
- [ ] Test case added to prevent regression
- [ ] Documentation updated if needed
```

### Feature Request Template
```markdown
## Feature Description
Clear description of the new feature.

## Problem Statement
What problem does this solve?

## Proposed Solution
How should this work?

## Alternative Solutions
Other approaches considered.

## Implementation Notes
Technical considerations, affected files, etc.

## Acceptance Criteria
- [ ] Feature implemented as described
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] No breaking changes (or breaking changes documented)

## Files Likely to Change
- `src/core/...`
- `tests/...`
- `docs/...`
```

### Enhancement Template
```markdown
## Enhancement Description
What existing functionality should be improved?

## Current Behavior
How it works now.

## Desired Behavior
How it should work.

## Benefits
Why this improvement is valuable.

## Implementation Approach
Technical approach and considerations.

## Acceptance Criteria
- [ ] Enhancement implemented
- [ ] Existing functionality preserved
- [ ] Tests updated
- [ ] Performance impact assessed

## Affected Components
List modules/files that will change.
```

## Workflow Process

### 1. Issue Creation

**For Users:**
```bash
# Create a bug report
gh issue create --template bug_report.md --label "bug,P2-medium"

# Create a feature request
gh issue create --template feature_request.md --label "feature,P2-medium"

# Quick issue creation
gh issue create --title "Fix typo in README" --body "Line 42 has a spelling error" --label "documentation,size/XS,P3-low"
```

**Metadata to include:**
- Appropriate type label (bug, feature, etc.)
- Priority level
- Size estimate
- Component affected
- Clear acceptance criteria

### 2. Issue Triage and Planning

**Review new issues for:**
- Clear requirements and acceptance criteria
- Appropriate labels and metadata
- Dependencies on other issues
- Priority and sizing accuracy

**Add missing information:**
- Component labels based on affected code
- Size estimates for effort planning
- Dependencies if issues are related
- Milestones for release planning

### 3. Development Process

**Starting Work:**
1. Assign the issue to yourself
2. Add `status/in-progress` label
3. Create a branch if needed: `git checkout -b issue-#-short-description`

**During Development:**
- Reference the issue in commit messages: `Fix bug in data loading (refs #42)`
- Update issue with progress if it's a large task
- Ask questions in issue comments if requirements are unclear

**Completing Work:**
1. Ensure all acceptance criteria are met
2. Add/update tests as specified
3. Update documentation as needed
4. Commit with closing keywords: `Fix data validation bug (fixes #42)`
5. Push changes to close issue automatically

### 4. Code Review and Completion

**For complex changes:**
- Create pull request referencing the issue
- Request review from appropriate team members
- Add `status/review` label during review process
- Address feedback and update as needed

**Issue closure:**
- Issues close automatically when commits with `fixes #N`, `closes #N`, or `resolves #N` are pushed
- Verify acceptance criteria were met
- Add any follow-up issues if discovered

## AI Assistant (Claude) Workflow

### When Receiving Task Requests

1. **Create GitHub Issue First:**
   ```bash
   gh issue create --title "Clear task description" \
     --body "Detailed requirements and acceptance criteria" \
     --label "appropriate,labels,here"
   ```

2. **Include in Issue Description:**
   - Clear acceptance criteria
   - Files that will likely change
   - Testing requirements
   - Documentation needs
   - Any dependencies or blockers

3. **Start Development:**
   - Reference issue number in all commits
   - Follow TDD workflow when appropriate
   - Update issue with progress on complex tasks

### Commit Message Format

```
type: Brief description of change (fixes #issue-number)

- Detailed bullet points of what changed
- Why the change was made
- Any important implementation notes

Fixes #42

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Testing and Validation

Before closing issues, ensure:
- [ ] All acceptance criteria met
- [ ] Tests added/updated as required
- [ ] Code follows project standards (linting, formatting)
- [ ] Documentation updated if needed
- [ ] No regressions introduced

## Advanced Workflows

### Epic Management

For large features spanning multiple issues:

1. **Create Epic Issue:**
   - Use `Epic:` prefix in title
   - List all related sub-issues
   - Track overall progress

2. **Create Sub-Issues:**
   - Reference epic in description
   - Use consistent labeling
   - Size appropriately (prefer smaller issues)

3. **Track Progress:**
   - Use project boards
   - Update epic with completion status
   - Close epic when all sub-issues complete

### Dependencies

For dependent issues:
- Use "Depends on #X" in issue description
- Add `dependencies` label
- Don't start until dependencies complete
- Consider breaking complex dependencies into smaller pieces

### Research and Spike Issues

For investigation work:
- Use `type/research` or `type/spike` labels
- Include time-box in acceptance criteria
- Define what decisions need to be made
- Create follow-up implementation issues

## Integration with Development Tools

### GitHub CLI Commands

```bash
# List my assigned issues
gh issue list --assignee @me

# View issue details
gh issue view 42

# Create issue with template
gh issue create --template feature_request.md

# Add labels to existing issue
gh issue edit 42 --add-label "bug,P1-high"

# Close issue with comment
gh issue close 42 --comment "Completed in commit abc123"
```

### Project Board Integration

- Create automated project boards
- Set up column automation (To Do → In Progress → Done)
- Use filters for different views (by component, priority, etc.)

### Branch Naming Convention

```bash
# For issues
git checkout -b issue-42-fix-data-validation

# For features
git checkout -b feature-new-renderer-system

# For bugs
git checkout -b bug-memory-leak-in-parser
```

## Best Practices

### Issue Creation
- **Be Specific:** Clear, actionable descriptions
- **Include Context:** Why is this needed?
- **Define Success:** What does "done" look like?
- **Size Appropriately:** Break large issues into smaller ones
- **Label Consistently:** Use standard label taxonomy

### Communication
- **Update Progress:** Comment on long-running issues
- **Ask Questions:** Use issue comments for clarification
- **Link Related Work:** Reference other issues and PRs
- **Document Decisions:** Capture important discussions

### Quality
- **Test Requirements:** Specify what tests are needed
- **Documentation:** Note what docs need updating
- **Breaking Changes:** Flag API or behavior changes
- **Performance:** Consider impact on performance

## Automation Opportunities

### GitHub Actions Integration
- Auto-label issues based on content
- Auto-assign issues based on components
- Run tests when issues are marked ready
- Notify team of critical issues

### Issue Templates
- Standardize information collection
- Ensure all necessary metadata is captured
- Guide users to provide complete information

This workflow ensures that all development work is properly tracked, requirements are clear, and progress is visible to all stakeholders.